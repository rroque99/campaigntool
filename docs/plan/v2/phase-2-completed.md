# Phase 2 — Playwright Sender Implementation — COMPLETED

## What Was Done

Implemented the Playwright-based email sender that automates the Gmail web UI to compose and send emails, as an alternative to the Gmail API sender.

### New Files Created

1. **`backend/src/campaign/playwright_sender.py`** — Full `PlaywrightSender` class implementing the `SendBackend` protocol. Includes:
   - Browser session management with persistent context (`credentials/playwright-session/`)
   - Multi-strategy selector resilience for all Gmail UI elements (compose button, to field, subject, body, send button, confirmation)
   - HTML body injection via `page.evaluate()` with plain text fallback
   - Configurable inter-send delay (`playwright_send_delay_seconds`)
   - Session checking, login initiation, and email detection
   - Proper error handling with retryable/non-retryable `SendError` exceptions

### Modified Files

2. **`backend/pyproject.toml`** — Added `playwright>=1.40` to dependencies. Users must run `playwright install chromium` after install.
3. **`backend/src/campaign/config.py`** — Added `playwright_session_dir` (default: `../credentials/playwright-session/`) and `playwright_send_delay_seconds` (default: 30) settings.
4. **`backend/src/campaign/schemas.py`** — Added `PlaywrightStatusResponse` schema with `session_active`, `email`, and `last_verified` fields.
5. **`backend/src/campaign/routers/auth.py`** — Added two new endpoints:
   - `GET /api/v1/auth/playwright/status` — Returns session status, email, and last verified time
   - `POST /api/v1/auth/playwright/login` — Launches browser and navigates to Gmail for manual login

### Plan Files Created

6. **`docs/plan/v2/phase-2-completed.md`** — This document.

## Test Results

- **142 tests pass** (all tests related to our changes)
- **1 pre-existing failure** (`test_add_to_non_draft_blocked`) — unrelated to Phase 2; same as Phase 1
- **Ruff lint**: All checks pass
- **Ruff format**: All files formatted

## Architecture After Phase 2

```
scheduler.py → get_sender() → GmailAPISender.send_email() → Gmail API
                             OR
                             → PlaywrightSender.send_email() → Browser automation

gmail.py     → check_replies(), get_send_quota_remaining()  (Gmail API-only operations)

PlaywrightSender:
  launch_browser() → persistent Chromium context in credentials/playwright-session/
  ensure_session() → checks if Gmail inbox is loaded
  initiate_login() → opens Gmail for manual user login
  send_email()     → compose → fill to/subject/body → send → wait for confirmation
  close_browser()  → cleanup on shutdown
```

## Key Integration Points for Phase 3

- **`config.py`**: Already has `send_backend`, `playwright_session_dir`, and `playwright_send_delay_seconds` settings. Phase 3 should wire `send_backend` into the Settings page and conditionally disable reply monitoring.
- **`sender_factory.py`**: Already imports `PlaywrightSender` when `send_backend="playwright"`. The `shutdown_sender()` function calls `close_browser()` if available.
- **`main.py` lifespan**: Phase 3 should add conditional reply monitor start (skip when `send_backend="playwright"`) and call `shutdown_sender()` on app shutdown.
- **`routers/auth.py`**: Playwright endpoints are functional. The frontend Settings page should call these endpoints when `send_backend="playwright"`.
- **Selectors**: Gmail's DOM changes frequently. The multi-selector approach in `playwright_sender.py` (e.g., `COMPOSE_BUTTON_SELECTORS`, `SEND_BUTTON_SELECTORS`) is designed to be resilient but may need updating as Gmail evolves.

## PlaywrightSender Methods

| Method | Description |
|--------|-------------|
| `send_email(to, subject, body_html, body_text, thread_id)` | Full send flow: ensure session → compose → fill fields → send → wait confirmation |
| `is_ready()` | Returns True if browser has active Gmail session |
| `get_display_name()` | Returns "Playwright (Browser Automation)" |
| `launch_browser()` | Starts headed Chromium with persistent context |
| `ensure_session()` | Checks if logged in, navigates to Gmail if needed |
| `initiate_login()` | Opens Gmail for manual login, returns status message |
| `wait_for_login(timeout_ms)` | Waits for user to complete login |
| `close_browser()` | Graceful browser/context cleanup |
| `get_session_email()` | Returns detected email or None |

## Commands

```bash
cd backend
export PATH="$HOME/.local/bin:$PATH"
uv sync --extra dev
playwright install chromium          # Required for Playwright browser binary
uv run pytest -v                     # Run tests
uv run ruff check src/ tests/        # Lint
uv run ruff format --check src/ tests/  # Format check
```

## Branch

All work is on branch `feature/playwright-sender`.

## Continuation Instructions

When this phase is complete, the next agent should implement Phase 3 (Configuration & Backend Integration) as defined in `docs/plan/v2/phase-3-config-integration.md`. Also look at the detailed tasks for the next phase in docs/plan/v2/tasks for more details. When that phase is complete, create a `phase-3-completed.md` document in `docs/plan/v2/` containing relevant context for the next agent to complete the following phase. Include this same instruction in the completed document so the pattern continues without the user needing to repeat the request.
