# Task 3.1 — Add New Settings to config.py

## File
`backend/src/campaign/config.py`

## Description
Add `send_backend` and Playwright-specific settings to the application configuration.

## Acceptance Criteria
- [ ] `send_backend: str = "gmail_api"` added (valid values: `gmail_api`, `playwright`)
- [ ] `playwright_session_dir: Path` added (default: `../credentials/playwright-session`)
- [ ] `playwright_send_delay_seconds: int = 30` added
- [ ] `playwright_page_timeout_ms: int = 15000` added
- [ ] `playwright_browser: str = "chromium"` added
- [ ] All new settings overridable via environment variables
- [ ] Existing settings unchanged
