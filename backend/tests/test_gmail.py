"""Tests for Gmail API integration (auth, send, reply detection)."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from campaign.auth import (
    AuthError,
    get_auth_url,
    get_credentials,
    handle_callback,
    is_authenticated,
    revoke_credentials,
)
from campaign.gmail import (
    GmailError,
    ReplyCheckResult,
    build_gmail_service,
    check_replies,
)
from campaign.models import Email
from campaign.sender import SendError

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_credentials():
    """Return a mock Credentials object that appears valid."""
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "fake-refresh-token"
    creds.token = "fake-access-token"
    creds.token_uri = "https://oauth2.googleapis.com/token"
    creds.client_id = "fake-client-id"
    creds.client_secret = "fake-client-secret"
    creds.scopes = ["https://www.googleapis.com/auth/gmail.send"]
    return creds


@pytest.fixture
def mock_gmail_service():
    """Return a mock Gmail API service."""
    service = MagicMock()
    return service


@pytest.fixture
def token_data():
    """Sample token.json data."""
    return {
        "token": "fake-access-token",
        "refresh_token": "fake-refresh-token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "fake-client-id",
        "client_secret": "fake-client-secret",
        "scopes": ["https://www.googleapis.com/auth/gmail.send"],
    }


# ── Auth Module Tests ─────────────────────────────────────────────────────


class TestGetAuthUrl:
    @patch("campaign.auth._credentials_json_path")
    @patch("campaign.auth.Flow.from_client_secrets_file")
    def test_returns_auth_url(self, mock_flow_cls, mock_creds_path, tmp_path):
        fake_creds = tmp_path / "credentials.json"
        fake_creds.write_text("{}")
        mock_creds_path.return_value = fake_creds

        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?...",
            "state",
        )
        mock_flow_cls.return_value = mock_flow

        url = get_auth_url()
        assert url.startswith("https://accounts.google.com")

    @patch("campaign.auth._credentials_json_path")
    def test_raises_when_no_credentials_json(self, mock_creds_path):
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False
        mock_creds_path.return_value = mock_path

        with pytest.raises(AuthError, match="credentials.json not found"):
            get_auth_url()


class TestHandleCallback:
    @patch("campaign.auth._token_json_path")
    @patch("campaign.auth._credentials_json_path")
    @patch("campaign.auth.Flow.from_client_secrets_file")
    def test_stores_token(self, mock_flow_cls, mock_creds_path, mock_token_path, tmp_path):
        mock_creds_file = MagicMock(spec=Path)
        mock_creds_file.exists.return_value = True
        mock_creds_path.return_value = mock_creds_file

        token_file = tmp_path / "token.json"
        mock_token_path.return_value = token_file

        mock_creds = MagicMock()
        mock_creds.token = "new-token"
        mock_creds.refresh_token = "new-refresh"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "cid"
        mock_creds.client_secret = "csecret"
        mock_creds.scopes = ["scope"]

        mock_flow = MagicMock()
        mock_flow.credentials = mock_creds
        mock_flow_cls.return_value = mock_flow

        handle_callback("auth-code-123")

        assert token_file.exists()
        data = json.loads(token_file.read_text())
        assert data["token"] == "new-token"
        assert data["refresh_token"] == "new-refresh"


class TestGetCredentials:
    @patch("campaign.auth._token_json_path")
    def test_returns_valid_credentials(self, mock_token_path, tmp_path, token_data):
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps(token_data))
        mock_token_path.return_value = token_file

        with patch("campaign.auth.Credentials") as MockCreds:
            mock_creds = MagicMock()
            mock_creds.valid = True
            MockCreds.return_value = mock_creds

            result = get_credentials()
            assert result.valid

    @patch("campaign.auth._token_json_path")
    def test_raises_when_no_token_file(self, mock_token_path):
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False
        mock_token_path.return_value = mock_path

        with pytest.raises(AuthError, match="Not authenticated"):
            get_credentials()

    @patch("campaign.auth._token_json_path")
    def test_refreshes_expired_token(self, mock_token_path, tmp_path, token_data):
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps(token_data))
        mock_token_path.return_value = token_file

        with patch("campaign.auth.Credentials") as MockCreds, patch("campaign.auth.Request"):
            mock_creds = MagicMock()
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "refresh"
            mock_creds.token = "new-token"
            MockCreds.return_value = mock_creds

            result = get_credentials()
            mock_creds.refresh.assert_called_once()
            assert result is mock_creds

    @patch("campaign.auth._token_json_path")
    def test_raises_when_refresh_fails(self, mock_token_path, tmp_path, token_data):
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps(token_data))
        mock_token_path.return_value = token_file

        with patch("campaign.auth.Credentials") as MockCreds, patch("campaign.auth.Request"):
            mock_creds = MagicMock()
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "refresh"
            mock_creds.refresh.side_effect = Exception("Network error")
            MockCreds.return_value = mock_creds

            with pytest.raises(AuthError, match="Failed to refresh token"):
                get_credentials()


class TestIsAuthenticated:
    @patch("campaign.auth.get_credentials")
    def test_returns_true_when_valid(self, mock_get_creds):
        mock_get_creds.return_value = MagicMock(valid=True)
        assert is_authenticated() is True

    @patch("campaign.auth.get_credentials")
    def test_returns_false_when_no_creds(self, mock_get_creds):
        mock_get_creds.side_effect = AuthError("Not authenticated")
        assert is_authenticated() is False


class TestRevokeCredentials:
    @patch("campaign.auth.Request")
    @patch("campaign.auth.get_credentials")
    @patch("campaign.auth._token_json_path")
    def test_deletes_token_file(self, mock_token_path, mock_get_creds, mock_request, tmp_path):
        token_file = tmp_path / "token.json"
        token_file.write_text("{}")
        mock_token_path.return_value = token_file

        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        revoke_credentials()

        assert not token_file.exists()
        mock_creds.revoke.assert_called_once()


# ── Gmail Send Tests (moved to test_gmail_sender.py) ─────────────────────


class TestGmailErrorHierarchy:
    def test_gmail_error_is_send_error(self):
        """GmailError should be a subclass of SendError."""
        error = GmailError("test", error_code="test")
        assert isinstance(error, SendError)

    def test_gmail_error_retryable(self):
        """GmailError supports the retryable flag."""
        error = GmailError("rate limited", error_code="rate_limited", retryable=True)
        assert error.retryable is True

        error2 = GmailError("failed", error_code="send_failed")
        assert error2.retryable is False


class TestBuildGmailService:
    @patch("campaign.gmail.get_credentials")
    @patch("campaign.gmail.build")
    def test_builds_service(self, mock_build, mock_get_creds):
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        result = build_gmail_service()
        assert result is mock_service
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)

    @patch("campaign.gmail.get_credentials")
    def test_raises_on_auth_error(self, mock_get_creds):
        mock_get_creds.side_effect = AuthError("Not authenticated")
        with pytest.raises(AuthError):
            build_gmail_service()


# ── Reply Detection Tests ─────────────────────────────────────────────────


class TestCheckReplies:
    @patch("campaign.gmail.build_gmail_service")
    def test_initial_sync_returns_current_history_id(self, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.users().getProfile.return_value.execute.return_value = {"historyId": "12345"}

        result = check_replies(None)

        assert isinstance(result, ReplyCheckResult)
        assert result.new_history_id == "12345"
        assert result.replied_thread_ids == []

    @patch("campaign.gmail.build_gmail_service")
    def test_detects_replies(self, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.users().history().list.return_value.execute.return_value = {
            "historyId": "12350",
            "history": [
                {
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "msg-abc",
                                "threadId": "thread-001",
                                "labelIds": ["INBOX"],
                            }
                        }
                    ]
                },
                {
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "msg-def",
                                "threadId": "thread-002",
                                "labelIds": ["INBOX"],
                            }
                        }
                    ]
                },
            ],
        }

        result = check_replies("12340")

        assert result.new_history_id == "12350"
        assert "thread-001" in result.replied_thread_ids
        assert "thread-002" in result.replied_thread_ids

    @patch("campaign.gmail.build_gmail_service")
    def test_ignores_sent_messages(self, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.users().history().list.return_value.execute.return_value = {
            "historyId": "12350",
            "history": [
                {
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "msg-sent",
                                "threadId": "thread-001",
                                "labelIds": ["SENT"],
                            }
                        }
                    ]
                }
            ],
        }

        result = check_replies("12340")
        assert result.replied_thread_ids == []

    @patch("campaign.gmail.build_gmail_service")
    def test_no_new_history(self, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.users().history().list.return_value.execute.return_value = {
            "historyId": "12340",
        }

        result = check_replies("12340")
        assert result.new_history_id == "12340"
        assert result.replied_thread_ids == []

    @patch("campaign.gmail.build_gmail_service")
    def test_expired_history_id_resyncs(self, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        from googleapiclient.errors import HttpError

        resp = MagicMock()
        resp.status = 404
        mock_service.users().history().list.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"History ID expired"
        )
        mock_service.users().getProfile.return_value.execute.return_value = {"historyId": "99999"}

        result = check_replies("old-id")
        assert result.new_history_id == "99999"
        assert result.replied_thread_ids == []

    @patch("campaign.gmail.build_gmail_service")
    def test_deduplicates_thread_ids(self, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.users().history().list.return_value.execute.return_value = {
            "historyId": "12350",
            "history": [
                {
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "msg-1",
                                "threadId": "thread-001",
                                "labelIds": ["INBOX"],
                            }
                        },
                        {
                            "message": {
                                "id": "msg-2",
                                "threadId": "thread-001",
                                "labelIds": ["INBOX"],
                            }
                        },
                    ]
                }
            ],
        }

        result = check_replies("12340")
        assert result.replied_thread_ids == ["thread-001"]


# ── Auth Router Tests ─────────────────────────────────────────────────────


class TestAuthRoutes:
    @pytest.mark.anyio
    @patch("campaign.routers.auth.is_authenticated", return_value=False)
    async def test_status_unauthenticated(self, mock_auth, test_client):
        response = await test_client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["email"] is None

    @pytest.mark.anyio
    @patch("campaign.routers.auth.get_user_email", return_value="user@gmail.com")
    @patch("campaign.routers.auth.is_authenticated", return_value=True)
    async def test_status_authenticated(self, mock_auth, mock_email, test_client):
        response = await test_client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["email"] == "user@gmail.com"

    @pytest.mark.anyio
    @patch(
        "campaign.routers.auth.get_auth_url", return_value="https://accounts.google.com/oauth?..."
    )
    async def test_login_returns_url(self, mock_url, test_client):
        response = await test_client.get("/api/v1/auth/login")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert data["auth_url"].startswith("https://accounts.google.com")

    @pytest.mark.anyio
    @patch("campaign.routers.auth.handle_callback")
    async def test_callback_redirects(self, mock_handle, test_client):
        response = await test_client.get(
            "/api/v1/auth/callback?code=test-code",
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert "auth=success" in response.headers["location"]
        mock_handle.assert_called_once_with("test-code")

    @pytest.mark.anyio
    @patch("campaign.routers.auth.revoke_credentials")
    async def test_logout(self, mock_revoke, test_client):
        response = await test_client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert "Logged out" in response.json()["detail"]
        mock_revoke.assert_called_once()


class TestQuotaRoute:
    @pytest.mark.anyio
    async def test_quota_empty(self, test_client):
        response = await test_client.get("/api/v1/auth/quota")
        assert response.status_code == 200
        data = response.json()
        assert data["sent_today"] == 0
        assert data["limit"] == 500
        assert data["remaining"] == 500

    @pytest.mark.anyio
    async def test_quota_with_sent_emails(self, test_client, test_db):
        from campaign.models import Campaign, Recipient

        campaign = Campaign(name="Test", status="in_progress")
        test_db.add(campaign)
        test_db.flush()

        recipient = Recipient(campaign_id=campaign.id, email="r@example.com")
        test_db.add(recipient)
        test_db.flush()

        for i in range(3):
            email = Email(
                campaign_id=campaign.id,
                recipient_id=recipient.id,
                subject=f"Email {i}",
                status="sent",
                sent_at=datetime.now(timezone.utc),
            )
            test_db.add(email)
        test_db.commit()

        response = await test_client.get("/api/v1/auth/quota")
        assert response.status_code == 200
        data = response.json()
        assert data["sent_today"] == 3
        assert data["remaining"] == 497
