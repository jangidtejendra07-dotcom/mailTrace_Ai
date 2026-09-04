"""
Feature 4 — Chain of Custody logging.

Every analyst-visible action taken on a case (created, auto-quarantined,
released, legal report generated) is logged with a timestamp and the
case's evidence hash at that moment, so a legal report can show an
unbroken custody trail — proof the evidence wasn't quietly altered
between analysis and reporting.

Usage pattern: call log_action() with the SAME db session that the
calling code will commit anyway (sync_engine's db.flush(), or a router's
db.commit()). This function itself never commits, so a custody-log write
never causes a stray partial commit if something later in the same
request fails.
"""
import logging

from sqlalchemy.orm import Session

from app.models import CustodyLog

logger = logging.getLogger("mailtrace.chain_of_custody")


def log_action(
    db: Session,
    case_id: str,
    action: str,
    evidence_hash: str | None = None,
    user_id: int | None = None,
) -> CustodyLog | None:
    """
    Records one custody-log entry against a case_id. Never raises — a
    logging failure should never take down the actual feature (sync,
    release, report generation) that triggered it.
    """
    try:
        entry = CustodyLog(
            case_id=case_id,
            user_id=user_id,
            action=action,
            evidence_hash=evidence_hash,
        )
        db.add(entry)
        return entry
    except Exception as exc:
        logger.warning("Could not log custody action '%s' for case %s: %s", action, case_id, exc)
        return None


def get_custody_log(db: Session, case_id: str) -> list[dict]:
    """
    Returns the full custody trail for one case, oldest first, formatted
    for direct use inside a Jinja2 legal report template.
    """
    logs = (
        db.query(CustodyLog)
        .filter(CustodyLog.case_id == case_id)
        .order_by(CustodyLog.timestamp.asc())
        .all()
    )
    return [
        {
            "action": entry.action,
            "evidence_hash": entry.evidence_hash or "-",
            "timestamp": (
                entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
                if entry.timestamp else "-"
            ),
            "user_id": entry.user_id,
        }
        for entry in logs
    ]