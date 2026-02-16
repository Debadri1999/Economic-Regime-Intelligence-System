"""
ERIS Regime detection: HMM + change-point (ruptures). Phase 3.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from data.storage.db_manager import get_config, get_connection

logger = logging.getLogger(__name__)


def run_hmm(features: np.ndarray, n_components: int = 3) -> Optional[object]:
    """Fit Gaussian HMM; return fitted model."""
    try:
        from hmmlearn import hmm
        cfg = get_config()
        n = cfg.get("regime", {}).get("hmm_n_components", n_components)
        model = hmm.GaussianHMM(n_components=n, covariance_type="full", n_iter=cfg.get("regime", {}).get("hmm_n_iter", 100))
        model.fit(features)
        return model
    except ImportError:
        return None


def run_change_point(signal: np.ndarray, kernel: str = "rbf") -> list:
    """Detect change points with ruptures Pelt. Returns list of indices."""
    try:
        import ruptures as rpt
        signal = signal.reshape(-1, 1)
        algo = rpt.Pelt(model=kernel).fit(signal)
        return algo.predict(pen=1.0)
    except Exception:
        return []
