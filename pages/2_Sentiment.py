"""ERIS Sentiment deep dive."""
import streamlit as st
from components.data_loader import load_nlp_signals

st.title("Sentiment Analysis")
days = st.session_state.get("days", 365)
source = st.session_state.get("data_source", "all")
source_filter = None if source == "all" else source

df = load_nlp_signals(days=days, source_type=source_filter)
if df.empty:
    st.info("No NLP signals yet. Run Phase 2 (Text Intelligence Engine) to compute sentiment and topics.")
else:
    if "daily_mean_sentiment" in df.columns:
        st.line_chart(df.set_index("date")[["daily_mean_sentiment"]])
    st.dataframe(df.head(100), use_container_width=True)
