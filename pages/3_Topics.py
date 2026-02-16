"""ERIS Topic & narrative intelligence."""
import streamlit as st
from components.data_loader import load_nlp_signals

st.title("Topics & Narratives")
st.caption("Topic prevalence and momentum from BERTopic (Phase 2).")
df = load_nlp_signals(days=st.session_state.get("days", 365))
if df.empty or "topic_label" not in df.columns:
    st.info("No topic signals yet. Run Phase 2 topic_engine to populate.")
else:
    st.write("Topic distribution and evolution will appear here.")
