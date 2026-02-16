"""
Market stress warning level from regime + sentiment.
Maps to Low / Elevated / High / Critical with infographic-ready values.
"""

from typing import Optional
import pandas as pd

# Stress level definitions for infographics and copy
STRESS_LEVELS = {
    "Low": {
        "level": 0,
        "score_range": (0, 25),
        "color": "#3fb950",
        "icon": "🟢",
        "short": "Low stress",
        "description": "Market mood is calm. Risk appetite is normal; no immediate precautions needed.",
        "suggested_actions": "Maintain normal positioning. Keep monitoring regime and sentiment for shifts.",
    },
    "Elevated": {
        "level": 1,
        "score_range": (25, 50),
        "color": "#d29922",
        "icon": "🟡",
        "short": "Elevated stress",
        "description": "Signs of caution. Sentiment or regime signals show increased uncertainty.",
        "suggested_actions": "Review exposure; consider modest defensive tweaks. Watch for move to High stress.",
    },
    "High": {
        "level": 2,
        "score_range": (50, 75),
        "color": "#f85149",
        "icon": "🟠",
        "short": "High stress",
        "description": "Risk-off signals are notable. Fear and defensive positioning are elevated.",
        "suggested_actions": "Reduce risk if aligned with your plan. Favor quality and liquidity. Monitor daily.",
    },
    "Critical": {
        "level": 3,
        "score_range": (75, 100),
        "color": "#da3633",
        "icon": "🔴",
        "short": "Critical stress",
        "description": "Strong risk-off regime. Market stress and aversion are very high.",
        "suggested_actions": "Prioritize capital preservation. Avoid large new risk; stay liquid. Seek professional advice if needed.",
    },
}


def compute_stress_score(regime: Optional[dict], regime_df: pd.DataFrame, daily_sent: pd.DataFrame) -> float:
    """
    Compute a 0–100 stress score from current regime and recent sentiment.
    Higher = more stress (risk-off).
    """
    score = 50.0  # default mid
    if regime:
        prob_off = regime.get("regime_prob_risk_off") or regime.get("regime_probability")
        if prob_off is not None:
            # Risk-Off probability maps directly to stress
            score = float(prob_off) * 100
        if regime.get("regime_label") == "Risk-Off":
            score = max(score, 60)
        elif regime.get("regime_label") == "Risk-On":
            score = min(score, 35)
    if not daily_sent.empty and "daily_mean_sentiment" in daily_sent.columns:
        latest_sent = daily_sent["daily_mean_sentiment"].iloc[-1]
        if latest_sent is not None:
            # Sentiment -1 -> +1 maps to stress +20 -> -20
            score = score - (float(latest_sent) * 20)
    return max(0.0, min(100.0, score))


def get_stress_level(score: float) -> str:
    """Map 0–100 score to Low / Elevated / High / Critical."""
    if score < 25:
        return "Low"
    if score < 50:
        return "Elevated"
    if score < 75:
        return "High"
    return "Critical"


def get_stress_info(regime: Optional[dict], regime_df: pd.DataFrame, daily_sent: pd.DataFrame) -> dict:
    """
    Return dict: score (0–100), level (str), color, short, description, suggested_actions, and full STRESS_LEVELS entry.
    """
    score = compute_stress_score(regime, regime_df, daily_sent)
    level = get_stress_level(score)
    info = STRESS_LEVELS[level].copy()
    info["score"] = round(score, 1)
    info["level_name"] = level
    return info
