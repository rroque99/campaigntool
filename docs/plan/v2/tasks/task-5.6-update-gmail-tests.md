# Task 5.6 — Update Existing test_gmail.py

## File
`backend/tests/test_gmail.py`

## Description
Remove send-related tests (moved to `test_gmail_sender.py`). Keep reply checking and quota tests.

## Acceptance Criteria
- [ ] `check_replies()` tests retained and passing
- [ ] `get_send_quota_remaining()` tests retained and passing
- [ ] `send_email()` tests removed (now in `test_gmail_sender.py`)
- [ ] No broken imports
