"""
ERIS Topic & Narrative Intelligence (BERTopic).
Phase 2. Fit on corpus; topics_over_time; store topic_id / topic_label in nlp_signals.
"""

import logging
from typing import List, Optional

from data.storage.db_manager import get_config, get_connection

logger = logging.getLogger(__name__)


def fit_bertopic(documents: List[str], **kwargs) -> object:
    """Fit BERTopic on document list. Returns fitted model."""
    try:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
        import umap
        import hdbscan
        cfg = get_config()
        emb_model = cfg.get("nlp", {}).get("sentence_transformer", "all-MiniLM-L6-v2")
        bt_cfg = cfg.get("nlp", {}).get("bertopic", {})
        model = BERTopic(
            embedding_model=SentenceTransformer(emb_model),
            umap_model=umap.UMAP(
                n_neighbors=bt_cfg.get("umap_n_neighbors", 15),
                n_components=bt_cfg.get("umap_n_components", 5),
                min_dist=0.0,
            ),
            hdbscan_model=hdbscan.HDBSCAN(
                min_cluster_size=bt_cfg.get("hdbscan_min_cluster_size", 15),
                min_samples=bt_cfg.get("hdbscan_min_samples", 5),
            ),
            **kwargs,
        )
        model.fit(documents)
        return model
    except ImportError as e:
        logger.warning("BERTopic deps missing: %s", e)
        return None


def run_topic_pipeline(limit: int = 2000) -> int:
    """Load documents_processed, fit BERTopic, assign topic_id per doc, update nlp_signals or store topic prevalence by date."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, content_clean, published_date FROM documents_processed WHERE content_clean IS NOT NULL AND length(content_clean) > 100 LIMIT ?", (limit,))
        rows = cur.fetchall()
    if not rows:
        return 0
    docs = [r[1] for r in rows]
    model = fit_bertopic(docs)
    if model is None:
        return 0
    topics = model.topics_
    # Map doc index to topic_id; could write back to DB or aggregate by date
    return len(topics)
