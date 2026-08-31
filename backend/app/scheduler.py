"""
Background job that keeps real-time detection alive.

Gmail push-notification watches (users.watch) expire after 7 days. Without
renewal, "real-time" detection would silently stop working a week after
being turned on. This scheduler checks every few hours for watches expiring
soon and renews them automatically.

Started from app.main on FastAPI startup. Wrapped defensively so a missing
APScheduler install or misconfigured Google Cloud project never crashes the
whole app — real-time detection is an enhancement, not a hard dependency.
"""
import datetime
import logging

from app.config import settings

logger = logging.getLogger("mailtrace.scheduler")

_scheduler = None


def _renew_expiring_watches():
    from app.database import SessionLocal
    from app.models import GmailAccount
    from app.services import gmail_service

    db = SessionLocal()
    try:
        soon = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        accounts = db.query(GmailAccount).filter(
            GmailAccount.watch_expiration.isnot(None),
            GmailAccount.watch_expiration <= soon,
        ).all()

        for account in accounts:
            try:
                creds = gmail_service.credentials_from_account(account)
                result = gmail_service.start_watch(creds, settings.pubsub_topic_full_name)
                account.last_history_id = result["history_id"]
                account.watch_expiration = result["expiration"]
                logger.info("Renewed Gmail watch for account_id=%s", account.id)
            except Exception as exc:
                logger.warning("Failed to renew watch for account_id=%s: %s", account.id, exc)

        db.commit()
    finally:
        db.close()


def start_scheduler():
    """Call once at app startup. No-ops safely if real-time detection isn't
    configured or APScheduler isn't installed."""
    global _scheduler
    if not settings.GOOGLE_CLOUD_PROJECT:
        logger.info("GOOGLE_CLOUD_PROJECT not set — skipping watch-renewal scheduler.")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("APScheduler not installed — watch auto-renewal is disabled. "
                        "Run 'pip install -r requirements.txt'.")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_renew_expiring_watches, "interval", hours=6, id="renew_gmail_watches")
    _scheduler.start()
    logger.info("Gmail watch-renewal scheduler started (checks every 6 hours).")


def stop_scheduler():
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
