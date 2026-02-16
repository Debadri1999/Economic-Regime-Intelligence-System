"""
ERIS Sentiment Intelligence (FinBERT).
Document-level sentiment and daily aggregates; derived metrics: drift, volatility, shock.
Phase 2.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd
from data.storage.db_manager import get_connection, get_config

logger = logging.getLogger(__name__)


def load_finbert():
    """Load FinBERT model and tokenizer. Requires transformers and torch."""
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
        cfg = get_config()
        model_name = cfg.get("nlp", {}).get("finbert_model", "ProsusAI/finbert")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        if torch.cuda.is_available():
            model = model.cuda()
        return model, tokenizer
    except ImportError as e:
        logger.warning("FinBERT dependencies missing: %s", e)
        return None, None


def score_sentiment_sentence(model, tokenizer, sentence: str, device: str = "cpu") -> Tuple[float, float, float, float]:
    """Return (score_cont, p_pos, p_neg, p_neu) for one sentence."""
    if not model or not tokenizer:
        return 0.0, 1/3, 1/3, 1/3
    try:
        import torch
        inputs = tokenizer(sentence[:512], return_tensors="pt", truncation=True, padding=True)
        if device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        with torch.no_grad():
            out = model(**inputs)
        probs = torch.softmax(out.logits, dim=1).squeeze().tolist()
        if len(probs) == 3:  # neg, neu, pos
            p_neg, p_neu, p_pos = probs[0], probs[1], probs[2]
        else:
            p_pos = p_neg = p_neu = 1/3
        score = (p_pos - p_neg)  # continuous -1 to +1
        return score, p_pos, p_neg, p_neu
    except Exception as e:
        logger.debug("Sentiment score failed: %s", e)
        return 0.0, 1/3, 1/3, 1/3


def run_sentiment_on_processed(limit: int = 1000) -> int:
    """Read documents_processed, score with FinBERT, write to nlp_signals (document-level then aggregate by date)."""
    model, tokenizer = load_finbert()
    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    if not model:
        logger.warning("FinBERT not loaded; skipping sentiment run.")
        return 0
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, content_clean, content_sentences, published_date, source_type FROM documents_processed LIMIT ?", (limit,))
        rows = cur.fetchall()
    inserted = 0
    for row in rows:
        doc_id, content_clean, content_sentences, published_date, source_type = row[0], row[1], row[2], row[3], row[4]
        sentences = (content_sentences or "").split("\n") if content_sentences else (content_clean or "").split(".")
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            continue
        scores = [score_sentiment_sentence(model, tokenizer, s, device) for s in sentences[:50]]
        if not scores:
            continue
        avg_score = sum(s[0] for s in scores) / len(scores)
        avg_pos = sum(s[1] for s in scores) / len(scores)
        avg_neg = sum(s[2] for s in scores) / len(scores)
        avg_neu = sum(s[3] for s in scores) / len(scores)
        conf = max(avg_pos, avg_neg, avg_neu)
        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT INTO nlp_signals (date, source_type, sentiment_score, sentiment_positive_prob, sentiment_negative_prob, sentiment_neutral_prob, sentiment_confidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (published_date, source_type, avg_score, avg_pos, avg_neg, avg_neu, conf),
                )
            inserted += 1
        except Exception as e:
            logger.debug("Insert nlp_signal: %s", e)
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from data.storage.db_manager import ensure_schema
    ensure_schema()
    n = run_sentiment_on_processed(limit=50)
    print("Inserted", n, "sentiment signals")
