# Task 2.6 — Implement Playwright Auth Endpoints

## File
`backend/src/campaign/routers/auth.py`

## Description
Add API endpoints for checking Playwright session status and triggering the login flow.

## Acceptance Criteria
- [ ] `GET /api/v1/auth/playwright/status` returns session status (active, email, last_verified)
- [ ] `POST /api/v1/auth/playwright/login` launches browser and navigates to Gmail
- [ ] Login endpoint returns immediately with a message (browser opens in background)
- [ ] Endpoints return 404 or appropriate error when `send_backend != "playwright"`
