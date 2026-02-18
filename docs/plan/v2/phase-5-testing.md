# Phase 5 — Testing & Documentation

## Goal

Comprehensive test coverage for the new sender abstraction and Playwright sender, plus documentation for setup and usage.

## Tasks

### Task 5.1 — Unit tests for sender abstraction

**File:** `backend/tests/test_sender.py`

- Test that `GmailAPISender` implements the `SendBackend` protocol
- Test that `PlaywrightSender` implements the `SendBackend` protocol
- Test `SendError` and `GmailError` hierarchy (GmailError is a SendError)
- Test `sender_factory.get_sender()` returns correct type based on settings

### Task 5.2 — Unit tests for GmailAPISender

**File:** `backend/tests/test_gmail_sender.py`

Migrate and adapt existing `test_gmail.py` tests:
- Test successful send returns `SendResult`
- Test rate limit raises `SendError(retryable=True)`
- Test other errors raise `SendError(retryable=False)`
- Test `is_ready()` delegates to `is_authenticated()`
- Mock Gmail API service as before

### Task 5.3 — Unit tests for PlaywrightSender

**File:** `backend/tests/test_playwright_sender.py`

Mock Playwright objects (page, browser, context):

- Test `send_email()` calls the correct sequence of Playwright actions (click compose, fill fields, click send)
- Test session expired detection raises `SendError(retryable=False)`
- Test send timeout raises `SendError(retryable=True)`
- Test `is_ready()` returns False when no browser session
- Test `is_ready()` returns True when session is active
- Test `ensure_session()` detects login page vs inbox
- Test multi-selector fallback (first selector fails, second succeeds)
- Test inter-send delay is applied

### Task 5.4 — Integration tests for scheduler with sender abstraction

**File:** `backend/tests/test_scheduler.py` (update existing)

- Test `send_email_job()` uses sender factory
- Test `send_email_job()` handles `SendError(retryable=True)` with retry
- Test `send_email_job()` handles `SendError(retryable=False)` by failing the email
- Test session_expired error pauses the campaign

### Task 5.5 — Test config and conditional behavior

**File:** `backend/tests/test_config.py` (new)

- Test default settings (`send_backend="gmail_api"`)
- Test Playwright settings are loaded when configured
- Test sender factory returns `GmailAPISender` by default
- Test sender factory returns `PlaywrightSender` when configured

### Task 5.6 — Update existing test_gmail.py

Adapt existing tests in `test_gmail.py` to only cover the retained functions:
- `check_replies()` tests remain
- `get_send_quota_remaining()` tests remain
- `send_email()` tests move to `test_gmail_sender.py`

### Task 5.7 — Manual test plan

**File:** `docs/plan/v2/manual-test-plan.md`

Document manual testing steps for Playwright mode:

1. Set `SEND_BACKEND=playwright` in `.env`
2. Start the backend
3. Open Settings page — verify Playwright section appears
4. Click "Open Gmail Login" — verify browser opens
5. Log in to Gmail in the browser
6. Verify session status shows active
7. Create a test campaign with 2-3 recipients
8. Schedule the campaign
9. Verify emails are sent (check recipient inboxes)
10. Restart the backend — verify session persists
11. Verify reply monitoring is disabled
12. Test session expiry: clear browser cookies, trigger send, verify error handling

### Task 5.8 — Update CLAUDE.md

Update the project's CLAUDE.md to document:
- New `send_backend` setting and valid values
- New Playwright-specific settings
- New files added (`sender.py`, `gmail_sender.py`, `playwright_sender.py`, `sender_factory.py`)
- Updated project layout
- Playwright setup instructions (`playwright install chromium`)
- Known limitations of Playwright mode

## Deliverables

- Unit tests for sender protocol, GmailAPISender, PlaywrightSender
- Updated scheduler tests
- Config tests
- Updated existing gmail.py tests
- Manual test plan document
- Updated CLAUDE.md
