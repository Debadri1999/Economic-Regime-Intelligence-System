"""ERIS Topics & Narratives — human-readable themes, trend summary, Plotly chart."""
import streamlit as st
import pandas as pd
from components.data_loader import load_topic_distribution, load_document_topics
from components.ui_theme import inject_theme, render_insight, render_script_help
from components.insights import get_topics_inference, get_topic_trend_summary, humanize_topic_label
from components.charts import topic_bar_chart
from data.storage.db_manager import get_connection

inject_theme()
st.title("Topics & Narratives")
st.caption("Topic prevalence from BERTopic; themes and trend for stakeholders.")

days = st.session_state.get("days", 365)
topic_dist = load_topic_distribution(days=days)
doc_topics = load_document_topics(days=days, limit=200)
agg = None
with get_connection() as conn:
    agg = pd.read_sql_query(
        """SELECT source_type, COUNT(*) AS doc_count FROM documents_processed
           WHERE published_date >= date('now', ?) GROUP BY source_type""",
        conn,
        params=(f"-{days} days",),
    )

has_topic_labels = not topic_dist.empty

# Inference + trend summary (what the data means)
render_insight(get_topics_inference(has_topic_labels, agg))
if has_topic_labels:
    trend_text = get_topic_trend_summary(topic_dist, top_n=6)
    render_insight(trend_text, box_class="eris-success-box")

if has_topic_labels:
    st.subheader("Topic distribution")
    plot_df = topic_dist.copy()
    plot_df["topic_label"] = plot_df["topic_label"].apply(humanize_topic_label)
    st.plotly_chart(topic_bar_chart(plot_df, top_n=14), use_container_width=True)
    st.subheader("Documents by topic (sample)")
    show = doc_topics.copy()
    show["topic_label"] = show["topic_label"].apply(humanize_topic_label)
    st.dataframe(show.head(100), use_container_width=True)
else:
    if agg is not None and not agg.empty:
        st.subheader("Document volume by source")
        st.bar_chart(agg.set_index("source_type")[["doc_count"]])
    render_script_help(
        "Topic labels (BERTopic) not generated yet",
        "python -m models.topic_engine",
        "Run the topic engine to fit BERTopic and write labels. First run may download sentence-transformers models.",
    )
