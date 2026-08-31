"""
Live Gmail inbox connection (spec Section 1 / 14).

Uses standard Google OAuth2 (Authorization Code flow) so a user can connect
their own Gmail inbox to MailTrace. Once connected, /api/v1/gmail/sync pulls
recent messages via the Gmail REST API (format=raw), decodes each into a raw
RFC822 byte string, and feeds it straight into the existing analysis pipeline
— the same pipeline used for manually uploaded .eml files.

Two sync modes are supported:
  1. Manual/on-demand — the "Sync Gmail" button (POST /api/v1/gmail/sync).
  2. Real-time — Gmail push notifications via Cloud Pub/Sub (`users.watch`),
     which POST to /api/v1/gmail/webhook the instant new mail arrives. This
     requires a publicly reachable HTTPS backend and a Google Cloud Pub/Sub
     topic/subscription (see SETUP_GUIDE.md) — it will NOT work against
     localhost, since Google's servers need to reach your webhook.

Honesty note (kept from the original spec): this is still *inbox* monitoring,
not *pre-delivery* blocking before a message is written to the mailbox — true
pre-delivery interception needs a mail-routing/security-gateway deployment
(e.g. a Workspace add-on with a pre-delivery hook). What this DOES achieve is
near-real-time (typically single-digit seconds) detection + auto-quarantine
after the message lands, which is what "always watching" means here.

Setup required (see README "Gmail OAuth setup"):
  1. Create a Google Cloud project, enable the Gmail API.
  2. Create an OAuth 2.0 Client ID (type: Web application).
  3. Add http://localhost:8000/api/v1/gmail/callback as an authorized
     redirect URI.
  4. Put the client ID/secret into backend/.env as GOOGLE_CLIENT_ID /
     GOOGLE_CLIENT_SECRET.
"""
import base64
import datetime
import requests

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build

from app.config import settings

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def is_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def build_authorization_url(state: str) -> str:
    flow = Flow.from_client_config(
        _client_config(), scopes=settings.GMAIL_SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",       # required to receive a refresh_token
        include_granted_scopes="true",
        prompt="consent",            # forces refresh_token on repeat connects too
        state=state,
    )
    return auth_url


def exchange_code_for_tokens(code: str) -> Credentials:
    flow = Flow.from_client_config(
        _client_config(), scopes=settings.GMAIL_SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    flow.fetch_token(code=code)
    return flow.credentials


def get_gmail_address(creds: Credentials) -> str:
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json().get("email", "")


def credentials_from_account(account) -> Credentials:
    """Rehydrate google.oauth2.Credentials from a stored GmailAccount row,
    refreshing the access token first if it's expired."""
    creds = Credentials(
        token=account.access_token,
        refresh_token=account.refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=settings.GMAIL_SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleAuthRequest())
    return creds


def list_recent_message_ids(creds: Credentials, max_results: int) -> list[str]:
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    resp = service.users().messages().list(
        userId="me", maxResults=max_results, labelIds=["INBOX"]
    ).execute()
    return [m["id"] for m in resp.get("messages", [])]


def fetch_raw_message(creds: Credentials, message_id: str) -> bytes:
    """Returns the full RFC822 raw bytes of a Gmail message — the exact same
    format as an uploaded .eml file, so it can go straight into parse_eml()."""
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    msg = service.users().messages().get(userId="me", id=message_id, format="raw").execute()
    raw_b64url = msg["raw"]
    # Gmail uses URL-safe base64 without padding; pad it back out
    padded = raw_b64url + "=" * (-len(raw_b64url) % 4)
    return base64.urlsafe_b64decode(padded)


def credentials_expiry(creds: Credentials) -> datetime.datetime | None:
    return creds.expiry


# --------------------------------------------------------------------------
# Real-time push notifications (Cloud Pub/Sub) — makes detection "always on"
# instead of relying on the manual Sync button.
# --------------------------------------------------------------------------

def start_watch(creds: Credentials, topic_full_name: str) -> dict:
    """Registers a Gmail push-notification watch. Google will publish a
    message to the given Pub/Sub topic every time this inbox's mailbox
    state changes (new mail, label changes, etc). Expires after 7 days —
    must be renewed (see app/scheduler.py)."""
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    resp = service.users().watch(
        userId="me",
        body={"topicName": topic_full_name, "labelIds": ["INBOX"], "labelFilterAction": "include"},
    ).execute()
    # resp = {"historyId": "...", "expiration": "<epoch millis as string>"}
    expiration_dt = datetime.datetime.fromtimestamp(
        int(resp["expiration"]) / 1000, tz=datetime.timezone.utc
    )
    return {"history_id": resp["historyId"], "expiration": expiration_dt}


def stop_watch(creds: Credentials) -> None:
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    service.users().stop(userId="me").execute()


def list_new_message_ids_since(creds: Credentials, start_history_id: str) -> tuple[list[str], str]:
    """Used by the webhook: given the historyId we last processed, returns
    only the message IDs that were newly added to INBOX since then, plus
    the latest historyId to checkpoint for next time."""
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    message_ids: list[str] = []
    page_token = None
    latest_history_id = start_history_id

    while True:
        resp = service.users().history().list(
            userId="me",
            startHistoryId=start_history_id,
            historyTypes=["messageAdded"],
            labelId="INBOX",
            pageToken=page_token,
        ).execute()

        for record in resp.get("history", []):
            for added in record.get("messagesAdded", []):
                msg_id = added["message"]["id"]
                if msg_id not in message_ids:
                    message_ids.append(msg_id)

        latest_history_id = resp.get("historyId", latest_history_id)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return message_ids, latest_history_id


# --------------------------------------------------------------------------
# Label management — powers the auto-quarantine feature. Never deletes mail,
# only moves it in/out of the INBOX label so it's always reversible.
# --------------------------------------------------------------------------

def ensure_label(creds: Credentials, label_name: str) -> str:
    """Returns the Gmail label ID for label_name, creating it if needed."""
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    existing = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in existing:
        if label["name"] == label_name:
            return label["id"]

    created = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()
    return created["id"]


def quarantine_message(creds: Credentials, message_id: str, quarantine_label_name: str) -> None:
    """Removes INBOX (hides it from the primary inbox view) and adds the
    MailTrace quarantine label. The message is NOT deleted — fully reversible."""
    label_id = ensure_label(creds, quarantine_label_name)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]},
    ).execute()


def release_message(creds: Credentials, message_id: str, quarantine_label_name: str) -> None:
    """Reverses quarantine_message(): puts the mail back in the inbox."""
    label_id = ensure_label(creds, quarantine_label_name)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": ["INBOX"], "removeLabelIds": [label_id]},
    ).execute()
