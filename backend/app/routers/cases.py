import datetime
from app.services.blockchain import blockchain_service
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Case, GmailAccount, User
from app.auth.dependencies import get_current_user, get_current_user_flexible
from app.services.report_generator import generate_case_report_pdf, generate_legal_report_pdf
from app.services import gmail_service, chain_of_custody, fusion_pipeline
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
    so "quarantined" isn't swallowed as a case_id path parameter.

    A case is "currently quarantined" when it has a quarantined_at
    timestamp AND has not since been released (released_at is still null).
    """
    cases = (
        db.query(Case)
        .filter(
            Case.user_id == current_user.id,
            Case.quarantined_at.isnot(None),
            Case.released_at.is_(None),
        )
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


@router.get("/cases/{case_id}/fusion-status")
def get_case_fusion_status(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Feature 1 — informational only. Shows whatever AI/Forensic stage
    results are currently cached in Redis for this case (24h TTL). This
    never affects the case's actual decision — that's already final and
    stored on the Case row itself. Returns null fields if Redis is
    unavailable or the cache has expired, which is expected and fine.
    """
    case = _get_owned_case(case_id, db, current_user)
    cached = fusion_pipeline.get_cached_fusion(case.case_id)
    return {
        "case_id": case.case_id,
        "cached_stages": cached,
        "note": "Informational only — the case's final decision is already stored and does not depend on this cache.",
    }


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


@router.get("/cases/{case_id}/report/legal/{jurisdiction}")
def get_case_legal_report(
    case_id: str,
    jurisdiction: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    Feature 4 — Legal-Grade Automation.

    Generates a jurisdiction-specific (us/eu), digitally-signed PDF that
    includes the full chain-of-custody trail for this case. Every call
    itself becomes a new custody-log entry, so if this report is
    regenerated later, both PDFs are visible in the trail.
    """
    if jurisdiction.lower() not in ("us", "eu"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "jurisdiction must be 'us' or 'eu'.")

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
    }

    custody_entries = chain_of_custody.get_custody_log(db, case.case_id)

    try:
        pdf_bytes = generate_legal_report_pdf(payload, jurisdiction.lower(), custody_entries)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))

    chain_of_custody.log_action(
        db, case.case_id, "LEGAL_REPORT_GENERATED", case.evidence_hash, current_user.id
    )
    db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{case_id}_legal_report_{jurisdiction.lower()}.pdf"'
        },
    )


@router.post("/cases/{case_id}/release")
def release_case(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """User reviewed a quarantined mail on the website and it was a false
    positive — put it back in the Gmail inbox. Always reversible; never a
    delete happens anywhere in this flow."""
    case = _get_owned_case(case_id, db, current_user)

    if case.quarantined_at is None or case.released_at is not None:
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

    case.released_at = datetime.datetime.utcnow()
    chain_of_custody.log_action(
        db, case.case_id, "RELEASED_FROM_QUARANTINE", case.evidence_hash, current_user.id
    )
    db.commit()

    return {"case_id": case.case_id, "released": True}