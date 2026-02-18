"""Sender abstraction — protocol and shared types for email send backends.

All sender implementations (Gmail API, Playwright, etc.) must satisfy
the SendBackend protocol defined here.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class SendError(Exception):
    """Base exception for all sender backends."""

    def __init__(self, message: str, error_code: str = "send_error", retryable: bool = False):
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        super().__init__(message)


@dataclass
class SendResult:
    """Result of a successful email send.

    message_id and thread_id may be empty strings for backends that
    cannot retrieve them (e.g., Playwright).
    """

    message_id: str
    thread_id: str


@runtime_checkable
class SendBackend(Protocol):
    """Protocol that all email sender backends must implement."""

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str,
        thread_id: str | None = None,
    ) -> SendResult: ...

    def is_ready(self) -> bool:
        """Check if this sender backend is configured and ready to send."""
        ...

    def get_display_name(self) -> str:
        """Human-readable name for the UI."""
        ...
