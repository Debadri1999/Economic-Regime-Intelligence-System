"""
Earnings call transcript collector for ERIS.
Option A: Place a CSV at data/raw/earnings.csv (columns: company, ticker, date, section, text).
Option B: Run Kaggle earnings download: python -m data.collectors.kaggle_collector (includes earnings_nasdaq).
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from data.storage.db_manager import get_connection

logger = logging.getLogger(__name__)

KAGGLE_EARNINGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "earnings.csv"


def load_earnings_from_csv(path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load earnings transcript segments from a CSV.
    Expected columns: company, ticker, date, section, text, fiscal_quarter (optional).
    """
    path = path or KAGGLE_EARNINGS_PATH
    if not path.exists():
        logger.warning("Earnings file not found: %s", path)
        print("  No earnings data. Either:\n    1. Add a CSV at data/raw/earnings.csv (company, ticker, date, section, text)\n    2. Run: python -m data.collectors.kaggle_collector  (downloads earnings_nasdaq into earnings_transcripts)")
        return pd.DataFrame()
    df = pd.read_csv(path, nrows=10000)
    for c in ["company", "ticker", "date", "section", "text"]:
        if c not in df.columns:
            df[c] = "" if c == "text" else None
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["text"])


def store_earnings(df: pd.DataFrame) -> int:
    """Insert rows into earnings_transcripts. Returns count inserted."""
    if df.empty:
        return 0
    with get_connection() as conn:
        cur = conn.cursor()
        for _, row in df.iterrows():
            cur.execute(
                """INSERT OR IGNORE INTO earnings_transcripts (company, ticker, date, section, text, fiscal_quarter)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    row.get("company"),
                    row.get("ticker"),
                    str(row["date"]) if row.get("date") else None,
                    row.get("section"),
                    row["text"],
                    row.get("fiscal_quarter"),
                ),
            )
    return len(df)


def collect_and_store_earnings(csv_path: Optional[Path] = None) -> int:
    """Load from CSV and store. Returns number of rows stored."""
    df = load_earnings_from_csv(csv_path)
    return store_earnings(df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from data.storage.db_manager import ensure_schema

    ensure_schema()
    n = collect_and_store_earnings()
    if n == 0:
        print("Stored 0 segments. See message above for how to add earnings data.")
    else:
        print(f"Stored {n} earnings transcript segments")
