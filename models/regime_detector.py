"""
ERIS Regime detection: HMM + change-point (ruptures). Phase 3.
Reads nlp_signals (or builds synthetic daily series if sparse), fits HMM, writes regime_states.
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from data.storage.db_manager import get_config, get_connection

logger = logging.getLogger(__name__)

REGIME_LABELS = ["Risk-On", "Transitional", "Risk-Off"]


def get_daily_nlp_features() -> pd.DataFrame:
    """Aggregate nlp_signals by date; add sentiment_drift (21d rolling mean diff). Returns daily DataFrame with date index."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT date, sentiment_score, source_type FROM nlp_signals WHERE date IS NOT NULL AND sentiment_score IS NOT NULL",
            conn,
        )
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    daily = df.groupby("date").agg(
        sentiment_mean=("sentiment_score", "mean"),
        sentiment_std=("sentiment_score", "std"),
        doc_count=("sentiment_score", "count"),
    ).reset_index()
    daily["sentiment_std"] = daily["sentiment_std"].fillna(0)
    daily["sentiment_drift"] = daily["sentiment_mean"].rolling(21, min_periods=1).mean().diff().fillna(0)
    return daily.sort_values("date").dropna(subset=["sentiment_mean"])


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


def run_regime_pipeline() -> int:
    """
    Build daily features from nlp_signals, fit HMM, label states (Risk-On / Transitional / Risk-Off), write regime_states.
    Returns number of days written. If nlp_signals is empty, writes a small synthetic demo so the dashboard has something.
    """
    daily = get_daily_nlp_features()
    min_days = 7  # HMM can fit with a week of daily aggregates; more is better
    if daily.empty or len(daily) < min_days:
        logger.warning(
            "Not enough nlp_signals for regime detection (have %d days, need >= %d). Run Phase 2 (sentiment) first, or writing placeholder.",
            len(daily), min_days,
        )
        with get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO regime_states (date, regime_label, regime_probability, confidence, regime_prob_risk_off)
                   VALUES (date('now'), 'Transitional', 0.5, 'Low', 0.33)"""
            )
        return 1
    feat_cols = ["sentiment_mean", "sentiment_std", "sentiment_drift"]
    X = daily[feat_cols].values.astype(np.float64)
    X = (X - np.nanmean(X, axis=0)) / (np.nanstd(X, axis=0) + 1e-8)
    model = run_hmm(X, n_components=3)
    if not model:
        logger.warning("hmmlearn not available; writing placeholder regime.")
        with get_connection() as conn:
            for _, row in daily.tail(90).iterrows():
                conn.execute(
                    """INSERT OR REPLACE INTO regime_states (date, regime_label, regime_probability, confidence, regime_prob_risk_off)
                       VALUES (?, 'Transitional', 0.5, 'Low', 0.33)""",
                    (str(row["date"]),),
                )
        return min(90, len(daily))
    hidden = model.predict(X)
    try:
        probs = model.predict_proba(X)
    except AttributeError:
        probs = np.eye(3)[hidden]
    emission_means = model.means_
    risk_off_state = int(np.argmin(emission_means[:, 0]))
    inserted = 0
    with get_connection() as conn:
        for i, (_, row) in enumerate(daily.iterrows()):
            state = int(hidden[i])
            prob_risk_off = float(probs[i, risk_off_state]) if probs.shape[1] > risk_off_state else (1.0 if state == risk_off_state else 0.33)
            label = REGIME_LABELS[state] if state < 3 else "Transitional"
            conf = "High" if np.max(probs[i]) > 0.7 else "Medium" if np.max(probs[i]) > 0.5 else "Low"
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO regime_states
                       (date, regime_label, regime_probability, confidence, regime_prob_risk_off, hmm_state, composite_prob)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (str(row["date"]), label, prob_risk_off, conf, prob_risk_off, state, prob_risk_off),
                )
                inserted += 1
            except Exception as e:
                logger.debug("Insert regime: %s", e)
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from data.storage.db_manager import ensure_schema
    ensure_schema()
    n = run_regime_pipeline()
    print("Regime states written:", n)
