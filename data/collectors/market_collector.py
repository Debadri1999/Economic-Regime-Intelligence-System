"""
Market and macro data collector for ERIS.
Uses yfinance for OHLCV and fredapi for FRED series; computes derived features.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv

from data.storage.db_manager import get_config, get_connection

load_dotenv()
logger = logging.getLogger(__name__)


def _load_market_config() -> dict:
    config = get_config()
    return config.get("data", {}).get("market", {})


def fetch_yfinance(
    tickers: Optional[List[str]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """Fetch daily OHLCV for given tickers. Returns long-format DataFrame with columns date, ticker, open, high, low, close, volume."""
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("yfinance is required. pip install yfinance")

    cfg = _load_market_config()
    tickers = tickers or cfg.get("yfinance_tickers", ["SPY", "^VIX", "GLD", "TLT", "HYG"])
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - timedelta(days=365 * 2)

    data = yf.download(
        tickers,
        start=start,
        end=end,
        progress=False,
        group_by="ticker",
        auto_adjust=True,
        threads=False,
    )
    if data.empty:
        return pd.DataFrame(columns=["date", "ticker", "open", "high", "low", "close", "volume"])

    # Handle single vs multiple tickers
    if len(tickers) == 1:
        data.columns = [c if isinstance(c, str) else c[0] for c in data.columns]
        data["ticker"] = tickers[0]
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data = data.stack(level=1).reset_index().rename(columns={"level_0": "date"})
        else:
            data = data.reset_index()
            data["ticker"] = tickers[0]

    data = data.rename(columns={
        "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume",
        "Adj Close": "close",
    })
    for c in ["open", "high", "low", "close", "volume"]:
        if c not in data.columns:
            data[c] = None
    data["date"] = pd.to_datetime(data.index if "date" not in data.columns else data["date"]).dt.date
    if "date" not in data.columns and hasattr(data.index, "date"):
        data["date"] = data.index
    return data[["date", "ticker", "open", "high", "low", "close", "volume"]].dropna(subset=["date"])


def compute_returns_and_vol(df: pd.DataFrame, windows: Optional[List[int]] = None) -> pd.DataFrame:
    """Add returns_1d, returns_5d, returns_21d, returns_63d, realized_vol_21d per ticker."""
    cfg = _load_market_config()
    windows = windows or cfg.get("rolling_windows", [5, 21, 63])
    df = df.sort_values(["ticker", "date"]).copy()
    df["returns_1d"] = df.groupby("ticker")["close"].pct_change()
    for w in windows:
        df[f"returns_{w}d"] = df.groupby("ticker")["close"].pct_change(w)
    df["realized_vol_21d"] = df.groupby("ticker")["returns_1d"].transform(
        lambda x: x.rolling(21, min_periods=5).std()
    )
    return df


def fetch_fred(
    series: Optional[List[str]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """Fetch FRED series. Returns DataFrame with date, indicator_name, value."""
    try:
        from fredapi import Fred
    except ImportError:
        raise ImportError("fredapi required. pip install fredapi")

    api_key = __import__("os").environ.get("FRED_API_KEY")
    if not api_key:
        logger.warning("FRED_API_KEY not set; skipping FRED fetch")
        return pd.DataFrame(columns=["date", "indicator_name", "value"])

    cfg = _load_market_config()
    series = series or cfg.get("fred_series", [])
    if not series:
        return pd.DataFrame(columns=["date", "indicator_name", "value"])

    fred = Fred(api_key=api_key)
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - timedelta(days=365 * 2)

    rows = []
    for s in series:
        try:
            ser = fred.get_series(s, start, end)
            if ser is not None and not ser.empty:
                for d, v in ser.items():
                    rows.append({"date": d.date(), "indicator_name": s, "value": float(v)})
        except Exception as e:
            logger.warning("FRED series %s failed: %s", s, e)
    return pd.DataFrame(rows)


def store_market_daily(df: pd.DataFrame) -> int:
    """Insert or replace market_daily rows. Returns number of rows written."""
    if df.empty:
        return 0
    cols = ["date", "ticker", "open", "high", "low", "close", "volume", "returns_1d", "returns_5d", "returns_21d", "returns_63d", "realized_vol_21d"]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].drop_duplicates(subset=["date", "ticker"])
    with get_connection() as conn:
        cur = conn.cursor()
        for _, row in df.iterrows():
            cur.execute(
                """INSERT OR REPLACE INTO market_daily
                   (date, ticker, open, high, low, close, volume, returns_1d, returns_5d, returns_21d, returns_63d, realized_vol_21d)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(row["date"]),
                    row["ticker"],
                    row.get("open"),
                    row.get("high"),
                    row.get("low"),
                    row.get("close"),
                    row.get("volume"),
                    row.get("returns_1d"),
                    row.get("returns_5d"),
                    row.get("returns_21d"),
                    row.get("returns_63d"),
                    row.get("realized_vol_21d"),
                ),
            )
    return len(df)


def store_macro_indicators(df: pd.DataFrame) -> int:
    """Insert or replace macro_indicators rows."""
    if df.empty:
        return 0
    with get_connection() as conn:
        cur = conn.cursor()
        for _, row in df.iterrows():
            cur.execute(
                """INSERT OR REPLACE INTO macro_indicators (date, indicator_name, value)
                   VALUES (?, ?, ?)""",
                (str(row["date"]), row["indicator_name"], row["value"]),
            )
    return len(df)


def collect_and_store_market(
    yf_tickers: Optional[List[str]] = None,
    fred_series: Optional[List[str]] = None,
    days: int = 730,
) -> dict:
    """
    Fetch yfinance + FRED, compute derived series, store to DB.
    Returns dict with market_daily and macro_indicators counts.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    counts = {"market_daily": 0, "macro_indicators": 0}

    try:
        df = fetch_yfinance(tickers=yf_tickers, start=start, end=end)
        if not df.empty:
            df = compute_returns_and_vol(df)
            counts["market_daily"] = store_market_daily(df)
    except Exception as e:
        logger.warning("yfinance fetch failed: %s", e)

    try:
        macro = fetch_fred(series=fred_series, start=start, end=end)
        if not macro.empty:
            counts["macro_indicators"] = store_macro_indicators(macro)
    except Exception as e:
        logger.warning("FRED fetch failed: %s", e)

    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from data.storage.db_manager import ensure_schema

    ensure_schema()
    counts = collect_and_store_market(days=365)
    print("Stored:", counts)
