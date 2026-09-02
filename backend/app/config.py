import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Auth ---
    JWT_SECRET: str = os.getenv("JWT_SECRET", "CHANGE_ME_dev_only_insecure_secret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

    # --- Google OAuth / Gmail API ---
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/gmail/callback")
    # NOTE: upgraded from gmail.readonly -> gmail.modify so the backend can
    # apply/remove labels for the auto-quarantine feature (still never
    # sends/deletes mail). See SETUP_GUIDE.md.
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ]

    # Where to send the browser back to after the Google consent screen
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # How many recent messages to pull per manual "Sync Gmail" click
    GMAIL_SYNC_MAX_RESULTS: int = int(os.getenv("GMAIL_SYNC_MAX_RESULTS", "15"))

    # --- AI engine: Groq (primary, fastest) + Gemini (fallback) + local
    # scikit-learn model (final offline fallback so analysis NEVER fails) ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "6"))

    # --- Real-time detection (Gmail push notifications via Cloud Pub/Sub) ---
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    PUBSUB_TOPIC: str = os.getenv("PUBSUB_TOPIC", "mailtrace-gmail-notifications")
    # Shared secret appended to the Pub/Sub push subscription's endpoint URL
    # (?token=...) so /gmail/webhook can reject requests that don't come
    # from your own Pub/Sub subscription.
    PUBSUB_VERIFICATION_TOKEN: str = os.getenv("PUBSUB_VERIFICATION_TOKEN", "")

    @property
    def pubsub_topic_full_name(self) -> str:
        return f"projects/{self.GOOGLE_CLOUD_PROJECT}/topics/{self.PUBSUB_TOPIC}"
        # --- Blockchain evidence audit ---
    BLOCKCHAIN_ENABLED: bool = (
        os.getenv("BLOCKCHAIN_ENABLED", "false").lower() == "true"
    )

    BLOCKCHAIN_RPC_URL: str = os.getenv("BLOCKCHAIN_RPC_URL", "")

    BLOCKCHAIN_CONTRACT_ADDRESS: str = os.getenv(
        "BLOCKCHAIN_CONTRACT_ADDRESS", ""
    )

    # NEVER hard-code this value.
    BLOCKCHAIN_PRIVATE_KEY: str = os.getenv(
        "BLOCKCHAIN_PRIVATE_KEY", ""
    )
    # --- Auto-quarantine ---
    # Any case with final_risk_score >= this AND decision in
    # (QUARANTINE, BLOCK) gets pulled out of the inbox automatically.
    QUARANTINE_RISK_THRESHOLD: int = int(os.getenv("QUARANTINE_RISK_THRESHOLD", "70"))
    QUARANTINE_GMAIL_LABEL: str = os.getenv("QUARANTINE_GMAIL_LABEL", "MailTrace/Quarantined")


settings = Settings()
