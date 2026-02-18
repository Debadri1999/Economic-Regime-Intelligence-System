"""
Regime-Aware Neural Network: macro -> regime embedding; characteristics + embedding -> ret_excess.
Conditional modeling so the relationship between characteristics and returns can vary by regime.
"""

from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def _get_config() -> dict:
    import yaml
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


if HAS_TORCH:

    class RegimeEncoder(nn.Module):
        """Macro (8) -> regime embedding (embed_dim)."""

        def __init__(self, macro_dim: int, embed_dim: int = 16, hidden: int = 32):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(macro_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, embed_dim),
                nn.ReLU(),
            )
            self.embed_dim = embed_dim

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)

    class RegimeAwareNet(nn.Module):
        """
        Two-headed: Regime Encoder(macro) -> embedding;
        Return Predictor(characteristics + industry + embedding) -> ret_excess.
        """

        def __init__(
            self,
            macro_dim: int,
            char_dim: int,
            embed_dim: int = 16,
            hidden_regime: int = 32,
            hidden_return: int = 64,
        ):
            super().__init__()
            self.regime_encoder = RegimeEncoder(macro_dim, embed_dim=embed_dim, hidden=hidden_regime)
            input_return = char_dim + embed_dim
            self.return_predictor = nn.Sequential(
                nn.Linear(input_return, hidden_return),
                nn.ReLU(),
                nn.Linear(hidden_return, hidden_return // 2),
                nn.ReLU(),
                nn.Linear(hidden_return // 2, 1),
            )

        def forward(
            self,
            macro: torch.Tensor,
            char: torch.Tensor,
        ) -> torch.Tensor:
            emb = self.regime_encoder(macro)
            x = torch.cat([char, emb], dim=1)
            return self.return_predictor(x).squeeze(-1)


def get_regime_aware_model(
    macro_dim: int,
    char_dim: int,
    embed_dim: int = 16,
) -> Optional["RegimeAwareNet"]:
    if not HAS_TORCH:
        return None
    return RegimeAwareNet(
        macro_dim=macro_dim,
        char_dim=char_dim,
        embed_dim=embed_dim,
    )


def train_regime_aware_nn(
    X_macro: np.ndarray,
    X_char: np.ndarray,
    y: np.ndarray,
    epochs: int = 50,
    lr: float = 1e-3,
    batch_size: int = 2048,
    device: Optional[str] = None,
) -> Tuple[Optional[object], List[float]]:
    """
    Train RegimeAwareNet. X_macro (n, 8), X_char (n, n_char), y (n,).
    Returns (model, loss_history).
    """
    if not HAS_TORCH:
        return None, []
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    X_macro = _safe_array(X_macro)
    X_char = _safe_array(X_char)
    y = np.asarray(y, dtype=np.float32).ravel()

    model = RegimeAwareNet(
        macro_dim=X_macro.shape[1],
        char_dim=X_char.shape[1],
        embed_dim=16,
    ).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    n = len(y)
    indices = np.arange(n)
    losses = []
    for ep in range(epochs):
        np.random.shuffle(indices)
        epoch_loss = 0.0
        for start in range(0, n, batch_size):
            idx = indices[start : start + batch_size]
            m = torch.from_numpy(X_macro[idx]).float().to(device)
            c = torch.from_numpy(X_char[idx]).float().to(device)
            t = torch.from_numpy(y[idx]).float().to(device)
            opt.zero_grad()
            out = model(m, c)
            loss = criterion(out, t)
            loss.backward()
            opt.step()
            epoch_loss += loss.item()
        losses.append(epoch_loss / max(1, n // batch_size))
    return model, losses


def predict_regime_aware_nn(
    model: object,
    X_macro: np.ndarray,
    X_char: np.ndarray,
    device: Optional[str] = None,
) -> np.ndarray:
    if not HAS_TORCH or model is None:
        return np.zeros(len(X_macro))
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()
    X_macro = _safe_array(X_macro)
    X_char = _safe_array(X_char)
    with torch.no_grad():
        m = torch.from_numpy(X_macro).float().to(device)
        c = torch.from_numpy(X_char).float().to(device)
        pred = model(m, c)
    return pred.cpu().numpy()


def _safe_array(X: np.ndarray) -> np.ndarray:
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    return X


def run_expanding_window_regime_nn(
    panel: pd.DataFrame,
    macro_cols: List[str],
    char_cols: List[str],
    target_col: str = "ret_excess",
    first_prediction_year: int = 2010,
    epochs: int = 30,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[pd.DataFrame, dict]:
    """
    Expanding-window train/predict with RegimeAwareNet.
    Returns (predictions_df with month_dt, permno, ret_excess, pred_RegimeNN), metrics.
    """
    from ml.validation import ExpandingWindowSplit, oos_r2

    splitter = ExpandingWindowSplit(first_prediction_year=first_prediction_year)
    pred_months = list(splitter.get_prediction_months(panel))
    total_months = len(pred_months)
    all_month = []
    all_permno = []
    all_y = []
    all_mktcap = []
    all_pred = []
    trained_models = []

    for idx, (train, test) in enumerate(splitter.split(panel)):
        if progress_callback and total_months:
            month_label = str(pred_months[idx]) if idx < len(pred_months) else ""
            progress_callback(idx + 1, total_months, month_label)
        X_macro_train = train[macro_cols].values
        X_char_train = train[char_cols].values
        y_train = train[target_col].values
        X_macro_test = test[macro_cols].values
        X_char_test = test[char_cols].values
        y_test = test[target_col].values

        model, _ = train_regime_aware_nn(
            X_macro_train, X_char_train, y_train,
            epochs=epochs, batch_size=2048,
        )
        if model is None:
            all_pred.extend(np.zeros(len(y_test)))
        else:
            preds = predict_regime_aware_nn(model, X_macro_test, X_char_test)
            all_pred.extend(preds)
            trained_models.append(model)

        all_y.extend(y_test)
        all_month.extend(test["month_dt"].tolist())
        all_permno.extend(test["permno"].tolist())
        if "mktcap_lag" in test.columns:
            all_mktcap.extend(test["mktcap_lag"].tolist())

    out = pd.DataFrame({
        "month_dt": all_month,
        "permno": all_permno,
        "ret_excess": all_y,
        "pred_RegimeNN": all_pred,
    })
    if all_mktcap:
        out["mktcap_lag"] = all_mktcap
    metrics = {"RegimeNN": {"oos_r2": oos_r2(np.array(all_y), np.array(all_pred))}}
    return out, metrics
