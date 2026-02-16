"""
Text cleaning for ERIS: HTML/boilerplate removal, normalization, sentence segmentation.
Uses trafilatura for web content and spaCy for sentence splitting when available.
"""

import re
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def strip_html_and_boilerplate(text: str, use_trafilatura: bool = True) -> str:
    """Remove HTML tags and common boilerplate. Use trafilatura if available for article-style content."""
    if not text or not isinstance(text, str):
        return ""
    text = text.strip()
    if use_trafilatura and len(text) > 200:
        try:
            import trafilatura
            extracted = trafilatura.extract(text)
            if extracted and len(extracted) > 50:
                return extracted.strip()
        except Exception:
            pass
    # Fallback: strip tags with regex
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    # Remove common boilerplate
    for pattern in [
        r"Copyright \d{4}.*?\.\s*",
        r"All rights reserved\.?\s*",
        r"Subscribe to.*?\.\s*",
        r"Read more\.?\s*",
        r"Advertisement\s*",
    ]:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_topic(text: str) -> str:
    """Lowercase and normalize for topic modeling; keep $ % and basis points."""
    if not text:
        return ""
    text = re.sub(r"[^\w\s$%\.\-]", " ", text)
    return " ".join(text.lower().split())


def normalize_preserve_case(text: str) -> str:
    """Remove special chars but preserve case for FinBERT."""
    if not text:
        return ""
    text = re.sub(r"[^\w\s$%\.\-]", " ", text)
    return " ".join(text.split())


def segment_sentences(text: str) -> List[str]:
    """Split into sentences. Uses spaCy en_core_web_sm if available, else simple heuristics."""
    if not text or not text.strip():
        return []
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            nlp = spacy.blank("en")
            nlp.add_pipe("sentencizer")
        doc = nlp(text[:1_000_000])
        return [s.text.strip() for s in doc.sents if s.text.strip()]
    except Exception:
        pass
    # Fallback: split on . ! ?
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def clean_document(
    raw_content: str,
    title: Optional[str] = None,
    preserve_case: bool = False,
) -> Tuple[str, List[str], int]:
    """
    Full clean pipeline. Returns (content_clean, sentences, word_count).
    If preserve_case=True, normalization keeps case (for FinBERT).
    """
    content = strip_html_and_boilerplate(raw_content or "")
    if title:
        content = f"{title}\n{content}"
    normalized = normalize_preserve_case(content) if preserve_case else normalize_for_topic(content)
    sentences = segment_sentences(content)
    word_count = len(normalized.split())
    return normalized, sentences, word_count
