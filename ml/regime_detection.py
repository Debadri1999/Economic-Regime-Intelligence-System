"""
Regime detection from course data: HMM on macro variables, stress index.
Labels: bull/expansion, bear/recession, transition.
Stress index: weighted combination of term spread, default spread, stock variance.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_config() -> dict:
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fit_regime_hmm(
    macro_df: pd.DataFrame,
    macro_cols: List[str],
    n_states: int = 3,
    n_iter: int = 100,
) -> Tuple[Optional[object], np.ndarray, pd.DataFrame]:
    """
    Fit Gaussian HMM on macro time series (one row per month).
    macro_df: DataFrame with month index and macro_cols.
    Returns (fitted_hmm, state_sequence, regime_df with month_dt, regime_label, hmm_state).
    """
    try:
        from hmmlearn import hmm
    except ImportError:
        return None, np.array([]), pd.DataFrame()

    X = macro_df[macro_cols].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    # Z-score for stability
    X = (X - np.nanmean(X, axis=0)) / (np.nanstd(X, axis=0) + 1e-8)
    model = hmm.GaussianHMM(n_components=n_states, covariance_type="full", n_iter=n_iter, random_state=42)
    model.fit(X)
    states = model.predict(X)
    # Label by mean of first macro (e.g. dp): low = bull, high = bear
    means_per_state = []
    for s in range(n_states):
        mask = states == s
        means_per_state.append(np.mean(X[mask, 0]) if mask.any() else 0)
    order = np.argsort(means_per_state)
    # Map: 0 -> bull, 1 -> transition, 2 -> bear (or similar)
    state_to_label = {order[0]: "Bull", order[1]: "Transition", order[2]: "Bear"}
    labels = [state_to_label.get(s, "Transition") for s in states]
    months = macro_df.index
    if hasattr(months, "to_timestamp"):
        months = months.to_timestamp()
    regime_df = pd.DataFrame({
        "month_dt": months,
        "hmm_state": states,
        "regime_label": labels,
    })
    return model, states, regime_df


def compute_stress_index(
    macro_df: pd.DataFrame,
    weights: Optional[dict] = None,
) -> pd.Series:
    """
    Stress index from macro_tms (term spread), macro_dfy (default spread), macro_svar (stock var).
    Negative term spread = inverted curve = stress. High dfy, high svar = stress.
    Weights from config or default: tms -1, dfy 1, svar 1. Result normalized to rough 0-100 scale.
    """
    cfg = _get_config()
    w = weights or cfg.get("course", {}).get("stress_weights", {}) or {
        "macro_tms": -1.0,
        "macro_dfy": 1.0,
        "macro_svar": 1.0,
    }
    series = []
    for col, coef in w.items():
        if col in macro_df.columns:
            s = macro_df[col].fillna(0)
            series.append(coef * s)
    if not series:
        return pd.Series(0.0, index=macro_df.index)
    combined = series[0]
    for s in series[1:]:
        combined = combined + s
    # Normalize to 0-100 (percentile-based)
    combined = (combined - combined.min()) / (combined.max() - combined.min() + 1e-8) * 100
    return combined


def run_regime_and_stress(
    panel: pd.DataFrame,
    macro_cols: List[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aggregate panel to one row per month (macro is same for all permnos).
    Fit HMM, compute stress index. Return (regime_df, macro_monthly with stress).
    """
    # One row per month: take first permno's macro (they're identical)
    monthly = panel.groupby("month_dt").agg({c: "first" for c in macro_cols}).reset_index()
    macro_df = monthly.set_index("month_dt")[macro_cols]
    stress = compute_stress_index(monthly.set_index("month_dt"))
    model, states, regime_df = fit_regime_hmm(macro_df, macro_cols, n_states=3)
    regime_df = regime_df.reset_index(drop=True)
    # Align stress (same index order as macro_df)
    stress_aligned = stress.reindex(macro_df.index).fillna(0)
    regime_df["stress_index"] = stress_aligned.values
    macro_monthly = monthly.copy()
    macro_monthly["stress_index"] = stress.values
    return regime_df, macro_monthly
