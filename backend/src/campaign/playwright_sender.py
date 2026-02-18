"""Playwright sender — sends emails by automating the Gmail web UI.

Implements the SendBackend protocol. Uses a persistent browser context
so the user only needs to log in once. The browser runs in headed mode
(Google blocks headless automation).

Uses the async Playwright API internally since FastAPI runs in an asyncio
event loop. Public methods come in both sync (for scheduler/APScheduler)
and async (for FastAPI endpoints) flavors where needed.
"""

import asyncio
import logging
import os
import signal
import threading
from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from campaign.config import settings
from campaign.sender import SendError, SendResult

logger = logging.getLogger(__name__)

GMAIL_URL = "https://mail.google.com"

# Multi-strategy selectors for Gmail UI elements (DOM is fragile).
COMPOSE_BUTTON_SELECTORS = [
    '[aria-label="Compose"]',
    'div[gh="cm"]',
    ".T-I.T-I-KE.L3",
]

SEND_BUTTON_SELECTORS = [
    '[aria-label="Send ‪(⌘Enter)‬"]',
    '[aria-label="Send ‪(Ctrl+Enter)‬"]',
    '[aria-label="Send"]',
    'div[data-tooltip="Send"]',
    'div[data-tooltip*="Send"]',
]

SUBJECT_SELECTORS = [
    '[name="subjectbox"]',
    'input[aria-label="Subject"]',
]

BODY_SELECTORS = [
    'div[aria-label="Message Body"]',
    'div[aria-label="Message Body"] div[contenteditable="true"]',
    'div[role="textbox"][aria-label="Message Body"]',
    "div.Am.Al.editable",
    'div[contenteditable="true"][aria-label]',
]

TO_FIELD_SELECTORS = [
    'input[aria-label="To recipients"]',
    'input[aria-label="To"]',
    'textarea[name="to"]',
    'input[name="to"]',
]

# Selector for the "Message sent" confirmation snackbar
SENT_CONFIRMATION_SELECTORS = [
    'span:has-text("Message sent")',
    'div[aria-live] span:has-text("Message sent")',
]

# Selectors indicating the inbox has loaded (user is logged in)
INBOX_LOADED_SELECTORS = [
    '[aria-label="Compose"]',
    'div[gh="cm"]',
    ".T-I.T-I-KE.L3",
    'div[role="navigation"]',
]


# Reference to the main asyncio event loop (set during browser launch).
# Needed so APScheduler threads can schedule coroutines on the correct loop.
_main_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro):
    """Run an async coroutine from synchronous code.

    Always schedules on the main event loop (where Playwright objects live)
    and waits via a threading event. Falls back to asyncio.run() only if
    no main loop has been set (e.g. before browser launch).
    """
    # Determine which loop to use
    loop = _main_loop
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

    if loop is not None and loop.is_running():
        result = [None]
        exc = [None]
        event = threading.Event()

        async def wrapper():
            try:
                result[0] = await coro
            except Exception as e:
                exc[0] = e
            finally:
                event.set()

        asyncio.run_coroutine_threadsafe(wrapper(), loop)
        event.wait(timeout=120)
        if exc[0] is not None:
            raise exc[0]
        return result[0]
    else:
        return asyncio.run(coro)


class PlaywrightSender:
    """Sends emails by automating the Gmail web UI via Playwright."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._session_email: str | None = None
        self._lock = asyncio.Lock()

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str,
        thread_id: str | None = None,
    ) -> SendResult:
        """Compose and send an email via Gmail web UI (sync wrapper)."""
        return _run_async(self._async_send_email(to, subject, body_html, body_text, thread_id))

    async def _async_send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str,
        thread_id: str | None = None,
    ) -> SendResult:
        """Compose and send an email via Gmail web UI."""
        await self._async_ensure_session()

        try:
            await self._click_compose()
            await self._fill_to(to)
            await self._fill_subject(subject)
            await self._fill_body(body_html, body_text)
            await self._click_send()
            await self._wait_for_sent_confirmation()
        except SendError:
            raise
        except PlaywrightTimeoutError as e:
            raise SendError(
                f"Timeout during send flow: {e}",
                error_code="timeout",
                retryable=True,
            ) from e
        except Exception as e:
            raise SendError(
                f"Unexpected error during send: {e}",
                error_code="send_failed",
                retryable=True,
            ) from e

        # Configurable delay between sends to avoid abuse detection
        delay = settings.playwright_send_delay_seconds
        if delay > 0:
            logger.debug("Waiting %d seconds before next send.", delay)
            await asyncio.sleep(delay)

        return SendResult(message_id="", thread_id="")

    async def async_is_ready(self) -> bool:
        """Async check if we have a valid Gmail session (no browser launch).

        Uses instant query_selector (no waiting) for fast status checks.
        Wrapped in a timeout to prevent blocking if Playwright is stuck.
        """
        if self._page is None or self._page.is_closed():
            return False

        try:
            return await asyncio.wait_for(
                self._async_is_inbox_loaded(), timeout=3.0
            )
        except (asyncio.TimeoutError, Exception):
            return False

    def is_ready(self) -> bool:
        """Check if we have a valid Gmail session."""
        if self._page is None or self._page.is_closed():
            return False
        try:
            return _run_async(self._async_is_inbox_loaded())
        except Exception:
            return False

    def get_display_name(self) -> str:
        return "Playwright (Browser Automation)"

    # ------------------------------------------------------------------
    # Browser session management
    # ------------------------------------------------------------------

    async def async_launch_browser(self) -> None:
        """Start Chromium in headed mode with a persistent context."""
        global _main_loop

        # If we have a context, check if it's still alive
        if self._context is not None:
            if self._page is not None and not self._page.is_closed():
                return
            # Browser was closed externally — clean up stale references
            logger.info("Browser was closed externally, cleaning up.")
            await self.async_close_browser()

        session_dir = Path(settings.playwright_session_dir).resolve()
        session_dir.mkdir(parents=True, exist_ok=True)

        # Kill any orphaned Chromium processes using the session dir
        # (can happen after server restart with --reload)
        self._kill_orphaned_browsers(session_dir)

        # Store the event loop so scheduler threads can use it
        _main_loop = asyncio.get_running_loop()

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        self._page = (
            self._context.pages[0] if self._context.pages else await self._context.new_page()
        )
        logger.info("Playwright browser launched (session dir: %s).", session_dir)

    @staticmethod
    def _kill_orphaned_browsers(session_dir: Path) -> None:
        """Kill Chromium processes that reference the session directory."""
        import subprocess

        session_str = str(session_dir)
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"chromium.*{session_str}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            pids = [int(p) for p in result.stdout.strip().split() if p.isdigit()]
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                    logger.info("Killed orphaned Chromium process %d.", pid)
                except OSError:
                    pass
        except Exception:
            pass

    def launch_browser(self) -> None:
        """Sync wrapper for async_launch_browser."""
        _run_async(self.async_launch_browser())

    async def async_ensure_session(self) -> bool:
        """Check if the current page has an active Gmail session."""
        await self.async_launch_browser()
        page = self._page

        current_url = page.url
        if "mail.google.com" not in current_url:
            await page.goto(GMAIL_URL, wait_until="domcontentloaded", timeout=30000)

        # Wait a moment for redirects to settle
        await page.wait_for_timeout(2000)

        return await self._async_is_inbox_loaded()

    def ensure_session(self) -> bool:
        """Sync wrapper for async_ensure_session."""
        return _run_async(self.async_ensure_session())

    async def async_initiate_login(self) -> str:
        """Launch the browser and navigate to Gmail for manual login."""
        await self.async_launch_browser()
        await self._page.goto(GMAIL_URL, wait_until="domcontentloaded", timeout=30000)
        return "Browser launched. Please log in to Gmail in the opened browser window."

    def initiate_login(self) -> str:
        """Sync wrapper for async_initiate_login."""
        return _run_async(self.async_initiate_login())

    async def async_wait_for_login(self, timeout_ms: int = 120000) -> bool:
        """Wait for the user to complete login."""
        if self._page is None:
            return False
        try:
            for selector in INBOX_LOADED_SELECTORS:
                try:
                    await self._page.wait_for_selector(selector, timeout=timeout_ms)
                    await self._detect_session_email()
                    return True
                except PlaywrightTimeoutError:
                    continue
            return False
        except Exception:
            return False

    def wait_for_login(self, timeout_ms: int = 120000) -> bool:
        """Sync wrapper for async_wait_for_login."""
        return _run_async(self.async_wait_for_login(timeout_ms))

    async def async_close_browser(self) -> None:
        """Gracefully close browser and context."""
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
            self._page = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        self._browser = None
        self._session_email = None
        logger.info("Playwright browser closed.")

    def close_browser(self) -> None:
        """Sync wrapper for async_close_browser."""
        try:
            _run_async(self.async_close_browser())
        except Exception:
            # Best-effort cleanup
            self._context = None
            self._page = None
            self._playwright = None
            self._browser = None
            self._session_email = None

    def get_session_email(self) -> str | None:
        """Return the email address of the logged-in Gmail account, if known."""
        return self._session_email

    # ------------------------------------------------------------------
    # Internal: session checking
    # ------------------------------------------------------------------

    async def _async_ensure_session(self) -> None:
        """Verify we have an active Gmail session. Raises SendError if not."""
        if not await self.async_ensure_session():
            raise SendError(
                "Gmail session expired. Please re-login via Settings.",
                error_code="session_expired",
                retryable=False,
            )

    def _ensure_session(self) -> None:
        """Sync wrapper."""
        _run_async(self._async_ensure_session())

    async def _async_is_inbox_loaded(self) -> bool:
        """Check if the Gmail inbox is loaded by looking for the Compose button."""
        if self._page is None or self._page.is_closed():
            return False

        current_url = self._page.url
        if "accounts.google.com" in current_url:
            return False

        for selector in INBOX_LOADED_SELECTORS:
            try:
                element = await self._page.query_selector(selector)
                if element:
                    return True
            except Exception:
                continue
        return False

    async def _detect_session_email(self) -> None:
        """Try to detect the logged-in email from the Gmail UI."""
        if self._page is None:
            return
        try:
            element = await self._page.query_selector('a[aria-label*="Google Account"] >> nth=0')
            if element:
                label = await element.get_attribute("aria-label") or ""
                if "(" in label and ")" in label:
                    self._session_email = label.split("(")[-1].rstrip(")")
                    return
        except Exception:
            pass
        self._session_email = None

    # ------------------------------------------------------------------
    # Internal: send flow steps with selector resilience
    # ------------------------------------------------------------------

    async def _try_selectors(self, selectors: list[str], action: str, timeout: int = 3000) -> None:
        """Try clicking each selector in order. Raises SendError if all fail."""
        for selector in selectors:
            try:
                await self._page.click(selector, timeout=timeout)
                return
            except (PlaywrightTimeoutError, Exception):
                continue
        raise SendError(
            f"Could not find {action} — Gmail UI may have changed.",
            error_code="ui_element_not_found",
            retryable=True,
        )

    async def _find_element(self, selectors: list[str], description: str):
        """Find the first matching element from a list of selectors."""
        for selector in selectors:
            try:
                element = await self._page.wait_for_selector(selector, timeout=3000)
                if element:
                    return element
            except (PlaywrightTimeoutError, Exception):
                continue
        raise SendError(
            f"Could not find {description} — Gmail UI may have changed.",
            error_code="ui_element_not_found",
            retryable=True,
        )

    async def _click_compose(self) -> None:
        """Click the Compose button to open a new email."""
        await self._try_selectors(COMPOSE_BUTTON_SELECTORS, "Compose button", timeout=5000)
        try:
            await self._page.wait_for_selector('[name="subjectbox"]', timeout=5000)
        except PlaywrightTimeoutError as e:
            raise SendError(
                "Failed to open compose window.",
                error_code="compose_failed",
                retryable=True,
            ) from e

    async def _fill_to(self, email_address: str) -> None:
        """Fill the To field with the recipient email."""
        element = await self._find_element(TO_FIELD_SELECTORS, "To field")
        await element.click()
        await element.fill(email_address)
        await self._page.keyboard.press("Tab")
        await self._page.wait_for_timeout(500)

    async def _fill_subject(self, subject: str) -> None:
        """Fill the Subject field."""
        element = await self._find_element(SUBJECT_SELECTORS, "Subject field")
        await element.click()
        await element.fill(subject)

    async def _fill_body(self, body_html: str, body_text: str) -> None:
        """Fill the email body. Tries HTML injection first, falls back to plain text."""
        element = await self._find_element(BODY_SELECTORS, "Body field")

        if body_html:
            try:
                await self._page.evaluate(
                    """(el, html) => { el.innerHTML = html; }""",
                    [element, body_html],
                )
                inner_text = await self._page.evaluate("""(el) => el.innerText""", element)
                if inner_text and inner_text.strip():
                    return
                logger.warning("HTML injection produced empty body, falling back to plain text.")
            except Exception:
                logger.warning("HTML body injection failed, falling back to plain text.")

        await element.click()
        await element.type(body_text or body_html, delay=10)

    async def _click_send(self) -> None:
        """Click the Send button."""
        await self._try_selectors(SEND_BUTTON_SELECTORS, "Send button", timeout=5000)

    async def _wait_for_sent_confirmation(self) -> None:
        """Wait for the 'Message sent' confirmation in Gmail UI."""
        for selector in SENT_CONFIRMATION_SELECTORS:
            try:
                await self._page.wait_for_selector(selector, timeout=10000)
                return
            except (PlaywrightTimeoutError, Exception):
                continue
        try:
            compose_visible = await self._page.query_selector('[name="subjectbox"]')
            if compose_visible is None:
                logger.info("Compose window closed — assuming message was sent.")
                return
        except Exception:
            pass
        raise SendError(
            "Send confirmation not detected — message may not have been sent.",
            error_code="confirmation_timeout",
            retryable=True,
        )
