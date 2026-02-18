# Task 2.3 — Implement Browser Session Management

## File
`backend/src/campaign/playwright_sender.py`

## Description
Handle browser lifecycle: launching, persistent session storage, login detection, and cleanup.

## Acceptance Criteria
- [ ] `launch_browser()` starts Chromium in headed mode with persistent context at `credentials/playwright-session/`
- [ ] Session cookies persist across app restarts (no re-login needed)
- [ ] `ensure_session()` detects whether user is logged into Gmail (inbox loaded vs login page)
- [ ] `ensure_session()` raises `SendError(error_code="session_expired")` when not logged in
- [ ] `initiate_login()` opens browser and navigates to Gmail for manual user login
- [ ] `close_browser()` gracefully shuts down browser and context
- [ ] CAPTCHA / "unusual activity" pages are detected and reported
