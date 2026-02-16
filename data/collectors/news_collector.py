"""
NewsAPI collector for ERIS.
Cycles through regime-relevant queries, deduplicates by URL hash, stores raw JSON and extracted fields.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any, List, Optional

import requests
from dotenv import load_dotenv

from data.storage.db_manager import get_config, get_connection

load_dotenv()
logger = logging.getLogger(__name__)


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _load_newsapi_config() -> dict:
    config = get_config()
    return config.get("data", {}).get("newsapi", {})


def fetch_newsapi(
    query: str,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page_size: int = 20,
    api_key: Optional[str] = None,
) -> List[dict]:
    """
    Fetch one page of results from NewsAPI for a given query.
    Returns list of article dicts with title, description, content, source, publishedAt, url.
    """
    api_key = api_key or os.getenv("NEWSAPI_KEY")
    if not api_key:
        raise ValueError("NEWSAPI_KEY not set in environment or .env")

    base = _load_newsapi_config().get("base_url", "https://newsapi.org/v2/everything")
    if not from_date:
        from_date = datetime.utcnow() - timedelta(days=7)
    if not to_date:
        to_date = datetime.utcnow()

    params = {
        "q": query,
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
        "pageSize": min(page_size, 100),
        "apiKey": api_key,
        "language": "en",
        "sortBy": "relevancy",
    }
    resp = requests.get(base, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"NewsAPI error: {data.get('message', 'unknown')}")
    return data.get("articles", [])


def article_to_row(article: dict, query_term: str) -> Optional[dict]:
    """Extract and normalize one article into a row for raw_articles."""
    url = (article.get("url") or "").strip()
    if not url:
        return None
    title = (article.get("title") or "").strip() or "(No title)"
    desc = (article.get("description") or "").strip()
    content = (article.get("content") or "").strip()
    source_name = (article.get("source") or {})
    if isinstance(source_name, dict):
        source_name = source_name.get("name", "unknown")
    published = article.get("publishedAt")
    if published:
        try:
            if published.endswith("Z"):
                published = published.replace("Z", "+00:00")
            published = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except Exception:
            published = None
    return {
        "source": source_name,
        "title": title,
        "content": content or desc,
        "description": desc,
        "published_at": published,
        "url": url,
        "url_hash": _url_hash(url),
        "query_term": query_term,
        "source_type": "news",
    }


def collect_and_store(
    queries: Optional[List[str]] = None,
    max_per_query: int = 20,
    from_days_ago: int = 7,
) -> int:
    """
    Run query rotation: for each query fetch up to max_per_query results,
    deduplicate by url_hash, insert new rows into raw_articles.
    Returns number of new articles inserted.
    """
    cfg = _load_newsapi_config()
    queries = queries or cfg.get("queries", [])
    max_per_query = min(max_per_query, cfg.get("max_results_per_query", 20))
    from_date = datetime.utcnow() - timedelta(days=from_days_ago)
    to_date = datetime.utcnow()

    seen_hashes = set()
    to_insert: List[dict] = []

    for query in queries:
        try:
            articles = fetch_newsapi(
                query,
                from_date=from_date,
                to_date=to_date,
                page_size=max_per_query,
            )
            for art in articles:
                row = article_to_row(art, query)
                if not row or row["url_hash"] in seen_hashes:
                    continue
                seen_hashes.add(row["url_hash"])
                to_insert.append(row)
        except Exception as e:
            logger.warning("NewsAPI query '%s' failed: %s", query, e)
            continue

    if not to_insert:
        return 0

    with get_connection() as conn:
        cur = conn.cursor()
        for row in to_insert:
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO raw_articles
                       (source, title, content, description, published_at, url, url_hash, query_term, source_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row["source"],
                        row["title"],
                        row["content"],
                        row["description"],
                        row["published_at"],
                        row["url"],
                        row["url_hash"],
                        row["query_term"],
                        row["source_type"],
                    ),
                )
            except Exception as e:
                logger.debug("Skip duplicate or error: %s", e)
        inserted = cur.rowcount if hasattr(cur, "rowcount") else len(to_insert)
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from data.storage.db_manager import ensure_schema

    ensure_schema()
    n = collect_and_store(queries=["inflation", "recession"], max_per_query=10, from_days_ago=3)
    print(f"Inserted {n} new articles")
