"""
Real-time LLM-based email intent + recommendation engine.

Analysis:
    Groq -> Gemini -> None

Recommendation:
    Groq -> Gemini -> unavailable

IMPORTANT:
    Local ML is used only for email classification fallback.
    It is NEVER used to generate recommendations.
"""

import json
import logging
import re

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


_RECOMMENDATION_SYSTEM_PROMPT = (
    "You are a senior email security analyst. "
    "Based on the supplied MailTrace email security analysis, provide a "
    "short practical recommendation for the user. "
    "Tell the user what they should do with this email. "
    "Do not invent facts. "
    "If the email is high risk, recommend not clicking links, not opening "
    "attachments, and not replying or providing credentials. "
    "If it is safe, say it appears safe but advise normal caution. "
    "Return ONLY a JSON object in exactly this shape: "
    '{"recommendation": "<short recommendation, maximum 60 words>"}'
)


def _build_user_prompt(subject: str, body: str) -> str:
    trimmed_body = (body or "")[:4000]
    return f"Subject: {subject}\n\nBody:\n{trimmed_body}"


def _extract_json(text: str) -> dict | None:
    if not text:
        return None

    # First try the complete response directly.
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: extract the first JSON object.
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def _normalize_result(raw: dict, engine_name: str) -> dict | None:
    try:
        score = int(raw.get("score", 0))
    except (TypeError, ValueError):
        return None

    score = max(0, min(100, score))

    category = str(
        raw.get("category", "safe")
    ).strip().lower()

    if category not in {
        "safe",
        "phishing",
        "bec",
        "spam",
        "malware",
    }:
        category = "safe" if score < 40 else "phishing"

    reasons = raw.get("reasons") or []

    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    reasons = [
        str(reason).strip()
        for reason in reasons
        if str(reason).strip()
    ][:4]

    if not reasons:
        reasons = [
            f"{engine_name} classified this email as '{category}'"
        ]

    return {
        "score": score,
        "category": category,
        "reasons": reasons,
        "engine_used": engine_name,
    }


def _call_groq(subject: str, body: str) -> dict | None:
    if not settings.GROQ_API_KEY:
        logger.warning("Groq API key is not configured.")
        return None

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": _SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": _build_user_prompt(subject, body),
                    },
                ],
                "temperature": 0.1,
                "max_tokens": 300,
                "response_format": {
                    "type": "json_object"
                },
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            logger.warning(
                "Groq analysis failed: HTTP %s %s",
                response.status_code,
                response.text[:300],
            )
            return None

        content = response.json()["choices"][0]["message"]["content"]

        parsed = _extract_json(content)

        if not parsed:
            return None

        return _normalize_result(parsed, "groq")

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning(
            "Groq analysis raised %s: %s",
            type(exc).__name__,
            exc,
        )
        return None


def _call_gemini(subject: str, body: str) -> dict | None:
    if not settings.GEMINI_API_KEY:
        logger.warning("Gemini API key is not configured.")
        return None

    try:
        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
            f"?key={settings.GEMINI_API_KEY}"
        )

        response = requests.post(
            url,
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": _build_user_prompt(
                                    subject,
                                    body,
                                )
                            }
                        ]
                    }
                ],
                "systemInstruction": {
                    "parts": [
                        {
                            "text": _SYSTEM_PROMPT
                        }
                    ]
                },
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 300,
                    "responseMimeType": "application/json",
                },
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            logger.warning(
                "Gemini analysis failed: HTTP %s %s",
                response.status_code,
                response.text[:300],
            )
            return None

        content = (
            response.json()
            ["candidates"][0]
            ["content"]["parts"][0]["text"]
        )

        parsed = _extract_json(content)

        if not parsed:
            return None

        return _normalize_result(parsed, "gemini")

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning(
            "Gemini analysis raised %s: %s",
            type(exc).__name__,
            exc,
        )
        return None


def analyze_intent_llm(subject: str, body: str) -> dict | None:
    """
    Analysis fallback chain:

        Groq -> Gemini -> None

    None means the caller should use local ML.
    """

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


# ============================================================
# FINAL RECOMMENDATION
# ============================================================


def _build_recommendation_prompt(
    subject: str,
    classification: str,
    risk_score: int,
    decision: str,
    reasons: list,
) -> str:
    safe_reasons = reasons[:6] if isinstance(reasons, list) else []

    return (
        "MailTrace email security result:\n\n"
        f"Subject: {subject}\n"
        f"Classification: {classification}\n"
        f"Risk Score: {risk_score}/100\n"
        f"Decision: {decision}\n"
        f"Reasons: {json.dumps(safe_reasons)}\n\n"
        "Give one concise practical recommendation for the user."
    )


def _normalize_recommendation(
    raw: dict,
    engine_name: str,
) -> dict | None:
    recommendation = raw.get("recommendation")

    if not recommendation:
        return None

    recommendation = str(recommendation).strip()

    if not recommendation:
        return None

    return {
        "recommendation": recommendation[:500],
        "recommendation_engine": engine_name,
    }


def _call_groq_recommendation(
    subject: str,
    classification: str,
    risk_score: int,
    decision: str,
    reasons: list,
) -> dict | None:

    if not settings.GROQ_API_KEY:
        return None

    try:
        prompt = _build_recommendation_prompt(
            subject,
            classification,
            risk_score,
            decision,
            reasons,
        )

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": _RECOMMENDATION_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.2,
                "max_tokens": 180,
                "response_format": {
                    "type": "json_object"
                },
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            logger.warning(
                "Groq recommendation failed: HTTP %s %s",
                response.status_code,
                response.text[:300],
            )
            return None

        content = response.json()["choices"][0]["message"]["content"]

        parsed = _extract_json(content)

        if not parsed:
            return None

        return _normalize_recommendation(
            parsed,
            "groq",
        )

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning(
            "Groq recommendation raised %s: %s",
            type(exc).__name__,
            exc,
        )
        return None


def _call_gemini_recommendation(
    subject: str,
    classification: str,
    risk_score: int,
    decision: str,
    reasons: list,
) -> dict | None:

    if not settings.GEMINI_API_KEY:
        return None

    try:
        prompt = _build_recommendation_prompt(
            subject,
            classification,
            risk_score,
            decision,
            reasons,
        )

        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
            f"?key={settings.GEMINI_API_KEY}"
        )

        response = requests.post(
            url,
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "systemInstruction": {
                    "parts": [
                        {
                            "text": _RECOMMENDATION_SYSTEM_PROMPT
                        }
                    ]
                },
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 180,
                    "responseMimeType": "application/json",
                },
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            logger.warning(
                "Gemini recommendation failed: HTTP %s %s",
                response.status_code,
                response.text[:300],
            )
            return None

        content = (
            response.json()
            ["candidates"][0]
            ["content"]["parts"][0]["text"]
        )

        parsed = _extract_json(content)

        if not parsed:
            return None

        return _normalize_recommendation(
            parsed,
            "gemini",
        )

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning(
            "Gemini recommendation raised %s: %s",
            type(exc).__name__,
            exc,
        )
        return None


def generate_recommendation(
    subject: str,
    classification: str,
    risk_score: int,
    decision: str,
    reasons: list,
) -> dict:

    """
    Recommendation is intentionally LLM-only.

    Priority:
        Groq -> Gemini -> unavailable

    Local ML NEVER generates the recommendation.
    """

    result = _call_groq_recommendation(
        subject,
        classification,
        risk_score,
        decision,
        reasons,
    )

    if result is not None:
        return result

    result = _call_gemini_recommendation(
        subject,
        classification,
        risk_score,
        decision,
        reasons,
    )

    if result is not None:
        return result

    return {
        "recommendation": (
            "AI recommendation is temporarily unavailable. "
            "Please try again in some time."
        ),
        "recommendation_engine": "unavailable",
    }