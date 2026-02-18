"""
Interpretability: SHAP on XGBoost, feature importance by regime.
"""

from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd


def shap_importance(
    model: object,
    X: np.ndarray,
    feature_names: List[str],
    n_samples: int = 2000,
) -> pd.DataFrame:
    """
    Compute SHAP feature importance (mean |SHAP|) for tree model.
    Subsamples X if n_samples < len(X). Returns DataFrame with feature, importance.
    """
    try:
        import shap
    except ImportError:
        return pd.DataFrame({"feature": feature_names, "importance": 0.0})

    if len(X) > n_samples:
        idx = np.random.RandomState(42).choice(len(X), n_samples, replace=False)
        X = X[idx]
    try:
        explainer = shap.TreeExplainer(model)
        sh = explainer.shap_values(X)
    except Exception:
        try:
            explainer = shap.Explainer(model, X, feature_names=feature_names)
            sh = explainer.shap_values(X)
        except Exception:
            return pd.DataFrame({"feature": feature_names, "importance": 0.0})
    if isinstance(sh, list):
        sh = sh[0]
    imp = np.abs(sh).mean(axis=0)
    return pd.DataFrame({"feature": feature_names, "importance": imp}).sort_values("importance", ascending=False)


def feature_importance_by_regime(
    panel: pd.DataFrame,
    predictions_df: pd.DataFrame,
    feature_cols: List[str],
    regime_df: pd.DataFrame,
    model_builder,
    pred_col: str = "pred_XGBoost",
    target_col: str = "ret_excess",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, pd.DataFrame]:
    """
    For each regime (Bull, Bear, Transition), fit model on that subset and compute SHAP importance.
    Returns dict regime_label -> DataFrame(feature, importance).
    """
    from ml.validation import ExpandingWindowSplit

    splitter = ExpandingWindowSplit(first_prediction_year=2010)
    # Merge regime into predictions so we have regime per (month_dt, permno)
    pred_with_regime = predictions_df.merge(
        regime_df[["month_dt", "regime_label"]],
        on="month_dt",
        how="left",
    )
    importance_by_regime = {}
    regimes = list(pred_with_regime["regime_label"].dropna().unique())
    total_regimes = len(regimes)
    for reg_idx, regime in enumerate(regimes):
        if progress_callback:
            progress_callback(reg_idx + 1, total_regimes, str(regime))
        sub = pred_with_regime[pred_with_regime["regime_label"] == regime]
        months = sub["month_dt"].unique()
        if len(months) < 12:
            continue
        sub_panel = panel[panel["month_dt"].isin(months)]
        if len(sub_panel) < 500:
            continue
        X = sub_panel[feature_cols].values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        y = sub_panel[target_col].values
        model = model_builder()
        if model is None:
            continue
        model.fit(X, y)
        # Tree model: get underlying estimator for SHAP (SklearnBaseline wraps .model)
        tree_model = getattr(model, "model", model)
        imp_df = shap_importance(tree_model, X, feature_cols, n_samples=min(2000, len(X)))
        importance_by_regime[str(regime)] = imp_df
    return importance_by_regime
