# Phase 1 — Sender Abstraction Layer — COMPLETED

## What Was Done

Extracted the email sending logic from `gmail.py` into a protocol-based abstraction so that multiple sender backends can be used interchangeably.

### New Files Created

1. **`backend/src/campaign/sender.py`** — Defines the `SendBackend` protocol, `SendResult` dataclass, and `SendError` base exception. All sender backends must implement this protocol.
2. **`backend/src/campaign/gmail_sender.py`** — `GmailAPISender` class implementing `SendBackend`. Contains the MIME message construction and Gmail API send logic previously in `gmail.py`.
3. **`backend/src/campaign/sender_factory.py`** — Thread-safe singleton factory. `get_sender()` returns the configured sender backend based on `settings.send_backend`. `shutdown_sender()` cleans up resources. Uses lazy imports so Playwright is only loaded when configured.

### Modified Files

4. **`backend/src/campaign/gmail.py`** — Removed `send_email()` function and `SendResult` dataclass. `GmailError` is now a subclass of `SendError` with a `retryable` parameter. Retained: `build_gmail_service()`, `check_replies()`, `get_send_quota_remaining()`, `ReplyCheckResult`.
5. **`backend/src/campaign/scheduler.py`** — `send_email_job()` now calls `get_sender().send_email()` instead of `gmail.send_email()`. Error handling catches `SendError` base class and uses `error.retryable` flag for retry decisions instead of checking `error.error_code == "rate_limited"`.
6. **`backend/src/campaign/config.py`** — Added `send_backend: str = "gmail_api"` setting. Defaults to `gmail_api` so existing behavior is unchanged.
7. **`backend/tests/test_gmail.py`** — Removed `TestSendEmail` class (send tests will be re-created in Phase 5 as `test_gmail_sender.py`). Added `TestGmailErrorHierarchy` to verify `GmailError` is a `SendError` subclass with `retryable` support.
8. **`backend/tests/test_scheduler.py`** — Updated all `send_email_job` tests to mock `campaign.scheduler.get_sender` instead of `campaign.scheduler.send_email`. Tests now use `SendError` with `retryable=True/False` instead of `GmailError` with specific `error_code`.

### Plan Files Created

9. **`docs/plan/v2/`** — Full plan with overview, 5 phase documents, and 37 task files in `docs/plan/v2/tasks/`.

## Test Results

- **142 tests pass** (all tests related to our changes)
- **1 pre-existing failure** (`test_add_to_non_draft_blocked`) — unrelated to Phase 1; this test expects 400 for adding recipients to active campaigns, but the endpoint correctly allows it per CLAUDE.md ("Recipients can be added to a campaign at any time")
- **Ruff lint**: All checks pass
- **Ruff format**: All files formatted

## Architecture After Phase 1

```
scheduler.py → get_sender() → GmailAPISender.send_email() → Gmail API
                             (future: PlaywrightSender.send_email() → Browser automation)

gmail.py     → check_replies(), get_send_quota_remaining()  (Gmail API-only operations)
```

## Key Integration Points for Phase 2

- **`SendBackend` protocol** (`sender.py`): The `PlaywrightSender` must implement `send_email()`, `is_ready()`, and `get_display_name()`.
- **`SendResult`** (`sender.py`): Playwright sender should return `SendResult(message_id="", thread_id="")` since these aren't available from the web UI.
- **`SendError`** (`sender.py`): Playwright sender should raise `SendError(retryable=True)` for transient failures (timeouts) and `SendError(retryable=False, error_code="session_expired")` for session issues.
- **`sender_factory.py`**: Already has the `elif backend == "playwright"` branch with lazy import of `PlaywrightSender`. Just needs `playwright_sender.py` to exist.
- **`config.py`**: Phase 3 will add Playwright-specific settings (`playwright_session_dir`, `playwright_send_delay_seconds`, etc.).

## Commands

```bash
cd backend
export PATH="$HOME/.local/bin:$PATH"
uv sync --extra dev
uv run pytest -v                          # Run tests
uv run ruff check src/ tests/             # Lint
uv run ruff format --check src/ tests/    # Format check
```

## Branch

All work is on branch `feature/playwright-sender`.

## Continuation Instructions

When this phase is complete, the next agent should implement Phase 2 (Playwright Sender Implementation) as defined in `docs/plan/v2/phase-2-playwright-sender.md`. Also look at the detailed tasks for the next phase in docs/plan/v2/tasks for more details.  When that phase is complete, create a `phase-2-completed.md` document in `docs/plan/v2/` containing relevant context for the next agent to complete the following phase. Include this same instruction in the completed document so the pattern continues without the user needing to repeat the request.
