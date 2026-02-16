"""
ERIS glossary: plain-language definitions for every term used on the dashboard.
For stakeholders and lay users.
"""

import streamlit as st

GLOSSARY = {
    "Regime": "The current 'mood' or mode the economy is in — like weather seasons. We classify it as Growth (Risk-On), Stress (Risk-Off), or Transition (mixed signals).",
    "Risk-On (Growth)": "A phase when investors and businesses are optimistic: hiring, spending, and lending are strong; stocks tend to rise. The vibe is 'let\'s make money.'",
    "Risk-Off (Stress)": "A phase when fear dominates: people sell riskier assets, hold cash, companies cut costs, banks tighten lending. The vibe is 'protect what we have.'",
    "Transitional": "The in-between phase: some indicators look good, others look bad. Uncertainty is highest here; the economy may be shifting toward Growth or Stress.",
    "Regime shift": "When the economy flips from one mode to another (e.g. from Growth to Stress). Text from news and earnings often signals a shift 1–4 weeks before official data.",
    "Sentiment": "How positive or negative the language is in news, Fed speeches, or earnings calls. We score it from −1 (very negative) to +1 (very positive).",
    "Sentiment score": "A number from −1 to +1: negative = cautious or fearful language; positive = optimistic or confident language.",
    "Confidence": "How sure our model is about the current regime (Low / Medium / High). Higher confidence means the signals are clearer.",
    "Probability": "The model\'s estimate (0–100%) that we are in a given regime (e.g. 60% Risk-Off means the model sees stress as more likely).",
    "Risk-Off probability": "The chance our model assigns to the economy being in Stress mode. Higher = more fear / defensive positioning.",
    "Processed docs": "News articles, Fed documents, or earnings text that we cleaned and are using for sentiment and topic analysis.",
    "Raw articles": "Total number of news (and similar) items we have collected before cleaning.",
    "Topics": "Recurring themes in the text (e.g. 'Federal Reserve', 'Bitcoin & crypto') found by our topic model (BERTopic).",
    "HMM": "Hidden Markov Model — a statistical method we use to infer the current regime from daily sentiment and related signals.",
    "SPY": "An ETF that tracks the S&P 500 stock index. We use it as a simple measure of broad market movement.",
    "At a glance": "Quick-view charts on the home page: regime over time, sentiment trend, and main topics.",
    "Executive summary": "A short, human-readable summary of what the data shows: data coverage, current regime, and key takeaways.",
}


def render_glossary_expander():
    """Show glossary in an expander (e.g. in sidebar)."""
    with st.expander("📖 What do these terms mean?", expanded=False):
        for term, definition in GLOSSARY.items():
            st.markdown(f"**{term}** — {definition}")


def get_definition(term: str) -> str:
    """Return plain-language definition for a term, or empty string."""
    return GLOSSARY.get(term, "")
