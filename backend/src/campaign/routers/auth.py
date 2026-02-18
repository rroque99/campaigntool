"""Auth router — OAuth flow initiation, callback, status, and logout.

Also provides Playwright browser session endpoints.
"""

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
from campaign.schemas import (
    AuthStatusResponse,
    ErrorResponse,
    PlaywrightStatusResponse,
    QuotaResponse,
    SetSendBackendRequest,
)
from campaign.sender_factory import get_active_backend, set_active_backend

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status():
    """Check if Gmail is authenticated. Includes sender backend info."""
    backend = get_active_backend()
    reply_monitoring = backend == "gmail_api"

    if backend == "gmail_api":
        authenticated = is_authenticated()
        email = get_user_email() if authenticated else None
        return AuthStatusResponse(
            authenticated=authenticated,
            email=email,
            send_backend=backend,
            reply_monitoring_enabled=reply_monitoring,
        )

    # Playwright mode: Gmail OAuth isn't used for sending
    pw_active = False
    pw_email = None
    try:
        from campaign.sender_factory import get_sender

        sender = get_sender()
        if hasattr(sender, "async_is_ready"):
            pw_active = await sender.async_is_ready()
        elif hasattr(sender, "is_ready"):
            pw_active = sender.is_ready()
        if pw_active and hasattr(sender, "get_session_email"):
            pw_email = sender.get_session_email()
    except Exception:
        pass

    return AuthStatusResponse(
        authenticated=False,
        email=None,
        send_backend=backend,
        reply_monitoring_enabled=reply_monitoring,
        playwright_session_active=pw_active,
        playwright_session_email=pw_email,
    )


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


@router.post("/send-backend", response_model=AuthStatusResponse)
async def set_send_backend(body: SetSendBackendRequest):
    """Switch the active send backend at runtime."""
    await set_active_backend(body.send_backend)
    # Return updated auth status
    return await auth_status()


@router.get("/playwright/status", response_model=PlaywrightStatusResponse)
async def playwright_status():
    """Check if the Playwright browser has an active Gmail session."""
    if get_active_backend() != "playwright":
        return PlaywrightStatusResponse(session_active=False)

    from campaign.sender_factory import get_sender

    sender = get_sender()
    if not hasattr(sender, "ensure_session"):
        return PlaywrightStatusResponse(session_active=False)

    try:
        active = await sender.async_is_ready()
        email = sender.get_session_email() if active else None
        return PlaywrightStatusResponse(
            session_active=active,
            email=email,
            last_verified=datetime.now(timezone.utc) if active else None,
        )
    except Exception:
        return PlaywrightStatusResponse(session_active=False)


@router.post("/playwright/login")
async def playwright_login():
    """Launch the Playwright browser and navigate to Gmail for manual login."""
    if get_active_backend() != "playwright":
        return ErrorResponse(
            detail="Playwright sender is not configured. Set SEND_BACKEND=playwright.",
            error_code="wrong_backend",
        )

    from campaign.sender_factory import get_sender

    sender = get_sender()
    if not hasattr(sender, "initiate_login"):
        return ErrorResponse(
            detail="Current sender does not support browser login.",
            error_code="not_supported",
        )

    message = await sender.async_initiate_login()
    return {"message": message}


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
