"""
Run ERIS data pipeline from the Streamlit app (backend).
Steps: schema -> market -> news -> fed -> preprocess -> sentiment -> regime -> (optional) topics.
Uses conservative limits so the run can complete on Streamlit Cloud.
"""

import os
from typing import Callable, List, Tuple

# Step = (display_name, callable that returns result message or raises)
Step = Tuple[str, Callable[[], str]]


def _step_schema() -> str:
    from data.storage.db_manager import ensure_schema
    ensure_schema()
    return "Schema ready."


def _step_market(days: int = 90) -> str:
    from data.collectors.market_collector import collect_and_store_market
    out = collect_and_store_market(days=days)
    n = out.get("market_daily", 0)
    return f"Market: {n} rows stored."


def _step_news(max_per_query: int = 15, from_days_ago: int = 7) -> str:
    if not os.getenv("NEWS_API_KEY", "").strip() and not os.getenv("NEWSAPI_KEY", "").strip():
        return "Skipped (no NEWS_API_KEY)."
    from data.collectors.news_collector import collect_and_store
    n = collect_and_store(max_per_query=max_per_query, from_days_ago=from_days_ago)
    return f"News: {n} articles stored."


def _step_fed(fomc_limit: int = 10, speeches_limit: int = 5) -> str:
    from data.collectors.fed_scraper import scrape_and_store_fed
    n = scrape_and_store_fed(fomc_limit=fomc_limit, speeches_limit=speeches_limit)
    return f"Fed: {n} documents stored."


def _step_preprocess(limit_per_source: int = 2000) -> str:
    from data.preprocessing.preprocess import run_full_preprocess
    counts = run_full_preprocess(limit_per_source=limit_per_source)
    total = sum(counts.values())
    return f"Preprocess: {total} docs processed."


def _step_sentiment(limit: int = 800) -> str:
    from models.sentiment_engine import run_sentiment_on_processed
    n = run_sentiment_on_processed(limit=limit)
    return f"Sentiment: {n} signals written."


def _step_regime() -> str:
    from models.regime_detector import run_regime_pipeline
    n = run_regime_pipeline()
    return f"Regime: {n} states written."


def _step_topics(limit: int = 400) -> str:
    from models.topic_engine import run_topic_pipeline
    n = run_topic_pipeline(limit=limit)
    return f"Topics: {n} docs labeled."


def get_pipeline_steps(
    include_news: bool = True,
    include_fed: bool = True,
    include_topics: bool = False,
    market_days: int = 90,
    sentiment_limit: int = 800,
    topic_limit: int = 400,
) -> List[Step]:
    """
    Return list of (step_name, callable) for the pipeline.
    include_topics=False by default (BERTopic is slow; enable for full Topics page).
    """
    steps: List[Step] = [
        ("Schema", _step_schema),
        ("Market (SPY, etc.)", lambda: _step_market(days=market_days)),
        ("Preprocess", lambda: _step_preprocess()),
        ("Sentiment (FinBERT)", lambda: _step_sentiment(limit=sentiment_limit)),
        ("Regime (HMM)", _step_regime),
    ]
    if include_news:
        steps.insert(2, ("News", lambda: _step_news()))
    else:
        steps.insert(2, ("News (skipped)", lambda: "Skipped (no NEWS_API_KEY)."))
    if include_fed:
        steps.insert(3, ("Fed documents", lambda: _step_fed()))
    else:
        steps.insert(3, ("Fed (skipped)", lambda: "Skipped."))
    if include_topics:
        steps.append(("Topics (BERTopic)", lambda: _step_topics(limit=topic_limit)))
    return steps


def run_pipeline(
    steps: List[Step],
    on_progress: Callable[[str, str], None],
) -> List[Tuple[str, str, bool]]:
    """
    Run each step; call on_progress(step_name, message) after each.
    Returns list of (step_name, message, success).
    """
    results: List[Tuple[str, str, bool]] = []
    for name, fn in steps:
        try:
            msg = fn()
            results.append((name, msg, True))
            on_progress(name, msg)
        except Exception as e:
            msg = str(e)
            results.append((name, msg, False))
            on_progress(name, f"Error: {msg}")
    return results
