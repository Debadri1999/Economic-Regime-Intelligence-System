"""
Federal Reserve document scraper for ERIS.
Targets FOMC statements, minutes, and speeches from federalreserve.gov.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from data.storage.db_manager import get_config, get_connection

logger = logging.getLogger(__name__)


def _load_fed_config() -> dict:
    config = get_config()
    return config.get("data", {}).get("fed", {})


def _fetch_soup(url: str) -> BeautifulSoup:
    base = _load_fed_config().get("base_url", "https://www.federalreserve.gov")
    full_url = url if url.startswith("http") else urljoin(base, url)
    resp = requests.get(full_url, timeout=30, headers={"User-Agent": "ERIS/1.0 (research)"})
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def _parse_date_from_text(text: str) -> Optional[datetime]:
    """Try to extract a date from Fed document text (e.g. 'March 15, 2023')."""
    if not text:
        return None
    # Common patterns
    for pattern in [
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        r"\d{4}-\d{2}-\d{2}",
        r"\d{1,2}/\d{1,2}/\d{4}",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                s = m.group(0)
                if "-" in s:
                    return datetime.strptime(s, "%Y-%m-%d")
                if "/" in s:
                    return datetime.strptime(s, "%m/%d/%Y")
                return datetime.strptime(s.replace(",", ""), "%B %d %Y")
            except ValueError:
                continue
    return None


def scrape_fomc_calendar_links() -> List[Tuple[str, str, Optional[datetime]]]:
    """
    Scrape FOMC calendar page for links to statements and minutes.
    Uses URL patterns (Fed links to /newsevents/pressreleases/monetary*.htm and /monetarypolicy/fomcminutes*.htm).
    Returns list of (doc_type, url, date).
    """
    cfg = _load_fed_config()
    base = cfg.get("base_url", "https://www.federalreserve.gov")
    path = cfg.get("fomc_calendar", "/monetarypolicy/fomccalendars.htm")
    url = urljoin(base, path)
    soup = _fetch_soup(url)
    results = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        full_url = urljoin(url, href)
        if full_url in seen_urls:
            continue
        text = (a.get_text() or "").strip().lower()
        doc_type = None
        if "/newsevents/pressreleases/monetary" in href and href.endswith(".htm") and ".pdf" not in href:
            doc_type = "fomc_statement"
        elif "/monetarypolicy/fomcminutes" in href and href.endswith(".htm") and ".pdf" not in href:
            doc_type = "fomc_minutes"
        elif "/monetarypolicy/fomcpressconf" in href or "/monetarypolicy/fomcpresconf" in href:
            doc_type = "fomc_press_conf"
        if not doc_type:
            continue
        seen_urls.add(full_url)
        date = _parse_date_from_text(a.get_text() or "") or _parse_date_from_url(href)
        results.append((doc_type, full_url, date))

    return results


def _parse_date_from_url(href: str) -> Optional[datetime]:
    """Extract date from Fed URL like monetary20250129a.htm or fomcminutes20250129.htm."""
    m = re.search(r"20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", href)
    if m:
        try:
            return datetime.strptime(m.group(0), "%Y%m%d")
        except ValueError:
            pass
    return None


def extract_text_from_html(soup: BeautifulSoup) -> str:
    """Extract main text from a Fed HTML page, stripping nav and boilerplate."""
    for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    body = soup.find("body") or soup
    return (body.get_text(separator="\n", strip=True) or "")


def scrape_speech_links(limit: int = 50) -> List[Tuple[str, str, Optional[datetime]]]:
    """
    Scrape Fed speeches page for recent speech links.
    Returns list of (doc_type, url, date).
    """
    cfg = _load_fed_config()
    base = cfg.get("base_url", "https://www.federalreserve.gov")
    path = cfg.get("speeches", "/newsevents/speeches.htm")
    url = urljoin(base, path)
    soup = _fetch_soup(url)
    results = []
    doc_type = "speech"

    for a in soup.find_all("a", href=True):
        if len(results) >= limit:
            break
        href = a.get("href", "")
        if "/newsevents/speech/" not in href:
            continue
        full_url = urljoin(url, href)
        date = _parse_date_from_text(a.get_text() or "")
        results.append((doc_type, full_url, date))

    return results


def fetch_and_extract_document(url: str) -> Tuple[str, str]:
    """Fetch URL and return (title, full_text). For HTML only; PDF handled separately."""
    soup = _fetch_soup(url)
    title = ""
    if soup.title:
        title = (soup.title.get_text() or "").strip()
    full_text = extract_text_from_html(soup)
    return title, full_text


def scrape_and_store_fed(
    fomc_limit: int = 100,
    speeches_limit: int = 30,
    backfill_from_year: Optional[int] = None,
) -> int:
    """
    Scrape FOMC calendar + speeches, fetch content, insert into fed_documents.
    Returns number of new rows inserted.
    """
    cfg = _load_fed_config()
    backfill_from_year = backfill_from_year or cfg.get("backfill_from_year", 2006)
    inserted = 0

    links: List[Tuple[str, str, Optional[datetime]]] = []
    try:
        links = scrape_fomc_calendar_links()
    except Exception as e:
        logger.warning("FOMC calendar scrape failed: %s", e)

    for doc_type, doc_url, doc_date in links[:fomc_limit]:
        if doc_date and doc_date.year < backfill_from_year:
            continue
        try:
            if doc_url.lower().endswith(".pdf"):
                continue
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM fed_documents WHERE url = ? LIMIT 1", (doc_url,))
                if cur.fetchone():
                    continue
            title, full_text = fetch_and_extract_document(doc_url)
            if len(full_text) < 100:
                continue
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO fed_documents (doc_type, title, full_text, date, url)
                       VALUES (?, ?, ?, ?, ?)""",
                    (doc_type, title, full_text, doc_date.date() if doc_date else None, doc_url),
                )
                inserted += 1
        except Exception as e:
            logger.warning("Failed to process %s: %s", doc_url, e)

    try:
        speech_links = scrape_speech_links(limit=speeches_limit)
        for doc_type, doc_url, doc_date in speech_links:
            try:
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM fed_documents WHERE url = ? LIMIT 1", (doc_url,))
                    if cur.fetchone():
                        continue
                title, full_text = fetch_and_extract_document(doc_url)
                if len(full_text) < 100:
                    continue
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """INSERT INTO fed_documents (doc_type, title, full_text, date, url)
                           VALUES (?, ?, ?, ?, ?)""",
                        (doc_type, title, full_text, doc_date.date() if doc_date else None, doc_url),
                    )
                    inserted += 1
            except Exception as e:
                logger.warning("Failed speech %s: %s", doc_url, e)
    except Exception as e:
        logger.warning("Speeches scrape failed: %s", e)

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from data.storage.db_manager import ensure_schema

    ensure_schema()
    n = scrape_and_store_fed(fomc_limit=20, speeches_limit=10)
    print(f"Inserted {n} Fed documents")
