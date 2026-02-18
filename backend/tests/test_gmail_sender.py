"""Tests for GmailAPISender — Gmail API email sending."""

from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from campaign.gmail import GmailError
from campaign.gmail_sender import GmailAPISender
from campaign.sender import SendResult


@pytest.fixture
def sender():
    return GmailAPISender()


@pytest.fixture
def mock_service():
    service = MagicMock()
    service.users().messages().send.return_value.execute.return_value = {
        "id": "msg-abc123",
        "threadId": "thread-xyz789",
    }
    return service


class TestSendEmail:
    @patch("campaign.gmail_sender.build_gmail_service")
    def test_successful_send(self, mock_build, sender, mock_service):
        mock_build.return_value = mock_service

        result = sender.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body_html="<p>Hello</p>",
            body_text="Hello",
        )

        assert isinstance(result, SendResult)
        assert result.message_id == "msg-abc123"
        assert result.thread_id == "thread-xyz789"
        mock_service.users().messages().send.assert_called_once()

    @patch("campaign.gmail_sender.build_gmail_service")
    def test_send_with_thread_id(self, mock_build, sender, mock_service):
        mock_build.return_value = mock_service

        sender.send_email(
            to="recipient@example.com",
            subject="Re: Test",
            body_html="<p>Reply</p>",
            body_text="Reply",
            thread_id="existing-thread-id",
        )

        call_args = mock_service.users().messages().send.call_args
        assert "threadId" in str(call_args)

    @patch("campaign.gmail_sender.build_gmail_service")
    def test_rate_limit_raises_retryable_error(self, mock_build, sender):
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        resp = MagicMock()
        resp.status = 429
        mock_service.users().messages().send.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"Rate Limit Exceeded"
        )

        with pytest.raises(GmailError) as exc_info:
            sender.send_email(
                to="recipient@example.com",
                subject="Test",
                body_html="<p>Hi</p>",
                body_text="Hi",
            )

        assert exc_info.value.retryable is True
        assert exc_info.value.error_code == "rate_limited"

    @patch("campaign.gmail_sender.build_gmail_service")
    def test_other_http_error_raises_non_retryable(self, mock_build, sender):
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        resp = MagicMock()
        resp.status = 403
        mock_service.users().messages().send.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"Forbidden"
        )

        with pytest.raises(GmailError) as exc_info:
            sender.send_email(
                to="recipient@example.com",
                subject="Test",
                body_html="<p>Hi</p>",
                body_text="Hi",
            )

        assert exc_info.value.retryable is False
        assert exc_info.value.error_code == "send_failed"

    @patch("campaign.gmail_sender.build_gmail_service")
    def test_unexpected_exception_raises_gmail_error(self, mock_build, sender):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.users().messages().send.return_value.execute.side_effect = RuntimeError(
            "Connection lost"
        )

        with pytest.raises(GmailError) as exc_info:
            sender.send_email(
                to="recipient@example.com",
                subject="Test",
                body_html="<p>Hi</p>",
                body_text="Hi",
            )

        assert "Failed to send email" in exc_info.value.message


class TestIsReady:
    @patch("campaign.gmail_sender.is_authenticated", return_value=True)
    def test_ready_when_authenticated(self, mock_auth, sender):
        assert sender.is_ready() is True

    @patch("campaign.gmail_sender.is_authenticated", return_value=False)
    def test_not_ready_when_unauthenticated(self, mock_auth, sender):
        assert sender.is_ready() is False


class TestGetDisplayName:
    def test_display_name(self, sender):
        assert sender.get_display_name() == "Gmail API"
