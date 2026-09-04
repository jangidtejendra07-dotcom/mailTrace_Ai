"""
Gmail Add-on API.

The Gmail add-on:
1. Authenticates the Gmail user through the MailTrace JWT.
2. Looks for an existing Case for the opened Gmail message.
3. If no Case exists, it analyzes that Gmail message immediately using the
   already-connected GmailAccount credentials.
4. Returns the compact security result to the Gmail add-on.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, User, GmailAccount
from app.auth.dependencies import get_current_user_flexible
from app.services import gmail_service
from app.services.sync_engine import process_gmail_message


router = APIRouter(
    prefix="/api/v1/addon",
    tags=["gmail-addon"],
)


def _count_items(value):
    if isinstance(value, list):
        return len(value)

    if isinstance(value, dict):
        for key in (
            "urls",
            "links",
            "attachments",
            "items",
            "indicators",
        ):
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


def _case_response(case: Case):
    """
    Convert a Case into the compact response expected by the Gmail add-on.
    """

    reasons = (case.ai_result or {}).get("reasons", [])

    full = case.full_response or {}

    thread_count = (
        full.get("thread_count", 1)
        if isinstance(full, dict)
        else 1
    )

    suspicious_count = (
        full.get("suspicious_count")
        if isinstance(full, dict)
        else None
    )

    if suspicious_count is None:
        suspicious_count = (
            1
            if case.decision in {"QUARANTINE", "BLOCK"}
            else 0
        )

    # Case model does not contain quarantine_status.
    # Derive it from the timestamps that actually exist.
    if case.quarantined_at is not None:
        quarantine_status = "QUARANTINED"
    elif case.released_at is not None:
        quarantine_status = "RELEASED"
    else:
        quarantine_status = None

    return {
        "analyzed": True,

        "case_id": case.case_id,

        "subject": case.subject,

        "from_address": case.from_address,

        "decision": case.decision,

        "classification": case.classification,

        "final_risk_score": case.final_risk_score,

        "reasons": (
            reasons[:6]
            if isinstance(reasons, list)
            else []
        ),

        "quarantine_status": quarantine_status,

        "thread_count": max(
            int(thread_count or 1),
            1,
        ),

        "suspicious_count": max(
            int(suspicious_count or 0),
            0,
        ),

        "threats": _threat_summary(case),
    }


@router.get("/lookup")
def lookup_case_by_message(
    gmail_message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    Look up a Gmail message.

    If it has already been analyzed, return the existing Case.

    If it has NOT been analyzed yet, analyze the currently opened Gmail
    message immediately using the Gmail account already connected to the
    MailTrace user.
    """

    gmail_message_id = str(
        gmail_message_id or ""
    ).strip()

    if not gmail_message_id:
        raise HTTPException(
            status_code=400,
            detail="Gmail message ID is required",
        )

    # ---------------------------------------------------------
    # 1. Existing case
    # ---------------------------------------------------------

    case = (
        db.query(Case)
        .filter(
            Case.user_id == current_user.id,
            Case.gmail_message_id == gmail_message_id,
        )
        .first()
    )

    if case:
        return _case_response(case)

    # ---------------------------------------------------------
    # 2. Find the Gmail account connected to this MailTrace user
    # ---------------------------------------------------------

    account = (
        db.query(GmailAccount)
        .filter(
            GmailAccount.user_id == current_user.id
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=403,
            detail=(
                "No Gmail account is connected to this "
                "MailTrace account."
            ),
        )

    # ---------------------------------------------------------
    # 3. Rebuild Gmail OAuth credentials
    # ---------------------------------------------------------

    try:
        creds = gmail_service.credentials_from_account(
            account
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not refresh the connected Gmail "
                f"credentials: {exc}"
            ),
        )

    # ---------------------------------------------------------
    # 4. Analyze the currently opened Gmail message
    # ---------------------------------------------------------

    try:
        process_gmail_message(
            db=db,
            user_id=current_user.id,
            account=account,
            creds=creds,
            msg_id=gmail_message_id,
        )

        db.commit()

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to analyze the Gmail message: "
                f"{exc}"
            ),
        )

    # ---------------------------------------------------------
    # 5. Read the newly created Case
    # ---------------------------------------------------------

    case = (
        db.query(Case)
        .filter(
            Case.user_id == current_user.id,
            Case.gmail_message_id == gmail_message_id,
        )
        .first()
    )

    if not case:
        return {
            "analyzed": False,
            "error": (
                "MailTrace could not create a case for "
                "this Gmail message."
            ),
        }

    return _case_response(case)