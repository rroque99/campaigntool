# Phase 1 — Sender Abstraction Layer

## Goal

Extract the email sending logic from `gmail.py` into a protocol-based abstraction so that multiple sender backends (Gmail API, Playwright) can be used interchangeably.

## Tasks

### Task 1.1 — Define the SendBackend protocol

**File:** `backend/src/campaign/sender.py`

Create a `SendBackend` protocol class:

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass
class SendResult:
    message_id: str  # May be empty for non-API backends
    thread_id: str   # May be empty for non-API backends

class SendError(Exception):
    def __init__(self, message: str, error_code: str = "send_error", retryable: bool = False):
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        super().__init__(message)

class SendBackend(Protocol):
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
        """Human-readable name for the UI (e.g., 'Gmail API', 'Playwright')."""
        ...
```

Move `SendResult` from `gmail.py` to `sender.py`. `SendError` replaces `GmailError` as the common error type (but `GmailError` remains as a subclass for API-specific errors).

### Task 1.2 — Create GmailAPISender class

**File:** `backend/src/campaign/gmail_sender.py`

Extract the current `send_email()` function from `gmail.py` into a class:

```python
class GmailAPISender:
    """Sends emails via the Gmail API."""

    def send_email(self, to, subject, body_html, body_text, thread_id=None) -> SendResult: ...
    def is_ready(self) -> bool: ...  # Delegates to auth.is_authenticated()
    def get_display_name(self) -> str: return "Gmail API"
```

- The implementation is a direct lift of the current `gmail.py:send_email()`.
- `GmailError` becomes a subclass of `SendError` with `retryable=True` for rate limits.
- `gmail.py` retains `check_replies()`, `get_send_quota_remaining()`, and `build_gmail_service()` — only send logic moves.

### Task 1.3 — Create sender factory

**File:** `backend/src/campaign/sender_factory.py`

```python
def get_sender() -> SendBackend:
    """Return the configured sender backend instance."""
    if settings.send_backend == "playwright":
        from campaign.playwright_sender import PlaywrightSender
        return PlaywrightSender()
    else:
        from campaign.gmail_sender import GmailAPISender
        return GmailAPISender()
```

Uses lazy imports to avoid requiring Playwright when not in use.

### Task 1.4 — Refactor scheduler.py to use sender factory

Update `scheduler.py`:

- Replace `from campaign.gmail import send_email` with `from campaign.sender_factory import get_sender`
- In `send_email_job()`, call `get_sender().send_email(...)` instead of `gmail.send_email(...)`
- Update error handling: catch `SendError` (base class) instead of `GmailError`. Check `error.retryable` instead of `error.error_code == "rate_limited"`.

### Task 1.5 — Update gmail.py

- Remove `send_email()` and `SendResult` (now in `sender.py` and `gmail_sender.py`)
- Keep `GmailError` but make it a subclass of `SendError`
- Keep `check_replies()`, `get_send_quota_remaining()`, `build_gmail_service()`
- Keep `ReplyCheckResult` (reply checking is Gmail API-only)

### Task 1.6 — Update existing imports

Audit and update all files that import from `gmail.py`:
- `scheduler.py` — already handled in Task 1.4
- `routers/emails.py` — if it imports `SendResult`, update to `from campaign.sender import SendResult`
- `tests/test_gmail.py` — update imports, ensure tests still pass against `GmailAPISender`

### Task 1.7 — Verify existing tests pass

Run `uv run pytest -v` and ensure all existing tests pass with the refactored structure. No behavior change — just a restructuring.

## Deliverables

- `sender.py` with `SendBackend` protocol, `SendResult`, `SendError`
- `gmail_sender.py` with `GmailAPISender` class
- `sender_factory.py` with `get_sender()` factory
- Refactored `gmail.py` (send logic removed, reply logic retained)
- Refactored `scheduler.py` (uses sender factory)
- All existing tests passing
