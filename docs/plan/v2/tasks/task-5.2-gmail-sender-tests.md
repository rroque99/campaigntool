# Task 5.2 — Unit Tests for GmailAPISender

## File
`backend/tests/test_gmail_sender.py`

## Description
Migrate existing send tests from `test_gmail.py` to test the `GmailAPISender` class.

## Acceptance Criteria
- [ ] Test successful send returns `SendResult`
- [ ] Test rate limit raises `SendError(retryable=True)`
- [ ] Test other errors raise `SendError(retryable=False)`
- [ ] Test `is_ready()` delegates to `is_authenticated()`
- [ ] All Gmail API calls mocked
