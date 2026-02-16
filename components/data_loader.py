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
            """SELECT date, regime_label, regime_probability, confidence, drivers
               FROM regime_states ORDER BY date DESC LIMIT 1"""
        )
        row = cur.fetchone()
        cols = [d[0] for d in cur.description] if cur.description else []
    if not row or not cols:
        return None
    return dict(zip(cols, row))
