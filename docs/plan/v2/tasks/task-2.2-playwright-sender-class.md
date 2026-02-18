# Task 2.2 — Implement PlaywrightSender Class

## File
`backend/src/campaign/playwright_sender.py`

## Description
Core Playwright sender class that implements `SendBackend` protocol. Manages browser instance and provides the `send_email()` method.

## Acceptance Criteria
- [ ] `PlaywrightSender` class implements `SendBackend` protocol
- [ ] `send_email()` method signature matches the protocol
- [ ] `is_ready()` returns True when browser session is active and Gmail is logged in
- [ ] `is_ready()` returns False when no session exists
- [ ] `get_display_name()` returns "Playwright (Browser Automation)"
- [ ] Class manages browser, context, and page lifecycle
