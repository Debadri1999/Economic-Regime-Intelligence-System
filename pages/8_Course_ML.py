"""
Course ML pipeline results: model comparison (OOS R²), cumulative returns, regime timeline, SHAP by regime.
Reads from data/processed/course/ (run scripts/run_offline_pipeline.py first).
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from components.ui_theme import inject_theme

inject_theme()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COURSE_DIR = PROJECT_ROOT / "data" / "processed" / "course"


def _load_json(name: str):
    p = COURSE_DIR / f"{name}.json"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _load_parquet(name: str) -> pd.DataFrame:
    p = COURSE_DIR / f"{name}.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


def _load_shap_regime(regime: str) -> pd.DataFrame:
    p = COURSE_DIR / f"shap_importance_{regime}.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p).head(15)


st.set_page_config(page_title="Course ML | ERIS", page_icon="📈", layout="wide")
st.title("Course ML Pipeline Results")
st.caption("Gu, Kelly & Xiu dataset: model comparison, portfolio performance, regime detection, SHAP by regime. Data from `data/processed/course/` (run `scripts/run_offline_pipeline.py` first).")

if not COURSE_DIR.exists():
    st.warning(f"Course output directory not found: `{COURSE_DIR}`. Run `python scripts/run_offline_pipeline.py` from the project root, then return here.")
    st.stop()

metrics = _load_json("metrics")
if not metrics:
    st.info("No `metrics.json` found. Run the offline pipeline to generate course artifacts.")
    st.stop()

# ----- Model comparison (OOS R²) -----
st.markdown("## Model comparison")
bm = metrics.get("baseline_metrics") or {}
if bm:
    rows = [{"Model": name, "OOS R² (%)": round(m.get("oos_r2", 0) * 100, 4)} for name, m in bm.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    # Regime-conditional R² if present
    r2_by_regime = metrics.get("regime_conditional_r2")
    if r2_by_regime:
        st.markdown("#### Regime-conditional OOS R²")
        st.dataframe(pd.DataFrame(r2_by_regime).T, use_container_width=True, hide_index=True)
else:
    st.write("No baseline metrics yet.")

# ----- Portfolio metrics -----
pm = metrics.get("portfolio_metrics") or {}
if pm:
    st.markdown("## Portfolio metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sharpe ratio", f"{pm.get('sharpe_ratio', 0):.3f}")
    with col2:
        st.metric("Max drawdown", f"{pm.get('max_drawdown', 0):.1%}")
    with col3:
        st.metric("Annualized alpha", f"{pm.get('annualized_alpha', 0):.2%}")
    with col4:
        st.metric("Long–short spread (mean)", f"{pm.get('long_short_spread_mean', 0):.4f}")

# ----- Cumulative return chart -----
port_df = _load_parquet("portfolio_returns")
if not port_df.empty and "cum_strategy" in port_df.columns:
    st.markdown("## Cumulative return (strategy vs market)")
    port_df = port_df.sort_values("month_dt")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=port_df["month_dt"].astype(str), y=port_df["cum_strategy"], name="Long–short strategy", mode="lines"))
    fig.add_trace(go.Scatter(x=port_df["month_dt"].astype(str), y=port_df["cum_market"], name="Market (VW)", mode="lines"))
    fig.update_layout(xaxis_title="Month", yaxis_title="Cumulative return", height=400, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Portfolio returns not found. Run the pipeline to generate `portfolio_returns.parquet`.")

# ----- Regime timeline -----
regime_df = _load_parquet("regime_states")
if not regime_df.empty and "regime_label" in regime_df.columns:
    st.markdown("## Regime (HMM on macro)")
    regime_df = regime_df.sort_values("month_dt")
    fig = px.line(regime_df, x=regime_df["month_dt"].astype(str), y="regime_label", title="Regime label over time")
    fig.update_layout(xaxis_title="Month", yaxis_title="Regime", height=280)
    st.plotly_chart(fig, use_container_width=True)
    if "stress_index" in regime_df.columns:
        fig2 = px.line(regime_df, x=regime_df["month_dt"].astype(str), y="stress_index", title="Stress index")
        fig2.update_layout(xaxis_title="Month", height=280)
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Regime states not found.")

# ----- SHAP by regime -----
st.markdown("## Feature importance by regime (SHAP)")
for reg in ["Bull", "Bear", "Transition"]:
    df = _load_shap_regime(reg)
    if df.empty:
        continue
    if "feature" not in df.columns and "importance" not in df.columns:
        cols = list(df.columns)
        if len(cols) >= 2:
            df = df.rename(columns={cols[0]: "feature", cols[1]: "importance"})
    if "feature" in df.columns and "importance" in df.columns:
        fig = px.bar(df, x="importance", y="feature", orientation="h", title=f"Top 15 — {reg}")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
