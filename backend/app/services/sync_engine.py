"""
Shared "fetch one Gmail message -> run pipeline -> save Case -> maybe
auto-quarantine" logic, used by BOTH:
  - the manual "Sync Gmail" button (app/routers/gmail.py: POST /sync)
  - the real-time Pub/Sub webhook (app/routers/webhook.py: POST /webhook)

Keeping this in one place means both paths always behave identically —
same risk logic, same quarantine rule, same DB shape — so there's no drift
between "on-demand" and "real-time" detection.
"""

import logging
import datetime

from sqlalchemy.orm import Session

from app.models import Case, GmailAccount
from app.pipeline import run_pipeline
from app.services import gmail_service, chain_of_custody, graph_manager
from app.services.blockchain import blockchain_service
from app.config import settings


logger = logging.getLogger("mailtrace.sync_engine")


def process_gmail_message(
    db: Session,
    user_id: int,
    account: GmailAccount,
    creds,
    msg_id: str
) -> dict | None:
    """
    Fetches + analyzes one Gmail message, persists it as a Case, and
    auto-quarantines it if the risk is high enough.

    Returns a small summary dict for the API response, or None if the
    message was already processed or could not be parsed.
    """

    already = db.query(Case).filter(
        Case.user_id == user_id,
        Case.gmail_message_id == msg_id
    ).first()

    if already:
        return None

    try:
        raw_bytes = gmail_service.fetch_raw_message(creds, msg_id)
        result = run_pipeline(raw_bytes)

    except Exception as exc:
        logger.warning(
            "Skipping unparseable Gmail message %s: %s",
            msg_id,
            exc
        )
        return None

    case = Case(
        case_id=result["case_id"],
        user_id=user_id,
        source="gmail",
        gmail_message_id=msg_id,
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
        full_response={
            k: v for k, v in result.items()
            if k != "_internal"
        },
    )

    # ---------------------------------------------------------
    # Auto-quarantine
    # ---------------------------------------------------------
    should_quarantine = (
        result["decision"] in ("QUARANTINE", "BLOCK")
        and result["risk_score"] >= settings.QUARANTINE_RISK_THRESHOLD
    )

    if should_quarantine:
        try:
            gmail_service.quarantine_message(
                creds,
                msg_id,
                settings.QUARANTINE_GMAIL_LABEL
            )

            case.quarantined_at = datetime.datetime.utcnow()

        except Exception as exc:
            logger.warning(
                "Could not quarantine message %s: %s",
                msg_id,
                exc
            )

    # ---------------------------------------------------------
    # Save Case first so DB-generated values are available
    # ---------------------------------------------------------
    db.add(case)
    db.flush()

    # ---------------------------------------------------------
    # Chain of custody — record analysis (and auto-quarantine, if it
    # happened) against this case_id now that it exists in the DB.
    # ---------------------------------------------------------
    chain_of_custody.log_action(db, case.case_id, "CASE_CREATED", case.evidence_hash, user_id)
    if case.quarantined_at is not None:
        chain_of_custody.log_action(db, case.case_id, "AUTO_QUARANTINED", case.evidence_hash, user_id)

    # ---------------------------------------------------------
    # Push this case's correlation graph into the persistent Neo4j
    # campaign graph (Feature 2). MERGE inside graph_manager means
    # repeated indicators across cases link automatically — no separate
    # correlation step needed here. Never blocks/fails email analysis.
    # ---------------------------------------------------------
    try:
        correlation_graph = result.get("correlation_graph") or {}
        graph_manager.update_graph(
            case.case_id,
            correlation_graph.get("nodes", []),
            correlation_graph.get("edges", []),
        )
    except Exception as exc:
        logger.warning(
            "Could not update campaign graph for case %s: %s",
            case.case_id,
            exc
        )

    # ---------------------------------------------------------
    # Record evidence on blockchain
    # ---------------------------------------------------------
    try:
        blockchain_result = blockchain_service.record_evidence(
            case_id=case.case_id,
            evidence_hash=case.evidence_hash,
            event_type="EMAIL_ANALYZED",
        )

        case.blockchain_status = blockchain_result.get("status")
        case.blockchain_tx_hash = blockchain_result.get(
            "transaction_hash"
        )
        case.blockchain_block_number = blockchain_result.get(
            "block_number"
        )
        case.blockchain_event_hash = case.evidence_hash

    except Exception as exc:
        # Blockchain failure should NOT stop email analysis.
        logger.warning(
            "Could not record blockchain evidence for case %s: %s",
            case.case_id,
            exc
        )

    # ---------------------------------------------------------
    # Return API summary
    # ---------------------------------------------------------
    return {
        "case_id": case.case_id,
        "subject": case.subject,
        "from_address": case.from_address,
        "decision": case.decision,
        "final_risk_score": case.final_risk_score,
        "quarantined": case.quarantined_at is not None,
    }