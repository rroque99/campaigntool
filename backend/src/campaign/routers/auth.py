"""Auth router — OAuth flow initiation, callback, status, and logout."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from campaign.auth import (
    AuthError,
    get_auth_url,
    get_user_email,
    handle_callback,
    is_authenticated,
    revoke_credentials,
)
from campaign.config import settings
from campaign.database import get_db
from campaign.models import Email
from campaign.schemas import AuthStatusResponse, ErrorResponse, QuotaResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status():
    """Check if Gmail is authenticated."""
    authenticated = is_authenticated()
    email = get_user_email() if authenticated else None
    return AuthStatusResponse(authenticated=authenticated, email=email)


@router.get("/login")
async def auth_login():
    """Return the Google OAuth consent URL."""
    try:
        auth_url = get_auth_url()
        return {"auth_url": auth_url}
    except AuthError as e:
        return ErrorResponse(detail=e.message, error_code=e.error_code)


def _frontend_url() -> str:
    """Return the frontend base URL based on environment."""
    if settings.is_production:
        return ""  # same origin
    return "http://localhost:5173"


@router.get("/callback")
async def auth_callback(code: str = Query(...)):
    """Handle OAuth callback, store token, redirect to frontend."""
    base = _frontend_url()
    try:
        handle_callback(code)
        return RedirectResponse(url=f"{base}/settings?auth=success")
    except AuthError as e:
        return RedirectResponse(url=f"{base}/settings?auth=error&message={e.message}")
    except Exception:
        return RedirectResponse(url=f"{base}/settings?auth=error&message=Unexpected+error")


@router.post("/logout")
async def auth_logout():
    """Revoke credentials and delete stored token."""
    revoke_credentials()
    return {"detail": "Logged out successfully."}


@router.get("/quota", response_model=QuotaResponse)
async def auth_quota(db: Session = Depends(get_db)):
    """Return daily send quota status."""
    today_utc = datetime.now(timezone.utc).date()
    sent_today = (
        db.query(func.count(Email.id))
        .filter(
            Email.status == "sent",
            func.date(Email.sent_at) == today_utc,
        )
        .scalar()
        or 0
    )
    return QuotaResponse(
        sent_today=sent_today,
        limit=settings.daily_send_limit,
        remaining=max(0, settings.daily_send_limit - sent_today),
    )
