"""
ERIS shared UI: production-grade dark theme and reusable components.
Insight text uses HTML <strong> so bold renders correctly (no literal **).
"""

import re
import streamlit as st

def _md_to_html(text: str) -> str:
    """Convert Markdown-style **bold** to HTML <strong> for use inside HTML divs."""
    if not text:
        return ""
    # Escape HTML first so we don't inject tags
    text = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    # Then convert **word** to <strong>word</strong>
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


# Production dark theme: high contrast, clear hierarchy
CSS = """
<style>
    /* Base: deep dark with high-contrast text */
    .stApp {
        background: #0a0e14;
        color: #e6edf3;
    }
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 1500px;
    }
    /* Typography */
    h1 { color: #58a6ff; font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.25rem; }
    h2 { color: #8b949e; font-size: 1.25rem; font-weight: 600; margin-top: 1.75rem; margin-bottom: 0.5rem; }
    h3 { color: #c9d1d9; font-size: 1.05rem; font-weight: 600; }
    p, .stMarkdown { color: #b1bac4; }
    .stCaption { color: #8b949e; }

    /* Metric cards: glass-style, high visibility, hover transition */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #161b22 0%, #21262d 100%);
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.45);
        border-color: #58a6ff;
    }
    div[data-testid="stMetric"] label {
        color: #8b949e !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
    }

    /* Insight boxes: readable, no raw ** */
    .eris-insight {
        background: linear-gradient(135deg, #0d419d 0%, #0d1117 100%);
        border: 1px solid #388bfd;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        color: #e6edf3;
        font-size: 1rem;
        line-height: 1.6;
    }
    .eris-insight strong { color: #79c0ff; font-weight: 600; }
    .eris-warning-box {
        background: linear-gradient(135deg, #3d1a00 0%, #161b22 100%);
        border: 1px solid #d29922;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        color: #e6edf3;
        font-size: 1rem;
    }
    .eris-success-box {
        background: linear-gradient(135deg, #0d3d1a 0%, #161b22 100%);
        border: 1px solid #3fb950;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        color: #e6edf3;
        font-size: 1rem;
    }
    .eris-success-box strong { color: #56d364; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important; }
    [data-testid="stSidebar"] .stMarkdown { color: #b1bac4 !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 { color: #58a6ff !important; }
    hr { border-color: #30363d !important; }

    /* DataFrames and tables */
    .stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #30363d; }
    .streamlit-expanderHeader { background: #161b22; border-radius: 8px; }

    /* Executive summary block on home */
    .eris-exec-summary {
        background: linear-gradient(135deg, #1a2332 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 1.5rem;
        margin: 1.25rem 0;
        color: #e6edf3;
        font-size: 1rem;
        line-height: 1.7;
    }
    .eris-exec-summary strong { color: #58a6ff; }
</style>
"""


def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def render_insight(text: str, box_class: str = "eris-insight"):
    """Render insight text; converts **bold** to HTML <strong> so it displays correctly."""
    html = _md_to_html(text)
    st.markdown(f'<div class="{box_class}">{html}</div>', unsafe_allow_html=True)


def render_script_help(title: str, script: str, description: str = ""):
    st.markdown(
        f'<div class="eris-warning-box">'
        f'<strong>{title}</strong><br>{description}<br>'
        f'<code style="background:#21262d;padding:6px 10px;border-radius:6px;color:#79c0ff;">{script}</code>'
        f'</div>',
        unsafe_allow_html=True,
    )
