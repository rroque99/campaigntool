# Task 2.4 — Implement the Send Flow

## File
`backend/src/campaign/playwright_sender.py`

## Description
Implement the step-by-step browser automation to compose and send an email through Gmail's web UI.

## Acceptance Criteria
- [ ] Clicks Compose button to open compose window
- [ ] Fills "To" field with recipient email and confirms with Tab
- [ ] Fills "Subject" field
- [ ] Sets email body (HTML via innerHTML injection, plain text fallback)
- [ ] Clicks Send button
- [ ] Waits for "Message sent" confirmation snackbar
- [ ] Returns `SendResult(message_id="", thread_id="")`
- [ ] Applies configurable delay (`playwright_send_delay_seconds`) between sends
- [ ] Each step has timeout-based error handling with descriptive `SendError`
- [ ] Compose window is dismissed/closed on error to prevent stale state
