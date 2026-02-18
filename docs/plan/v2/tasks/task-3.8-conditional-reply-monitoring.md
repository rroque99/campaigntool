# Task 3.8 — Conditional Reply Monitoring in Scheduler

## File
`backend/src/campaign/scheduler.py`

## Description
Update campaign scheduling flow to handle missing thread IDs when using Playwright mode.

## Acceptance Criteria
- [ ] Empty `thread_id` from `SendResult` is stored as empty string (not None) in emails table
- [ ] Campaign status display indicates reply detection unavailable when using Playwright
- [ ] `cancel_campaign()` and `pause_campaign()` still work (they operate on email status)
- [ ] No errors when `thread_id` is empty in downstream logic
