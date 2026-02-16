"""
Deduplication for ERIS using MinHash and Jaccard similarity.
"""

import hashlib
import logging
from typing import List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def _get_shingles(text: str, k: int = 3) -> Set[str]:
    """Character k-shingles for MinHash."""
    text = (text or "").lower().replace(" ", "")
    if len(text) < k:
        return {text} if text else set()
    return {text[i : i + k] for i in range(len(text) - k + 1)}


def minhash_fingerprint(text: str, num_perm: int = 128) -> Optional[bytes]:
    """Compute MinHash fingerprint. Returns bytes for storage; None if datasketch not available."""
    shingles = _get_shingles(text, k=3)
    if not shingles:
        return None
    try:
        import pickle
        from datasketch import MinHash
        m = MinHash(num_perm=num_perm)
        for s in shingles:
            m.update(s.encode("utf-8"))
        return pickle.dumps(m)
    except ImportError:
        # Fallback: simple hash of sorted shingles
        h = hashlib.sha256("|".join(sorted(shingles)).encode()).digest()
        return h


def jaccard_similarity(text_a: str, text_b: str, k: int = 3) -> float:
    """Jaccard similarity between two texts (shingle sets)."""
    sa, sb = _get_shingles(text_a, k), _get_shingles(text_b, k)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def is_duplicate(
    text: str,
    existing_fingerprints: List[bytes],
    threshold: float = 0.85,
) -> bool:
    """
    Check if text is near-duplicate of any existing (by MinHash).
    If datasketch not available, falls back to no dedup (returns False).
    """
    if not existing_fingerprints or threshold <= 0:
        return False
    try:
        import pickle
        from datasketch import MinHash
        new_fp = minhash_fingerprint(text)
        if not new_fp:
            return False
        new_m = pickle.loads(new_fp)
        for fp in existing_fingerprints:
            if isinstance(fp, bytes) and len(fp) > 0:
                try:
                    other = pickle.loads(fp)
                    if new_m.jaccard(other) >= threshold:
                        return True
                except Exception:
                    continue
    except (ImportError, Exception):
        pass
    return False
