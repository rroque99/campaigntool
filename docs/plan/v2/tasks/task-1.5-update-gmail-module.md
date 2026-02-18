# Task 1.5 — Update gmail.py

## File
`backend/src/campaign/gmail.py`

## Description
Remove send logic from `gmail.py` (moved to `gmail_sender.py`). Retain reply checking and quota functions. Make `GmailError` a subclass of `SendError`.

## Acceptance Criteria
- [ ] `send_email()` removed from `gmail.py`
- [ ] `SendResult` removed (now in `sender.py`)
- [ ] `GmailError` is a subclass of `SendError`
- [ ] `check_replies()`, `get_send_quota_remaining()`, `build_gmail_service()` retained
- [ ] `ReplyCheckResult` retained
