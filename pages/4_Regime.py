"""ERIS Regime engine details and model comparison."""
import streamlit as st
from components.data_loader import load_regime_states

st.title("Regime Engine")
st.caption("HMM, change-point, and XGBoost ensemble (Phase 3).")
df = load_regime_states(days=st.session_state.get("days", 365))
if df.empty:
    st.info("No regime states. Run Phase 3 regime detector and classifier.")
else:
    st.dataframe(df, use_container_width=True)
