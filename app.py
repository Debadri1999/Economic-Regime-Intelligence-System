"""
ERIS - Economic Regime Intelligence System
Streamlit entry point, page routing, session state.
"""

import streamlit as st
from utils.config import load_config, get_app_config

# Page config
cfg = get_app_config()
st.set_page_config(
    page_title=cfg.get("page_title", "ERIS - Economic Regime Intelligence System"),
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for institutional look
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
    h1 { color: #1B2A4A; }
    h2, h3 { color: #2E75B6; }
    .stSidebar { background-color: #1B2A4A; }
    .stSidebar .stMarkdown { color: #e0e0e0; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 📊 ERIS")
    st.markdown("Economic Regime Intelligence System")
    st.divider()
    default_days = cfg.get("default_days", 365)
    days = st.slider("Time range (days)", 30, 730, default_days, 30)
    st.session_state["days"] = days
    data_filter = st.selectbox("Data source", ["all", "news", "fed", "earnings"], index=0)
    st.session_state["data_source"] = data_filter
    st.divider()
    st.caption("Phase 1–2 data pipeline ready. Regime engine and LLM in later phases.")

# Main area: show dashboard by default (multipage app uses pages/ folder)
st.markdown("# Economic Regime Intelligence System")
st.markdown("Monitor regime state, sentiment, and narrative signals from financial text.")
st.info("Use the sidebar to change time range and data source. Navigate via the left sidebar or **pages**.")

# Placeholder until regime data exists
from components.data_loader import get_document_counts, get_latest_regime
counts = get_document_counts()
regime = get_latest_regime()

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Raw articles", counts.get("raw_articles", 0))
with c2:
    st.metric("Fed documents", counts.get("fed_documents", 0))
with c3:
    st.metric("Processed docs", counts.get("documents_processed", 0))

if regime:
    st.success(f"Latest regime: **{regime.get('regime_label', 'N/A')}** (prob: {regime.get('regime_probability', 0):.0%}) — {regime.get('date')}")
else:
    st.warning("No regime states yet. Run data collection and regime detection (Phases 1–3) to populate.")
