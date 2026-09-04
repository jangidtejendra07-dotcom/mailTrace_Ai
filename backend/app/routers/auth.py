from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import requests

from app.database import get_db
from app.models import User, GmailAccount
from app.schemas import UserRegister, UserLogin, TokenResponse, UserOut
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(User)
        .filter(User.email == payload.email.lower())
        .first()
    )

    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An account with this email already exists",
        )

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id))

    return TokenResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == payload.email.lower())
        .first()
    )

    if not user or not verify_password(
        payload.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Account is disabled",
        )

    token = create_access_token(subject=str(user.id))

    return TokenResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(
    current_user: User = Depends(get_current_user),
):
    return UserOut.model_validate(current_user)


@router.post("/gmail-addon")
def gmail_addon_auth(
    google_access_token: str,
    db: Session = Depends(get_db),
):
    """
    Authenticate Gmail Add-on using Google's temporary Gmail access token.
    """

    if not google_access_token:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Google access token is required",
        )

    try:
        response = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={
                "Authorization": f"Bearer {google_access_token}",
            },
            timeout=8,
        )
    except requests.RequestException:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Could not verify Gmail identity with Google",
        )

    if response.status_code != 200:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired Google Gmail access token",
        )

    try:
        profile = response.json()
    except Exception:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Invalid response from Google Gmail API",
        )

    gmail_address = str(
        profile.get("emailAddress", "")
    ).strip().lower()

    if not gmail_address:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Could not determine Gmail account",
        )

    account = (
        db.query(GmailAccount)
        .filter(
            GmailAccount.gmail_address == gmail_address
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This Gmail account is not connected to MailTrace AI. "
            "Connect this Gmail account from the MailTrace dashboard first.",
        )

    user = (
        db.query(User)
        .filter(User.id == account.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "MailTrace user for this Gmail account was not found",
        )

    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "MailTrace account is disabled",
        )

    token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "purpose": "gmail_addon",
        },
    )

    return {
        "access_token": token,
        "gmail_address": gmail_address,
        "user_id": user.id,
    }