# Task 3.5 — Update Auth Router for Sender-Aware Status

## File
`backend/src/campaign/routers/auth.py`

## Description
Update the auth status endpoint to include sender backend information and Playwright session status.

## Acceptance Criteria
- [ ] `GET /api/v1/auth/status` includes `send_backend` field
- [ ] `GET /api/v1/auth/status` includes `reply_monitoring_enabled` field
- [ ] For Playwright mode: includes `playwright_session_active` and `playwright_session_email`
- [ ] Backward compatible — existing fields still present
