# Task 2.7 — Handle HTML Email Body Injection

## File
`backend/src/campaign/playwright_sender.py`

## Description
Gmail's compose body is a contenteditable div. HTML email content must be injected via JavaScript, with a plain text fallback.

## Acceptance Criteria
- [ ] Primary: uses `page.evaluate()` to set `innerHTML` on the compose body div
- [ ] Fallback: if HTML injection fails, types plain text body via `page.type()`
- [ ] After injection, validates that body div is non-empty
- [ ] Documents known limitation: complex HTML may render differently than API-sent emails
