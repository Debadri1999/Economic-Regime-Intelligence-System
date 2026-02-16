"""
Run Phase 2 (NLP signals) and Phase 3 (Regime detection) to populate the dashboard.
Run from project root:  python run_phase2_and_3.py

Step 1: Sentiment (FinBERT) on documents_processed -> nlp_signals
Step 2: Regime detection (HMM on daily sentiment) -> regime_states
"""

# Initialize torch before any other heavy imports to avoid torchvision circular import
try:
    import torch  # noqa: F401
except ImportError:
    pass

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    from data.storage.db_manager import ensure_schema
    ensure_schema()

    # Phase 2: sentiment
    print("Phase 2: Running sentiment (FinBERT) on processed documents...")
    try:
        from models.sentiment_engine import run_sentiment_on_processed
        n_sent = run_sentiment_on_processed(limit=3000)
        print("  -> Inserted", n_sent, "nlp_signals (sentiment).")
    except Exception as e:
        print("  -> Sentiment failed (install transformers, torch?):", e)
        print("  -> Continuing; regime will use placeholder if no nlp_signals.")

    # Phase 3: regime
    print("Phase 3: Running regime detection (HMM)...")
    try:
        from models.regime_detector import run_regime_pipeline
        n_regime = run_regime_pipeline()
        print("  -> Written", n_regime, "regime_states.")
    except Exception as e:
        print("  -> Regime failed:", e)
        sys.exit(1)

    print("Done. Refresh the Streamlit dashboard to see regime and sentiment.")


if __name__ == "__main__":
    main()
