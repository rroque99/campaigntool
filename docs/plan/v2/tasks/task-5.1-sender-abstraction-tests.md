# Task 5.1 — Unit Tests for Sender Abstraction

## File
`backend/tests/test_sender.py`

## Description
Test the sender protocol, error hierarchy, and factory.

## Acceptance Criteria
- [ ] Test `GmailAPISender` satisfies `SendBackend` protocol
- [ ] Test `PlaywrightSender` satisfies `SendBackend` protocol
- [ ] Test `GmailError` is a subclass of `SendError`
- [ ] Test `sender_factory.get_sender()` returns correct type based on settings
- [ ] Test `shutdown_sender()` cleans up properly
