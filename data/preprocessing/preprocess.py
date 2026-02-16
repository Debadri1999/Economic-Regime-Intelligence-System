"""
ERIS preprocessing pipeline: clean, deduplicate, language filter, time-align, enrich metadata.
Reads from raw_articles + fed_documents + earnings_transcripts; writes to documents_processed.
"""

import logging
from datetime import datetime
from typing import Optional

from data.storage.db_manager import get_connection, get_config
from data.preprocessing.cleaner import clean_document
from data.preprocessing.deduplicator import minhash_fingerprint, is_duplicate
from data.preprocessing.time_aligner import align_publish_to_date, to_date

logger = logging.getLogger(__name__)


def _language_is_english(text: str) -> bool:
    """Keep English-only. Uses langdetect if available."""
    if not text or len(text) < 50:
        return True
    try:
        import langdetect
        return langdetect.detect(text) == "en"
    except Exception:
        return True


def _min_word_count(text: str, min_w: Optional[int] = None) -> bool:
    cfg = get_config()
    if min_w is None:
        min_w = cfg.get("data", {}).get("preprocessing", {}).get("min_word_count", 20)
    return len((text or "").split()) >= min_w


def run_preprocess_batch(
    source_table: str,
    source_type: str,
    id_col: str,
    title_col: str,
    content_col: str,
    date_col: Optional[str],
    limit: int = 5000,
) -> int:
    """
    Process rows from a source table into documents_processed.
    Skips rows already in documents_processed (same source_id + source_table).
    Returns number of rows inserted.
    """
    threshold = get_config().get("data", {}).get("preprocessing", {}).get("dedup_jaccard_threshold", 0.85)
    inserted = 0

    select_cols = [id_col, title_col, content_col]
    if date_col:
        select_cols.append(date_col)
    cols_sql = ", ".join(select_cols)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {source_table}")
        source_count = cur.fetchone()[0]
        cur.execute(
            f"SELECT {cols_sql} FROM {source_table} ORDER BY id LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        # Already-processed source IDs (so we skip re-cleaning and report accurately)
        cur.execute(
            "SELECT source_id FROM documents_processed WHERE source_table = ?",
            (source_table,),
        )
        already_processed_ids = {row[0] for row in cur.fetchall()}
        cur.execute("SELECT minhash_fingerprint FROM documents_processed WHERE minhash_fingerprint IS NOT NULL")
        existing_fps = [row[0] for row in cur.fetchall()]

    skipped_already = 0
    for row in rows:
        doc_id = row[0]
        if doc_id in already_processed_ids:
            skipped_already += 1
            continue
        doc_id, title, content = row[0], row[1], row[2]
        pub = row[3] if date_col and len(row) > 3 else None
        if not content or not _min_word_count(content):
            continue
        if not _language_is_english(content):
            continue
        content_clean, sentences, word_count = clean_document(content, title=title, preserve_case=False)
        if word_count < 20:
            continue
        fp = minhash_fingerprint(content_clean)
        if is_duplicate(content_clean, existing_fps, threshold=threshold):
            continue
        if fp:
            existing_fps.append(fp)
        published_date = None
        if pub:
            try:
                if isinstance(pub, str):
                    pub = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                published_date = align_publish_to_date(pub)
                if hasattr(published_date, "strftime"):
                    published_date = published_date.strftime("%Y-%m-%d")
                else:
                    published_date = to_date(published_date)
            except Exception:
                published_date = to_date(pub)
        content_sentences = "\n".join(sentences) if sentences else ""
        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT INTO documents_processed
                       (source_id, source_table, source_type, title, content_clean, content_sentences, published_date, word_count, minhash_fingerprint)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (doc_id, source_table, source_type, title, content_clean, content_sentences, published_date, word_count, fp),
                )
            inserted += 1
        except Exception as e:
            logger.debug("Skip insert: %s", e)

    if source_count > 0 or inserted > 0 or skipped_already > 0:
        logger.info(
            "%s: %d in source, %d already in docs_processed, %d new inserted",
            source_table, min(source_count, limit), skipped_already, inserted,
        )
    return inserted


def run_full_preprocess(limit_per_source: int = 5000) -> dict:
    """
    Run preprocessing for raw_articles, fed_documents, earnings_transcripts.
    Returns counts per source.
    """
    counts = {}
    # raw_articles
    try:
        counts["raw_articles"] = run_preprocess_batch(
            "raw_articles", "news", "id", "title", "content", "published_at", limit=limit_per_source
        )
    except Exception as e:
        logger.warning("Preprocess raw_articles failed: %s", e)
        counts["raw_articles"] = 0
    # fed_documents
    try:
        counts["fed_documents"] = run_preprocess_batch(
            "fed_documents", "fed", "id", "title", "full_text", "date", limit=limit_per_source
        )
    except Exception as e:
        logger.warning("Preprocess fed_documents failed: %s", e)
        counts["fed_documents"] = 0
    # earnings_transcripts
    try:
        counts["earnings_transcripts"] = run_preprocess_batch(
            "earnings_transcripts", "earnings", "id", "company", "text", "date", limit=limit_per_source
        )
    except Exception as e:
        logger.warning("Preprocess earnings_transcripts failed: %s", e)
        counts["earnings_transcripts"] = 0
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from data.storage.db_manager import ensure_schema, get_document_count

    ensure_schema()
    # Show source table counts so user knows why counts might be 0
    doc_counts = get_document_count()
    print("Source rows in DB: raw_articles=%s, fed_documents=%s, earnings_transcripts=%s"
          % (doc_counts.get("raw_articles", 0), doc_counts.get("fed_documents", 0), doc_counts.get("earnings_transcripts", 0)))
    counts = run_full_preprocess(limit_per_source=5000)
    print("Newly processed (inserted this run):", counts)
