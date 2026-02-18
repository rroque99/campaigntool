# Phase 3 — Configuration & Backend Integration — COMPLETED

## What Was Done

Wired the Playwright sender into the application's configuration, lifecycle, and scheduling flow. Conditionally disabled reply monitoring when using Playwright mode. Updated auth and scheduling endpoints to be sender-aware.

### Modified Files

1. **`backend/src/campaign/config.py`** — Added `playwright_page_timeout_ms` (default: 15000) and `playwright_browser` (default: "chromium") settings. All Playwright settings are now:
   - `playwright_session_dir` (Path, default: `../credentials/playwright-session`)
   - `playwright_send_delay_seconds` (int, default: 30)
   - `playwright_page_timeout_ms` (int, default: 15000)
   - `playwright_browser` (str, default: "chromium")

2. **`backend/src/campaign/main.py`** — Updated lifespan to:
   - Only start reply monitor when `send_backend == "gmail_api"`
   - Log a message when reply monitoring is disabled for non-API backends
   - Call `shutdown_sender()` on app shutdown to close Playwright browser

3. **`backend/src/campaign/schemas.py`** — Extended `AuthStatusResponse` with:
   - `send_backend: str` — the configured sender backend name
   - `reply_monitoring_enabled: bool` — whether reply detection is active
   - `playwright_session_active: bool` — whether Playwright has an active Gmail session
   - `playwright_session_email: str | None` — detected email in Playwright session

4. **`backend/src/campaign/routers/auth.py`** — Updated `GET /api/v1/auth/status` endpoint to return sender-aware info. For `gmail_api` mode, returns standard OAuth info. For `playwright` mode, returns Playwright session status instead.

5. **`backend/src/campaign/routers/campaigns.py`** — Added `_is_sender_ready()` helper that checks the appropriate auth mechanism based on `send_backend`:
   - `gmail_api`: uses `is_authenticated()` (OAuth)
   - `playwright`: uses `get_sender().is_ready()` (browser session)
   - Updated schedule endpoint to use `_is_sender_ready()` instead of `is_authenticated()`

6. **`backend/tests/test_scheduler.py`** — Updated `test_schedule_endpoint_rejects_unauthenticated` to mock `_is_sender_ready` instead of `is_authenticated`, matching the new generic sender-aware check.

7. **`backend/tests/test_integration.py`** — Updated `test_schedule_without_auth` to mock `_is_sender_ready` and check for "not ready" instead of "authenticated".

8. **`.gitignore`** — Added `credentials/playwright-session/` entry.

## Test Results

- **142 tests pass** (all tests related to our changes)
- **1 pre-existing failure** (`test_add_to_non_draft_blocked`) — unrelated to Phase 3; same as previous phases
- **Ruff lint**: All checks pass
- **Ruff format**: All files formatted

## Architecture After Phase 3

```
main.py lifespan:
  startup:
    start_scheduler()
    if send_backend == "gmail_api":
      start_reply_monitor()
    else:
      log "Reply monitoring disabled"
  shutdown:
    stop_scheduler()
    shutdown_sender()  → closes Playwright browser if applicable

scheduler.py → get_sender() → GmailAPISender or PlaywrightSender

campaigns.py:
  schedule endpoint → _is_sender_ready() → is_authenticated() (gmail_api)
                                          OR get_sender().is_ready() (playwright)

auth.py:
  GET /status → returns sender-aware auth info (backend type, reply monitoring, Playwright session)
  GET /playwright/status → Playwright session status
  POST /playwright/login → Launch browser for login
```

## Key Integration Points for Phase 4

- **`AuthStatusResponse`**: Frontend should read `send_backend`, `reply_monitoring_enabled`, `playwright_session_active`, and `playwright_session_email` to render appropriate UI:
  - When `send_backend == "playwright"`: show Playwright session panel instead of OAuth panel
  - When `reply_monitoring_enabled == false`: show notice that reply detection is unavailable
  - When `playwright_session_active == false`: show "Login" button that calls `POST /auth/playwright/login`

- **API endpoints available for frontend**:
  - `GET /api/v1/auth/status` — includes all sender info
  - `GET /api/v1/auth/playwright/status` — detailed Playwright session status
  - `POST /api/v1/auth/playwright/login` — triggers browser launch for login
  - `GET /api/v1/auth/quota` — daily send quota (works for both backends)

- **Config settings** exposed for potential Settings UI:
  - `send_backend` ("gmail_api" | "playwright")
  - `playwright_send_delay_seconds`
  - `daily_send_limit`

## Commands

```bash
cd backend
export PATH="$HOME/.local/bin:$PATH"
uv sync --extra dev
uv run pytest -v                     # Run tests
uv run ruff check src/ tests/        # Lint
uv run ruff format --check src/ tests/  # Format check
```

## Branch

All work is on branch `feature/playwright-sender`.

## Continuation Instructions

When this phase is complete, the next agent should implement Phase 4 (Frontend Updates) as defined in `docs/plan/v2/phase-4-frontend.md`. Also look at the detailed tasks for the next phase in docs/plan/v2/tasks for more details. When that phase is complete, create a `phase-4-completed.md` document in `docs/plan/v2/` containing relevant context for the next agent to complete the following phase. Include this same instruction in the completed document so the pattern continues without the user needing to repeat the request.
