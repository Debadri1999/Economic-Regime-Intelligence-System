"""
GPT-4 powered briefing: current scenario, examples, early warnings, and precautions.
Uses forecasted regime, sentiment, topics, and stress level. Caches in llm_briefings.
"""

import json
import logging
import os
from datetime import date
from typing import Optional

from data.storage.db_manager import get_connection
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _build_context(regime: Optional[dict], regime_trend: str, sentiment_trend: str, topic_summary: str, stress_info: dict) -> str:
    """Build a short context string for the LLM."""
    parts = []
    if regime:
        parts.append(f"Current regime: {regime.get('regime_label', 'N/A')} (probability {regime.get('regime_probability') or regime.get('regime_prob_risk_off')}, confidence {regime.get('confidence', 'N/A')}).")
    parts.append(f"Regime trend (last 30 days): {regime_trend}")
    parts.append(f"Sentiment trend: {sentiment_trend}")
    parts.append(f"Topics: {topic_summary}")
    parts.append(f"Market stress level: {stress_info.get('level_name', 'N/A')} (score {stress_info.get('score', 0):.0f}/100). {stress_info.get('short', '')} — {stress_info.get('description', '')}")
    return "\n".join(parts)


def _call_gpt4(context: str) -> Optional[str]:
    """Call OpenAI GPT-4 with the given context; return raw response or None."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert economic and market analyst for ERIS (Economic Regime Intelligence System). "
                    "Write in clear, plain language for investors and decision-makers. Be concise. "
                    "Provide: (1) scenario_summary: 2–3 sentence current scenario with concrete examples; "
                    "(2) risk_briefing: a complete 2–3 paragraph risk assessment for stakeholders; "
                    "(3) early_warnings: array of 1–3 short strings (what to watch); "
                    "(4) precautions: array of 2–4 short strings (actions to prepare); "
                    "(5) mitigation_paths: array of 2–4 short strings (concrete mitigation steps stakeholders can take). "
                    "Respond in valid JSON only with keys: scenario_summary, risk_briefing, early_warnings, precautions, mitigation_paths."
                },
                {
                    "role": "user",
                    "content": "Based on the following ERIS forecast and signals, provide the full risk briefing and mitigation paths.\n\n" + context,
                },
            ],
            temperature=0.4,
            max_tokens=1000,
        )
        text = response.choices[0].message.content
        if not text:
            return None
        # Strip markdown code block if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text
    except Exception as e:
        logger.warning("GPT-4 briefing failed: %s", e)
        return None


def _parse_briefing(raw: str) -> dict:
    """Parse JSON response into scenario_summary, risk_briefing, early_warnings, precautions, mitigation_paths."""
    out = {"scenario_summary": "", "risk_briefing": "", "early_warnings": [], "precautions": [], "mitigation_paths": []}
    if not raw:
        return out
    try:
        data = json.loads(raw)
        out["scenario_summary"] = data.get("scenario_summary", "") or ""
        out["risk_briefing"] = data.get("risk_briefing", "") or ""
        out["early_warnings"] = data.get("early_warnings") or []
        out["precautions"] = data.get("precautions") or []
        out["mitigation_paths"] = data.get("mitigation_paths") or []
    except json.JSONDecodeError:
        out["scenario_summary"] = raw[:500]
    return out


def get_or_create_briefing(
    as_of_date: str,
    regime: Optional[dict],
    regime_trend: str,
    sentiment_trend: str,
    topic_summary: str,
    stress_info: dict,
    force_refresh: bool = False,
) -> dict:
    """
    Return cached briefing for as_of_date or generate via GPT-4 and cache.
    Returns dict: scenario_summary, risk_briefing, early_warnings, precautions, mitigation_paths, from_cache.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        if not force_refresh:
            cur.execute(
                "SELECT raw_response FROM llm_briefings WHERE date = ? ORDER BY created_at DESC LIMIT 1",
                (as_of_date,),
            )
            row = cur.fetchone()
            if row and row[0]:
                parsed = _parse_briefing(row[0])
                parsed["from_cache"] = True
                return parsed
        context = _build_context(regime, regime_trend, sentiment_trend, topic_summary, stress_info)
        raw = _call_gpt4(context)
        if not raw:
            return {"scenario_summary": "", "risk_briefing": "", "early_warnings": [], "precautions": [], "mitigation_paths": [], "from_cache": False}
        parsed = _parse_briefing(raw)
        parsed["from_cache"] = False
        cur.execute(
            """INSERT INTO llm_briefings (date, regime_status, risk_assessment, raw_response)
               VALUES (?, ?, ?, ?)""",
            (as_of_date, regime.get("regime_label") if regime else "", parsed.get("scenario_summary", ""), raw),
        )
        return parsed


def get_market_linkage_analogy(
    regime_trend: str,
    market_movement: str,
    regime_label: str,
    has_market_data: bool,
) -> Optional[str]:
    """
    Ask GPT for a concise market-linkage analogy for stakeholders (no script instructions).
    Returns 2–4 sentences or None if no API key.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        context = f"Regime trend: {regime_trend}. Market: {market_movement}. Current regime label: {regime_label}. Has market data: {has_market_data}."
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert for ERIS (Economic Regime Intelligence System). "
                    "In 2–4 concise sentences, explain the link between the current regime and market for stakeholders. "
                    "Use plain language. Do not mention running scripts or technical setup. "
                    "Focus on what the regime and market data imply for risk and positioning."
                },
                {"role": "user", "content": "Provide a short market-linkage analogy for stakeholders.\n\n" + context},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        text = (response.choices[0].message.content or "").strip()
        return text if text else None
    except Exception as e:
        logger.warning("GPT market linkage failed: %s", e)
        return None
