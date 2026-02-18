# Task 1.1 — Define the SendBackend Protocol

## File
`backend/src/campaign/sender.py`

## Description
Create the abstract sender interface that all email backends must implement. This is the foundational contract for the sender abstraction.

## Acceptance Criteria
- [ ] `SendBackend` protocol class with `send_email()`, `is_ready()`, `get_display_name()` methods
- [ ] `SendResult` dataclass with `message_id` and `thread_id` fields
- [ ] `SendError` exception class with `message`, `error_code`, and `retryable` attributes
- [ ] Module is importable without any Gmail API or Playwright dependencies
