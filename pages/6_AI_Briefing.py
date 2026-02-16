"""ERIS AI Risk Briefing — complete risk briefing and mitigation paths (GPT)."""
from datetime import date
import streamlit as st
from components.data_loader import get_latest_regime, load_regime_states, load_daily_sentiment, load_topic_distribution
from components.ui_theme import inject_theme, render_insight
from components.insights import get_regime_inference, get_regime_trend_summary, get_topic_trend_summary
from components.stress_level import get_stress_info
from components.llm_briefing import get_or_create_briefing

inject_theme()
st.title("AI Risk Briefing")
st.caption("Complete risk briefing and mitigation paths for stakeholders (GPT-4).")

days = st.session_state.get("days", 365)
source_filter = None if st.session_state.get("data_source", "all") == "all" else st.session_state.get("data_source")
regime = get_latest_regime()
regime_df = load_regime_states(days=min(days, 90))
daily_sent = load_daily_sentiment(days=min(days, 90), source_type=source_filter)
topic_dist = load_topic_distribution(days=min(days, 365))
stress_info = get_stress_info(regime, regime_df, daily_sent)

if regime:
    render_insight(get_regime_inference(regime, regime_df))
    prob = regime.get("regime_probability") or regime.get("regime_prob_risk_off") or 0
    prob_pct = f"{float(prob):.0%}" if prob is not None else "N/A"
    st.markdown(
        f'<div class="eris-success-box">'
        f'<strong>Latest regime</strong> (as of {regime.get("date", "N/A")})<br>'
        f'Label: <b>{regime.get("regime_label", "N/A")}</b> · Probability: {prob_pct} · Confidence: {regime.get("confidence", "N/A")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    regime_trend = get_regime_trend_summary(regime_df, last_n=min(30, len(regime_df))) if not regime_df.empty else "No regime history."
    if not daily_sent.empty and "daily_mean_sentiment" in daily_sent.columns:
        mean_s = daily_sent["daily_mean_sentiment"].iloc[-1]
        trend_s = "improving" if mean_s is not None and len(daily_sent) > 1 and mean_s > daily_sent["daily_mean_sentiment"].iloc[0] else "weakening" if mean_s is not None else "neutral"
        sentiment_trend = f"Latest daily mean {mean_s:.2f}; trend {trend_s}."
    else:
        sentiment_trend = "No sentiment data."
    topic_summary = get_topic_trend_summary(topic_dist, top_n=5) if not topic_dist.empty else "No topic data."
    as_of_date = str(regime.get("date", "") or "")[:10] or str(date.today())

    force_refresh = st.button("Regenerate briefing")
    briefing = get_or_create_briefing(
        as_of_date, regime, regime_trend, sentiment_trend, topic_summary, stress_info, force_refresh=force_refresh
    )

    # ----- Complete risk briefing -----
    st.markdown("### Complete risk briefing")
    risk_briefing = briefing.get("risk_briefing") or briefing.get("scenario_summary") or ""
    if risk_briefing:
        st.markdown(risk_briefing)
    else:
        st.caption("No risk briefing text yet. Set **OPENAI_API_KEY** in `.env` and click «Regenerate briefing».")

    # ----- Early warnings -----
    early = briefing.get("early_warnings") or []
    if early:
        st.markdown("### Early warnings")
        for w in early:
            st.warning(w)

    # ----- Mitigation paths -----
    mitigation = briefing.get("mitigation_paths") or briefing.get("precautions") or []
    if mitigation:
        st.markdown("### Mitigation paths")
        for p in mitigation:
            st.success(p)

    if briefing.get("from_cache"):
        st.caption("(Cached. Click «Regenerate briefing» to refresh with latest data.)")

    with st.expander("Raw regime record"):
        st.json(regime)
    st.subheader("Recent history")
    if not regime_df.empty:
        h = regime_df[["date", "regime_label", "confidence"]].head(20).copy()
        h["date"] = h["date"].astype(str)
        st.dataframe(h, use_container_width=True)
else:
    st.info("Regime data is not yet available.")
st.caption("Set **OPENAI_API_KEY** in `.env` to enable GPT-4 risk briefing and mitigation paths.")
