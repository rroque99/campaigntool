"""OAuth2 flow and token management for Gmail API."""

import json
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from campaign.config import settings

logger = logging.getLogger(__name__)

REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback"


class AuthError(Exception):
    """Raised when authentication operations fail."""

    def __init__(self, message: str, error_code: str = "auth_error"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


def _credentials_json_path() -> Path:
    return settings.credentials_dir / "credentials.json"


def _token_json_path() -> Path:
    return settings.credentials_dir / "token.json"


def get_auth_url() -> str:
    """Generate Google OAuth consent URL."""
    creds_path = _credentials_json_path()
    if not creds_path.exists():
        raise AuthError(
            "credentials.json not found. Download it from Google Cloud Console.",
            error_code="missing_credentials",
        )

    flow = Flow.from_client_secrets_file(
        str(creds_path),
        scopes=settings.gmail_scopes,
        redirect_uri=REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def handle_callback(code: str) -> None:
    """Exchange authorization code for tokens and save to token.json."""
    creds_path = _credentials_json_path()
    if not creds_path.exists():
        raise AuthError(
            "credentials.json not found.",
            error_code="missing_credentials",
        )

    flow = Flow.from_client_secrets_file(
        str(creds_path),
        scopes=settings.gmail_scopes,
        redirect_uri=REDIRECT_URI,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    token_path = _token_json_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    token_path.write_text(json.dumps(token_data))
    logger.info("OAuth token saved successfully.")


def get_credentials() -> Credentials:
    """Load credentials from token.json, refreshing if needed.

    Returns valid Credentials or raises AuthError.
    """
    token_path = _token_json_path()
    if not token_path.exists():
        raise AuthError(
            "Not authenticated. Please complete the OAuth flow.",
            error_code="not_authenticated",
        )

    token_data = json.loads(token_path.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            token_data["token"] = creds.token
            token_path.write_text(json.dumps(token_data))
            return creds
        except Exception as e:
            raise AuthError(
                f"Failed to refresh token: {e}",
                error_code="token_refresh_failed",
            ) from e

    raise AuthError(
        "Credentials expired and cannot be refreshed. Please re-authenticate.",
        error_code="token_expired",
    )


def is_authenticated() -> bool:
    """Return True if valid (or refreshable) credentials exist."""
    try:
        get_credentials()
        return True
    except AuthError:
        return False


def get_user_email() -> str | None:
    """Fetch the authenticated user's email address from Gmail API."""
    try:
        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress")
    except AuthError:
        return None
    except Exception:
        logger.exception("Failed to fetch user email")
        return None


def revoke_credentials() -> None:
    """Revoke token and delete token.json."""
    token_path = _token_json_path()
    if token_path.exists():
        try:
            creds = get_credentials()
            creds.revoke(Request())
        except Exception:
            logger.warning("Could not revoke token with Google, deleting locally.")
        token_path.unlink()
        logger.info("Credentials revoked and token.json deleted.")
