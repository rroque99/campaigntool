# Task 3.3 — Update main.py Lifespan

## File
`backend/src/campaign/main.py`

## Description
Update the FastAPI lifespan to conditionally start reply monitoring and clean up Playwright on shutdown.

## Acceptance Criteria
- [ ] Reply monitor only starts when `send_backend == "gmail_api"`
- [ ] Log message when reply monitoring is skipped
- [ ] `shutdown_sender()` called on app shutdown
- [ ] Existing behavior unchanged for `gmail_api` mode
