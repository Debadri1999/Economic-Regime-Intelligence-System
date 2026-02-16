"""
ERIS Topic & Narrative Intelligence (BERTopic).
Phase 2. Fit on corpus; topics_over_time; store topic_id / topic_label in nlp_signals.
"""

import logging
from typing import List, Optional

from data.storage.db_manager import get_config, get_connection

logger = logging.getLogger(__name__)


def fit_bertopic(documents: List[str], **kwargs) -> object:
    """Fit BERTopic on document list. Returns fitted model.
    Uses smaller cluster sizes for small corpora so more docs get real topics (not all 'Other'/outlier).
    """
    try:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
        import umap
        import hdbscan
        cfg = get_config()
        emb_model = cfg.get("nlp", {}).get("sentence_transformer", "all-MiniLM-L6-v2")
        bt_cfg = cfg.get("nlp", {}).get("bertopic", {})
        n_docs = len(documents)
        # On Streamlit/small runs, default 15/5 often puts everything in outlier; use smaller clusters
        default_min_size = bt_cfg.get("hdbscan_min_cluster_size", 15)
        default_min_samples = bt_cfg.get("hdbscan_min_samples", 5)
        min_cluster_size = max(3, min(default_min_size, max(5, n_docs // 30)))
        min_samples = max(2, min(default_min_samples, max(3, n_docs // 100)))
        model = BERTopic(
            embedding_model=SentenceTransformer(emb_model),
            umap_model=umap.UMAP(
                n_neighbors=min(bt_cfg.get("umap_n_neighbors", 15), max(5, n_docs // 10)),
                n_components=min(bt_cfg.get("umap_n_components", 5), max(2, n_docs // 50)),
                min_dist=0.0,
            ),
            hdbscan_model=hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
            ),
            **kwargs,
        )
        model.fit(documents)
        return model
    except ImportError as e:
        logger.warning("BERTopic deps missing: %s", e)
        return None


def _topic_labels_from_model(model) -> dict:
    """Build topic_id -> label from BERTopic model. -1 -> Outlier."""
    try:
        info = model.get_topic_info()
        if info is not None and not info.empty and "Topic" in info.columns and "Name" in info.columns:
            return {int(k): str(v) for k, v in zip(info["Topic"], info["Name"])}
    except Exception:
        pass
    return {}


def run_topic_pipeline(limit: int = 2000) -> int:
    """Load documents_processed, fit BERTopic, assign topic label per doc, write to documents_processed.topic_hint."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, content_clean, published_date, source_type FROM documents_processed WHERE content_clean IS NOT NULL AND length(content_clean) > 100 LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
    if not rows:
        logger.warning("No documents_processed rows for BERTopic.")
        return 0
    docs = [r[1] for r in rows]
    model = fit_bertopic(docs)
    if model is None:
        return 0
    topics = model.topics_
    labels_map = _topic_labels_from_model(model)
    if not labels_map:
        labels_map = {-1: "Outlier"}
    updated = 0
    with get_connection() as conn:
        for i, raw_id in enumerate(topics):
            if i >= len(rows):
                break
            topic_id = int(raw_id) if raw_id is not None else -1
            doc_id = rows[i][0]
            label = labels_map.get(topic_id, "Outlier" if topic_id == -1 else f"Topic_{topic_id}")
            try:
                conn.execute("UPDATE documents_processed SET topic_hint = ? WHERE id = ?", (label, doc_id))
                updated += 1
            except Exception as e:
                logger.debug("Update topic_hint: %s", e)
    return updated


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    from data.storage.db_manager import ensure_schema
    ensure_schema()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    n = run_topic_pipeline(limit=limit)
    print(f"Updated {n} documents with BERTopic labels. Refresh the Topics page to see distribution.")
