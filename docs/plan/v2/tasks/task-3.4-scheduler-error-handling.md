# Task 3.4 — Update Scheduler Error Handling

## File
`backend/src/campaign/scheduler.py`

## Description
Update `send_email_job()` to use generic `SendError` handling instead of Gmail-specific error handling.

## Acceptance Criteria
- [ ] Catches `SendError` instead of `GmailError`
- [ ] Uses `error.retryable` for retry decisions
- [ ] `session_expired` errors set email to failed with descriptive message
- [ ] Quota checking still works for gmail_api mode
- [ ] Daily send limit is respected regardless of backend
