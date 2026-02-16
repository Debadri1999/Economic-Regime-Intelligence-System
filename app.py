"""
ERIS - Economic Regime Intelligence System
Main dashboard: stress warning level, AI briefing (GPT-4), regime, sentiment, topics.
Single entry point; no separate Dashboard tab.
"""

import os
from datetime import date
import streamlit as st
from utils.config import get_app_config
from components.ui_theme import inject_theme, render_insight, render_script_help
from components.insights import (
    get_dashboard_summary,
    get_regime_trend_summary,
    get_topic_trend_summary,
    get_market_movement_summary,
    humanize_topic_label,
)
from components.data_loader import (
    get_document_counts,
    get_latest_regime,
    load_regime_states,
    load_daily_sentiment,
    load_topic_distribution,
    load_market_daily,
)
from components.charts import (
    regime_timeseries,
    sentiment_timeseries,
    topic_bar_chart,
    market_line,
    stress_gauge,
)
from components.glossary import render_glossary_expander
from components.stress_level import get_stress_info
from components.llm_briefing import get_or_create_briefing

# Page config
logo_path = os.path.join(os.path.dirname(__file__), "assets", "eris_logo.svg")
cfg = get_app_config()
st.set_page_config(
    page_title="ERIS - Main Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

# Sidebar
with st.sidebar:
    if os.path.isfile(logo_path):
        st.image(logo_path, width=140)
    else:
        st.markdown("## 📊 ERIS")
    st.markdown("**Economic Regime Intelligence System**")
    st.caption("Main dashboard · Regime, stress & early warnings")
    st.divider()
    default_days = cfg.get("default_days", 365)
    days = st.slider("Time range (days)", 30, 730, default_days, 30, help="Drives all data on this page.")
    st.session_state["days"] = days
    data_filter = st.selectbox("Data source", ["all", "news", "fed", "earnings"], index=0)
    st.session_state["data_source"] = data_filter
    st.divider()
    render_glossary_expander()
    st.divider()
    # Run pipeline from app (collectors -> preprocess -> sentiment -> regime)
    st.markdown("**Fetch data**")
    include_topic_labels = st.checkbox("Include topic labels (slower)", value=True, help="Run BERTopic to label themes for the Topics page. Uncheck if the run times out.")
    run_pipeline_clicked = st.button("Run pipeline now", help="Run collectors, preprocess, sentiment & regime on the backend. May take 2–5 min.")
    if run_pipeline_clicked:
        from utils.run_pipeline import get_pipeline_steps, run_pipeline
        steps = get_pipeline_steps(
            include_news=bool(os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY")),
            include_fed=True,
            include_topics=include_topic_labels,
            market_days=90,
            sentiment_limit=3000,
        )
        with st.status("Running pipeline…", expanded=True) as status:
            log_placeholder = st.empty()
            log_lines = []
            def on_progress(name: str, msg: str):
                log_lines.append(f"**{name}:** {msg}")
                log_placeholder.markdown("\n".join(log_lines))
            results = run_pipeline(steps, on_progress=on_progress)
            failed = [r for r in results if not r[2]]
            if failed:
                status.update(label="Pipeline finished with errors", state="error")
            else:
                status.update(label="Pipeline finished", state="complete")
        st.cache_data.clear()
        st.rerun()
    st.caption("Or run locally: python run_all_data.py")

days = st.session_state.get("days", 365)
source_filter = None if st.session_state.get("data_source", "all") == "all" else st.session_state.get("data_source")

with st.spinner("Loading data…"):
    counts = get_document_counts()
    regime = get_latest_regime()
    regime_df = load_regime_states(days=min(days, 90))
    daily_sent = load_daily_sentiment(days=min(days, 90), source_type=source_filter)
    topic_dist = load_topic_distribution(days=min(days, 365))
    market_df = load_market_daily(ticker="SPY", days=min(days, 90))

# ----- Main dashboard -----
st.markdown("# ERIS · Main Dashboard")
st.caption(f"Regime, market stress & early warnings · Last **{days}** days" + (f" · **{source_filter}**" if source_filter else ""))

# ----- 1. Market stress warning level (infographic) -----
st.markdown("## Market stress warning level")
stress_info = get_stress_info(regime, regime_df, daily_sent)
score = stress_info["score"]
level_name = stress_info["level_name"]
color = stress_info["color"]
icon = stress_info["icon"]

col_gauge, col_desc = st.columns([1, 2])
with col_gauge:
    st.plotly_chart(stress_gauge(score, level_name, color), use_container_width=True)
with col_desc:
    st.markdown(
        f'<div style="background: linear-gradient(145deg, #161b22 0%, #21262d 100%); border: 1px solid {color}; '
        f'border-radius: 12px; padding: 1.25rem;">'
        f'<span style="font-size: 1.5rem;">{icon}</span> '
        f'<strong style="color:{color}; font-size: 1.2rem;">{level_name}</strong> — {stress_info["short"]}<br><br>'
        f'<span style="color:#b1bac4;">{stress_info["description"]}</span><br><br>'
        f'<strong style="color:#8b949e;">Suggested actions:</strong> '
        f'<span style="color:#e6edf3;">{stress_info["suggested_actions"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
# Stress level scale legend
st.caption("Scale: 0–25 Low · 25–50 Elevated · 50–75 High · 75–100 Critical (risk-off stress)")

# ----- 2. Early warnings & AI briefing (GPT-4) -----
st.markdown("## Early warnings & AI briefing")
st.caption("GPT-4 generated scenario, early warnings, and precautions from current regime, sentiment, and topics.")

regime_trend = get_regime_trend_summary(regime_df, last_n=min(30, len(regime_df))) if not regime_df.empty else "No regime history."
if not daily_sent.empty and "daily_mean_sentiment" in daily_sent.columns:
    mean_s = daily_sent["daily_mean_sentiment"].iloc[-1]
    trend_s = "improving" if mean_s is not None and len(daily_sent) > 1 and mean_s > daily_sent["daily_mean_sentiment"].iloc[0] else "weakening" if mean_s is not None else "neutral"
    sentiment_trend = f"Latest daily mean {mean_s:.2f}; trend {trend_s}."
else:
    sentiment_trend = "No sentiment data."
topic_summary = get_topic_trend_summary(topic_dist, top_n=5) if not topic_dist.empty else "No topic data."
as_of_date = str(regime.get("date", "") or "")[:10] if regime else ""
if not as_of_date:
    as_of_date = str(date.today())

force_refresh = st.button("Regenerate AI briefing")
briefing = get_or_create_briefing(
    as_of_date, regime, regime_trend, sentiment_trend, topic_summary, stress_info, force_refresh=force_refresh
)

if briefing.get("scenario_summary") or briefing.get("early_warnings") or briefing.get("precautions"):
    if briefing.get("scenario_summary"):
        st.markdown("### Current scenario")
        st.markdown(briefing["scenario_summary"])
    if briefing.get("early_warnings"):
        st.markdown("### Early warnings")
        for w in briefing["early_warnings"]:
            st.warning(w)
    if briefing.get("precautions"):
        st.markdown("### Precautions — what you can do")
        for p in briefing["precautions"]:
            st.success(p)
    if briefing.get("from_cache"):
        st.caption("(Cached briefing. Click «Regenerate AI briefing» to refresh with latest data.)")
else:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        st.info("Set **OPENAI_API_KEY** in `.env` to enable GPT-4 scenario, early warnings, and precautions. Until then, use the stress level and regime sections above.")
    else:
        st.caption("No briefing generated yet. Click «Regenerate AI briefing» or run with regime/sentiment data.")

# ----- 3. KPIs & executive summary -----
st.markdown("---")
st.markdown("## Summary")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Raw articles", f"{counts.get('raw_articles', 0):,}")
with c2:
    st.metric("Fed documents", f"{counts.get('fed_documents', 0):,}")
with c3:
    st.metric("Processed docs", f"{counts.get('documents_processed', 0):,}")
with c4:
    n_regime = regime.get("regime_label", "—") if regime else "—"
    st.metric("Current regime", n_regime)

render_insight(get_dashboard_summary(counts, regime))

takeaways = []
if not regime_df.empty:
    takeaways.append("<strong>Regime:</strong> " + get_regime_trend_summary(regime_df, last_n=min(30, len(regime_df))))
if not daily_sent.empty:
    mean_s = daily_sent["daily_mean_sentiment"].iloc[-1] if "daily_mean_sentiment" in daily_sent.columns else None
    trend = "improving" if mean_s is not None and len(daily_sent) > 1 and mean_s > daily_sent["daily_mean_sentiment"].iloc[0] else "weakening" if mean_s is not None else "—"
    mean_str = f"{mean_s:.2f}" if mean_s is not None else "—"
    takeaways.append(f"<strong>Sentiment:</strong> Latest {mean_str} (−1 to +1); trend {trend}.")
if not topic_dist.empty:
    takeaways.append("<strong>Topics:</strong> " + get_topic_trend_summary(topic_dist, top_n=4))
if not market_df.empty:
    takeaways.append("<strong>Market:</strong> " + get_market_movement_summary(market_df))
if takeaways:
    st.markdown(
        "<div class='eris-exec-summary'>" + " ".join(f"<span>{t}</span><br/>" for t in takeaways) + "</div>",
        unsafe_allow_html=True,
    )

if regime:
    prob = regime.get("regime_probability") or regime.get("regime_prob_risk_off") or 0
    pct = f"{float(prob):.0%}" if prob is not None else "N/A"
    label = regime.get("regime_label", "N/A")
    conf = regime.get("confidence", "N/A")
    date_r = regime.get("date", "N/A")
    st.markdown(
        f'<div class="eris-success-box">'
        f'<strong>Current regime</strong>: <strong>{label}</strong> (probability {pct}, confidence {conf}) as of {date_r}. '
        f'See <b>Regime</b> and <b>AI Briefing</b> pages for details.'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    render_script_help("No regime data yet", "python run_all_data.py", "Run the full pipeline to populate regime and stress.")

# ----- 4. At a glance charts -----
st.markdown("## At a glance")
col1, col2, col3 = st.columns(3)
with col1:
    if not regime_df.empty:
        r = regime_df.copy()
        r["date"] = r["date"].astype("datetime64[ns]")
        st.plotly_chart(regime_timeseries(r), use_container_width=True)
    else:
        st.caption("Regime (run Phase 2+3)")
with col2:
    if not daily_sent.empty:
        st.plotly_chart(sentiment_timeseries(daily_sent), use_container_width=True)
    else:
        st.caption("Sentiment (run Phase 2)")
with col3:
    if not topic_dist.empty:
        plot_df = topic_dist.head(10).copy()
        plot_df["topic_label"] = plot_df["topic_label"].apply(humanize_topic_label)
        st.plotly_chart(topic_bar_chart(plot_df), use_container_width=True)
    else:
        st.caption("Topics (run topic_engine)")
