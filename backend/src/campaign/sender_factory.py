"""Sender factory — returns the configured sender backend instance.

Uses lazy imports so Playwright is only imported when configured.
Manages a singleton sender instance for backends that need persistent
state (e.g., Playwright browser session).

The active backend can be switched at runtime via set_active_backend(),
which is exposed through the POST /auth/send-backend API endpoint.
"""

import asyncio
import logging
import threading

from campaign.config import settings
from campaign.sender import SendBackend

logger = logging.getLogger(__name__)

_sender_instance: SendBackend | None = None
_lock = threading.Lock()

# Mutable runtime override for the send backend.
# When None, falls back to settings.send_backend (env var / default).
_active_backend: str | None = None


def get_active_backend() -> str:
    """Return the currently active send backend name."""
    return _active_backend or settings.send_backend


async def set_active_backend(backend: str) -> None:
    """Switch the active send backend at runtime.

    Must be called from an async context (e.g. a FastAPI endpoint).
    Shuts down any existing sender, updates the active backend,
    and handles side-effects (Playwright event loop, reply monitor).
    """
    global _active_backend

    if backend not in ("gmail_api", "playwright"):
        raise ValueError(f"Unknown send_backend: '{backend}'. Must be 'gmail_api' or 'playwright'.")

    old_backend = get_active_backend()
    if backend == old_backend:
        return

    # Shut down existing sender — use async path to avoid deadlock
    # when Playwright browser needs closing from the running event loop
    await async_shutdown_sender()

    _active_backend = backend
    logger.info("Send backend switched from '%s' to '%s'.", old_backend, backend)

    if backend == "playwright":
        # Playwright needs the main asyncio event loop reference
        import campaign.playwright_sender as pw_mod

        try:
            pw_mod._main_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass  # No running loop — will be set when needed

        # Stop reply monitor (not supported in Playwright mode)
        _stop_reply_monitor_safe()

    elif backend == "gmail_api":
        # Start reply monitor if Gmail is authenticated
        _start_reply_monitor_safe()


def _start_reply_monitor_safe() -> None:
    """Start the reply monitor job, ignoring errors if not authenticated."""
    try:
        from campaign.auth import is_authenticated

        if is_authenticated():
            from campaign.scheduler import start_reply_monitor

            start_reply_monitor()
            logger.info("Reply monitor started after backend switch.")
    except Exception:
        logger.warning("Could not start reply monitor after backend switch.")


def _stop_reply_monitor_safe() -> None:
    """Remove the reply monitor job if it exists."""
    try:
        from campaign.scheduler import get_scheduler

        scheduler = get_scheduler()
        if scheduler.get_job("check_replies"):
            scheduler.remove_job("check_replies")
            logger.info("Reply monitor stopped after backend switch.")
    except Exception:
        logger.warning("Could not stop reply monitor after backend switch.")


def get_sender() -> SendBackend:
    """Return the configured sender backend instance (singleton)."""
    global _sender_instance
    if _sender_instance is not None:
        return _sender_instance

    with _lock:
        # Double-checked locking
        if _sender_instance is not None:
            return _sender_instance

        _sender_instance = _create_sender()
        return _sender_instance


def _create_sender() -> SendBackend:
    """Create a new sender backend based on the active backend."""
    backend = get_active_backend()

    if backend == "gmail_api":
        from campaign.gmail_sender import GmailAPISender

        logger.info("Using Gmail API sender backend.")
        return GmailAPISender()
    elif backend == "playwright":
        from campaign.playwright_sender import PlaywrightSender

        logger.info("Using Playwright sender backend.")
        return PlaywrightSender()
    else:
        raise ValueError(f"Unknown send_backend: '{backend}'. Must be 'gmail_api' or 'playwright'.")


async def async_shutdown_sender() -> None:
    """Async cleanup — directly awaits async_close_browser to avoid deadlock."""
    global _sender_instance
    with _lock:
        if _sender_instance is not None and hasattr(_sender_instance, "async_close_browser"):
            await _sender_instance.async_close_browser()
        _sender_instance = None
        logger.info("Sender shut down.")


def shutdown_sender() -> None:
    """Clean up sender resources (e.g., close Playwright browser).

    Used during app shutdown (lifespan). For async contexts (e.g. switching
    backends from an endpoint), use async_shutdown_sender() instead.
    """
    global _sender_instance
    with _lock:
        if _sender_instance is not None and hasattr(_sender_instance, "close_browser"):
            _sender_instance.close_browser()
        _sender_instance = None
        logger.info("Sender shut down.")
