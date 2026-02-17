"""ERIS KPI & Project Success — data coverage, quality metrics, and benchmark comparison."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from components.ui_theme import inject_theme
from components.insights import humanize_topic_label
from components.data_loader import get_document_counts, load_regime_states, load_topic_distribution
from data.storage.db_manager import get_connection

# Minimal dark layout (avoid DARK_LAYOUT to prevent TypeError with update_layout on Cloud)
_LAYOUT = dict(
    paper_bgcolor="rgba(10,14,20,0.9)",
    plot_bgcolor="rgba(22,27,34,0.95)",
    font=dict(color="#e6edf3", size=12),
    margin=dict(t=50, b=50, l=60, r=40),
    xaxis=dict(gridcolor="#30363d", zerolinecolor="#30363d"),
    yaxis=dict(gridcolor="#30363d", zerolinecolor="#30363d"),
    height=280,
)

inject_theme()
st.title("KPI & Project Success")
st.caption("Data coverage, model quality indicators, and benchmark comparison for stakeholder reporting.")

# Benchmarks (targets for project success)
BENCHMARKS = {
    "raw_articles": 1000,
    "processed_docs": 500,
    "regime_days": 90,
    "topic_diversity": 3,
    "nlp_signals": 500,
}

counts = get_document_counts()
regime_df = load_regime_states(days=730)
topic_dist = load_topic_distribution(days=730)

# Date range and topic diversity (inline to avoid import issues on Streamlit Cloud)
def _get_data_date_range():
    out = {"docs_min": None, "docs_max": None, "regime_min": None, "regime_max": None, "regime_days": 0}
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MIN(published_date), MAX(published_date) FROM documents_processed WHERE published_date IS NOT NULL")
            row = cur.fetchone()
            if row and row[0]:
                out["docs_min"], out["docs_max"] = str(row[0]), str(row[1])
            cur.execute("SELECT MIN(date), MAX(date), COUNT(DISTINCT date) FROM regime_states WHERE date IS NOT NULL")
            row = cur.fetchone()
            if row and row[0]:
                out["regime_min"], out["regime_max"] = str(row[0]), str(row[1])
                out["regime_days"] = row[2] if row[2] is not None else 0
    except Exception:
        pass
    return out

def _get_topic_diversity_count():
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(DISTINCT topic_hint) FROM documents_processed WHERE topic_hint IS NOT NULL AND topic_hint != ''")
            row = cur.fetchone()
            return row[0] if row and row[0] is not None else 0
    except Exception:
        return 0

date_range = _get_data_date_range()
topic_diversity = _get_topic_diversity_count()

# ----- 1. Data coverage KPIs -----
st.markdown("## Data coverage")
st.markdown("How much data the system has collected and processed (foundation for regime & insights).")

c1, c2, c3, c4, c5 = st.columns(5)
raw = counts.get("raw_articles", 0)
proc = counts.get("documents_processed", 0)
regime_days = date_range.get("regime_days", 0)
nlp = counts.get("nlp_signals", 0)

with c1:
    st.metric("Raw articles", f"{raw:,}", delta=f"Target ≥{BENCHMARKS['raw_articles']:,}")
with c2:
    st.metric("Processed docs", f"{proc:,}", delta=f"Target ≥{BENCHMARKS['processed_docs']:,}")
with c3:
    st.metric("Regime days", f"{regime_days}", delta=f"Target ≥{BENCHMARKS['regime_days']}")
with c4:
    st.metric("NLP signals", f"{nlp:,}", delta=f"Target ≥{BENCHMARKS['nlp_signals']}")
with c5:
    st.metric("Topic themes", f"{topic_diversity}", delta=f"Target ≥{BENCHMARKS['topic_diversity']}")

# Date range
docs_min, docs_max = date_range.get("docs_min"), date_range.get("docs_max")
regime_min, regime_max = date_range.get("regime_min"), date_range.get("regime_max")
if docs_min or regime_min:
    st.markdown("**Date range**")
    if docs_min and docs_max:
        st.caption(f"Documents: **{docs_min}** → **{docs_max}**")
    if regime_min and regime_max:
        st.caption(f"Regime series: **{regime_min}** → **{regime_max}**")

# ----- 2. Benchmark comparison (gauges) -----
st.markdown("---")
st.markdown("## Benchmark vs target")

def _gauge(value: float, target: float, title: str, color_ok: str = "#3fb950", color_low: str = "#f85149") -> go.Figure:
    """0–100 score: 100 if value >= target, else proportional."""
    value = float(value if value is not None else 0)
    target = float(target if target is not None else 1)
    if target <= 0:
        target = 1.0
    score = min(100.0, 100.0 * value / target)
    color = color_ok if score >= 100 else (color_low if score < 50 else "#d29922")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(suffix="%"),
        title=dict(text=title),
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color=color),
            threshold=dict(line=dict(color="white", width=2), value=100),
            steps=[dict(range=[0, 50], color="rgba(248,81,73,0.3)"), dict(range=[50, 100], color="rgba(210,153,34,0.3)")],
        ),
    ))
    # Minimal layout for Indicator (DARK_LAYOUT has xaxis/yaxis/legend that can cause TypeError on gauge)
    fig.update_layout(
        paper_bgcolor="rgba(10,14,20,0.9)",
        plot_bgcolor="rgba(22,27,34,0.95)",
        font=dict(color="#e6edf3", size=12),
        height=220,
        margin=dict(t=40, b=20, l=40, r=40),
    )
    return fig

# Coerce to numbers in case counts/date_range return None or non-numeric
raw = int(raw) if raw is not None else 0
proc = int(proc) if proc is not None else 0
regime_days = int(regime_days) if regime_days is not None else 0
nlp = int(nlp) if nlp is not None else 0
topic_diversity = int(topic_diversity) if topic_diversity is not None else 0

g1, g2, g3, g4, g5 = st.columns(5)
with g1:
    st.plotly_chart(_gauge(raw, BENCHMARKS["raw_articles"], "Raw articles"), use_container_width=True)
with g2:
    st.plotly_chart(_gauge(proc, BENCHMARKS["processed_docs"], "Processed docs"), use_container_width=True)
with g3:
    st.plotly_chart(_gauge(regime_days, BENCHMARKS["regime_days"], "Regime days"), use_container_width=True)
with g4:
    st.plotly_chart(_gauge(nlp, BENCHMARKS["nlp_signals"], "NLP signals"), use_container_width=True)
with g5:
    st.plotly_chart(_gauge(topic_diversity, BENCHMARKS["topic_diversity"], "Topic themes"), use_container_width=True)

# ----- 3. Success statement -----
st.markdown("---")
st.markdown("## Project success summary")

passed = (
    raw >= BENCHMARKS["raw_articles"]
    and proc >= BENCHMARKS["processed_docs"]
    and regime_days >= BENCHMARKS["regime_days"]
    and topic_diversity >= BENCHMARKS["topic_diversity"]
)
if passed:
    st.success(
        "**All benchmark targets are met.** The ERIS pipeline has sufficient data coverage and model outputs "
        "(regime, topics, sentiment) to support stakeholder insights and risk analysis above the defined benchmark."
    )
else:
    short = []
    if raw < BENCHMARKS["raw_articles"]:
        short.append("raw articles")
    if proc < BENCHMARKS["processed_docs"]:
        short.append("processed docs")
    if regime_days < BENCHMARKS["regime_days"]:
        short.append("regime days")
    if topic_diversity < BENCHMARKS["topic_diversity"]:
        short.append("topic diversity")
    st.warning(
        f"**Some targets are below benchmark.** Run the full data pipeline (including Kaggle and topic labels) "
        f"to improve: {', '.join(short)}. Once targets are met, insights and regime analysis will be at benchmark quality."
    )

# ----- 4. Regime & topic quality (infographic) -----
st.markdown("---")
st.markdown("## Quality at a glance")

col_a, col_b = st.columns(2)
with col_a:
    if not regime_df.empty and "regime_label" in regime_df.columns:
        mix = regime_df["regime_label"].value_counts()
        total = len(regime_df)
        labels = ["Risk-Off", "Transitional", "Risk-On"]
        pcts = [mix.get(l, 0) / total * 100 for l in labels]
        fig = go.Figure(data=[go.Bar(x=labels, y=pcts, marker_color=["#f85149", "#d29922", "#3fb950"])])
        fig.update_layout(
            **_LAYOUT,
            title="Regime mix (% of days)",
            yaxis_title="%",
            yaxis=dict(tickformat=".0f", gridcolor="#30363d", zerolinecolor="#30363d"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Regime mix will appear once regime data is available.")

with col_b:
    if not topic_dist.empty and "doc_count" in topic_dist.columns:
        top = topic_dist.head(10).copy()
        top["display_label"] = top["topic_label"].astype(str).apply(humanize_topic_label)
        fig = go.Figure(
            data=[go.Bar(y=top["display_label"], x=top["doc_count"], orientation="h", marker_color="#58a6ff")]
        )
        fig.update_layout(
            **_LAYOUT,
            title="Topic distribution (top 10)",
            xaxis_title="Documents",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Topic distribution will appear once topic labels are generated.")

st.caption(
    "KPIs are derived from actual pipeline output. Targets can be adjusted in the app configuration for your organization."
)
