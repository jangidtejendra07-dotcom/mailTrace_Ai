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
"""
MailTrace AI — Real-time LLM email intent analysis.

Priority:
1. Groq
2. Gemini
3. Local ML fallback (handled by ai_engine.py)

This version includes detailed provider diagnostics in Render logs.
"""

import json
import re
import logging
import requests

from app.config import settings


logger = logging.getLogger("mailtrace.llm_engine")


SYSTEM_PROMPT = """
You are an email security analyst.

Analyze the email for:
- phishing
- business email compromise (BEC)
- malware lure
- spam
- safe email

Return ONLY valid JSON.

Required format:
{
  "score": 0,
  "category": "safe",
  "reasons": []
}

Rules:
- score must be integer from 0 to 100
- 100 means definitely malicious
- category must be one of:
  safe, phishing, bec, spam, malware
- reasons must contain at most 4 short explanations
"""


def _build_user_prompt(subject: str, body: str) -> str:
    trimmed_body = (body or "")[:4000]

    return (
        f"Subject: {subject or ''}\n\n"
        f"Body:\n{trimmed_body}"
    )


def _extract_json(text: str):
    """
    Extract JSON even if the model accidentally wraps it in markdown.
    """

    if not text:
        return None

    text = text.strip()

    # Remove markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    # First try entire response
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Then find first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except (json.JSONDecodeError, ValueError):
        return None


def _normalize_result(raw: dict, engine_name: str):
    if not isinstance(raw, dict):
        return None

    try:
        score = int(raw.get("score", 0))
    except (TypeError, ValueError):
        return None

    score = max(0, min(100, score))

    category = str(
        raw.get("category", "safe")
    ).strip().lower()

    valid_categories = {
        "safe",
        "phishing",
        "bec",
        "spam",
        "malware",
    }

    if category not in valid_categories:
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


def _call_groq(subject: str, body: str):
    """
    Primary provider: Groq.
    """

    api_key = settings.GROQ_API_KEY

    if not api_key:
        logger.warning("GROQ_API_KEY is not configured.")
        return None

    model = settings.GROQ_MODEL

    logger.info(
        "Trying Groq | model=%s | timeout=%ss",
        model,
        settings.LLM_TIMEOUT_SECONDS,
    )

    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
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
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        logger.info(
            "Groq response | HTTP %s",
            response.status_code,
        )

        if response.status_code != 200:
            logger.error(
                "Groq failed | HTTP %s | body=%s",
                response.status_code,
                response.text[:500],
            )
            return None

        data = response.json()

        content = (
            data
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:
            logger.error("Groq returned empty content.")
            return None

        parsed = _extract_json(content)

        if not parsed:
            logger.error(
                "Groq returned invalid JSON | content=%s",
                content[:500],
            )
            return None

        result = _normalize_result(
            parsed,
            "groq",
        )

        if result:
            logger.info(
                "Groq analysis successful | category=%s | score=%s",
                result["category"],
                result["score"],
            )

        return result

    except requests.Timeout:
        logger.error("Groq request timed out.")
        return None

    except requests.RequestException as exc:
        logger.error(
            "Groq network error: %s",
            exc,
        )
        return None

    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.error(
            "Groq response parsing error: %s",
            exc,
        )
        return None

    except Exception as exc:
        logger.exception(
            "Unexpected Groq error: %s",
            exc,
        )
        return None


def _call_gemini(subject: str, body: str):
    """
    Fallback provider: Google Gemini.
    """

    api_key = settings.GEMINI_API_KEY

    if not api_key:
        logger.warning("GEMINI_API_KEY is not configured.")
        return None

    model = settings.GEMINI_MODEL

    logger.info(
        "Trying Gemini | model=%s | timeout=%ss",
        model,
        settings.LLM_TIMEOUT_SECONDS,
    )

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        f"{model}:generateContent"
    )

    params = {
        "key": api_key,
    }

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": SYSTEM_PROMPT
                }
            ]
        },
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
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 300,
            "responseMimeType": "application/json",
        },
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            url,
            params=params,
            headers=headers,
            json=payload,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        logger.info(
            "Gemini response | HTTP %s",
            response.status_code,
        )

        if response.status_code != 200:
            logger.error(
                "Gemini failed | HTTP %s | body=%s",
                response.status_code,
                response.text[:500],
            )
            return None

        data = response.json()

        candidates = data.get("candidates") or []

        if not candidates:
            logger.error(
                "Gemini returned no candidates."
            )
            return None

        content = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not content:
            logger.error(
                "Gemini returned empty content."
            )
            return None

        parsed = _extract_json(content)

        if not parsed:
            logger.error(
                "Gemini returned invalid JSON | content=%s",
                content[:500],
            )
            return None

        result = _normalize_result(
            parsed,
            "gemini",
        )

        if result:
            logger.info(
                "Gemini analysis successful | category=%s | score=%s",
                result["category"],
                result["score"],
            )

        return result

    except requests.Timeout:
        logger.error(
            "Gemini request timed out."
        )
        return None

    except requests.RequestException as exc:
        logger.error(
            "Gemini network error: %s",
            exc,
        )
        return None

    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.error(
            "Gemini response parsing error: %s",
            exc,
        )
        return None

    except Exception as exc:
        logger.exception(
            "Unexpected Gemini error: %s",
            exc,
        )
        return None


def analyze_intent_llm(subject: str, body: str):
    """
    Groq -> Gemini -> None.

    ai_engine.py handles the final local ML fallback.
    """

    text = f"{subject or ''}\n{body or ''}".strip()

    if not text:
        logger.warning(
            "LLM analysis skipped: empty email."
        )
        return None

    # ---------------------------------------------------------
    # 1. GROQ
    # ---------------------------------------------------------

    result = _call_groq(
        subject,
        body,
    )

    if result is not None:
        logger.info(
            "LLM engine selected Groq."
        )
        return result

    # ---------------------------------------------------------
    # 2. GEMINI
    # ---------------------------------------------------------

    logger.warning(
        "Groq unavailable. Falling back to Gemini."
    )

    result = _call_gemini(
        subject,
        body,
    )

    if result is not None:
        logger.info(
            "LLM engine selected Gemini."
        )
        return result

    # ---------------------------------------------------------
    # 3. LOCAL MODEL
    # ---------------------------------------------------------

    logger.error(
        "Groq and Gemini both unavailable. "
        "Falling back to local ML model."
    )

    return None