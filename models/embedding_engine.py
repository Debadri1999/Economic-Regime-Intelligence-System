"""
ERIS Semantic embedding layer: daily average embedding, rolling baseline, semantic_drift, semantic_acceleration.
Phase 2.
"""

import logging
from typing import List, Optional

import numpy as np
from data.storage.db_manager import get_config, get_connection

logger = logging.getLogger(__name__)


def get_embedding_model():
    """Load sentence-transformer model."""
    try:
        from sentence_transformers import SentenceTransformer
        cfg = get_config()
        name = cfg.get("nlp", {}).get("sentence_transformer", "all-MiniLM-L6-v2")
        return SentenceTransformer(name)
    except ImportError:
        return None


def compute_daily_embedding(documents: List[str], model) -> Optional[np.ndarray]:
    """Average embedding over documents. Returns vector or None."""
    if not model or not documents:
        return None
    try:
        embs = model.encode(documents, show_progress_bar=False)
        return np.mean(embs, axis=0)
    except Exception as e:
        logger.debug("Embedding failed: %s", e)
        return None


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance = 1 - cosine_similarity."""
    if a is None or b is None or len(a) != len(b):
        return 0.0
    return 1.0 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)
