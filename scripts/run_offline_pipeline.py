"""
Offline ERIS pipeline: Gu, Kelly & Xiu course data.
1. Load parquet panel (Data1)
2. Expanding-window validation
3. Baseline models (OLS, Ridge, RF, XGBoost)
4. Regime-Aware NN
5. Regime detection (HMM on macro) + stress index
6. Portfolio (decile long-short, cumulative returns, Sharpe)
7. SHAP and feature importance by regime
8. Save artifacts for dashboard (data/processed/course/)
Run from project root: python scripts/run_offline_pipeline.py
"""

import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = PROJECT_ROOT / "data" / "processed" / "course"

TOTAL_STEPS = 8
STEP_NAMES = [
    "Load panel (Data1)",
    "Baseline models (expanding window)",
    "Regime-Aware NN",
    "Regime detection (HMM) + stress index",
    "Portfolio (decile long-short)",
    "SHAP by regime",
    "Save artifacts",
]


def load_config() -> dict:
    with open(PROJECT_ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _remaining(current: int) -> str:
    left = TOTAL_STEPS - current
    return f"({left} step{'s' if left != 1 else ''} left after this)"


def _elapsed(start: float) -> str:
    s = time.time() - start
    if s < 60:
        return f"{s:.0f}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m:.0f}m {s:.0f}s"
    h, m = divmod(m, 60)
    return f"{h:.0f}h {m:.0f}m {s:.0f}s"


def main() -> None:
    pipeline_start = time.time()
    cfg = load_config()
    course_cfg = cfg.get("course", {})
    first_pred = course_cfg.get("first_prediction_year", 2010)
    macro_cols_cfg = course_cfg.get("macro_cols", [])
    retrain_baselines = course_cfg.get("retrain_baselines_every", 3)
    retrain_nn = course_cfg.get("retrain_nn_every", 6)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=== ERIS Offline Pipeline ===")
    logger.info("Total steps: %d. %s", TOTAL_STEPS, " | ".join(f"%d=%s" % (i + 1, STEP_NAMES[i]) for i in range(min(7, len(STEP_NAMES)))))
    logger.info("")

    # 1. Load panel
    step_start = time.time()
    logger.info("[Step 1/8] Loading course panel from Data1... %s", _remaining(1))
    from data.loaders.course_data import load_course_panel, get_feature_columns

    try:
        panel = load_course_panel()
    except FileNotFoundError as e:
        logger.error("%s", e)
        logger.info("Place parquet files (e.g. 200101.parquet) in Data1/ and re-run.")
        return
    logger.info("  -> Panel shape: %s (done in %s)", panel.shape, _elapsed(step_start))

    cols = get_feature_columns(panel)
    feature_cols = cols["all_features"]
    macro_cols = cols["macro"] or macro_cols_cfg
    char_cols = cols["characteristic"]
    if not macro_cols and macro_cols_cfg:
        macro_cols = [c for c in macro_cols_cfg if c in panel.columns]
    if not feature_cols:
        logger.error("No feature columns (macro_*, characteristic_*, sic2_*) found.")
        return

    # 2 & 3. Baselines (expanding window)
    step_start = time.time()
    logger.info("[Step 2/8] Baseline models (expanding window)... %s", _remaining(2))
    from ml.baselines import run_expanding_window_baselines

    def baseline_progress(current: int, total: int, month_label: str) -> None:
        pct = 100 * current / total if total else 0
        # Log every 12 months (yearly) or at start/end
        if current == 1 or current == total or current % 12 == 0:
            logger.info("  -> OOS month %d/%d (%s) — %.1f%%", current, total, month_label, pct)

    # Matches ERIS_Optimized_Pipeline: OLS, Ridge, XGBoost, LightGBM (no RF)
    model_list = ["OLS", "Ridge", "XGBoost", "LightGBM"]
    predictions_df, baseline_metrics = run_expanding_window_baselines(
        panel, feature_cols, first_prediction_year=first_pred, model_names=model_list,
        progress_callback=baseline_progress,
        retrain_every=retrain_baselines,
    )
    logger.info("  -> Baseline OOS R²: %s (done in %s)", {k: round(v["oos_r2"], 4) for k, v in baseline_metrics.items()}, _elapsed(step_start))

    # 4. Regime-Aware NN (if we have macro + char)
    if macro_cols and char_cols:
        step_start = time.time()
        logger.info("[Step 3/8] Regime-Aware NN (expanding window)... %s", _remaining(3))
        from ml.regime_aware_nn import run_expanding_window_regime_nn

        def nn_progress(current: int, total: int, month_label: str) -> None:
            pct = 100 * current / total if total else 0
            if current == 1 or current == total or current % 12 == 0:
                logger.info("  -> OOS month %d/%d (%s) — %.1f%%", current, total, month_label, pct)

        try:
            nn_pred, nn_metrics = run_expanding_window_regime_nn(
                panel, macro_cols, char_cols, first_prediction_year=first_pred, epochs=30,
                progress_callback=nn_progress,
                retrain_every=retrain_nn,
            )
            predictions_df = predictions_df.merge(
                nn_pred[["month_dt", "permno", "pred_RegimeNN"]],
                on=["month_dt", "permno"],
                how="left",
            )
            baseline_metrics.update(nn_metrics)
            logger.info("  -> Regime NN OOS R²: %s (done in %s)", nn_metrics.get("RegimeNN", {}).get("oos_r2"), _elapsed(step_start))
        except Exception as e:
            logger.warning("Regime NN failed: %s", e)

    # 5. Regime + stress
    step_start = time.time()
    logger.info("[Step 4/8] Regime detection (HMM) + stress index... %s", _remaining(4))
    from ml.regime_detection import run_regime_and_stress
    regime_df, macro_monthly = run_regime_and_stress(panel, macro_cols)
    # Ensure month_dt is serializable (Period -> str)
    for _df in (regime_df, macro_monthly):
        if "month_dt" in _df.columns:
            _df["month_dt"] = _df["month_dt"].astype(str)
    regime_df.to_parquet(OUT_DIR / "regime_states.parquet", index=False)
    macro_monthly.to_parquet(OUT_DIR / "macro_monthly.parquet", index=False)
    logger.info("  -> Done in %s", _elapsed(step_start))

    # 6. Portfolio (use best model or XGBoost)
    step_start = time.time()
    logger.info("[Step 5/8] Portfolio (decile long-short)... %s", _remaining(5))
    from ml.portfolio import portfolio_metrics
    pred_col = "pred_XGBoost" if "pred_XGBoost" in predictions_df.columns else f"pred_{model_list[0]}"
    port_df, port_metrics = portfolio_metrics(predictions_df, panel, pred_col=pred_col)
    port_df = port_df.copy()
    port_df["month_dt"] = port_df["month_dt"].astype(str)
    port_df.to_parquet(OUT_DIR / "portfolio_returns.parquet", index=False)
    logger.info("  -> Sharpe=%.3f, MaxDD=%.3f, Alpha=%.4f (done in %s)", port_metrics["sharpe_ratio"], port_metrics["max_drawdown"], port_metrics["annualized_alpha"], _elapsed(step_start))

    # Regime-conditional OOS R² (for understanding rubric)
    from ml.validation import regime_conditional_r2
    pred_col_used = pred_col
    regime_cond_r2 = regime_conditional_r2(predictions_df, regime_df, pred_col=pred_col_used, month_col="month_dt")
    if regime_cond_r2:
        logger.info("  -> Regime-conditional R²: %s", regime_cond_r2)

    # 7. SHAP / importance by regime
    step_start = time.time()
    logger.info("[Step 6/8] SHAP and feature importance by regime... %s", _remaining(6))
    from ml.baselines import get_xgb_model
    from ml.interpretability import feature_importance_by_regime
    importance_by_regime = {}
    def shap_progress(current: int, total: int, regime_name: str) -> None:
        logger.info("  -> Regime %d/%d: %s", current, total, regime_name)
    try:
        importance_by_regime = feature_importance_by_regime(
            panel, predictions_df, feature_cols, regime_df,
            model_builder=get_xgb_model,
            pred_col=pred_col,
            progress_callback=shap_progress,
        )
        for reg, df in importance_by_regime.items():
            df.to_csv(OUT_DIR / f"shap_importance_{reg}.csv", index=False)
        logger.info("  -> Done in %s", _elapsed(step_start))
    except Exception as e:
        logger.warning("SHAP by regime failed: %s", e)

    # 8. Save artifacts (convert period to str for parquet)
    step_start = time.time()
    logger.info("[Step 7/8] Saving artifacts... %s", _remaining(7))
    out_pred = predictions_df.copy()
    if "month_dt" in out_pred.columns:
        out_pred["month_dt"] = out_pred["month_dt"].astype(str)
    out_pred.to_parquet(OUT_DIR / "predictions.parquet", index=False)
    with open(OUT_DIR / "metrics.json", "w") as f:
        json.dump({
            "baseline_metrics": baseline_metrics,
            "portfolio_metrics": port_metrics,
            "regime_conditional_r2": regime_cond_r2 if regime_cond_r2 else {},
        }, f, indent=2)
    with open(OUT_DIR / "feature_columns.json", "w") as f:
        json.dump({"all_features": feature_cols, "macro": macro_cols, "characteristic": char_cols}, f, indent=2)
    logger.info("  -> Done in %s", _elapsed(step_start))

    logger.info("")
    logger.info("[Step 8/8] Pipeline complete.")
    logger.info("Total time: %s", _elapsed(pipeline_start))
    logger.info("Artifacts in %s", OUT_DIR)
    logger.info("Next: run python scripts/export_dashboard_data.py then open dashboard/index.html (or serve dashboard/ with a local server) for the web dashboard.")


if __name__ == "__main__":
    main()
