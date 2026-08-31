from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Gmail ----------
class GmailStatus(BaseModel):
    connected: bool
    gmail_address: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    realtime_enabled: bool = False
    watch_expires_at: Optional[datetime] = None


class GmailAuthUrl(BaseModel):
    authorization_url: str


class GmailSyncResult(BaseModel):
    fetched: int
    new_cases: int
    skipped_existing: int
    cases: list[dict]


# ---------- Cases ----------
class CaseSummary(BaseModel):
    case_id: str
    subject: Optional[str] = None
    from_address: Optional[str] = None
    classification: Optional[str] = None
    decision: Optional[str] = None
    final_risk_score: Optional[int] = None
    source: Optional[str] = None
    created_at: Optional[Any] = None

    class Config:
        from_attributes = True


class AnalyzeResponse(BaseModel):
    classification: str
    risk_score: int
    decision: str
    ai: dict
    authentication: dict
    sender: dict
    urls: list
    attachments: list
    ip_intelligence: dict
    geolocation: dict
    correlation_graph: dict
    case_id: str
    evidence_hash: str
    explanation: list

    class Config:
        extra = "allow"
