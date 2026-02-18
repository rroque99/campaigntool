# V2 — Playwright Email Sender Implementation Plan

## Summary

Add Playwright as an alternative email sending backend. Users who cannot access the Gmail API can send campaign emails through browser automation of the Gmail web UI. Reply detection is **not supported** in Playwright mode — campaigns run send-only.

## Scope

- Abstract the current `gmail.py` send logic behind a sender interface
- Implement a Playwright-based sender that automates the Gmail web UI
- Add configuration to switch between `gmail_api` and `playwright` send backends
- Update the frontend Settings page to show sender mode and Playwright session status
- Update the scheduler to use the configured sender
- Disable reply monitoring when using Playwright mode
- Add tests for the new sender (mocking Playwright interactions)

## Out of Scope

- Reply detection via Playwright (DOM scraping the inbox)
- IMAP/SMTP integration
- Headless mode (Google blocks headless browsers — user must see the browser)
- Multi-browser-session parallelism

## Phases

| Phase | Name | Description | Dependencies |
|-------|------|-------------|--------------|
| 1 | [Sender Abstraction Layer](phase-1-sender-abstraction.md) | Extract a sender interface from gmail.py, refactor scheduler to use it | None |
| 2 | [Playwright Sender Implementation](phase-2-playwright-sender.md) | Implement the Playwright Gmail web automation sender | Phase 1 |
| 3 | [Configuration & Backend Integration](phase-3-config-integration.md) | Settings, sender factory, scheduler integration, conditional reply monitoring | Phases 1 & 2 |
| 4 | [Frontend Updates](phase-4-frontend.md) | Settings page sender mode selector, Playwright session status, login flow | Phase 3 |
| 5 | [Testing & Documentation](phase-5-testing.md) | Unit tests, integration tests, manual test plan, documentation | Phases 1–4 |

## Architecture Changes

```
Current:
  scheduler.py → gmail.send_email() → Gmail API

After:
  scheduler.py → sender_factory.get_sender() → GmailAPISender.send_email()
                                               OR
                                               → PlaywrightSender.send_email()

  config.py:  send_backend = "gmail_api" | "playwright"
```

### New Files

```
backend/src/campaign/
├── sender.py              # Abstract base class (SendBackend protocol)
├── gmail_sender.py        # Gmail API sender (extracted from gmail.py)
├── playwright_sender.py   # Playwright Gmail web UI sender
└── sender_factory.py      # Factory: returns sender based on config
```

### Modified Files

```
backend/src/campaign/
├── config.py              # New settings: send_backend, playwright_*
├── gmail.py               # Retains reply-check logic; send logic moves out
├── scheduler.py           # Uses sender_factory instead of direct gmail import
├── main.py                # Lifespan: conditional reply monitor, Playwright cleanup
└── routers/
    └── auth.py            # New endpoints for Playwright session status

frontend/src/
├── pages/Settings.tsx     # Sender mode display, Playwright login trigger
└── types/index.ts         # New types for sender config
```

## Key Design Decisions

1. **Protocol-based abstraction**: Use `typing.Protocol` (not ABC) for the sender interface — keeps it lightweight and testable.
2. **Persistent browser context**: Playwright stores session cookies in a user data directory (`credentials/playwright-session/`) so users only log in once. Session persists across app restarts.
3. **Visible browser required**: Google blocks headless automation. The Playwright browser launches in headed mode. The user must manually complete login (including 2FA) on first run.
4. **Inter-send delay**: Configurable delay between sends (default 30s) to avoid triggering Google's abuse detection.
5. **No thread tracking**: `SendResult` from Playwright returns empty `message_id` and `thread_id` since we can't reliably extract these from the web UI. The `emails` table records `status=sent` but without Gmail IDs.
6. **Reply monitoring disabled**: When `send_backend=playwright`, the reply monitor job is not started. The UI shows a notice explaining this.
7. **Graceful degradation**: If the Playwright browser session expires mid-campaign, the sender raises a `SendError` and the scheduler pauses the campaign (same retry/fail logic as API errors).
