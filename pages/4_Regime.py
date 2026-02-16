"""ERIS Regime Engine — what is a regime, definitions, examples, current forecast, charts."""
import streamlit as st
import pandas as pd
from components.data_loader import load_regime_states, get_latest_regime
from components.ui_theme import inject_theme, render_insight
from components.insights import get_regime_inference, get_regime_trend_summary
from components.regime_definitions import (
    REGIME_DEFINITIONS,
    REGIME_SHIFT_EXPLANATION,
    get_current_regime_interpretation,
)
from components.charts import regime_timeseries

inject_theme()
st.title("Regime Engine")
st.caption("Understand economic regimes and see how our model classifies the current 'mood' of the economy.")

# ---- What is a regime? (for everyone) ----
st.markdown("---")
st.subheader("What is an economic regime?")
st.markdown(
    "Think of an **economic regime** as the **mood** or **mode** the economy is in at any given time. "
    "Just like weather has seasons — summer, winter, monsoon — the economy cycles through distinct modes where everything behaves differently."
)
st.markdown(REGIME_SHIFT_EXPLANATION)

# Three regime cards
st.subheader("The three regimes")
r1, r2, r3 = st.columns(3)
for col, (key, d) in zip([r1, r2, r3], REGIME_DEFINITIONS.items()):
    with col:
        color = "#3fb950" if key == "Risk-On" else "#f85149" if key == "Risk-Off" else "#d29922"
        st.markdown(
            f'<div style="background: linear-gradient(145deg, #161b22 0%, #21262d 100%); border: 1px solid {color}; '
            f'border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">'
            f'<strong style="color:{color};">{d["title"]}</strong><br>'
            f'<span style="color:#8b949e; font-style: italic;">{d["subtitle"]}</span><br><br>'
            f'<span style="color:#b1bac4;">{d["description"]}</span><br><br>'
            f'<span style="color:#8b949e; font-size: 0.9rem;">Example: {d["example"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")
st.subheader("Current regime: what our model says")

days = st.session_state.get("days", 365)
df = load_regime_states(days=days)
latest = get_latest_regime()

if df.empty:
    st.info("No regime states yet. Run the data pipeline (Fetch data → Run pipeline now) to populate regime and sentiment.")
else:
    # Current forecast with plain-language interpretation
    prob = latest.get("regime_probability") or latest.get("regime_prob_risk_off")
    pct = f"{float(prob):.0%}" if prob is not None else "N/A"
    conf = latest.get("confidence") or "N/A"
    label = latest.get("regime_label") or "N/A"
    render_insight(get_current_regime_interpretation(label, pct, conf))
    render_insight(get_regime_inference(latest, df))
    render_insight(get_regime_trend_summary(df, last_n=min(30, len(df))), box_class="eris-success-box")

    st.subheader("Regime over time")
    df_plot = df.copy()
    df_plot["date"] = pd.to_datetime(df_plot["date"])
    st.plotly_chart(regime_timeseries(df_plot), use_container_width=True)

    st.subheader("Regime time series (table)")
    st.caption("Each row is one day. Regime label = our classification; probability = how sure the model is.")
    display = df.copy()
    display["date"] = pd.to_datetime(display["date"]).dt.strftime("%Y-%m-%d")
    for col in ["regime_probability", "regime_prob_risk_off", "composite_prob"]:
        if col in display.columns:
            display[col] = display[col].apply(
                lambda x: f"{float(x):.0%}" if x is not None and str(x) != "nan" else ""
            )
    cols_show = ["date", "regime_label", "confidence", "regime_probability", "regime_prob_risk_off"]
    if "drivers" in display.columns and display["drivers"].notna().any():
        cols_show.append("drivers")
    cols_show = [c for c in cols_show if c in display.columns]
    st.dataframe(display[cols_show], use_container_width=True)
