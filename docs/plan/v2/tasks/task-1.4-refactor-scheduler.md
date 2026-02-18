# Task 1.4 — Refactor Scheduler to Use Sender Factory

## File
`backend/src/campaign/scheduler.py`

## Description
Update the scheduler's `send_email_job()` to use the sender factory instead of directly importing `gmail.send_email()`.

## Acceptance Criteria
- [ ] `send_email_job()` calls `get_sender().send_email()` instead of `gmail.send_email()`
- [ ] Error handling catches `SendError` (base class) instead of `GmailError`
- [ ] Retry logic uses `error.retryable` flag instead of `error.error_code == "rate_limited"`
- [ ] Non-retryable `session_expired` errors set email to failed and include descriptive error message
- [ ] All existing scheduler tests still pass
