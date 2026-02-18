"""Tests for PlaywrightSender — Gmail web UI automation sender.

All Playwright objects (page, browser, context) are mocked using AsyncMock
since the sender uses the async Playwright API internally.
"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from campaign.playwright_sender import (
    COMPOSE_BUTTON_SELECTORS,
    PlaywrightSender,
)
from campaign.sender import SendError


@pytest.fixture
def mock_page():
    """Return a mock async Playwright Page.

    Most methods are AsyncMock (awaitable), but `url` and `is_closed()`
    are synchronous properties/methods on the real Playwright Page.
    """
    page = AsyncMock()
    # url is a plain property (not awaitable)
    type(page).url = PropertyMock(
        return_value="https://mail.google.com/mail/u/0/#inbox"
    )
    # is_closed() is synchronous on the real Page
    page.is_closed = MagicMock(return_value=False)
    # query_selector returns truthy for inbox-loaded checks
    page.query_selector.return_value = MagicMock()
    return page


@pytest.fixture
def sender(mock_page):
    """Return a PlaywrightSender with mocked browser/page."""
    s = PlaywrightSender()
    s._playwright = AsyncMock()
    s._browser = AsyncMock()
    s._context = AsyncMock()
    s._context.pages = [mock_page]
    s._page = mock_page
    return s


# ── send_email ───────────────────────────────────────────────────────────


class TestSendEmail:
    @pytest.mark.asyncio
    @patch("campaign.playwright_sender.settings")
    async def test_successful_send_calls_correct_sequence(
        self,
        mock_settings,
        sender,
        mock_page,
    ):
        mock_settings.playwright_send_delay_seconds = 0

        mock_element = AsyncMock()
        mock_page.wait_for_selector.return_value = mock_element
        mock_page.click.return_value = None
        mock_page.evaluate.return_value = "Hello body text"

        result = await sender._async_send_email(
            to="test@example.com",
            subject="Test Subject",
            body_html="<p>Hello</p>",
            body_text="Hello",
        )

        assert result.message_id == ""
        assert result.thread_id == ""
        assert mock_page.click.called

    @pytest.mark.asyncio
    @patch("campaign.playwright_sender.settings")
    async def test_applies_inter_send_delay(
        self, mock_settings, sender, mock_page
    ):
        mock_settings.playwright_send_delay_seconds = 5

        mock_element = AsyncMock()
        mock_page.wait_for_selector.return_value = mock_element
        mock_page.evaluate.return_value = "Hello body text"

        sleep_target = "campaign.playwright_sender.asyncio.sleep"
        with patch(sleep_target, new_callable=AsyncMock) as mock_sleep:
            await sender._async_send_email(
                to="test@example.com",
                subject="Test",
                body_html="<p>Hi</p>",
                body_text="Hi",
            )
            mock_sleep.assert_called_once_with(5)

    @pytest.mark.asyncio
    @patch("campaign.playwright_sender.settings")
    async def test_no_delay_when_zero(
        self, mock_settings, sender, mock_page
    ):
        mock_settings.playwright_send_delay_seconds = 0

        mock_element = AsyncMock()
        mock_page.wait_for_selector.return_value = mock_element
        mock_page.evaluate.return_value = "Hello body text"

        sleep_target = "campaign.playwright_sender.asyncio.sleep"
        with patch(sleep_target, new_callable=AsyncMock) as mock_sleep:
            await sender._async_send_email(
                to="test@example.com",
                subject="Test",
                body_html="<p>Hi</p>",
                body_text="Hi",
            )
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_expired_raises_send_error(
        self, sender, mock_page
    ):
        """When inbox is not loaded, send should fail with session_expired."""
        mock_page.query_selector.return_value = None
        type(mock_page).url = PropertyMock(
            return_value="https://accounts.google.com/signin"
        )

        with pytest.raises(SendError) as exc_info:
            await sender._async_send_email(
                to="test@example.com",
                subject="Test",
                body_html="<p>Hi</p>",
                body_text="Hi",
            )

        assert exc_info.value.error_code == "session_expired"
        assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    @patch("campaign.playwright_sender.settings")
    async def test_timeout_raises_retryable_error(
        self, mock_settings, sender, mock_page
    ):
        """Playwright timeout should be retryable."""
        mock_settings.playwright_send_delay_seconds = 0
        from playwright.async_api import (
            TimeoutError as PlaywrightTimeoutError,
        )

        mock_page.click.side_effect = PlaywrightTimeoutError("Timeout")
        mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError(
            "Timeout"
        )

        with pytest.raises(SendError) as exc_info:
            await sender._async_send_email(
                to="test@example.com",
                subject="Test",
                body_html="<p>Hi</p>",
                body_text="Hi",
            )

        assert exc_info.value.retryable is True


# ── is_ready ─────────────────────────────────────────────────────────────


class TestIsReady:
    def test_returns_false_when_no_page(self):
        sender = PlaywrightSender()
        assert sender.is_ready() is False

    def test_returns_false_when_page_closed(self, sender, mock_page):
        mock_page.is_closed.return_value = True
        assert sender.is_ready() is False

    @pytest.mark.asyncio
    async def test_returns_true_when_inbox_loaded(self, sender, mock_page):
        mock_page.query_selector.return_value = MagicMock()
        result = await sender._async_is_inbox_loaded()
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_on_login_page(
        self, sender, mock_page
    ):
        type(mock_page).url = PropertyMock(
            return_value="https://accounts.google.com/signin"
        )
        mock_page.query_selector.return_value = None
        result = await sender._async_is_inbox_loaded()
        assert result is False


# ── ensure_session ───────────────────────────────────────────────────────


class TestEnsureSession:
    @pytest.mark.asyncio
    async def test_detects_inbox_loaded(self, sender, mock_page):
        mock_page.query_selector.return_value = MagicMock()
        result = await sender.async_ensure_session()
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_login_page(self, sender, mock_page):
        type(mock_page).url = PropertyMock(
            return_value="https://accounts.google.com/signin"
        )
        mock_page.query_selector.return_value = None
        result = await sender.async_ensure_session()
        assert result is False

    @pytest.mark.asyncio
    async def test_navigates_to_gmail_when_not_on_gmail(
        self, sender, mock_page
    ):
        type(mock_page).url = PropertyMock(return_value="about:blank")
        mock_page.query_selector.return_value = MagicMock()
        await sender.async_ensure_session()
        mock_page.goto.assert_called_once()


# ── Multi-selector fallback ──────────────────────────────────────────────


class TestMultiSelectorFallback:
    @pytest.mark.asyncio
    @patch("campaign.playwright_sender.settings")
    async def test_first_selector_fails_second_succeeds(
        self,
        mock_settings,
        sender,
        mock_page,
    ):
        """When the first selector fails, _try_selectors tries the next."""
        mock_settings.playwright_send_delay_seconds = 0
        from playwright.async_api import (
            TimeoutError as PlaywrightTimeoutError,
        )

        call_count = 0

        async def click_side_effect(selector, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PlaywrightTimeoutError("First selector not found")
            return None

        mock_page.click.side_effect = click_side_effect
        mock_element = AsyncMock()
        mock_page.wait_for_selector.return_value = mock_element
        mock_page.evaluate.return_value = "Body text"

        result = await sender._async_send_email(
            to="test@example.com",
            subject="Test",
            body_html="<p>Hi</p>",
            body_text="Hi",
        )
        assert result.message_id == ""

    @pytest.mark.asyncio
    async def test_all_selectors_fail_raises_error(
        self, sender, mock_page
    ):
        """When all selectors fail, _try_selectors raises SendError."""
        from playwright.async_api import (
            TimeoutError as PlaywrightTimeoutError,
        )

        mock_page.click.side_effect = PlaywrightTimeoutError("Not found")
        mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError(
            "Not found"
        )

        with pytest.raises(SendError) as exc_info:
            await sender._try_selectors(
                COMPOSE_BUTTON_SELECTORS, "Compose button"
            )

        assert "Could not find Compose button" in exc_info.value.message


# ── close_browser ────────────────────────────────────────────────────────


class TestCloseBrowser:
    @pytest.mark.asyncio
    async def test_closes_context_and_playwright(self, sender):
        context = sender._context
        pw = sender._playwright

        await sender.async_close_browser()

        context.close.assert_called_once()
        pw.stop.assert_called_once()
        assert sender._page is None
        assert sender._context is None
        assert sender._playwright is None

    @pytest.mark.asyncio
    async def test_close_when_already_closed(self):
        sender = PlaywrightSender()
        # Should not raise
        await sender.async_close_browser()


# ── get_display_name ─────────────────────────────────────────────────────


class TestGetDisplayName:
    def test_display_name(self):
        sender = PlaywrightSender()
        assert sender.get_display_name() == "Playwright (Browser Automation)"


# ── get_session_email ────────────────────────────────────────────────────


class TestGetSessionEmail:
    def test_returns_none_when_not_detected(self):
        sender = PlaywrightSender()
        assert sender.get_session_email() is None

    def test_returns_email_when_set(self, sender):
        sender._session_email = "user@gmail.com"
        assert sender.get_session_email() == "user@gmail.com"
