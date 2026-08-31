"""
Real-time detection entry point.

Google Cloud Pub/Sub calls this endpoint (HTTP POST) the instant a watched
Gmail inbox changes, via a "push subscription". This is what makes MailTrace
"always on" instead of relying on a manual Sync click — see SETUP_GUIDE.md
for how to wire up the Pub/Sub topic/subscription that points here.

Security: Pub/Sub push requests aren't authenticated by default. We require
a shared-secret `?token=` query parameter (set on the push subscription's
endpoint URL) so random internet traffic can't trigger fake syncs.
"""
import base64
import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import GmailAccount
from app.services import gmail_service
from app.services.sync_engine import process_gmail_message
from app.config import settings

logger = logging.getLogger("mailtrace.webhook")

router = APIRouter(prefix="/api/v1/gmail", tags=["gmail-realtime"])


@router.post("/webhook")
async def gmail_webhook(request: Request):
    # --- 1. Verify the shared secret so only our own Pub/Sub subscription
    # can reach this endpoint. ---
    if settings.PUBSUB_VERIFICATION_TOKEN:
        token = request.query_params.get("token")
        if token != settings.PUBSUB_VERIFICATION_TOKEN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid webhook token")

    body = await request.json()
    # Pub/Sub push payload shape:
    # {"message": {"data": "<base64>", "messageId": "...", ...}, "subscription": "..."}
    envelope = body.get("message")
    if not envelope or "data" not in envelope:
        # Acknowledge anyway (200) so Pub/Sub doesn't keep retrying a
        # malformed message forever.
        return {"status": "ignored", "reason": "no data in envelope"}

    try:
        decoded = base64.b64decode(envelope["data"]).decode("utf-8")
        payload = json.loads(decoded)
        gmail_address = payload["emailAddress"]
        new_history_id = str(payload["historyId"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Malformed Pub/Sub payload: %s", exc)
        return {"status": "ignored", "reason": "malformed payload"}

    db: Session = SessionLocal()
    try:
        account = db.query(GmailAccount).filter(GmailAccount.gmail_address == gmail_address).first()
        if not account or not account.last_history_id:
            # Either this Gmail address isn't connected to any MailTrace
            # user, or we haven't started a watch/baseline for it yet.
            return {"status": "ignored", "reason": "unknown or unbaselined account"}

        try:
            creds = gmail_service.credentials_from_account(account)
            new_msg_ids, latest_history_id = gmail_service.list_new_message_ids_since(
                creds, account.last_history_id
            )
        except Exception as exc:
            # historyId can go stale (e.g. >7 days of no activity) — Google's
            # fix is to re-sync from scratch and start a fresh watch.
            logger.warning("History lookup failed for %s: %s", gmail_address, exc)
            return {"status": "error", "reason": "history lookup failed, re-run /gmail/watch/start"}

        processed = 0
        for msg_id in new_msg_ids:
            summary = process_gmail_message(db, account.user_id, account, creds, msg_id)
            if summary is not None:
                processed += 1

        account.last_history_id = latest_history_id
        db.commit()

        return {"status": "ok", "new_messages": len(new_msg_ids), "processed": processed}
    finally:
        db.close()
