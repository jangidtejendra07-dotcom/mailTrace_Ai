"""
Real-time LLM-based email intent analysis.

Fallback chain (each step only runs if the previous one fails/times out),
so a single provider outage or a hit rate-limit NEVER breaks analysis:

    1. Groq   (llama-3.3-70b-versatile) -- primary, fastest inference (LPU
       hardware), free tier: 30 req/min, 1,000 req/day.
    2. Gemini (gemini-2.5-flash-lite)   -- fallback, free tier: 15 req/min,
       1,000 req/day, huge token budget.
    3. None -> caller (ai_engine.py) falls back to the local scikit-learn
       model, so the pipeline always returns a result even fully offline.

Both providers are called with plain `requests` (no extra SDK dependency,
smaller surface area, fewer things that can break) and a short timeout so a
slow/hanging provider never stalls the whole analysis pipeline.
"""
import json
import re
import logging

import requests

from app.config import settings

logger = logging.getLogger("mailtrace.llm_engine")

_SYSTEM_PROMPT = (
    "You are an email security analyst. Analyze the given email subject and "
    "body for phishing, business-email-compromise (BEC), malware-lure, or "
    "spam intent. Respond with ONLY a compact JSON object, no markdown, no "
    "extra text, in exactly this shape: "
    '{"score": <integer 0-100, 100=definitely malicious>, '
    '"category": <one of "safe","phishing","bec","spam","malware">, '
    '"reasons": [<short strings, max 4, each under 15 words>]}'
)


def _build_user_prompt(subject: str, body: str) -> str:
    # Truncate to keep token usage low and requests fast — a phishing verdict
    # rarely needs more than the first ~4000 characters of body text.
    trimmed_body = (body or "")[:4000]
    return f"Subject: {subject}\n\nBody:\n{trimmed_body}"


def _extract_json(text: str) -> dict | None:
    """LLMs occasionally wrap JSON in markdown fences or add stray text
    despite instructions — pull out the first {...} block defensively."""
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except (json.JSONDecodeError, ValueError):
        return None


def _normalize_result(raw: dict, engine_name: str) -> dict | None:
    try:
        score = int(raw.get("score", 0))
    except (TypeError, ValueError):
        return None
    score = max(0, min(100, score))

    category = str(raw.get("category", "safe")).strip().lower()
    if category not in {"safe", "phishing", "bec", "spam", "malware"}:
        category = "safe" if score < 40 else "phishing"

    reasons = raw.get("reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]
    reasons = [str(r).strip() for r in reasons if str(r).strip()][:4]
    if not reasons:
        reasons = [f"{engine_name} classified this email as '{category}'"]

    return {"score": score, "category": category, "reasons": reasons, "engine_used": engine_name}


def _call_groq(subject: str, body: str) -> dict | None:
    if not settings.GROQ_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(subject, body)},
                ],
                "temperature": 0.1,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            logger.warning("Groq call failed: HTTP %s %s", resp.status_code, resp.text[:200])
            return None
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
        return _normalize_result(parsed, "groq") if parsed else None
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        logger.warning("Groq call raised %s: %s", type(exc).__name__, exc)
        return None


def _call_gemini(subject: str, body: str) -> dict | None:
    if not settings.GEMINI_API_KEY:
        return None
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        )
        resp = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": _build_user_prompt(subject, body)}]}],
                "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 300,
                    "responseMimeType": "application/json",
                },
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            logger.warning("Gemini call failed: HTTP %s %s", resp.status_code, resp.text[:200])
            return None
        content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = _extract_json(content)
        return _normalize_result(parsed, "gemini") if parsed else None
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        logger.warning("Gemini call raised %s: %s", type(exc).__name__, exc)
        return None


def analyze_intent_llm(subject: str, body: str) -> dict | None:
    """Try Groq first, then Gemini. Returns None if both are unavailable/
    unconfigured/failed so the caller can fall back to the local model."""
    text = f"{subject}\n{body}".strip()
    if not text:
        return None

    result = _call_groq(subject, body)
    if result is not None:
        return result

    result = _call_gemini(subject, body)
    if result is not None:
        return result

    return None
