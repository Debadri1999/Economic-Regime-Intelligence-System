"""ERIS Main Dashboard - regime monitoring at a glance."""
import streamlit as st
from components.data_loader import load_regime_states, get_latest_regime
from components.charts import regime_area_chart

st.title("Regime Dashboard")
days = st.session_state.get("days", 365)

regime = get_latest_regime()
if regime:
    prob = regime.get("regime_probability") or 0
    label = regime.get("regime_label") or "Unknown"
    if prob >= 0.6:
        st.error(f"**{label}** — {prob:.0%} probability")
    elif prob >= 0.35:
        st.warning(f"**{label}** — {prob:.0%} probability")
    else:
        st.success(f"**{label}** — {prob:.0%} probability")
else:
    st.info("No regime state available. Run regime detection to populate.")

df = load_regime_states(days=days)
if not df.empty:
    fig = regime_area_chart(df)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No regime history in range. Complete Phase 3 to generate regime states.")
