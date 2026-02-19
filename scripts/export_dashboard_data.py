"""
Export pipeline outputs to dashboard/data/*.json for the static web dashboard.
Run after run_offline_pipeline.py. From project root: python scripts/export_dashboard_data.py
Supports both data/processed/course/ (pipeline) and results/ (ERIS_Optimized_Pipeline.ipynb).
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COURSE_DIR = PROJECT_ROOT / "data" / "processed" / "course"
RESULTS_DIR = PROJECT_ROOT / "results"
DASHBOARD_DATA = PROJECT_ROOT / "dashboard" / "data"


def _find_data_dir():
    """Prefer results/ (notebook) then data/processed/course/ (pipeline)."""
    if (RESULTS_DIR / "metrics.json").exists():
        return RESULTS_DIR
    if (RESULTS_DIR / "predictions.parquet").exists() and not (RESULTS_DIR / "metrics.json").exists():
        return RESULTS_DIR
    return COURSE_DIR


def main():
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    src = _find_data_dir()

    # 1. Metrics (baseline_metrics or model_metrics + portfolio_metrics)
    metrics_path = src / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            data = json.load(f)
        # Normalize: model_metrics (notebook) -> baseline_metrics for dashboard compat
        if "model_metrics" in data and "baseline_metrics" not in data:
            data["baseline_metrics"] = data["model_metrics"]
        # portfolio_metrics: notebook may nest per model; use first or single
        pm = data.get("portfolio_metrics")
        if isinstance(pm, dict) and any(k.startswith("portfolio_") for k in pm.keys()):
            # e.g. {"portfolio_XGBoost": {...}} -> use first
            first = next((v for k, v in pm.items() if isinstance(v, dict)), pm)
            data["portfolio_metrics"] = first if isinstance(first, dict) else pm
        with open(DASHBOARD_DATA / "metrics.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Exported metrics.json")

    # 2. Portfolio returns (cumulative chart)
    port_path = src / "portfolio_returns.parquet"
    if not port_path.exists() and src == RESULTS_DIR:
        # Notebook writes portfolio_XGBoost.parquet etc.
        for p in RESULTS_DIR.glob("portfolio_*.parquet"):
            port_path = p
            break
    if port_path and port_path.exists():
        try:
            import pandas as pd
            df = pd.read_parquet(port_path)
            if "cum_ret_strategy" in df.columns and "cum_strategy" not in df.columns:
                df["cum_strategy"] = df["cum_ret_strategy"]
            if "cum_ret_market" in df.columns and "cum_market" not in df.columns:
                df["cum_market"] = df["cum_ret_market"]
            for col in ["month_dt", "month"]:
                if col in df.columns:
                    df[col] = df[col].astype(str)
            out = df.to_dict(orient="records")
            with open(DASHBOARD_DATA / "portfolio.json", "w") as f:
                json.dump(out, f, indent=0)
            print("Exported portfolio.json")
        except ImportError:
            pass

    # 3. Regime states (HMM + stress index)
    regime_path = src / "regime_states.parquet"
    if regime_path.exists():
        try:
            import pandas as pd
            df = pd.read_parquet(regime_path)
            for c in ["month_dt", "month"]:
                if c in df.columns:
                    df[c] = df[c].astype(str)
            out = df.to_dict(orient="records")
            with open(DASHBOARD_DATA / "regime.json", "w") as f:
                json.dump(out, f, indent=0)
            print("Exported regime.json")
        except ImportError:
            pass

    # 4. SHAP importance by regime
    shap_data = {}
    try:
        import pandas as pd
    except ImportError:
        pd = None
    for reg in ["Bull", "Bear", "Transition"]:
        p = src / f"shap_importance_{reg}.csv"
        if p.exists() and pd is not None:
            df = pd.read_csv(p).head(20)
            shap_data[reg] = df.to_dict(orient="records")
    if shap_data:
        with open(DASHBOARD_DATA / "shap_by_regime.json", "w") as f:
            json.dump(shap_data, f, indent=2)
        print("Exported shap_by_regime.json")
    else:
        # Fallback so feature importance charts always have data
        fallback_shap = {
            "Bull": [{"feature": "macro_dp", "importance": 0.012}, {"feature": "char_mom12m", "importance": 0.009}, {"feature": "macro_tms", "importance": 0.007}],
            "Bear": [{"feature": "macro_dfy", "importance": 0.015}, {"feature": "macro_svar", "importance": 0.011}, {"feature": "char_size", "importance": 0.008}],
            "Transition": [{"feature": "macro_ep", "importance": 0.01}, {"feature": "char_bm", "importance": 0.008}, {"feature": "macro_ntis", "importance": 0.006}],
        }
        with open(DASHBOARD_DATA / "shap_by_regime.json", "w") as f:
            json.dump(fallback_shap, f, indent=2)
        print("Created fallback shap_by_regime.json (run pipeline for real SHAP)")

    # 5. Ensure SHAP fallback exists for feature importance charts
    if not (DASHBOARD_DATA / "shap_by_regime.json").exists():
        fallback = {
            "Bull": [{"feature": "macro_dp", "importance": 0.012}, {"feature": "char_mom12m", "importance": 0.009}],
            "Bear": [{"feature": "macro_dfy", "importance": 0.015}, {"feature": "macro_svar", "importance": 0.011}],
            "Transition": [{"feature": "macro_ep", "importance": 0.01}, {"feature": "char_bm", "importance": 0.008}],
        }
        with open(DASHBOARD_DATA / "shap_by_regime.json", "w") as f:
            json.dump(fallback, f, indent=2)
        print("Created fallback shap_by_regime.json")

    # 6. Fallback sample data if nothing exists (for demo)
    if not (DASHBOARD_DATA / "metrics.json").exists():
        with open(DASHBOARD_DATA / "metrics.json", "w") as f:
            json.dump({
                "baseline_metrics": {"OLS": {"oos_r2": 0.008}, "Ridge": {"oos_r2": 0.012}, "XGBoost": {"oos_r2": 0.022}, "LightGBM": {"oos_r2": 0.02}, "RegimeNN": {"oos_r2": 0.019}},
                "portfolio_metrics": {"sharpe_ratio": 1.2, "max_drawdown": -0.15, "annualized_alpha": 0.04, "long_short_spread_mean": 0.003},
            }, f, indent=2)
        print("Created sample metrics.json (run pipeline for real data)")
    print("Dashboard data ready in dashboard/data/")


if __name__ == "__main__":
    main()
