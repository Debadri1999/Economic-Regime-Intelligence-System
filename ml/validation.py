"""
Expanding-window validation for time series. No random split — no look-ahead bias.
Train on all data up to month t-1, predict month t; roll forward.
"""

from pathlib import Path
from typing import Generator, List, Optional, Tuple

import pandas as pd
import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_config() -> dict:
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ExpandingWindowSplit:
    """
    Expanding window: for each prediction month t, training set is all months < t.
    First prediction month is set in config (e.g. 2010).
    """

    def __init__(
        self,
        first_prediction_year: int = 2010,
        month_col: str = "month_dt",
    ):
        cfg = _get_config()
        course = cfg.get("course", {})
        self.first_prediction_year = course.get("first_prediction_year", first_prediction_year)
        self.month_col = month_col

    def split(
        self,
        panel: pd.DataFrame,
    ) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
        """
        Yields (train_df, test_df) for each out-of-sample month.
        train_df: all rows with month_dt < pred_month
        test_df: all rows with month_dt == pred_month
        """
        if self.month_col not in panel.columns:
            raise ValueError(f"Panel must have column {self.month_col}")
        months = panel[self.month_col].drop_duplicates().sort_values()
        # Prediction months: first month where year >= first_prediction_year
        pred_months = months[months.dt.year >= self.first_prediction_year]
        for m in pred_months:
            train = panel[panel[self.month_col] < m]
            test = panel[panel[self.month_col] == m]
            if train.empty or test.empty:
                continue
            yield train, test

    def get_prediction_months(self, panel: pd.DataFrame) -> pd.PeriodIndex:
        """Return the list of months we predict (OOS)."""
        months = panel[self.month_col].drop_duplicates().sort_values()
        return months[months.dt.year >= self.first_prediction_year]

    def train_test_split_single(
        self,
        panel: pd.DataFrame,
        pred_month: pd.Period,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Single split: train on all < pred_month, test on pred_month."""
        train = panel[panel[self.month_col] < pred_month]
        test = panel[panel[self.month_col] == pred_month]
        return train, test


def oos_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Out-of-sample R²: 1 - SS_res / SS_tot."""
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1 - ss_res / ss_tot)


def regime_conditional_r2(
    predictions_df: pd.DataFrame,
    regime_df: pd.DataFrame,
    pred_col: str = "pred_XGBoost",
    ret_col: str = "ret_excess",
    month_col: str = "month_dt",
    regime_col: str = "regime_label",
) -> dict:
    """
    Compute OOS R² per regime (Bull, Bear, Transition). Returns dict model_name -> { regime -> r2 }.
    """
    left = predictions_df[[month_col, ret_col] + [c for c in predictions_df.columns if c.startswith("pred_")]].copy()
    left[month_col] = left[month_col].astype(str)
    right = regime_df[[month_col, regime_col]].drop_duplicates()
    right[month_col] = right[month_col].astype(str)
    merged = left.merge(right, on=month_col, how="left")
    if merged[regime_col].isna().all():
        return {}
    out = {}
    for model in [c.replace("pred_", "") for c in merged.columns if c.startswith("pred_")]:
        pcol = f"pred_{model}"
        if pcol not in merged.columns:
            continue
        by_regime = {}
        for reg in merged[regime_col].dropna().unique():
            sub = merged[merged[regime_col] == reg]
            if len(sub) < 100:
                continue
            y_true = sub[ret_col].values
            y_pred = sub[pcol].values
            by_regime[str(reg)] = round(oos_r2(y_true, y_pred), 6)
        if by_regime:
            out[model] = by_regime
    return out
