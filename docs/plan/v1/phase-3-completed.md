# Phase 3 — Completed

**Status:** Done
**Date:** 2026-02-15

## What Was Built

All 8 tasks in Phase 3 are complete. Campaign management backend is fully implemented: file parsing, email template rendering, campaign CRUD, recipient management, and email preview endpoints.

### Task 3.1 — Recipients & Schedule Parsers (CSV & XLSX)
- `backend/src/campaign/parser.py` — full file parsing module:
  - `parse_recipients_file(file: UploadFile) -> RecipientsParseResult` — parses CSV/XLSX recipients files
  - `parse_schedule_file(file: UploadFile) -> ScheduleParseResult` — parses CSV/XLSX schedule files
  - Required columns validated: `recipient_email`, `recipient_name` for recipients; `send_date`, `send_time`, `email_template_ref` for schedule
  - Extra columns in recipients become `custom_fields` dict entries
  - Email validation via regex, invalid emails flagged per-row (not entire file rejected)
  - Empty rows silently skipped
  - `send_date` supports absolute dates (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY) and relative integers
  - First schedule step must have absolute date (relative returns error)
  - Past absolute dates flagged as warnings
  - File type detection from extension, with XLSX-then-CSV fallback
- Data classes: `RecipientData`, `RecipientsParseResult`, `ScheduleStepData`, `ScheduleParseResult`

### Task 3.2 — Email Document Parser
- Added to `parser.py`:
  - `parse_email_document(file: UploadFile) -> list[EmailTemplate]`
  - Supports `.md` (Markdown) format — body rendered to HTML via `markdown` library
  - Supports `.docx` (Word) format via `python-docx`
  - Sections separated by `---` on its own line
  - Frontmatter: `ref:` (template identifier) and `subject:` lines
  - Auto-numbered refs (1, 2, 3...) when `ref:` not specified
  - `EmailTemplate` data class: `ref`, `subject`, `body_html`, `body_text`
- Parses `examples/sample_emails.md` correctly (verified by test)

### Task 3.3 — Email Template Rendering
- `backend/src/campaign/templates.py`:
  - `render_email(template: EmailTemplate, variables: dict) -> RenderedEmail`
  - Replaces `{{variable_name}}` placeholders in subject, body_html, and body_text
  - HTML body: variable values are HTML-escaped (prevents XSS)
  - Plain text body: variable values inserted as-is
  - Missing variables: placeholder preserved, warning added (deduplicated)
  - Extra variables: silently ignored
- `RenderedEmail` data class: `subject`, `body_html`, `body_text`, `warnings`

### Task 3.4 — Campaign CRUD Endpoints
- `backend/src/campaign/routers/campaigns.py` — 4 endpoints:
  - `POST /api/v1/campaigns` — multipart form: name, description, recipients_file, schedule_file, email_document
    - Parses all three files, validates template refs match between schedule and document
    - Creates Campaign (draft), CampaignScheduleStep records, Recipient records, and Email records (recipient × step)
    - Returns 201 with `CampaignResponse`
  - `GET /api/v1/campaigns` — list with optional `status` filter, ordered by created_at desc
  - `GET /api/v1/campaigns/{id}` — single campaign with computed stats (recipient_count, sent/failed/pending counts, step_count)
  - `DELETE /api/v1/campaigns/{id}` — only allowed for draft/completed/failed campaigns (cascade deletes)
- Helper `_campaign_to_response()` computes aggregate stats from DB queries

### Task 3.5 — Recipient Endpoints
- `backend/src/campaign/routers/recipients.py` — 3 endpoints (no prefix, full paths):
  - `GET /api/v1/campaigns/{id}/recipients` — paginated list with `page`, `page_size`, `status` filter, `search` (case-insensitive partial match on email/name)
  - `GET /api/v1/campaigns/{id}/recipients/{recipient_id}` — single recipient detail with email status
  - Each recipient includes `email_status` from their first email record

### Task 3.6 — Email Preview Endpoint
- `backend/src/campaign/routers/emails.py` — 2 endpoints (no prefix, full paths):
  - `GET /api/v1/campaigns/{id}/preview` — preview for a specific recipient (or first recipient if not specified)
  - `GET /api/v1/campaigns/{id}/preview/all` — previews for all recipients across all steps

### Task 3.7 — Parser & Template Tests
- `backend/tests/test_parser.py` — 16 tests:
  - Recipients CSV: valid, missing columns, invalid email, empty email, empty rows skipped, custom fields, empty file
  - Recipients XLSX: valid, missing columns
  - Schedule CSV: valid (absolute + relative), missing columns, first step relative error, past date warning, invalid date, invalid time, empty template ref
  - Schedule XLSX: valid
  - Email document: Markdown with refs, auto-numbered refs, missing subject, empty document, sample_emails.md
- `backend/tests/test_templates.py` — 7 tests:
  - Basic substitution, missing variable preserved, HTML escaping, extra variables ignored, subject substitution, deduplicated warnings, ampersand escaping
- `backend/tests/test_campaigns.py` — 25 tests:
  - Campaign creation: success, bad recipients, bad schedule, missing template ref
  - Campaign list: empty, with campaigns, status filter
  - Campaign detail: success, not found
  - Campaign deletion: draft OK, active blocked, not found
  - Recipient list: basic, search, pagination, single recipient detail
  - Manual add: success, duplicate email (409), non-draft blocked (400), generates email records
  - Email preview: default first recipient, specific recipient, all recipients, not found

### Task 3.8 — Manual Recipient Add Endpoint
- `POST /api/v1/campaigns/{id}/recipients` in recipients router:
  - Validates campaign is draft, checks duplicate email (409)
  - Creates Recipient record and Email records for all schedule steps
  - Uses existing email content from same step as template for the new recipient

## Router URL Fix
- Fixed `recipients.py` and `emails.py` routers: removed `prefix="/recipients"` and `prefix="/emails"` to avoid incorrect nested paths (e.g., `/api/v1/recipients/campaigns/{id}/recipients`)
- Routes now use full paths like `/campaigns/{campaign_id}/recipients` and `/campaigns/{campaign_id}/preview`, mounted under `/api/v1` prefix by main.py

## Verification Commands

All commands run from `backend/`:

```bash
export PATH="$HOME/.local/bin:$PATH"

# Lint
cd backend
uv run ruff check src/ tests/           # All checks passed
uv run ruff format --check src/ tests/  # 22 files already formatted

# Tests
uv run pytest -v                         # 85 passed (32 from Phase 2, 53 new in Phase 3)
```

## What's Next — Phase 4 (Scheduling & Email Delivery)

Phase 4 depends on Phases 2 & 3. The next agent should:

1. **Read:** `docs/plan/phase-4-scheduling.md` for the full task breakdown
2. **Key files to create/modify:**
   - `backend/src/campaign/scheduler.py` — APScheduler integration, job management
   - `backend/src/campaign/main.py` — start/stop scheduler in lifespan (replace placeholder comments)
   - `backend/src/campaign/routers/campaigns.py` — add schedule/pause/cancel endpoints
   - `backend/tests/test_scheduler.py` — scheduler tests (existing placeholder)
3. **Important context:**
   - APScheduler `BackgroundScheduler` runs within the FastAPI process
   - Jobs persist in SQLite so they survive restarts
   - `send_email()` from `gmail.py` returns `SendResult(message_id, thread_id)` — store both in Email record
   - Relative send dates resolved lazily: when step N completes for a recipient, calculate next step's `scheduled_at` from actual `sent_at`
   - Reply detection: `check_replies()` from `gmail.py` returns `ReplyCheckResult(new_history_id, replied_thread_ids)` — cancel unsent emails for recipients with matching thread_ids
   - `ReplyCheckState` model already exists for tracking history_id cursor
   - Config: `settings.reply_check_interval_minutes` (default 15) controls how often reply checking runs
   - Daily send limit: `settings.daily_send_limit` (default 500) — `GET /api/v1/auth/quota` endpoint already returns counts
   - Campaign statuses flow: draft → scheduled → in_progress → completed/paused/failed
   - Schedule steps have `send_date` (absolute) or `relative_days` (relative to previous email sent_at)
   - Email statuses: pending → scheduled → sent/failed/cancelled
4. **Existing endpoints to reference:**
   - `POST /api/v1/campaigns/{id}/schedule` — needs to be implemented (schedule all pending emails)
   - `POST /api/v1/campaigns/{id}/pause` — needs to be implemented (pause scheduled sends)
   - `POST /api/v1/campaigns/{id}/cancel` — needs to be implemented (cancel remaining unsent emails)
5. **Running commands:** Always prefix with `export PATH="$HOME/.local/bin:$PATH"` and run from `backend/` directory using `uv run`

## Standing Instructions for Next Phase

When this phase is complete, create a `phase-4-completed.md` document that contains relevant context for the next agent to complete the next phase. Include this same instruction in the phase-4-completed document so the pattern continues without the user needing to repeat the request.

## File Tree (Backend — Phase 3 changes highlighted)

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
│       ├── auth.py
│       ├── config.py
│       ├── database.py
│       ├── gmail.py
│       ├── main.py
│       ├── models.py
│       ├── parser.py             ← NEW (recipients, schedule, email document parsing)
│       ├── schemas.py
│       ├── templates.py          ← NEW (email template rendering with {{variable}} substitution)
│       └── routers/
│           ├── __init__.py
│           ├── auth.py
│           ├── campaigns.py      ← UPDATED (POST/GET/DELETE campaign CRUD with file upload)
│           ├── emails.py         ← UPDATED (preview endpoints, no prefix)
│           └── recipients.py     ← UPDATED (list/detail/manual add endpoints, no prefix)
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_campaigns.py         ← UPDATED (25 tests: CRUD, recipients, preview)
    ├── test_gmail.py
    ├── test_parser.py            ← UPDATED (16 tests: CSV/XLSX/email document parsing)
    ├── test_scheduler.py
    └── test_templates.py         ← UPDATED (7 tests: variable substitution, escaping)
```
