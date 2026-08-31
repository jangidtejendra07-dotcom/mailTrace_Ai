from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import datetime

from app.database import get_db
from app.models import User, GmailAccount
from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, decode_access_token
from app.schemas import GmailStatus, GmailAuthUrl, GmailSyncResult
from app.services import gmail_service
from app.services.sync_engine import process_gmail_message
from app.config import settings

router = APIRouter(prefix="/api/v1/gmail", tags=["gmail"])


@router.get("/status", response_model=GmailStatus)
def gmail_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = db.query(GmailAccount).filter(GmailAccount.user_id == current_user.id).first()
    if not account:
        return GmailStatus(connected=False)

    realtime_enabled = bool(
        account.watch_expiration and account.watch_expiration > datetime.datetime.now(datetime.timezone.utc)
    )
    return GmailStatus(
        connected=True,
        gmail_address=account.gmail_address,
        last_synced_at=account.last_synced_at,
        realtime_enabled=realtime_enabled,
        watch_expires_at=account.watch_expiration,
    )


@router.get("/connect", response_model=GmailAuthUrl)
def gmail_connect(current_user: User = Depends(get_current_user)):
    if not gmail_service.is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Gmail integration is not configured on this server. "
            "Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in backend/.env (see README).",
        )
    # Encode the user id into a short-lived signed 'state' token so the
    # public /callback redirect (no Authorization header available) can
    # still identify which account to attach the Gmail tokens to.
    state = create_access_token(subject=str(current_user.id), extra_claims={"purpose": "gmail_oauth"})
    url = gmail_service.build_authorization_url(state=state)
    return GmailAuthUrl(authorization_url=url)


@router.get("/callback")
def gmail_callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(state)
        if payload.get("purpose") != "gmail_oauth":
            raise ValueError("invalid state purpose")
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OAuth state")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    creds = gmail_service.exchange_code_for_tokens(code)
    gmail_address = gmail_service.get_gmail_address(creds)

    account = db.query(GmailAccount).filter(GmailAccount.user_id == user.id).first()
    if not account:
        account = GmailAccount(user_id=user.id, gmail_address=gmail_address, access_token=creds.token)
        db.add(account)

    account.gmail_address = gmail_address
    account.access_token = creds.token
    if creds.refresh_token:  # only present on first consent — don't overwrite with None on reconnect
        account.refresh_token = creds.refresh_token
    account.token_expiry = creds.expiry
    db.commit()

    # Bounce the browser back to the frontend dashboard
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/inbox?gmail_connected=1")


@router.post("/disconnect")
def gmail_disconnect(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = db.query(GmailAccount).filter(GmailAccount.user_id == current_user.id).first()
    if account:
        db.delete(account)
        db.commit()
    return {"disconnected": True}


@router.post("/sync", response_model=GmailSyncResult)
def gmail_sync(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = db.query(GmailAccount).filter(GmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No Gmail account connected. Connect Gmail first.")

    try:
        creds = gmail_service.credentials_from_account(account)
        message_ids = gmail_service.list_recent_message_ids(creds, settings.GMAIL_SYNC_MAX_RESULTS)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not reach Gmail: {exc}")

    new_cases = []
    skipped = 0

    for msg_id in message_ids:
        summary = process_gmail_message(db, current_user.id, account, creds, msg_id)
        if summary is None:
            skipped += 1
        else:
            new_cases.append(summary)

    account.last_synced_at = datetime.datetime.utcnow()
    db.commit()

    return GmailSyncResult(
        fetched=len(message_ids),
        new_cases=len(new_cases),
        skipped_existing=skipped,
        cases=new_cases,
    )


@router.post("/watch/start")
def gmail_watch_start(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Turns on real-time detection: registers a Gmail push-notification
    watch so new mail is analyzed within seconds instead of waiting for a
    manual Sync click. Requires GOOGLE_CLOUD_PROJECT + PUBSUB_TOPIC to be
    configured and a Pub/Sub subscription pointed at /api/v1/gmail/webhook
    (see SETUP_GUIDE.md) — this call only fails gracefully if that's missing."""
    if not settings.GOOGLE_CLOUD_PROJECT:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Real-time detection isn't configured yet. Set GOOGLE_CLOUD_PROJECT "
            "and PUBSUB_TOPIC in backend/.env first — see SETUP_GUIDE.md.",
        )
    account = db.query(GmailAccount).filter(GmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Connect Gmail first.")

    try:
        creds = gmail_service.credentials_from_account(account)
        watch_result = gmail_service.start_watch(creds, settings.pubsub_topic_full_name)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not start Gmail watch: {exc}")

    account.last_history_id = watch_result["history_id"]
    account.watch_expiration = watch_result["expiration"]
    db.commit()

    return {
        "watching": True,
        "expires_at": watch_result["expiration"],
        "note": "Real-time detection is now on. New mail will be analyzed automatically.",
    }


@router.post("/watch/stop")
def gmail_watch_stop(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = db.query(GmailAccount).filter(GmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No Gmail account connected.")
    try:
        creds = gmail_service.credentials_from_account(account)
        gmail_service.stop_watch(creds)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not stop Gmail watch: {exc}")

    account.watch_expiration = None
    db.commit()
    return {"watching": False}
