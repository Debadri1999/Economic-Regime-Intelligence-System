"""
Export pipeline outputs to dashboard/data/*.json for the static web dashboard.
Run after run_offline_pipeline.py. From project root: python scripts/export_dashboard_data.py
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COURSE_DIR = PROJECT_ROOT / "data" / "processed" / "course"
DASHBOARD_DATA = PROJECT_ROOT / "dashboard" / "data"


def main():
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)

    # 1. Metrics (baseline OOS R² + portfolio)
    metrics_path = COURSE_DIR / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            data = json.load(f)
        with open(DASHBOARD_DATA / "metrics.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Exported metrics.json")

    # 2. Portfolio returns (cumulative chart)
    port_path = COURSE_DIR / "portfolio_returns.parquet"
    if port_path.exists():
        import pandas as pd
        df = pd.read_parquet(port_path)
        for col in ["month_dt", "month"]:
            if col in df.columns:
                df[col] = df[col].astype(str)
        out = df.to_dict(orient="records")
        with open(DASHBOARD_DATA / "portfolio.json", "w") as f:
            json.dump(out, f, indent=0)
        print("Exported portfolio.json")

    # 3. Regime states (HMM + stress index)
    regime_path = COURSE_DIR / "regime_states.parquet"
    if regime_path.exists():
        import pandas as pd
        df = pd.read_parquet(regime_path)
        for c in ["month_dt", "month"]:
            if c in df.columns:
                df[c] = df[c].astype(str)
        out = df.to_dict(orient="records")
        with open(DASHBOARD_DATA / "regime.json", "w") as f:
            json.dump(out, f, indent=0)
        print("Exported regime.json")

    # 4. SHAP importance by regime
    shap_data = {}
    for reg in ["Bull", "Bear", "Transition"]:
        p = COURSE_DIR / f"shap_importance_{reg}.csv"
        if p.exists():
            import pandas as pd
            df = pd.read_csv(p)
            df = df.head(20)  # top 20 for dashboard
            shap_data[reg] = df.to_dict(orient="records")
    if shap_data:
        with open(DASHBOARD_DATA / "shap_by_regime.json", "w") as f:
            json.dump(shap_data, f, indent=2)
        print("Exported shap_by_regime.json")

    # 5. Fallback sample data if nothing exists (for demo)
    if not (DASHBOARD_DATA / "metrics.json").exists():
        with open(DASHBOARD_DATA / "metrics.json", "w") as f:
            json.dump({
                "baseline_metrics": {"OLS": {"oos_r2": 0.008}, "Ridge": {"oos_r2": 0.012}, "RF": {"oos_r2": 0.018}, "XGBoost": {"oos_r2": 0.022}, "RegimeNN": {"oos_r2": 0.019}},
                "portfolio_metrics": {"sharpe_ratio": 1.2, "max_drawdown": -0.15, "annualized_alpha": 0.04, "long_short_spread_mean": 0.003},
            }, f, indent=2)
        print("Created sample metrics.json (run pipeline for real data)")
    print("Dashboard data ready in dashboard/data/")


if __name__ == "__main__":
    main()
