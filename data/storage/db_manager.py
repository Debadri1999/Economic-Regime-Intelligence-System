"""
ERIS Database Manager
Handles connection, schema initialization, and common queries.
Supports SQLite (default/MVP) and PostgreSQL via DATABASE_URL.
"""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Iterator

import yaml
from dotenv import load_dotenv

load_dotenv()

# Project root (parent of data/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_config() -> dict:
    """Load config.yaml from project root."""
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_database_url() -> str:
    """Return DATABASE_URL from env or default SQLite path."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    db_dir = PROJECT_ROOT / "data" / "raw"
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_dir / 'eris.db'}"


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


@contextmanager
def get_connection():
    """Context manager for database connection. Use for SQLite or psycopg2."""
    url = get_database_url()
    if _is_sqlite(url):
        path = url.replace("sqlite:///", "")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    else:
        try:
            import psycopg2
            from urllib.parse import urlparse
            parsed = urlparse(url)
            conn = psycopg2.connect(
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port or 5432,
            )
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        except ImportError:
            raise RuntimeError("PostgreSQL requires psycopg2. Install with: pip install psycopg2-binary")


def init_schema(conn) -> None:
    """Execute schema.sql to create tables."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    if _is_sqlite(get_database_url()):
        conn.executescript(sql)
    else:
        cur = conn.cursor()
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--"):
                cur.execute(statement)
        cur.close()


def ensure_schema() -> None:
    """Create database and tables if they do not exist."""
    with get_connection() as conn:
        init_schema(conn)


def get_document_count() -> dict:
    """Return approximate row counts for main tables (for README/status)."""
    counts = {}
    with get_connection() as conn:
        for table in (
            "raw_articles",
            "fed_documents",
            "earnings_transcripts",
            "market_daily",
            "macro_indicators",
            "documents_processed",
            "nlp_signals",
            "regime_states",
        ):
            try:
                cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            except Exception:
                counts[table] = 0
    return counts
