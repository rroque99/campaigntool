# Phase 2 — Completed

**Status:** Done
**Date:** 2026-02-15

## What Was Built

All 7 tasks in Phase 2 are complete. Gmail OAuth2 authentication, email sending, reply detection, and daily quota tracking are fully implemented and tested.

### Task 2.1 — OAuth2 Flow Implementation
- `backend/src/campaign/auth.py` — full OAuth2 module:
  - `get_auth_url()` — generates Google OAuth consent URL using `credentials/credentials.json`
  - `handle_callback(code)` — exchanges auth code for tokens, saves `credentials/token.json`
  - `get_credentials()` — loads token.json, auto-refreshes expired access tokens via refresh token
  - `is_authenticated()` — returns `True` if valid/refreshable credentials exist
  - `get_user_email()` — fetches authenticated user's email via Gmail API profile
  - `revoke_credentials()` — revokes token with Google and deletes token.json
  - `AuthError` exception class with `message` and `error_code` fields
- Uses `pathlib` for all file path operations
- Private helpers `_credentials_json_path()` and `_token_json_path()` use `settings.credentials_dir`

### Task 2.2 — Auth API Router
- `backend/src/campaign/routers/auth.py` — 5 endpoints:
  - `GET /api/v1/auth/status` → `{"authenticated": bool, "email": str | null}`
  - `GET /api/v1/auth/login` → `{"auth_url": str}`
  - `GET /api/v1/auth/callback?code=...` → redirects to `http://localhost:5173/settings?auth=success` (or `?auth=error&message=...`)
  - `POST /api/v1/auth/logout` → revokes credentials, returns confirmation
  - `GET /api/v1/auth/quota` → `{"sent_today": int, "limit": int, "remaining": int}`

### Task 2.3 — Gmail API Send Module
- `backend/src/campaign/gmail.py` — isolated Gmail API module:
  - `build_gmail_service()` — creates Gmail API service object using credentials from `auth.py`
  - `send_email(to, subject, body_html, body_text, thread_id=None) -> SendResult` — constructs MIME multipart/alternative message, base64url encodes, sends via Gmail API
  - `SendResult` dataclass: `message_id: str`, `thread_id: str`
  - `GmailError` exception class with `message` and `error_code` fields
  - Handles rate limiting (429), API errors, and network failures with structured error responses

### Task 2.4 — Auth & Gmail Tests
- 31 tests in `backend/tests/test_gmail.py` covering:
  - Auth: `get_auth_url`, `handle_callback`, `get_credentials` (valid, missing, expired, refresh failure), `is_authenticated`, `revoke_credentials`
  - Gmail send: successful send, thread ID threading, MIME structure verification, rate limit handling, API error handling, network error handling
  - Service builder: successful build, auth error propagation
  - Auth routes: status (authenticated/unauthenticated), login URL, callback redirect, logout
  - Quota route: empty quota, quota with sent emails
- 100% of Gmail API interactions are mocked

### Task 2.5 — Daily Send Tracking
- `GET /api/v1/auth/quota` endpoint queries emails with `status="sent"` and `sent_at` on current UTC date
- Compares against `settings.daily_send_limit` (default 500)
- `get_send_quota_remaining(sent_today)` utility in gmail.py for use by scheduler

### Task 2.6 — Reply Detection Module
- `check_replies(history_id: str | None) -> ReplyCheckResult` in `gmail.py`:
  - If `history_id` is `None`: fetches current Gmail history ID as starting point (no retroactive detection)
  - Otherwise: uses `history.list` with `historyTypes=["messageAdded"]` to find new messages
  - Filters out SENT messages (only counts incoming replies)
  - Deduplicates thread IDs
  - Handles expired history ID (404) by falling back to full resync
  - Supports pagination via `nextPageToken`
- `ReplyCheckResult` dataclass: `new_history_id: str`, `replied_thread_ids: list[str]`
- `send_email()` returns `thread_id` in `SendResult` for later reply matching

### Task 2.7 — Reply Detection Tests
- 6 tests covering:
  - Initial sync with `None` history_id
  - Detecting replies across multiple history records
  - Ignoring SENT messages
  - Empty history (no new messages)
  - Expired history ID resync fallback
  - Thread ID deduplication

## Verification Commands

All commands run from `backend/`:

```bash
export PATH="$HOME/.local/bin:$PATH"

# Lint
cd backend
uv run ruff check src/ tests/           # All checks passed
uv run ruff format --check src/ tests/  # 20 files already formatted

# Tests
uv run pytest -v                         # 32 passed (1 from Phase 1, 31 from Phase 2)
```

## What's Next — Phase 3 (Campaign Management Backend)

Phase 3 depends only on Phase 1. The next agent should:

1. **Read:** `docs/plan/phase-3-campaign-backend.md` for the full task breakdown
2. **Key files to create/modify:**
   - `backend/src/campaign/parser.py` — spreadsheet (CSV/XLSX) and document parsing
   - `backend/src/campaign/templates.py` — email template rendering with `{{variable}}` substitution
   - `backend/src/campaign/routers/campaigns.py` — campaign CRUD endpoints (existing stub)
   - `backend/src/campaign/routers/recipients.py` — recipient endpoints (existing stub)
   - `backend/src/campaign/routers/emails.py` — email preview endpoints (existing stub)
   - `backend/tests/test_parser.py` — parser tests (existing placeholder)
   - `backend/tests/test_templates.py` — template tests (existing placeholder)
   - `backend/tests/test_campaigns.py` — campaign route tests (has health check only)
3. **Important context:**
   - Two separate input files per campaign: **recipients list** (CSV/XLSX: recipient_email, recipient_name, plus custom columns) and **campaign schedule** (CSV/XLSX: send_date, send_time, email_template_ref)
   - The schedule defines the email sequence — every recipient gets the same schedule
   - `send_date` supports relative values (integer = days after previous email sent); first step must use an absolute date
   - Email content documents contain multiple emails separated by `---` with frontmatter for subject line
   - Template variables use `{{variable_name}}` syntax, populated from spreadsheet columns
   - Models already exist: `Campaign`, `Recipient`, `Email`, `CampaignScheduleStep` in `models.py`
   - Schemas already exist: `CampaignCreate`, `CampaignResponse`, `RecipientResponse`, `RecipientCreate`, `EmailPreviewResponse` in `schemas.py`
   - Example files in `examples/`: `sample_recipients.xlsx`, `sample_schedule.xlsx`, `sample_emails.md`
   - `POST /api/v1/campaigns` is multipart (spreadsheet uploads + config)
   - `POST /api/v1/campaigns/{id}/recipients` allows manual recipient addition (draft campaigns only)
4. **Running commands:** Always prefix with `export PATH="$HOME/.local/bin:$PATH"` and run from `backend/` directory using `uv run`

## File Tree (Backend — Phase 2 changes highlighted)

```
backend/
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   ├── README
│   └── versions/
│       └── b26bc8c1f04f_initial_schema.py
├── src/
│   └── campaign/
│       ├── __init__.py
│       ├── auth.py              ← NEW (OAuth2 flow, token management)
│       ├── config.py
│       ├── database.py
│       ├── gmail.py             ← NEW (Gmail API send, reply detection)
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       └── routers/
│           ├── __init__.py
│           ├── auth.py          ← UPDATED (5 endpoints: status, login, callback, logout, quota)
│           ├── campaigns.py
│           ├── emails.py
│           └── recipients.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_campaigns.py
    ├── test_gmail.py            ← UPDATED (31 tests for auth, send, reply detection, routes)
    ├── test_parser.py
    ├── test_scheduler.py
    └── test_templates.py
```
