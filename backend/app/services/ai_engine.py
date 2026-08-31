"""
Section 3 — AI / NLP Engine.

Pipeline:
    Email -> feature extraction -> TF-IDF + Logistic Regression
          -> ai_score + category + reasons

AI output is a RISK SIGNAL, not a sole enforcement decision (fed into
risk_fusion.py alongside forensics/attachment/url scores).
"""
import os
import re
import joblib

from app.ml.dataset import LABEL_MAP
from app.ml.train_model import train, MODEL_PATH
from app.services.llm_engine import analyze_intent_llm

URGENCY_WORDS = [
    "urgent", "immediately", "asap", "right away", "as soon as possible",
    "act now", "final notice", "final warning", "verify now", "act immediately",
    "before it's too late", "time sensitive", "expire", "expires", "suspended",
    "locked", "confidential", "don't tell", "do not discuss", "wire transfer",
    "gift card", "gift cards", "reset your password", "click here",
]

CREDENTIAL_WORDS = [
    "verify your account", "confirm your identity", "login now", "sign in now",
    "update your billing", "enter your password", "enter your credit card",
    "verify your identity", "confirm your details", "reset your password",
]

EXEC_IMPERSONATION_HINTS = [
    "ceo", "cfo", "director", "this is the ceo", "on behalf of the ceo",
    "i'm in a meeting", "i'm traveling", "unavailable by phone",
]


def _load_model():
    if not os.path.exists(MODEL_PATH):
        return train()
    return joblib.load(MODEL_PATH)


_MODEL = None


def get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = _load_model()
    return _MODEL


def _find_matches(text: str, phrases: list[str]) -> list[str]:
    text_l = text.lower()
    return [p for p in phrases if p in text_l]


def _analyze_with_local_model(text: str) -> dict:
    """Offline fallback: TF-IDF + Logistic Regression. Always available,
    used when Groq and Gemini are both unreachable/unconfigured/rate-limited."""
    model = get_model()
    proba = model.predict_proba([text])[0]
    classes = model.classes_
    pred_idx = int(proba.argmax())
    pred_label = int(classes[pred_idx])
    confidence = float(proba[pred_idx])

    category = LABEL_MAP.get(pred_label, "safe")
    if category == "safe":
        score = round((1 - confidence) * 40)  # cap safe-leaning score low
    else:
        score = round(confidence * 100)

    return {
        "score": score,
        "category": category,
        "reasons": [],
        "engine_used": "local-sklearn",
        "model_confidence": round(confidence, 3),
    }


def analyze_intent(subject: str, body: str) -> dict:
    """
    Returns:
        {
            "score": 0-100,
            "category": "safe" | "phishing" | "bec" | "spam" | "malware",
            "reasons": [str, ...],
            "engine_used": "groq" | "gemini" | "local-sklearn",
        }

    Engine priority: Groq -> Gemini -> local scikit-learn model. Whichever
    engine answers first supplies the base score/category; the keyword-based
    heuristics below are ALWAYS applied on top as an extra layer, regardless
    of engine, so a fast LLM response never skips the deterministic checks.
    """
    text = f"{subject}\n{body}".strip()
    if not text:
        return {"score": 0, "category": "safe", "reasons": ["Empty email content"], "engine_used": "none"}

    llm_result = analyze_intent_llm(subject, body)
    base = llm_result if llm_result is not None else _analyze_with_local_model(text)

    score = base["score"]
    category = base["category"]
    engine_used = base["engine_used"]
    confidence = base.get("model_confidence")

    reasons = list(base.get("reasons") or [])
    urgency_hits = _find_matches(text, URGENCY_WORDS)
    cred_hits = _find_matches(text, CREDENTIAL_WORDS)
    exec_hits = _find_matches(text, EXEC_IMPERSONATION_HINTS)

    if urgency_hits:
        reasons.append(f"Urgency/pressure language detected: {', '.join(sorted(set(urgency_hits))[:4])}")
        score = min(100, score + 10)
    if cred_hits:
        reasons.append(f"Credential-harvesting phrasing detected: {', '.join(sorted(set(cred_hits))[:3])}")
        score = min(100, score + 15)
        if category == "safe":
            category = "phishing"
    if exec_hits and category != "phishing":
        reasons.append(f"Executive-impersonation / BEC pattern detected: {', '.join(sorted(set(exec_hits))[:3])}")
        score = min(100, score + 10)
        if category == "safe":
            category = "bec"

    money_pattern = re.search(r"(wire|transfer|gift card|payment).{0,40}(\$|usd|inr|₹)?\s?\d{2,}", text, re.I)
    if money_pattern:
        reasons.append("Monetary transfer / payment-diversion request detected")
        score = min(100, score + 15)
        if category == "safe":
            category = "bec"

    if not reasons:
        if confidence is not None:
            reasons.append(f"Model classified content as '{category}' with {round(confidence * 100)}% confidence")
        else:
            reasons.append(f"{engine_used} classified content as '{category}'")

    result = {
        "score": int(min(100, max(0, score))),
        "category": category,
        "reasons": reasons,
        "engine_used": engine_used,
    }
    if confidence is not None:
        result["model_confidence"] = confidence
    return result
