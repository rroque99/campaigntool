# Phase 3 — Configuration & Backend Integration

## Goal

Wire the Playwright sender into the application's configuration, scheduler, and lifecycle management. Conditionally disable reply monitoring when using Playwright mode.

## Tasks

### Task 3.1 — Add new settings to config.py

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Sender backend: "gmail_api" or "playwright"
    send_backend: str = "gmail_api"

    # Playwright-specific settings
    playwright_session_dir: Path = Path("../credentials/playwright-session")
    playwright_send_delay_seconds: int = 30
    playwright_page_timeout_ms: int = 15000
    playwright_browser: str = "chromium"  # chromium, firefox, webkit
```

All Playwright settings are optional and only used when `send_backend = "playwright"`.

### Task 3.2 — Update sender_factory.py with singleton management

The Playwright sender needs a persistent browser instance. The factory should manage sender lifecycle:

```python
_sender_instance: SendBackend | None = None

def get_sender() -> SendBackend:
    global _sender_instance
    if _sender_instance is None:
        _sender_instance = _create_sender()
    return _sender_instance

def shutdown_sender() -> None:
    """Cleanup sender resources (e.g., close Playwright browser)."""
    global _sender_instance
    if _sender_instance is not None and hasattr(_sender_instance, 'close_browser'):
        _sender_instance.close_browser()
    _sender_instance = None
```

### Task 3.3 — Update main.py lifespan

Modify the FastAPI lifespan to:

1. **On startup:**
   - Start the scheduler (unchanged)
   - Only start the reply monitor if `settings.send_backend == "gmail_api"`
   - If `send_backend == "playwright"`, log a message that reply monitoring is disabled

2. **On shutdown:**
   - Stop the scheduler (unchanged)
   - Call `shutdown_sender()` to close any Playwright browser

```python
@asynccontextmanager
async def lifespan(app):
    start_scheduler()
    if settings.send_backend == "gmail_api":
        start_reply_monitor()
    else:
        logger.info("Reply monitoring disabled (send_backend=%s)", settings.send_backend)
    yield
    stop_scheduler()
    shutdown_sender()
```

### Task 3.4 — Update scheduler.py error handling

Refactor `send_email_job()`:

- Replace `GmailError` catch with `SendError`
- Use `error.retryable` flag instead of checking `error.error_code == "rate_limited"`
- On non-retryable `session_expired` errors: set the email to `failed` and pause the campaign with a descriptive status message ("Playwright session expired — re-login required")
- Keep quota checking only for `gmail_api` backend (Playwright has no API quota, but still respect the daily send limit as a safety measure)

### Task 3.5 — Update auth router for sender-aware status

Modify `GET /api/v1/auth/status` response to include sender information:

```json
{
  "authenticated": true,
  "email": "user@gmail.com",
  "send_backend": "gmail_api",
  "reply_monitoring_enabled": true
}
```

For Playwright mode:
```json
{
  "authenticated": false,
  "email": null,
  "send_backend": "playwright",
  "reply_monitoring_enabled": false,
  "playwright_session_active": true,
  "playwright_session_email": "user@gmail.com"
}
```

### Task 3.6 — Update schemas.py

Add/update Pydantic schemas:

```python
class AuthStatusResponse(BaseModel):
    authenticated: bool
    email: str | None = None
    send_backend: str
    reply_monitoring_enabled: bool
    playwright_session_active: bool = False
    playwright_session_email: str | None = None

class PlaywrightStatusResponse(BaseModel):
    session_active: bool
    email: str | None = None
    last_verified: datetime | None = None

class PlaywrightLoginResponse(BaseModel):
    message: str
```

### Task 3.7 — Add .gitignore entry for Playwright session

Add `credentials/playwright-session/` to `.gitignore` — this directory contains browser cookies and session data.

### Task 3.8 — Conditional reply monitoring in scheduler

Update `schedule_campaign()` and the campaign scheduling flow:

- When `send_backend == "playwright"`, skip thread_id assignment on send (it's always empty)
- When displaying campaign status, indicate that reply-based cancellation is unavailable
- Ensure `cancel_campaign()` and `pause_campaign()` still work (they operate on email status, not thread IDs)

## Deliverables

- Updated `config.py` with Playwright settings
- Updated `sender_factory.py` with singleton lifecycle management
- Updated `main.py` lifespan with conditional startup/shutdown
- Updated `scheduler.py` with generic error handling
- Updated `auth` router with sender-aware status
- Updated schemas
- `.gitignore` updated
