"""
Kaggle dataset collector for ERIS.
Downloads financial news and/or earnings datasets from Kaggle and ingests into raw_articles.

Credentials: set KAGGLE_USERNAME and KAGGLE_KEY in .env (or use kaggle.json in ~/.kaggle/).
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

from data.storage.db_manager import get_connection

# Load .env so KAGGLE_USERNAME and KAGGLE_KEY are available to the Kaggle API
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
KAGGLE_DIR = RAW_DIR / "kaggle"

# Multiple Kaggle datasets. File names vary; we also support .txt folders and JSON.
DATASETS = {
    "financial_news_ankurzing": {
        "slug": "ankurzing/sentiment-analysis-for-financial-news",
        "table": "raw_articles",
        "file": "all-data.csv",
    },
    "financial_news_ticker": {
        "slug": "rdolphin/financial-news-with-ticker-level-sentiment",
        "table": "raw_articles",
        "file": "polygon_news_sample.json",
    },
    "finance_news_sentiments": {
        "slug": "antobenedetti/finance-news-sentiments",
        "table": "raw_articles",
        "file": None,
    },
    "earnings_nasdaq": {
        "slug": "ashwinm500/earnings-call-transcripts",
        "table": "earnings_transcripts",
        "file": "txt_folder",
    },
}


def _url_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def ensure_kaggle_auth() -> bool:
    """Check that Kaggle API is installed and authenticated."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        return True
    except Exception as e:
        msg = str(e).lower()
        if "authenticate" in msg or "credentials" in msg or "401" in msg:
            print("\n  Kaggle API requires authentication.")
            print("  1. Go to https://www.kaggle.com/settings")
            print("  2. Click 'Create New Token' to download kaggle.json")
            print("  3. Create folder:  %USERPROFILE%\\.kaggle\\  (Windows)  or  ~/.kaggle/  (Mac/Linux)")
            print("  4. Move kaggle.json into that folder (no other files in .kaggle)")
            print("  5. Run this script again.\n")
        logger.warning("Kaggle API: %s", e)
        return False


def download_dataset(slug: str, dest: Optional[Path] = None, unzip: bool = True) -> Path:
    """Download a Kaggle dataset by slug (e.g. ankurzing/sentiment-analysis-for-financial-news). Returns path to folder."""
    if not ensure_kaggle_auth():
        raise RuntimeError("Kaggle API not authenticated")
    dest = dest or (KAGGLE_DIR / slug.replace("/", "_"))
    dest.mkdir(parents=True, exist_ok=True)
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.dataset_download_files(slug, path=str(dest), unzip=unzip)
    return dest


def load_csv_from_download(dest_folder: Path, filename: Optional[str]) -> pd.DataFrame:
    """Load a CSV from the downloaded folder (may be in a subfolder after unzip). Handles non-UTF-8 encodings."""
    candidates = []
    if filename and filename != "txt_folder":
        candidates = list(dest_folder.rglob(filename))
    if not candidates:
        candidates = list(dest_folder.rglob("*.csv"))
    if not candidates:
        return pd.DataFrame()
    path = candidates[0]
    try:
        df = pd.read_csv(path, nrows=50000, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(path, nrows=50000, encoding="latin-1")
        except Exception:
            df = pd.read_csv(path, nrows=50000, encoding="utf-8", errors="replace")
    return df


def load_json_from_download(dest_folder: Path, filename: str) -> pd.DataFrame:
    """Load a JSON file (or first JSON in folder) into a DataFrame."""
    candidates = list(dest_folder.rglob(filename)) if filename else []
    if not candidates:
        candidates = list(dest_folder.rglob("*.json"))
    if not candidates:
        return pd.DataFrame()
    path = candidates[0]
    try:
        import json
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            if "results" in data:
                return pd.DataFrame(data["results"])
            if "data" in data:
                return pd.DataFrame(data["data"])
            return pd.DataFrame([data])
    except Exception as e:
        logger.warning("JSON load failed %s: %s", path, e)
    return pd.DataFrame()


def load_earnings_txt_folder(dest_folder: Path) -> pd.DataFrame:
    """Load earnings from ashwinm500 structure: Transcripts/TICKER/date-TICKER.txt."""
    rows = []
    transcripts_dir = dest_folder / "Transcripts"
    if not transcripts_dir.exists():
        return pd.DataFrame()
    for ticker_dir in transcripts_dir.iterdir():
        if not ticker_dir.is_dir():
            continue
        ticker = ticker_dir.name
        for txt_path in ticker_dir.glob("*.txt"):
            try:
                text = txt_path.read_text(encoding="utf-8", errors="replace").strip()
                if len(text) < 50:
                    continue
                name = txt_path.stem
                parts = name.split("-")
                date_str = None
                if len(parts) >= 3:
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(f"{parts[0]}-{parts[1]}-{parts[2]}", "%Y-%b-%d")
                        date_str = dt.strftime("%Y-%m-%d")
                    except Exception:
                        date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
                rows.append({"company": ticker, "ticker": ticker, "date": date_str, "section": "full", "text": text})
            except Exception as e:
                logger.debug("Skip %s: %s", txt_path, e)
    return pd.DataFrame(rows)


def _detect_text_column(df: pd.DataFrame) -> str:
    """Pick the column most likely to contain article/headline text (by name or longest strings)."""
    for pattern in ("headline", "headlines", "sentence", "text", "content", "news", "body", "article", "title", "summary"):
        for c in df.columns:
            if pattern in c.lower():
                return c
    # Fallback: column with highest average string length (skip short label columns like Sentiment)
    numeric_or_short = [c for c in df.columns if df[c].astype(str).str.len().mean() > 8]
    if numeric_or_short:
        return max(numeric_or_short, key=lambda c: df[c].astype(str).str.len().mean())
    return df.columns[0]


def ingest_financial_news_to_raw_articles(df: pd.DataFrame, source: str = "kaggle") -> int:
    """Map a financial news DataFrame to raw_articles and insert. Returns count inserted."""
    if df.empty:
        return 0
    content_col = _detect_text_column(df)
    title_col = "title" if "title" in df.columns else "News Headline" if "News Headline" in df.columns else content_col
    date_col = "date" if "date" in df.columns else "Date" if "Date" in df.columns else "published" if "published" in df.columns else None
    min_len = 10
    inserted = 0
    with get_connection() as conn:
        cur = conn.cursor()
        for idx, row in df.iterrows():
            content = str(row.get(content_col, "")).strip()
            if not content or len(content) < min_len:
                continue
            title = str(row.get(title_col, content))[:500] if title_col else content[:200]
            fake_url = f"https://kaggle.com/{source}/{idx}"
            url_hash = _url_hash(fake_url)
            pub = row.get(date_col) if date_col else None
            pub_str = None
            if pub is not None and pd.notna(pub):
                try:
                    pub_str = pd.to_datetime(pub).strftime("%Y-%m-%d")
                except Exception:
                    pub_str = str(pub)[:10]
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO raw_articles
                       (source, title, content, description, published_at, url, url_hash, query_term, source_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source, title, content, content[:500], pub_str, fake_url, url_hash, "kaggle", "news"),
                )
                if getattr(cur, "rowcount", 0) and cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.debug("Skip row: %s", e)
    return inserted


def _detect_earnings_text_column(df: pd.DataFrame) -> str:
    """Pick column that contains transcript/text for earnings."""
    for pattern in ("transcript", "text", "content", "body", "speech", "call"):
        for c in df.columns:
            if pattern in c.lower():
                return c
    long_cols = [c for c in df.columns if df[c].astype(str).str.len().mean() > 50]
    return long_cols[0] if long_cols else df.columns[0]


def ingest_earnings_to_transcripts(df: pd.DataFrame, source: str = "kaggle") -> int:
    """Map DataFrame to earnings_transcripts. Auto-detect company, date, text columns. Returns count inserted."""
    if df.empty:
        return 0
    text_col = _detect_earnings_text_column(df)
    company_col = next((c for c in df.columns if "compan" in c.lower() or "name" in c.lower()), df.columns[0])
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    ticker_col = next((c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()), None)
    section_col = next((c for c in df.columns if "section" in c.lower() or "type" in c.lower()), None)
    inserted = 0
    with get_connection() as conn:
        cur = conn.cursor()
        for idx, row in df.iterrows():
            text = str(row.get(text_col, "")).strip()
            if not text or len(text) < 30:
                continue
            company = str(row.get(company_col, ""))[:128] if company_col else ""
            ticker = str(row.get(ticker_col, ""))[:16] if ticker_col else None
            section = str(row.get(section_col, ""))[:64] if section_col else "full"
            pub_str = None
            if date_col and row.get(date_col) is not None and pd.notna(row.get(date_col)):
                try:
                    pub_str = pd.to_datetime(row[date_col]).strftime("%Y-%m-%d")
                except Exception:
                    pub_str = str(row[date_col])[:10]
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO earnings_transcripts (company, ticker, date, section, text, fiscal_quarter)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (company or None, ticker, pub_str, section, text, None),
                )
                if getattr(cur, "rowcount", 0) and cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.debug("Skip earnings row: %s", e)
    return inserted


def collect_and_store_kaggle(
    dataset_key: str = "financial_news_ankurzing",
    max_rows: Optional[int] = 50000,
) -> dict:
    """
    Download one Kaggle dataset and ingest into raw_articles.
    dataset_key: one of DATASETS keys (financial_news_ankurzing, financial_news_ticker, etc.).
    Returns dict with path, rows inserted, table.
    """
    if dataset_key not in DATASETS:
        raise ValueError("dataset_key must be one of %s" % list(DATASETS.keys()))
    meta = DATASETS[dataset_key]
    slug = meta["slug"]
    table = meta["table"]
    filename = meta.get("file")
    KAGGLE_DIR.mkdir(parents=True, exist_ok=True)
    dest = KAGGLE_DIR / slug.replace("/", "_")
    if filename == "txt_folder" and (dest / "Transcripts").exists():
        df = load_earnings_txt_folder(dest)
    else:
        dest = download_dataset(slug, dest=dest, unzip=True)
        df = pd.DataFrame()
    if filename == "txt_folder" and df.empty:
        df = load_earnings_txt_folder(dest)
    elif filename and filename.endswith(".json"):
        df = load_json_from_download(dest, filename)
        if df.empty:
            df = load_json_from_download(dest, None)
    if df.empty and table != "earnings_transcripts":
        df = load_csv_from_download(dest, filename)
    if df.empty and table == "earnings_transcripts" and filename == "txt_folder":
        df = load_earnings_txt_folder(dest)
    if df.empty:
        logger.warning("No data file found in %s", dest)
        return {"dataset": dataset_key, "path": str(dest), "rows": 0, "table": table}
    if max_rows:
        df = df.head(max_rows)
    if table == "earnings_transcripts":
        inserted = ingest_earnings_to_transcripts(df, source=dataset_key)
    else:
        inserted = ingest_financial_news_to_raw_articles(df, source=dataset_key)
    return {"dataset": dataset_key, "path": str(dest), "rows": inserted, "table": table}


def collect_all_kaggle(max_rows_per_dataset: Optional[int] = 50000) -> dict:
    """Download and ingest all configured Kaggle datasets. Returns total rows and per-dataset results."""
    from data.storage.db_manager import ensure_schema
    ensure_schema()
    total = 0
    results = []
    for key in DATASETS:
        try:
            out = collect_and_store_kaggle(key, max_rows=max_rows_per_dataset)
            total += out.get("rows", 0)
            results.append(out)
            print("  %s: %d rows" % (key, out.get("rows", 0)))
        except Exception as e:
            logger.warning("Dataset %s failed: %s", key, e)
            results.append({"dataset": key, "rows": 0, "error": str(e)})
    return {"total_rows": total, "results": results}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from data.storage.db_manager import ensure_schema

    ensure_schema()
    print("Fetching from multiple Kaggle datasets...")
    try:
        summary = collect_all_kaggle(max_rows_per_dataset=50000)
        print("Kaggle ingest total: %d rows" % summary["total_rows"])
        print("Details:", summary["results"])
    except Exception as e:
        if "authenticate" in str(e).lower():
            print("Fix: set KAGGLE_USERNAME and KAGGLE_KEY in .env")
        else:
            print("Kaggle collect failed:", e)
