"""
Earnings call transcript collector for ERIS.
Placeholder: use Kaggle datasets or external APIs; ingest into earnings_transcripts.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from data.storage.db_manager import get_connection

logger = logging.getLogger(__name__)

# Optional: path to a CSV/Parquet from Kaggle (e.g. Financial Phrasebank or S&P earnings)
KAGGLE_EARNINGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "earnings.csv"


def load_earnings_from_csv(path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load earnings transcript segments from a CSV.
    Expected columns: company, ticker, date, section, text, fiscal_quarter (optional).
    """
    path = path or KAGGLE_EARNINGS_PATH
    if not path.exists():
        logger.warning("Earnings file not found: %s. Add a CSV with company, ticker, date, section, text.", path)
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
    print(f"Stored {n} earnings transcript segments")
