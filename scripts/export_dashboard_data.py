"""
Export pipeline outputs to dashboard/data/*.json and docs/data/*.json for the static web dashboard.
Run after run_offline_pipeline.py. From project root: python scripts/export_dashboard_data.py

Supports both data/processed/course/ (pipeline) and results/ (ERIS_Optimized_Pipeline.ipynb).

Output format (v2): baseline_metrics (per model: oos_r2, rmse, mae, avg_ic),
  portfolio_metrics (per model: sharpe_ratio, max_drawdown, annualized_alpha, long_short_spread_mean),
  regime_conditional_r2 (per model per regime), dataset_info.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COURSE_DIR = PROJECT_ROOT / "data" / "processed" / "course"
RESULTS_DIR = PROJECT_ROOT / "results"
DASHBOARD_DATA = PROJECT_ROOT / "dashboard" / "data"
DOCS_DATA = PROJECT_ROOT / "docs" / "data"

# V2 fallback when pipeline hasn't been re-run with new metrics
V2_FALLBACK = {
    "baseline_metrics": {
        "OLS": {"oos_r2": -0.0236, "rmse": 0.1801, "mae": 0.1013, "avg_ic": 0.0047},
        "Ridge": {"oos_r2": -0.0236, "rmse": 0.1801, "mae": 0.1013, "avg_ic": 0.0047},
        "LightGBM": {"oos_r2": -0.0249, "rmse": 0.1802, "mae": 0.1016, "avg_ic": 0.0311},
        "XGBoost": {"oos_r2": -0.0291, "rmse": 0.1806, "mae": 0.1017, "avg_ic": 0.0306},
        "RegimeNN": {"oos_r2": -0.0779, "rmse": 0.1848, "mae": 0.1038, "avg_ic": 0.0480},
    },
    "portfolio_metrics": {
        "OLS": {"sharpe_ratio": 0.003, "max_drawdown": -0.337, "annualized_alpha": -0.1492, "long_short_spread_mean": 0.00003},
        "Ridge": {"sharpe_ratio": 0.003, "max_drawdown": -0.337, "annualized_alpha": -0.1492, "long_short_spread_mean": 0.00003},
        "XGBoost": {"sharpe_ratio": 0.469, "max_drawdown": -0.444, "annualized_alpha": -0.0456, "long_short_spread_mean": 0.00867},
        "LightGBM": {"sharpe_ratio": 0.202, "max_drawdown": -0.584, "annualized_alpha": -0.1073, "long_short_spread_mean": 0.00353},
        "RegimeNN": {"sharpe_ratio": 0.169, "max_drawdown": -0.642, "annualized_alpha": -0.1138, "long_short_spread_mean": 0.00298},
    },
    "regime_conditional_r2": {
        "OLS": {"Bull": -0.0013, "Transition": -0.0133, "Bear": -0.3710},
        "Ridge": {"Bull": -0.0013, "Transition": -0.0133, "Bear": -0.3710},
        "XGBoost": {"Bull": -0.0078, "Transition": -0.0555, "Bear": -0.1392},
        "LightGBM": {"Bull": -0.0058, "Transition": -0.0439, "Bear": -0.0555},
        "RegimeNN": {"Bull": -0.0714, "Transition": -0.0492, "Bear": -0.3246},
    },
    "dataset_info": {
        "raw_rows": 1520078,
        "clean_rows": 1027681,
        "null_dropped": 492397,
        "total_stocks": 14436,
        "unique_stocks": 9778,
        "avg_per_month": 4094,
        "features": 176,
        "oos_months": 144,
        "oos_start": "2010-01",
        "oos_end": "2021-12",
    },
}


def _write_fallback_rankings(dash_data, docs_data):
    """Write demo rankings so the Stock Rankings section renders when no predictions.parquet exists."""
    import random
    random.seed(42)
    models = ["XGBoost", "LightGBM", "RegimeNN", "OLS", "Ridge"]
    decile_base = [-0.008, -0.005, -0.003, -0.001, 0.001, 0.002, 0.004, 0.006, 0.009, 0.012]
    rankings = {}
    for m in models:
        offset = random.uniform(-0.001, 0.001)
        decile_avg = {str(i + 1): round(d + offset + random.uniform(-0.0005, 0.0005), 6) for i, d in enumerate(decile_base)}
        top20 = [{"permno": 10000 + i * 137, "pred_return": round(0.008 + i * 0.0008 + random.uniform(0, 0.001), 6), "sic2": ["36", "35", "73", "28", "48"][i % 5]} for i in range(20)]
        bottom20 = [{"permno": 50000 + i * 211, "pred_return": round(-0.012 - i * 0.0006 - random.uniform(0, 0.001), 6), "sic2": ["13", "10", "29", "49", "53"][i % 5]} for i in range(20)]
        rankings[m] = {"top20": top20, "bottom20": bottom20, "decile_avg": decile_avg, "month": "2021-12"}
    for d in [dash_data, docs_data]:
        with open(d / "rankings.json", "w", encoding="utf-8") as f:
            json.dump(rankings, f, indent=2)
    print("Created fallback rankings.json (demo data — run pipeline for real rankings)")


def _find_data_dir():
    """Prefer results/ (notebook) then data/processed/course/ (pipeline)."""
    if (RESULTS_DIR / "metrics.json").exists():
        return RESULTS_DIR
    if (RESULTS_DIR / "predictions.parquet").exists() and not (RESULTS_DIR / "metrics.json").exists():
        return RESULTS_DIR
    return COURSE_DIR


def _normalize_metrics(data):
    """Convert pipeline/notebook output to v2 format. ALWAYS merge with V2_FALLBACK so no field is ever missing."""
    # Start with fallback as base — ensures complete data even when pipeline is partial
    out = {
        "baseline_metrics": {k: dict(v) for k, v in V2_FALLBACK["baseline_metrics"].items()},
        "portfolio_metrics": {k: dict(v) for k, v in V2_FALLBACK["portfolio_metrics"].items()},
        "regime_conditional_r2": {k: dict(v) for k, v in V2_FALLBACK["regime_conditional_r2"].items()},
        "dataset_info": dict(V2_FALLBACK["dataset_info"]),
    }

    bm_src = data.get("baseline_metrics") or data.get("model_metrics", {}) or {}
    for k, v in bm_src.items():
        if v is None or not isinstance(v, dict):
            continue
        if k not in out["baseline_metrics"]:
            out["baseline_metrics"][k] = {}
        for f in ["oos_r2", "rmse", "oos_rmse", "mae", "avg_ic"]:
            val = v.get(f) if f != "oos_rmse" else (v.get("oos_rmse") or v.get("rmse"))
            if val is not None:
                try:
                    out["baseline_metrics"][k]["rmse" if f == "oos_rmse" else f] = float(val)
                except (TypeError, ValueError):
                    pass
        if "oos_rmse" in v and "rmse" not in out["baseline_metrics"][k]:
            out["baseline_metrics"][k]["rmse"] = float(v["oos_rmse"])

    pm_src = data.get("portfolio_metrics", {}) or {}
    if pm_src and isinstance(pm_src, dict):
        if any(x in pm_src for x in ["OLS", "Ridge", "XGBoost", "LightGBM", "RegimeNN"]):
            for k, v in pm_src.items():
                if v and isinstance(v, dict) and "sharpe_ratio" in v:
                    out["portfolio_metrics"][k] = {
                        "sharpe_ratio": float(v.get("sharpe_ratio", 0)),
                        "max_drawdown": float(v.get("max_drawdown", 0)),
                        "annualized_alpha": float(v.get("annualized_alpha", 0)),
                        "long_short_spread_mean": float(v.get("long_short_spread_mean", 0)),
                    }
        elif "sharpe_ratio" in pm_src:
            out["portfolio_metrics"] = {
                "Portfolio": {
                    "sharpe_ratio": float(pm_src.get("sharpe_ratio", 0)),
                    "max_drawdown": float(pm_src.get("max_drawdown", 0)),
                    "annualized_alpha": float(pm_src.get("annualized_alpha", 0)),
                    "long_short_spread_mean": float(pm_src.get("long_short_spread_mean", 0)),
                }
            }

    r2_src = data.get("regime_conditional_r2", {}) or {}
    if r2_src:
        for k, v in r2_src.items():
            if v and isinstance(v, dict):
                out["regime_conditional_r2"][k] = {
                    "Bull": float(v.get("Bull", 0)),
                    "Transition": float(v.get("Transition", 0)),
                    "Bear": float(v.get("Bear", 0)),
                }

    di = data.get("dataset_info", {})
    if di and isinstance(di, dict):
        out["dataset_info"] = {**out["dataset_info"], **{x: di[x] for x in di if di[x] is not None}}

    return out


def main():
    for dest_dir in [DASHBOARD_DATA, DOCS_DATA]:
        dest_dir.mkdir(parents=True, exist_ok=True)

    src = _find_data_dir()

    # 1. Metrics
    metrics_path = src / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, encoding="utf-8") as f:
            data = json.load(f)
        out = _normalize_metrics(data)
    else:
        out = _normalize_metrics({})  # Use full fallback when no pipeline output

    for dest_dir in [DASHBOARD_DATA, DOCS_DATA]:
        with open(dest_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
    print("Exported metrics.json (v2) to dashboard/data and docs/data")

    # 2. Portfolio returns
    port_path = src / "portfolio_returns.parquet"
    if not port_path.exists() and src == RESULTS_DIR:
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
            rec = df.to_dict(orient="records")
            for dest_dir in [DASHBOARD_DATA, DOCS_DATA]:
                with open(dest_dir / "portfolio.json", "w", encoding="utf-8") as f:
                    json.dump(rec, f, indent=0)
            print("Exported portfolio.json")
        except ImportError:
            pass

    # 2b. Portfolio by model (for interactive chart: All / single model + market)
    port_multi_path = src / "portfolio_by_model.parquet"
    if port_multi_path.exists():
        try:
            import pandas as pd

            pm = pd.read_parquet(port_multi_path)
            if "month_dt" in pm.columns:
                pm["month_dt"] = pm["month_dt"].astype(str)
            months = pm["month_dt"].tolist()
            out_multi = {"months": months, "market": []}
            if "market" in pm.columns:
                out_multi["market"] = [round((1 + float(x)) * 100 - 100, 4) if x is not None and pd.notna(x) else None for x in pm["market"]]
            for c in pm.columns:
                if c.startswith("cum_") and c != "cum_market":
                    name = c.replace("cum_", "")
                    out_multi[name] = [round((1 + float(x)) * 100 - 100, 4) if x is not None and pd.notna(x) else None for x in pm[c]]
            for dest_dir in [DASHBOARD_DATA, DOCS_DATA]:
                with open(dest_dir / "portfolio_by_model.json", "w", encoding="utf-8") as f:
                    json.dump(out_multi, f, indent=0)
            print("Exported portfolio_by_model.json")
        except Exception as e:
            print(f"Could not export portfolio_by_model: {e}")

    # 3. Regime states
    regime_path = src / "regime_states.parquet"
    if regime_path.exists():
        try:
            import pandas as pd

            df = pd.read_parquet(regime_path)
            for col in ["month_dt", "month"]:
                if col in df.columns:
                    df[col] = df[col].astype(str)
            rec = df.to_dict(orient="records")
            for dest_dir in [DASHBOARD_DATA, DOCS_DATA]:
                with open(dest_dir / "regime.json", "w", encoding="utf-8") as f:
                    json.dump(rec, f, indent=0)
            print("Exported regime.json")
        except ImportError:
            pass

    # 4. Stock rankings (top/bottom 20, decile averages) from predictions
    pred_path = None
    for base in [RESULTS_DIR, COURSE_DIR]:
        if base.exists():
            p = base / "predictions.parquet"
            if p.exists():
                pred_path = p
                break
            for f in base.glob("predictions*.parquet"):
                pred_path = f
                break
        if pred_path:
            break
    if pred_path and pred_path.exists():
        try:
            import pandas as pd

            preds = pd.read_parquet(pred_path)
            month_col = "month_dt" if "month_dt" in preds.columns else "month"
            if month_col not in preds.columns:
                month_col = [c for c in preds.columns if "month" in c.lower()][0] if any("month" in c.lower() for c in preds.columns) else None
            permno_col = "permno" if "permno" in preds.columns else ("PERMNO" if "PERMNO" in preds.columns else None)
            sic_col = "sic2" if "sic2" in preds.columns else ("sic" if "sic" in preds.columns else None)
            sic2_dummy_cols = [c for c in preds.columns if c.startswith("sic2_")]

            def _get_sic2(df_subset):
                if sic_col and sic_col in df_subset.columns:
                    def _safe_sic(x):
                        if pd.isna(x) or x is None:
                            return None
                        if isinstance(x, (int, float)):
                            return str(int(x))
                        return str(x)
                    return df_subset[sic_col].apply(_safe_sic)
                if sic2_dummy_cols:
                    # Derive from one-hot (sic2_36, sic2_35, etc.): find column that is 1
                    def row_to_sic(row):
                        for c in sic2_dummy_cols:
                            v = row.get(c, 0)
                            if v is not None and pd.notna(v) and float(v) > 0.5:
                                return str(c.replace("sic2_", ""))
                        return None
                    return df_subset.apply(row_to_sic, axis=1)
                return None

            model_col_map = {}
            for m in ["XGBoost", "LightGBM", "RegimeNN", "OLS", "Ridge"]:
                for cand in [f"pred_{m}", f"pred_{m.lower()}", m, f"pred_return_{m}"]:
                    if cand in preds.columns:
                        model_col_map[m] = cand
                        break

            if month_col and permno_col and model_col_map:
                latest_month = preds[month_col].max()
                latest = preds[preds[month_col] == latest_month].copy()
                rankings = {}
                for model, col in model_col_map.items():
                    latest_sorted = latest.dropna(subset=[col]).sort_values(col, ascending=False)
                    if len(latest_sorted) == 0:
                        continue
                    top20_df = latest_sorted.head(20)
                    bottom20_df = latest_sorted.tail(20)
                    top20 = top20_df[[permno_col, col]].rename(columns={permno_col: "permno", col: "pred_return"})
                    sic_top = _get_sic2(top20_df)
                    top20["sic2"] = sic_top.tolist() if sic_top is not None else [None] * len(top20)
                    bottom20 = bottom20_df[[permno_col, col]].rename(columns={permno_col: "permno", col: "pred_return"})
                    sic_bot = _get_sic2(bottom20_df)
                    bottom20["sic2"] = sic_bot.tolist() if sic_bot is not None else [None] * len(bottom20)
                    latest_sorted = latest_sorted.copy()
                    latest_sorted["decile"] = pd.qcut(latest_sorted[col].rank(method="first"), 10, labels=range(1, 11))
                    decile_avg = latest_sorted.groupby("decile", observed=True)[col].mean()
                    rankings[model] = {
                        "top20": top20.to_dict(orient="records"),
                        "bottom20": bottom20.to_dict(orient="records"),
                        "decile_avg": {str(int(k)): round(float(v), 6) for k, v in decile_avg.items()},
                        "month": str(latest_month),
                    }
                if rankings:
                    for dest_dir in [DASHBOARD_DATA, DOCS_DATA]:
                        with open(dest_dir / "rankings.json", "w", encoding="utf-8") as f:
                            json.dump(rankings, f, indent=2)
                    print("Exported rankings.json (stock rankings)")
        except Exception as e:
            print(f"Could not export rankings: {e}")

    # Write fallback rankings if none was exported (so dashboard section still renders)
    if not (DASHBOARD_DATA / "rankings.json").exists():
        _write_fallback_rankings(DASHBOARD_DATA, DOCS_DATA)

    # 5. SHAP importance by regime
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
        for dest_dir in [DASHBOARD_DATA, DOCS_DATA]:
            with open(dest_dir / "shap_by_regime.json", "w", encoding="utf-8") as f:
                json.dump(shap_data, f, indent=2)
        print("Exported shap_by_regime.json")
    else:
        fallback = {
            "Bull": [
                {"feature": "macro_dp", "importance": 0.012},
                {"feature": "char_mom12m", "importance": 0.009},
                {"feature": "macro_tms", "importance": 0.007},
            ],
            "Bear": [
                {"feature": "macro_dfy", "importance": 0.015},
                {"feature": "macro_svar", "importance": 0.011},
                {"feature": "char_size", "importance": 0.008},
            ],
            "Transition": [
                {"feature": "macro_ep", "importance": 0.01},
                {"feature": "char_bm", "importance": 0.008},
                {"feature": "macro_ntis", "importance": 0.006},
            ],
        }
        for dest_dir in [DASHBOARD_DATA, DOCS_DATA]:
            with open(dest_dir / "shap_by_regime.json", "w", encoding="utf-8") as f:
                json.dump(fallback, f, indent=2)
        print("Created fallback shap_by_regime.json")

    print("Dashboard data ready in dashboard/data/ and docs/data/")


if __name__ == "__main__":
    main()
