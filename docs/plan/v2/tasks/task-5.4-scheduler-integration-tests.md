# Task 5.4 — Integration Tests for Scheduler with Sender Abstraction

## File
`backend/tests/test_scheduler.py`

## Description
Update scheduler tests to verify sender factory integration and generic error handling.

## Acceptance Criteria
- [ ] Test `send_email_job()` uses sender factory
- [ ] Test retryable `SendError` triggers retry with backoff
- [ ] Test non-retryable `SendError` fails the email
- [ ] Test `session_expired` error produces descriptive error message
- [ ] Existing scheduler tests still pass
