# Task 1.3 — Create Sender Factory

## File
`backend/src/campaign/sender_factory.py`

## Description
Create a factory function that returns the appropriate sender backend based on configuration. Uses lazy imports to avoid requiring Playwright when not in use.

## Acceptance Criteria
- [ ] `get_sender()` returns `GmailAPISender` when `settings.send_backend == "gmail_api"`
- [ ] `get_sender()` returns `PlaywrightSender` when `settings.send_backend == "playwright"`
- [ ] `shutdown_sender()` cleans up sender resources
- [ ] Playwright import is lazy (only when needed)
- [ ] Unknown send_backend values raise a clear error
