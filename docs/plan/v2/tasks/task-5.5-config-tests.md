# Task 5.5 — Test Config and Conditional Behavior

## File
`backend/tests/test_config.py`

## Description
Test that configuration correctly controls sender selection and behavior.

## Acceptance Criteria
- [ ] Test default `send_backend` is `"gmail_api"`
- [ ] Test Playwright settings loaded when configured via env vars
- [ ] Test factory returns correct sender type for each backend value
