"""
Regime definitions and real-world examples for the Regime dashboard.
Plain language so any user (including laymen) understands.
"""

REGIME_DEFINITIONS = {
    "Risk-On": {
        "title": "Growth / Risk-On",
        "subtitle": "“Let’s make money.”",
        "description": "Everyone’s optimistic. Companies are hiring, stocks are going up, people are spending freely, banks are lending easily.",
        "example": "Long stretches of 2017–2019 and post-COVID rebound in 2020–2021: low rates, strong jobs, rising markets.",
    },
    "Risk-Off": {
        "title": "Stress / Risk-Off",
        "subtitle": "“Let’s protect what we have.”",
        "description": "Fear takes over. People sell stocks, hoard cash, companies freeze hiring, banks tighten lending.",
        "example": "Early 2020 (COVID): economy flipped from growth to crisis in 2–3 weeks. 2022: shift from ‘easy money’ to high inflation and Fed tightening — stocks and bonds both fell.",
    },
    "Transitional": {
        "title": "Transition",
        "subtitle": "“Mixed signals — uncertainty is high.”",
        "description": "The messy in-between. Some indicators say growth, others say trouble. This is where the real uncertainty lives and where regime shifts often start.",
        "example": "Mid-2022: debate between ‘soft landing’ and ‘recession.’ Late 2023–2024: mixed jobs and inflation data — neither clearly growth nor clearly stress.",
    },
}

REGIME_SHIFT_EXPLANATION = (
    "A **regime shift** is when the economy flips from one mode to another. "
    "Traditional indicators (GDP, unemployment) usually tell you about a shift *after* it’s happened. "
    "ERIS reads the *language* in news, Fed speeches, and earnings calls to spot when the mood is changing, "
    "often 1–4 weeks before the numbers confirm it. When executives say ‘cautious’ instead of ‘optimistic,’ "
    "or when headlines move from ‘soft landing’ to ‘recession risk,’ that text can lead the data — that’s the edge we’re building."
)


def get_current_regime_interpretation(regime_label: str, probability_pct: str, confidence: str) -> str:
    """One short paragraph: what the current forecast means in plain language."""
    if not regime_label or regime_label == "N/A":
        return "No regime has been estimated yet. Run the pipeline (Phase 2 + 3) to get a reading."
    label = str(regime_label).strip()
    d = REGIME_DEFINITIONS.get(label, REGIME_DEFINITIONS.get("Transitional"))
    title = d["title"]
    subtitle = d["subtitle"]
    desc = d["description"]
    return (
        f"Our model currently classifies the economy as **{title}** (probability {probability_pct}, confidence {confidence}). "
        f"In plain terms: {desc} The vibe is {subtitle} "
        f"Use the chart and table below to see how we got here and how the regime has moved over time."
    )
