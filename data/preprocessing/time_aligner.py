"""
Temporal alignment for ERIS: map documents to calendar/trading date.
Articles after market close (4 PM ET) assign to next trading day.
"""

from datetime import datetime, time, timedelta
from typing import Optional

from data.storage.db_manager import get_config


def _market_close_hour() -> int:
    cfg = get_config()
    return cfg.get("data", {}).get("preprocessing", {}).get("market_close_hour_et", 16)


def align_publish_to_date(
    published_at: Optional[datetime],
    market_close_hour_et: Optional[int] = None,
) -> Optional[datetime]:
    """
    Map publish timestamp to 'effective' date for market alignment.
    If published after market_close_hour_et (default 16), assign to next day.
    Simplified: assumes UTC input; for production use pytz for ET.
    """
    if published_at is None:
        return None
    close = market_close_hour_et if market_close_hour_et is not None else _market_close_hour()
    # Treat as UTC for simplicity; 4 PM ET ≈ 21:00 UTC (EDT) or 22:00 (EST)
    cutoff = time(20, 0)  # 8 PM UTC as proxy for 4 PM ET
    dt = published_at if isinstance(published_at, datetime) else datetime.fromisoformat(str(published_at))
    t = dt.time() if hasattr(dt, "time") else dt
    if hasattr(t, "hour") and t.hour >= cutoff.hour:
        return (dt.date() if hasattr(dt, "date") else dt) + timedelta(days=1)
    return dt.date() if hasattr(dt, "date") else dt


def to_date(d) -> Optional[str]:
    """Normalize to YYYY-MM-DD string."""
    if d is None:
        return None
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d")
    if isinstance(d, str) and len(d) >= 10:
        return d[:10]
    return str(d)
