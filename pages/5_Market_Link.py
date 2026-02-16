"""ERIS Market Linkage — regime & market movement, stakeholder inference, GPT analogy."""
import streamlit as st
import pandas as pd
from components.data_loader import load_market_daily, load_regime_states, get_latest_regime
from components.ui_theme import inject_theme, render_insight
from components.insights import get_market_link_inference, get_market_movement_summary, get_regime_trend_summary
from components.charts import regime_timeseries, market_line, dual_axis_overlay
from components.llm_briefing import get_market_linkage_analogy

inject_theme()
st.title("Market Linkage")
st.caption("Regime vs market overlay. Movement and trend for stakeholders.")

days = st.session_state.get("days", 365)
market = load_market_daily(ticker="SPY", days=days)
regime_df = load_regime_states(days=days)

# ----- Stakeholder inference (no script instructions) -----
st.markdown("### Stakeholder inference")
render_insight(get_market_link_inference(not market.empty, not regime_df.empty))
if not market.empty:
    render_insight(get_market_movement_summary(market), box_class="eris-success-box")
if not regime_df.empty:
    render_insight(get_regime_trend_summary(regime_df, last_n=min(30, len(regime_df))), box_class="eris-success-box")

# ----- GPT market linkage analogy -----
regime_trend = get_regime_trend_summary(regime_df, last_n=min(30, len(regime_df))) if not regime_df.empty else "No regime history."
market_movement = get_market_movement_summary(market) if not market.empty else "No market data for the period."
latest_regime = get_latest_regime()
regime_label = (latest_regime.get("regime_label") or "N/A") if latest_regime else "N/A"
analogy = get_market_linkage_analogy(regime_trend, market_movement, regime_label, not market.empty) if not regime_df.empty else None
if analogy:
    st.markdown("### Market linkage analogy")
    render_insight(analogy, box_class="eris-insight")
else:
    if regime_df.empty:
        render_insight("Regime and market linkage insight will appear here once regime data is available.")
    else:
        render_insight(
            f"**Regime:** {regime_trend} **Market:** {market_movement}. "
            "Set **OPENAI_API_KEY** in `.env` to enable the AI-generated market linkage analogy."
        )

# ----- Charts -----
col1, col2 = st.columns(2)
with col1:
    if market.empty:
        st.subheader("SPY (close)")
        st.info("Market data (SPY) is not yet loaded. Regime and inference above are based on text signals.")
    else:
        st.subheader("SPY (close)")
        m = market.copy()
        m["date"] = pd.to_datetime(m["date"])
        st.plotly_chart(market_line(m), use_container_width=True)

with col2:
    if regime_df.empty:
        st.subheader("Regime (Risk-Off probability)")
        st.info("Regime data is not yet available.")
    else:
        st.subheader("Regime (Risk-Off probability)")
        r = regime_df.copy()
        r["date"] = pd.to_datetime(r["date"])
        st.plotly_chart(regime_timeseries(r), use_container_width=True)
        display = r[["date", "regime_label", "confidence"]].head(60).copy()
        display["date"] = pd.to_datetime(display["date"]).dt.strftime("%Y-%m-%d")
        st.dataframe(display, use_container_width=True)

if not market.empty and not regime_df.empty:
    st.subheader("Regime vs SPY (overlay)")
    r2 = regime_df.copy()
    r2["date"] = pd.to_datetime(r2["date"])
    m2 = market.copy()
    m2["date"] = pd.to_datetime(m2["date"])
    merged = pd.merge(r2, m2[["date", "close"]], on="date", how="inner")
    prob_col = "regime_prob_risk_off" if "regime_prob_risk_off" in merged.columns else "regime_probability"
    if not merged.empty and prob_col in merged.columns:
        st.plotly_chart(
            dual_axis_overlay(merged, "date", prob_col, "close", "Risk-Off prob", "SPY close"),
            use_container_width=True,
        )
    st.caption("Phase 4 will add: Granger causality (sentiment → returns), predictive regression, event studies.")
