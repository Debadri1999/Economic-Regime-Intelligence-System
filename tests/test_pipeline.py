"""Smoke tests for ERIS data pipeline."""
import pytest
from pathlib import Path

# Ensure we can load project modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_config_loads():
    from data.storage.db_manager import get_config
    cfg = get_config()
    assert isinstance(cfg, dict)
    assert "data" in cfg or cfg == {}


def test_schema_init():
    from data.storage.db_manager import ensure_schema, get_connection, get_database_url
    ensure_schema()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM raw_articles LIMIT 1")
        cur.fetchone()
    # Table raw_articles exists (no error)
    assert get_database_url()
