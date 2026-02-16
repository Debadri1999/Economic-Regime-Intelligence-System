"""ERIS AI risk briefing (LLM layer)."""
import streamlit as st
from components.data_loader import get_latest_regime

st.title("AI Risk Briefing")
st.caption("GPT-4 powered narrative from regime signals (Phase 5).")
regime = get_latest_regime()
if regime:
    st.json(regime)
st.info("LLM explanation engine (Phase 5) will generate structured risk assessments here.")
