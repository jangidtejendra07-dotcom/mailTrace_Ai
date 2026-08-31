from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, User
from app.pipeline import run_pipeline
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze-email")
async def analyze_email(
    email_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not email_file.filename.lower().endswith((".eml", ".txt", ".msg")):
        raise HTTPException(400, "Please upload a .eml (RFC 822) email file")

    raw_bytes = await email_file.read()
    if not raw_bytes:
        raise HTTPException(400, "Uploaded file is empty")

    try:
        result = run_pipeline(raw_bytes)
    except Exception as exc:
        raise HTTPException(500, f"Failed to analyze email: {exc}")

    case = Case(
        case_id=result["case_id"],
        user_id=current_user.id,
        source="upload",
        subject=result.get("subject"),
        from_address=result["sender"]["from_address"],
        to_address=result["_internal"]["parsed_email"].get("to_header"),
        classification=result["classification"],
        decision=result["decision"],
        final_risk_score=result["risk_score"],
        ai_result=result["ai"],
        forensics_result=result["forensics"],
        url_result={"items": result["urls"]},
        attachment_result={"items": result["attachments"]},
        ip_intelligence=result["ip_intelligence"],
        geolocation=result["geolocation"],
        risk_fusion={"explanation": result["explanation"]},
        evidence_hash=result["evidence_hash"],
        full_response={k: v for k, v in result.items() if k != "_internal"},
    )
    db.add(case)
    db.commit()

    response = {k: v for k, v in result.items() if k != "_internal"}
    return response
