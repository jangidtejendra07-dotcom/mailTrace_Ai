from sqlalchemy import (
    Column, String, Integer, JSON, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    gmail_account = relationship("GmailAccount", back_populates="user", uselist=False, cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="user", cascade="all, delete-orphan")


class GmailAccount(Base):
    """
    Stores the OAuth2 tokens for a user's connected Gmail inbox so MailTrace
    can pull messages via the Gmail API (Section 1/14 — live inbox connection,
    not just manual .eml upload).
    """
    __tablename__ = "gmail_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    gmail_address = Column(String, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Gmail historyId used for incremental sync (only fetch what's new) —
    # also the anchor point for real-time Pub/Sub webhook processing.
    last_history_id = Column(String, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    # Gmail push notification (users.watch) bookkeeping. Watches expire
    # after 7 days and must be renewed (see app/scheduler.py).
    watch_expiration = Column(DateTime(timezone=True), nullable=True)

    connected_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="gmail_account")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # "upload" (manual .eml) or "gmail" (pulled live from a connected inbox)
    source = Column(String, default="upload")
    gmail_message_id = Column(String, nullable=True, index=True)

    subject = Column(Text)
    from_address = Column(String)
    to_address = Column(String)

    classification = Column(String)
    decision = Column(String)
    final_risk_score = Column(Integer)

    ai_result = Column(JSON)
    forensics_result = Column(JSON)
    url_result = Column(JSON)
    attachment_result = Column(JSON)
    ip_intelligence = Column(JSON)
    geolocation = Column(JSON)
    risk_fusion = Column(JSON)

    evidence_hash = Column(String)
    full_response = Column(JSON)
        # Blockchain evidence audit
    blockchain_status = Column(String, nullable=True)
    blockchain_tx_hash = Column(String, nullable=True)
    blockchain_block_number = Column(Integer, nullable=True)
    blockchain_event_hash = Column(String, nullable=True)
    # Auto-quarantine tracking: null = never touched, "quarantined" = pulled
    # out of the inbox via Gmail label swap, "released" = user reviewed it
    # on the website and put it back in the inbox.
    quarantined_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="cases")

    __table_args__ = (
        UniqueConstraint("user_id", "gmail_message_id", name="uq_user_gmail_message"),
    )


class CustodyLog(Base):
    """
    Feature 4 — Chain of Custody.

    Every notable action taken on a case (analyzed, auto-quarantined,
    released, legal report generated, etc.) gets one row here with a
    timestamp and the evidence hash at that moment. A legal report pulls
    all rows for its case_id to show an unbroken custody trail — i.e. proof
    that the evidence wasn't silently altered between analysis and
    reporting.
    """
    __tablename__ = "custody_log"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.case_id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # e.g. "CASE_CREATED", "AUTO_QUARANTINED", "RELEASED_FROM_QUARANTINE",
    # "LEGAL_REPORT_GENERATED"
    action = Column(String, nullable=False)
    evidence_hash = Column(String, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())