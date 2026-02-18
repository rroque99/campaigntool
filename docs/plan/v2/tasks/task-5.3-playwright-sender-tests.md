# Task 5.3 — Unit Tests for PlaywrightSender

## File
`backend/tests/test_playwright_sender.py`

## Description
Test the Playwright sender with mocked Playwright objects.

## Acceptance Criteria
- [ ] Test `send_email()` calls correct sequence of Playwright actions
- [ ] Test session expired detection raises `SendError(retryable=False)`
- [ ] Test send timeout raises `SendError(retryable=True)`
- [ ] Test `is_ready()` returns correct status
- [ ] Test multi-selector fallback (first selector fails, second succeeds)
- [ ] Test inter-send delay is applied
- [ ] All Playwright objects (page, browser, context) are mocked
