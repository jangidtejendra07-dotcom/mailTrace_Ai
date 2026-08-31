"""Gmail Add-on API: compact, user-scoped analysis for the open Gmail message."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, User
from app.auth.dependencies import get_current_user_flexible

router = APIRouter(prefix="/api/v1/addon", tags=["gmail-addon"])


def _count_items(value):
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("urls", "links", "attachments", "items", "indicators"):
            if isinstance(value.get(key), list):
                return len(value[key])
    return 0


def _threat_summary(case: Case):
    url_result = case.url_result or {}
    attachment_result = case.attachment_result or {}
    forensics = case.forensics_result or {}
    geo = case.geolocation or {}

    return {
        "url_count": _count_items(url_result),
        "attachment_count": _count_items(attachment_result),
        "has_header_findings": bool(forensics),
        "has_geolocation": bool(geo),
        "geolocation": geo,
    }


@router.get("/lookup")
def lookup_case_by_message(
    gmail_message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    case = (
        db.query(Case)
        .filter(
            Case.user_id == current_user.id,
            Case.gmail_message_id == gmail_message_id,
        )
        .first()
    )
    if not case:
        return {"analyzed": False}

    reasons = (case.ai_result or {}).get("reasons", [])
    full = case.full_response or {}
    thread_count = full.get("thread_count", 1) if isinstance(full, dict) else 1
    suspicious_count = full.get("suspicious_count") if isinstance(full, dict) else None
    if suspicious_count is None:
        suspicious_count = 1 if case.decision in {"QUARANTINE", "BLOCK"} else 0

    return {
        "analyzed": True,
        "case_id": case.case_id,
        "subject": case.subject,
        "from_address": case.from_address,
        "decision": case.decision,
        "classification": case.classification,
        "final_risk_score": case.final_risk_score,
        "reasons": reasons[:6] if isinstance(reasons, list) else [],
        "quarantine_status": case.quarantine_status,
        "thread_count": max(int(thread_count or 1), 1),
        "suspicious_count": max(int(suspicious_count or 0), 0),
        "threats": _threat_summary(case),
    }