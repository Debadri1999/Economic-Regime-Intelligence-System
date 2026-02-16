"""ERIS Sentiment — daily trend and document-level signals with inference."""
import streamlit as st
import pandas as pd
from components.data_loader import load_nlp_signals, load_daily_sentiment
from components.ui_theme import inject_theme, render_insight, render_script_help
from components.insights import get_sentiment_inference

inject_theme()
st.title("Sentiment Analysis")
st.caption("FinBERT-based sentiment from processed documents; daily aggregate and trend.")

days = st.session_state.get("days", 365)
source = st.session_state.get("data_source", "all")
source_filter = None if source == "all" else source

df = load_nlp_signals(days=days, source_type=source_filter)
daily = load_daily_sentiment(days=days, source_type=source_filter)

if df.empty:
    render_script_help(
        "No NLP signals yet",
        "python run_phase2_and_3.py",
        "Run Phase 2 (FinBERT on documents_processed) to populate sentiment. Or run_all_data.py for full pipeline.",
    )
else:
    # Stakeholder inference
    render_insight(get_sentiment_inference(daily, len(df)))

    st.subheader("Daily mean sentiment")
    if not daily.empty:
        from components.charts import sentiment_timeseries
        st.plotly_chart(sentiment_timeseries(daily), use_container_width=True)
    else:
        st.caption("No daily aggregate yet.")

    st.subheader("Document-level signals (sample)")
    # Show only columns that are populated; format for readability
    display_cols = ["id", "date", "source_type", "sentiment_score",
                    "sentiment_positive_prob", "sentiment_negative_prob", "sentiment_neutral_prob", "sentiment_confidence"]
    existing = [c for c in display_cols if c in df.columns]
    show = df[existing].head(100).copy()
    if "sentiment_score" in show.columns:
        show["sentiment_score"] = pd.to_numeric(show["sentiment_score"], errors="coerce").round(4)
    for c in ["sentiment_positive_prob", "sentiment_negative_prob", "sentiment_neutral_prob", "sentiment_confidence"]:
        if c in show.columns:
            num = pd.to_numeric(show[c], errors="coerce")
            show[c] = num.apply(lambda x: f"{x:.0%}" if pd.notna(x) else "")
    st.dataframe(show, use_container_width=True)
