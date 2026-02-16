"""
Database queries and caching for ERIS Streamlit app.
"""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import streamlit as st

from data.storage.db_manager import get_connection, get_database_url


@st.cache_data(ttl=300)
def load_regime_states(days: int = 365) -> pd.DataFrame:
    """Load regime_states for the last N days."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT date, regime_label, regime_probability, confidence, drivers,
                      regime_prob_risk_off, composite_prob
               FROM regime_states WHERE date IS NOT NULL ORDER BY date DESC LIMIT ?""",
            (days,),
        )
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
    if not rows:
        return pd.DataFrame(columns=columns or ["date", "regime_label", "regime_probability"])
    return pd.DataFrame(rows, columns=columns).sort_values("date").reset_index(drop=True)


@st.cache_data(ttl=300)
def load_nlp_signals(days: int = 365, source_type: Optional[str] = None) -> pd.DataFrame:
    """Load nlp_signals; optional filter by source_type."""
    with get_connection() as conn:
        cur = conn.cursor()
        if source_type:
            cur.execute(
                """SELECT * FROM nlp_signals WHERE date >= date('now', ?) AND source_type = ? ORDER BY date""",
                (f"-{days} days", source_type),
            )
        else:
            cur.execute(
                """SELECT * FROM nlp_signals WHERE date >= date('now', ?) ORDER BY date""",
                (f"-{days} days",),
            )
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=300)
def load_daily_sentiment(days: int = 365, source_type: Optional[str] = None) -> pd.DataFrame:
    """Aggregate nlp_signals by date (mean sentiment, doc count) for charts."""
    with get_connection() as conn:
        if source_type:
            q = """
                SELECT date, AVG(sentiment_score) AS daily_mean_sentiment, COUNT(*) AS doc_count
                FROM nlp_signals WHERE date >= date('now', ?) AND sentiment_score IS NOT NULL AND source_type = ?
                GROUP BY date ORDER BY date
            """
            params = (f"-{days} days", source_type)
        else:
            q = """
                SELECT date, AVG(sentiment_score) AS daily_mean_sentiment, COUNT(*) AS doc_count
                FROM nlp_signals WHERE date >= date('now', ?) AND sentiment_score IS NOT NULL
                GROUP BY date ORDER BY date
            """
            params = (f"-{days} days",)
        df = pd.read_sql_query(q, conn, params=params)
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(ttl=300)
def load_topic_distribution(days: int = 365) -> pd.DataFrame:
    """Topic counts from documents_processed.topic_hint (populated by BERTopic pipeline)."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """SELECT topic_hint AS topic_label, COUNT(*) AS doc_count
               FROM documents_processed
               WHERE topic_hint IS NOT NULL AND topic_hint != '' AND published_date >= date('now', ?)
               GROUP BY topic_hint ORDER BY doc_count DESC""",
            conn,
            params=(f"-{days} days",),
        )
    return df


@st.cache_data(ttl=300)
def load_document_topics(days: int = 365, limit: int = 200) -> pd.DataFrame:
    """Documents with topic labels for Topics page table (date, source_type, topic_label)."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """SELECT published_date AS date, source_type, topic_hint AS topic_label
               FROM documents_processed
               WHERE topic_hint IS NOT NULL AND topic_hint != '' AND published_date >= date('now', ?)
               ORDER BY published_date DESC LIMIT ?""",
            conn,
            params=(f"-{days} days", limit),
        )
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(ttl=300)
def load_market_daily(ticker: str = "SPY", days: int = 365) -> pd.DataFrame:
    """Load market_daily for one ticker."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT date, open, high, low, close, volume, returns_1d, returns_21d
               FROM market_daily WHERE ticker = ? AND date >= date('now', ?) ORDER BY date""",
            (ticker, f"-{days} days"),
        )
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
    if not rows:
        return pd.DataFrame(columns=columns or ["date", "close"])
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=600)
def get_document_counts() -> dict:
    """Return row counts for main tables."""
    from data.storage.db_manager import get_document_count
    return get_document_count()


def get_latest_regime() -> Optional[dict]:
    """Return most recent regime_states row as dict."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT date, regime_label, regime_probability, confidence, drivers, regime_prob_risk_off
               FROM regime_states ORDER BY date DESC LIMIT 1"""
        )
        row = cur.fetchone()
        cols = [d[0] for d in cur.description] if cur.description else []
    if not row or not cols:
        return None
    return dict(zip(cols, row))
