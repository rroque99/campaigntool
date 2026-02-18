# Task 3.6 — Update Pydantic Schemas

## File
`backend/src/campaign/schemas.py`

## Description
Add new and update existing Pydantic schemas for sender configuration and Playwright status.

## Acceptance Criteria
- [ ] `AuthStatusResponse` updated with `send_backend`, `reply_monitoring_enabled`, `playwright_session_active`, `playwright_session_email`
- [ ] New `PlaywrightStatusResponse` schema
- [ ] New `PlaywrightLoginResponse` schema
- [ ] All new schemas have proper type annotations and defaults
