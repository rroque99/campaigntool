# Task 1.6 — Update Existing Imports

## Files
Multiple files across the codebase

## Description
Audit and update all files that import `send_email`, `SendResult`, or `GmailError` from `gmail.py` to use the new locations.

## Acceptance Criteria
- [ ] All imports of `SendResult` point to `campaign.sender`
- [ ] All imports of `send_email` in production code use `sender_factory.get_sender()`
- [ ] `GmailError` imports still work (it stays in `gmail.py` as a subclass of `SendError`)
- [ ] No circular imports
- [ ] `ruff check` passes with no import errors
