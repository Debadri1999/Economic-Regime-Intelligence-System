"""
ERIS inference and conclusion text for stakeholder-facing dashboard.
All strings use ** for bold; UI converts to HTML <strong> when rendering in boxes.
"""

from typing import Optional
import pandas as pd


def humanize_topic_label(raw: str) -> str:
    """Turn BERTopic raw label into readable theme for stakeholders."""
    if not raw or str(raw).strip() == "":
        return "Other"
    s = str(raw).strip()
    if s.startswith("-1_") or s == "-1":
        return "Outlier / noise"
    if s.lower() in ("other", "outlier"):
        return "Outlier / noise"
    # "15_bitcoin_crypto_chars_analysts" -> "Bitcoin & crypto"
    if "_" in s:
        parts = s.split("_")
        # Drop leading number
        if parts and parts[0].lstrip("-").isdigit():
            parts = parts[1:]
        # Drop filler like chars, the, and, in, of
        stop = {"chars", "the", "and", "in", "of", "to", "for", "on", "with", "at"}
        words = [p for p in parts if p.lower() not in stop and len(p) > 1][:4]
        if not words:
            return "Other"
        # BERTopic often names outlier topic "0_other_..." -> treat as outlier for UI
        if words and words[0].lower() in ("other", "outlier"):
            return "Outlier / noise"
        return " ".join(w.capitalize() for w in words[:3])
    return s.replace("_", " ").capitalize()


def get_regime_trend_summary(regime_df: pd.DataFrame, last_n: int = 30) -> str:
    """E.g. 'Last 30 days: 40% Risk-Off, 35% Transitional, 25% Risk-On.'"""
    if regime_df.empty or "regime_label" not in regime_df.columns:
        return "No regime history yet."
    tail = regime_df.tail(last_n)
    counts = tail["regime_label"].value_counts()
    total = len(tail)
    if total == 0:
        return "No regime history in the period."
    parts = [f"{counts.get(l, 0) / total:.0%} {l}" for l in ["Risk-Off", "Transitional", "Risk-On"]]
    return f"Last {last_n} days regime mix: " + ", ".join(parts) + "."


def get_topic_trend_summary(topic_dist: pd.DataFrame, top_n: int = 5) -> str:
    """E.g. 'Top themes: Bitcoin & crypto (72), Federal Reserve (29), ...'"""
    if topic_dist.empty or "doc_count" not in topic_dist.columns or "topic_label" not in topic_dist.columns:
        return "No topic distribution yet."
    top = topic_dist.head(top_n)
    items = [f"{humanize_topic_label(row['topic_label'])} ({int(row['doc_count'])})" for _, row in top.iterrows()]
    return "Top themes by volume: " + ", ".join(items) + "."


def get_market_movement_summary(market_df: pd.DataFrame, ticker: str = "SPY") -> str:
    """E.g. 'SPY: +5.2% over the period.'"""
    if market_df.empty or "close" not in market_df.columns or len(market_df) < 2:
        return "No market data for return calculation."
    first = market_df["close"].iloc[0]
    last = market_df["close"].iloc[-1]
    if first and first != 0:
        pct = 100 * (last - first) / first
        return f"{ticker}: {pct:+.1f}% over the period."
    return f"{ticker}: insufficient data for return."


def get_sentiment_inference(daily: pd.DataFrame, raw_count: int) -> str:
    if daily.empty or len(daily) < 2:
        return "Not enough daily sentiment yet. Run **Phase 2** to populate NLP signals."
    mean_now = daily["daily_mean_sentiment"].iloc[-1] if "daily_mean_sentiment" in daily.columns else 0
    mean_prev = daily["daily_mean_sentiment"].iloc[0] if len(daily) > 0 else 0
    trend = "improving" if mean_now > mean_prev else "weakening" if mean_now < mean_prev else "stable"
    return (
        f"**Sentiment trend:** {trend} over the period. "
        f"Latest daily mean: **{mean_now:.2f}** (−1 to +1 scale). "
        f"Based on **{raw_count}** document-level signals."
    )


def get_regime_inference(latest: Optional[dict], regime_df: pd.DataFrame) -> str:
    if not latest:
        return "No regime classification yet. Run **Phase 2 + 3** to generate sentiment and regime states."
    label = latest.get("regime_label") or "N/A"
    prob = latest.get("regime_probability") or latest.get("regime_prob_risk_off")
    pct = f"{float(prob):.0%}" if prob is not None else "N/A"
    conf = latest.get("confidence") or "N/A"
    if label == "Risk-Off":
        interp = "Market stress and risk aversion are elevated; defensive positioning may be warranted."
    elif label == "Risk-On":
        interp = "Risk appetite is elevated; growth and risk assets tend to perform relatively better."
    else:
        interp = "Regime is transitional; monitor for a shift toward Risk-On or Risk-Off."
    return (
        f"**Current regime:** **{label}** (probability {pct}, confidence {conf}). "
        f"{interp}"
    )


def get_dashboard_summary(counts: dict, regime: Optional[dict]) -> str:
    raw = counts.get("raw_articles", 0)
    processed = counts.get("documents_processed", 0)
    if raw == 0:
        return "No articles collected yet. Run **Phase 1** collectors, then preprocess and Phase 2+3."
    pct_processed = (100 * processed / raw) if raw else 0
    if not regime:
        return (
            f"**Data:** {raw:,} raw articles, {processed:,} processed ({pct_processed:.0f}%). "
            "Run **Phase 2 + 3** to compute sentiment and regime."
        )
    label = regime.get("regime_label") or "N/A"
    return (
        f"**Data:** {raw:,} raw articles, {processed:,} processed. "
        f"**Latest regime:** **{label}** — use Regime and AI Briefing pages for details."
    )


def get_market_link_inference(has_market: bool, has_regime: bool) -> str:
    if not has_market and not has_regime:
        return "Run **market_collector** and **run_phase2_and_3.py** to see SPY vs regime overlay."
    if not has_market:
        return "Run **python -m data.collectors.market_collector** to add SPY (and other tickers) for comparison."
    if not has_regime:
        return "Run **python run_phase2_and_3.py** to add regime series for overlay."
    return "**Inference:** Compare Regime (Risk-Off probability) with SPY price. Phase 4 will add Granger causality and predictive regression."


def get_topics_inference(has_topic_labels: bool, doc_volume_by_source: pd.DataFrame) -> str:
    if has_topic_labels:
        return "Topic distribution is driven by BERTopic on processed documents. Use filters to see prevalence by source."
    if doc_volume_by_source is not None and not doc_volume_by_source.empty:
        total = doc_volume_by_source.get("doc_count", pd.Series()).sum()
        return (
            f"**Document volume** by source (total {int(total):,} in range). "
            "Run **python -m models.topic_engine** to add BERTopic topic labels for narrative insight."
        )
    return "No document volume in range. Run preprocessing, then optionally **python -m models.topic_engine** for topic labels."
