"""Tests for sender abstraction — protocol conformance, error hierarchy, and factory."""

from unittest.mock import MagicMock, patch

import pytest

from campaign.gmail import GmailError
from campaign.gmail_sender import GmailAPISender
from campaign.playwright_sender import PlaywrightSender
from campaign.sender import SendBackend, SendError, SendResult
from campaign.sender_factory import get_sender, shutdown_sender

# ── Protocol Conformance ─────────────────────────────────────────────────


class TestSendBackendProtocol:
    def test_gmail_api_sender_satisfies_protocol(self):
        """GmailAPISender should implement all methods of SendBackend."""
        sender = GmailAPISender()
        assert hasattr(sender, "send_email")
        assert hasattr(sender, "is_ready")
        assert hasattr(sender, "get_display_name")
        # Verify it's structurally compatible with the protocol
        assert isinstance(sender, SendBackend)

    def test_playwright_sender_satisfies_protocol(self):
        """PlaywrightSender should implement all methods of SendBackend."""
        sender = PlaywrightSender()
        assert hasattr(sender, "send_email")
        assert hasattr(sender, "is_ready")
        assert hasattr(sender, "get_display_name")
        assert isinstance(sender, SendBackend)


# ── Error Hierarchy ──────────────────────────────────────────────────────


class TestErrorHierarchy:
    def test_send_error_defaults(self):
        error = SendError("test error")
        assert error.message == "test error"
        assert error.error_code == "send_error"
        assert error.retryable is False

    def test_send_error_retryable(self):
        error = SendError("retry me", retryable=True)
        assert error.retryable is True

    def test_gmail_error_is_send_error(self):
        error = GmailError("gmail fail", error_code="test")
        assert isinstance(error, SendError)

    def test_gmail_error_retryable(self):
        error = GmailError("rate limited", error_code="rate_limited", retryable=True)
        assert error.retryable is True
        error2 = GmailError("failed", error_code="send_failed")
        assert error2.retryable is False


# ── SendResult ───────────────────────────────────────────────────────────


class TestSendResult:
    def test_send_result_fields(self):
        result = SendResult(message_id="msg-123", thread_id="thread-456")
        assert result.message_id == "msg-123"
        assert result.thread_id == "thread-456"

    def test_send_result_empty_ids(self):
        result = SendResult(message_id="", thread_id="")
        assert result.message_id == ""
        assert result.thread_id == ""


# ── Sender Factory ───────────────────────────────────────────────────────


class TestSenderFactory:
    def setup_method(self):
        """Reset singleton before each test."""
        shutdown_sender()

    def teardown_method(self):
        shutdown_sender()

    @patch("campaign.sender_factory.settings")
    def test_returns_gmail_api_sender_by_default(self, mock_settings):
        mock_settings.send_backend = "gmail_api"
        sender = get_sender()
        assert isinstance(sender, GmailAPISender)

    @patch("campaign.sender_factory.settings")
    def test_returns_playwright_sender_when_configured(self, mock_settings):
        mock_settings.send_backend = "playwright"
        sender = get_sender()
        assert isinstance(sender, PlaywrightSender)

    @patch("campaign.sender_factory.settings")
    def test_raises_for_unknown_backend(self, mock_settings):
        mock_settings.send_backend = "unknown"
        with pytest.raises(ValueError, match="Unknown send_backend"):
            get_sender()

    @patch("campaign.sender_factory.settings")
    def test_singleton_returns_same_instance(self, mock_settings):
        mock_settings.send_backend = "gmail_api"
        sender1 = get_sender()
        sender2 = get_sender()
        assert sender1 is sender2

    @patch("campaign.sender_factory.settings")
    def test_shutdown_clears_singleton(self, mock_settings):
        mock_settings.send_backend = "gmail_api"
        sender1 = get_sender()
        shutdown_sender()
        sender2 = get_sender()
        assert sender1 is not sender2

    @patch("campaign.sender_factory.settings")
    def test_shutdown_calls_close_browser_on_playwright(self, mock_settings):
        mock_settings.send_backend = "playwright"
        sender = get_sender()
        sender.close_browser = MagicMock()
        shutdown_sender()
        sender.close_browser.assert_called_once()
