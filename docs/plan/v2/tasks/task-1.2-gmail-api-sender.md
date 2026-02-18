# Task 1.2 — Create GmailAPISender Class

## File
`backend/src/campaign/gmail_sender.py`

## Description
Extract the existing `send_email()` function from `gmail.py` into a `GmailAPISender` class that implements the `SendBackend` protocol.

## Acceptance Criteria
- [ ] `GmailAPISender` class with `send_email()`, `is_ready()`, `get_display_name()` methods
- [ ] `send_email()` is functionally identical to the current `gmail.py:send_email()`
- [ ] `is_ready()` delegates to `auth.is_authenticated()`
- [ ] `GmailError` is now a subclass of `SendError` with appropriate `retryable` flag
- [ ] Rate limit errors have `retryable=True`, other errors have `retryable=False`
