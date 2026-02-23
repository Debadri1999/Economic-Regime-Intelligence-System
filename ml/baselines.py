"""
Baseline models for monthly return prediction (Gu, Kelly & Xiu style).
OLS, Ridge/Lasso/ElasticNet, Random Forest, XGBoost/LightGBM.
All used with expanding-window validation (no look-ahead).
"""

from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, Lasso, ElasticNet, LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# Optional XGBoost / LightGBM
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False


def _safe_fill(X: np.ndarray) -> np.ndarray:
    """Replace remaining NaN/Inf with 0."""
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X


class SklearnBaseline:
    """Wrapper for sklearn-style fit/predict with optional scaling."""

    def __init__(self, model: Any, scale: bool = True):
        self.model = model
        self.scale = scale
        self.scaler = StandardScaler() if scale else None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SklearnBaseline":
        X = _safe_fill(X)
        y = np.asarray(y).ravel()
        if self.scaler is not None:
            X = self.scaler.fit_transform(X)
        self.model.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = _safe_fill(X)
        if self.scaler is not None:
            X = self.scaler.transform(X)
        return self.model.predict(X)


def get_ols_model() -> SklearnBaseline:
    return SklearnBaseline(LinearRegression(), scale=True)


def get_ridge_model(alpha: float = 1.0) -> SklearnBaseline:
    return SklearnBaseline(Ridge(alpha=alpha), scale=True)


def get_lasso_model(alpha: float = 0.001) -> SklearnBaseline:
    return SklearnBaseline(Lasso(alpha=alpha), scale=True)


def get_elasticnet_model(alpha: float = 0.001, l1_ratio: float = 0.5) -> SklearnBaseline:
    return SklearnBaseline(ElasticNet(alpha=alpha, l1_ratio=l1_ratio), scale=True)


def get_rf_model(n_estimators: int = 100, max_depth: int = 8) -> SklearnBaseline:
    return SklearnBaseline(
        RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42),
        scale=False,
    )


def get_xgb_model(
    n_estimators: int = 100,
    max_depth: int = 6,
    learning_rate: float = 0.05,
) -> Optional[SklearnBaseline]:
    if not HAS_XGB:
        return None
    return SklearnBaseline(
        xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
        ),
        scale=False,
    )


def get_lgb_model(
    n_estimators: int = 100,
    max_depth: int = 6,
    learning_rate: float = 0.05,
) -> Optional[SklearnBaseline]:
    if not HAS_LGB:
        return None
    return SklearnBaseline(
        lgb.LGBMRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
        ),
        scale=False,
    )


def run_expanding_window_baselines(
    panel: pd.DataFrame,
    feature_cols: List[str],
    target_col: str = "ret_excess",
    first_prediction_year: int = 2010,
    model_names: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    retrain_every: int = 1,
) -> tuple:
    """
    Run expanding-window prediction for baseline models.
    Returns (predictions_df, metrics_dict).
    predictions_df has columns: month_dt, permno, ret_excess, pred_OLS, pred_Ridge, ...
    metrics_dict: { "OLS": {"oos_r2": ...}, "Ridge": {...}, ... }
    """
    from ml.validation import ExpandingWindowSplit, oos_r2, oos_rmse, oos_mae

    splitter = ExpandingWindowSplit(first_prediction_year=first_prediction_year)
    model_names = model_names or ["OLS", "Ridge", "RF", "XGBoost"]
    builders = {
        "OLS": get_ols_model,
        "Ridge": lambda: get_ridge_model(alpha=1.0),
        "Lasso": lambda: get_lasso_model(alpha=0.001),
        "ElasticNet": lambda: get_elasticnet_model(alpha=0.001),
        "RF": lambda: get_rf_model(n_estimators=100, max_depth=8),
        "XGBoost": get_xgb_model,
        "LightGBM": get_lgb_model,
    }
    models = {}
    for name in model_names:
        if name in builders:
            m = builders[name]()
            if m is not None:
                models[name] = m

    id_cols = ["month_dt", "permno"]
    if "mktcap_lag" in panel.columns:
        id_cols.append("mktcap_lag")
    pred_dfs = []
    all_preds = {n: [] for n in models}
    all_y = []
    all_month = []
    all_permno = []
    all_mktcap = []

    pred_months = list(splitter.get_prediction_months(panel))
    total_months = len(pred_months)

    for idx, (train, test) in enumerate(splitter.split(panel)):
        if progress_callback and total_months:
            month_label = str(pred_months[idx]) if idx < len(pred_months) else ""
            progress_callback(idx + 1, total_months, month_label)
        X_train = train[feature_cols].values
        y_train = train[target_col].values
        X_test = test[feature_cols].values
        y_test = test[target_col].values

        # Quarterly retrain (retrain_every=3): matches ERIS_Optimized_Pipeline.ipynb
        if idx % retrain_every == 0:
            for name, model in models.items():
                model.fit(X_train, y_train)

        for name, model in models.items():
            preds = model.predict(X_test)
            all_preds[name].extend(preds)

        all_y.extend(y_test)
        all_month.extend(test["month_dt"].tolist())
        all_permno.extend(test["permno"].tolist())
        if "mktcap_lag" in test.columns:
            all_mktcap.extend(test["mktcap_lag"].tolist())

    # Build predictions DataFrame
    out = pd.DataFrame({
        "month_dt": all_month,
        "permno": all_permno,
        "ret_excess": all_y,
    })
    if all_mktcap:
        out["mktcap_lag"] = all_mktcap
    for name in models:
        out[f"pred_{name}"] = all_preds[name]

    # Metrics per model: OOS R², RMSE, MAE
    metrics = {}
    y_true = np.array(all_y)
    for name in models:
        y_pred = np.array(all_preds[name])
        metrics[name] = {
            "oos_r2": oos_r2(y_true, y_pred),
            "oos_rmse": oos_rmse(y_true, y_pred),
            "oos_mae": oos_mae(y_true, y_pred),
        }

    return out, metrics
