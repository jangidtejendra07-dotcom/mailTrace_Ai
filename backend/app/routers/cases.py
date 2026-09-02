import datetime
from app.services.blockchain import blockchain_service
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Case, GmailAccount, User
from app.auth.dependencies import get_current_user, get_current_user_flexible
from app.services.report_generator import generate_case_report_pdf
from app.services import gmail_service
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["cases"])


@router.get("/cases")
def list_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    cases = (
        db.query(Case)
        .filter(Case.user_id == current_user.id)
        .order_by(desc(Case.created_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "case_id": c.case_id,
            "subject": c.subject,
            "from_address": c.from_address,
            "classification": c.classification,
            "decision": c.decision,
            "final_risk_score": c.final_risk_score,
            "source": c.source,
            "created_at": c.created_at,
        }
        for c in cases
    ]


@router.get("/cases/quarantined")
def list_quarantined_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mail that was automatically pulled out of the user's inbox because it
    scored above the quarantine threshold. Registered BEFORE /cases/{case_id}
    so "quarantined" isn't swallowed as a case_id path parameter."""
    cases = (
        db.query(Case)
        .filter(Case.user_id == current_user.id, Case.quarantine_status == "quarantined")
        .order_by(desc(Case.created_at))
        .all()
    )
    return [
        {
            "case_id": c.case_id,
            "subject": c.subject,
            "from_address": c.from_address,
            "classification": c.classification,
            "decision": c.decision,
            "final_risk_score": c.final_risk_score,
            "reasons": (c.ai_result or {}).get("reasons", []),
            "quarantined_at": c.quarantined_at,
            "created_at": c.created_at,
        }
        for c in cases
    ]


def _get_owned_case(case_id: str, db: Session, current_user: User) -> Case:
    case = db.query(Case).filter(Case.case_id == case_id, Case.user_id == current_user.id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = _get_owned_case(case_id, db, current_user)
    return case.full_response

@router.get("/cases/{case_id}/blockchain/verify")
def verify_case_blockchain(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(case_id, db, current_user)

    if not case.evidence_hash:
        raise HTTPException(
            status_code=400,
            detail="This case has no evidence hash.",
        )

    result = blockchain_service.verify_evidence(
        case_id=case.case_id,
        evidence_hash=case.evidence_hash,
    )

    return {
        "case_id": case.case_id,
        "local_evidence_hash": case.evidence_hash,
        "blockchain_status": case.blockchain_status,
        "blockchain_transaction": case.blockchain_tx_hash,
        "verification": result,
    }


@router.get("/cases/{case_id}/report")
def get_case_report(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_flexible)):
    case = _get_owned_case(case_id, db, current_user)

    payload = {
        "case_id": case.case_id,
        "classification": case.classification,
        "decision": case.decision,
        "final_risk_score": case.final_risk_score,
        "subject": case.subject,
        "from_address": case.from_address,
        "evidence_hash": case.evidence_hash,
        "generated_at": str(case.created_at),
        "explanation": (case.risk_fusion or {}).get("explanation", []),
        "forensics_result": case.forensics_result or {},
        "geolocation": case.geolocation or {},
        "url_result": case.url_result or {},
        "attachment_result": case.attachment_result or {},
    }
    pdf_bytes = generate_case_report_pdf(payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{case_id}_report.pdf"'},
    )


@router.post("/cases/{case_id}/release")
def release_case(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """User reviewed a quarantined mail on the website and it was a false
    positive — put it back in the Gmail inbox. Always reversible; never a
    delete happens anywhere in this flow."""
    case = _get_owned_case(case_id, db, current_user)

    if case.quarantine_status != "quarantined":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This case isn't currently quarantined.")
    if not case.gmail_message_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This case has no linked Gmail message to release.")

    account = db.query(GmailAccount).filter(GmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Gmail account is no longer connected.")

    try:
        creds = gmail_service.credentials_from_account(account)
        gmail_service.release_message(creds, case.gmail_message_id, settings.QUARANTINE_GMAIL_LABEL)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not release message in Gmail: {exc}")

    case.quarantine_status = "released"
    case.released_at = datetime.datetime.utcnow()
    db.commit()

    return {"case_id": case.case_id, "quarantine_status": case.quarantine_status, "released": True}
