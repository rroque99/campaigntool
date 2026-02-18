# Phase 2 — Playwright Sender Implementation

## Goal

Implement a Playwright-based email sender that automates the Gmail web UI to compose and send emails.

## Tasks

### Task 2.1 — Add Playwright dependency

Update `backend/pyproject.toml`:
- Add `playwright` to dependencies
- Document that `playwright install chromium` must be run after install (installs the browser binary)

### Task 2.2 — Implement PlaywrightSender class

**File:** `backend/src/campaign/playwright_sender.py`

Core class implementing the `SendBackend` protocol:

```python
class PlaywrightSender:
    """Sends emails by automating the Gmail web UI via Playwright."""

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None

    def send_email(self, to, subject, body_html, body_text, thread_id=None) -> SendResult:
        """Compose and send an email via Gmail web UI."""
        ...

    def is_ready(self) -> bool:
        """Check if we have a valid Gmail session."""
        ...

    def get_display_name(self) -> str:
        return "Playwright (Browser Automation)"
```

### Task 2.3 — Implement browser session management

Within `PlaywrightSender`, handle browser lifecycle:

1. **`launch_browser()`**: Start Chromium in headed mode with a persistent context stored at `credentials/playwright-session/`. This directory stores cookies/localStorage so the user stays logged in across restarts.

2. **`ensure_session()`**: Check if the current page is on `mail.google.com` and the user is logged in. Detection approach:
   - Navigate to `https://mail.google.com`
   - Check if redirected to accounts.google.com (not logged in) or if the inbox loaded (look for compose button via `div[gh="cm"]` or `[aria-label="Compose"]`)
   - If not logged in, raise `SendError("Gmail session expired. Please re-login via Settings.", error_code="session_expired", retryable=False)`

3. **`close_browser()`**: Gracefully close browser and context. Called during app shutdown.

4. **`initiate_login()`**: Launch the browser, navigate to `https://mail.google.com`, and let the user manually log in. Return once the inbox is detected. This is triggered from the Settings page.

### Task 2.4 — Implement the send flow

The core `send_email()` automation sequence:

1. Call `ensure_session()` — verify logged in
2. Click the Compose button (`[aria-label="Compose"]` or `div[gh="cm"]`)
3. Wait for the compose window to appear
4. Fill the "To" field — locate the input within the compose window, type the email address, press Tab to confirm
5. Fill the "Subject" field — locate by `[name="subjectbox"]` or aria label
6. Fill the "Body" field — locate the contenteditable body div, set innerHTML for HTML content (or type plain text as fallback)
7. Click the Send button (`[aria-label="Send"]` or `div[data-tooltip="Send"]`)
8. Wait for the "Message sent" confirmation (snackbar/toast in Gmail UI)
9. Return `SendResult(message_id="", thread_id="")` — no IDs available from UI
10. Add configurable delay (`settings.playwright_send_delay_seconds`) before returning

**Error handling at each step:**
- Timeout waiting for compose window → `SendError("Failed to open compose window", retryable=True)`
- Timeout waiting for send confirmation → `SendError("Send confirmation not detected", retryable=True)`
- CAPTCHA or unusual activity page detected → `SendError("Google security challenge detected", error_code="session_expired", retryable=False)`
- Any unexpected page state → `SendError` with descriptive message

### Task 2.5 — Implement selector resilience

Gmail's DOM is fragile. Implement a multi-strategy selector approach:

```python
COMPOSE_BUTTON_SELECTORS = [
    '[aria-label="Compose"]',
    'div[gh="cm"]',
    '.T-I.T-I-KE.L3',  # Known Gmail class pattern
]

async def _click_compose(self):
    for selector in COMPOSE_BUTTON_SELECTORS:
        try:
            await self._page.click(selector, timeout=3000)
            return
        except TimeoutError:
            continue
    raise SendError("Could not find Compose button — Gmail UI may have changed")
```

Apply this pattern to all key interactions: compose, to field, subject, body, send button, confirmation.

### Task 2.6 — Implement session status endpoint

**File:** `backend/src/campaign/routers/auth.py`

Add a new endpoint:

```
GET /api/v1/auth/playwright/status
→ { "session_active": bool, "email": str | null, "last_verified": datetime | null }
```

And a login trigger endpoint:

```
POST /api/v1/auth/playwright/login
→ { "message": "Browser launched. Please log in to Gmail in the opened browser window." }
```

This launches the Playwright browser and navigates to Gmail, letting the user log in manually.

### Task 2.7 — Handle HTML email body injection

Gmail's compose body is a contenteditable div. For HTML emails:

1. **Primary approach**: Use `page.evaluate()` to set `innerHTML` on the compose body div. This preserves HTML formatting.
2. **Fallback**: If HTML injection fails, fall back to typing the plain text body via `page.type()`.
3. **Validation**: After injection, verify the body div is non-empty.

Note: Complex HTML (tables, images) may render differently in Gmail's compose editor vs. the API. Document this as a known limitation.

## Deliverables

- `playwright_sender.py` with full `PlaywrightSender` implementation
- Browser session management (persistent context, login, session checking)
- Multi-selector resilience for all Gmail UI interactions
- Playwright auth endpoints in `routers/auth.py`
- Configurable inter-send delay
