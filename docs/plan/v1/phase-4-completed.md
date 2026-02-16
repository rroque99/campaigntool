# Phase 4 — Completed

**Status:** Done
**Date:** 2026-02-15

## What Was Built

All 7 tasks in Phase 4 are complete. The scheduling engine, email delivery pipeline, campaign lifecycle management, delivery status tracking, and reply monitoring are fully implemented.

### Task 4.1 — APScheduler Setup & Lifespan Integration
- `backend/src/campaign/scheduler.py` — full scheduler module:
  - `BackgroundScheduler` with SQLAlchemy job store (persists jobs in SQLite)
  - `coalesce=True`, `max_instances=1`, `misfire_grace_time=3600`
  - `start_scheduler()` / `stop_scheduler()` / `get_scheduler()`
  - Event listener logging for job execution and errors
- `backend/src/campaign/main.py` — lifespan updated:
  - Calls `start_scheduler()` on startup
  - Calls `stop_scheduler()` on shutdown
  - Starts reply monitor with graceful fallback if Gmail not yet authenticated

### Task 4.2 — Email Send Job Function
- `send_email_job(email_id, retry_count=0)` in scheduler.py:
  - Uses fresh DB session (thread-safe for background execution)
  - Checks email status is `scheduled` before sending (skips cancelled/sent)
  - Checks daily send quota, reschedules for tomorrow if exceeded
  - Calls `gmail.send_email()`, records `message_id`, `thread_id`, `sent_at`
  - On success: resolves next relative-date step for the recipient
  - On failure: marks email as `failed` with error message
  - Retry logic: rate-limited errors retry up to 3 times with exponential backoff (5s, 10s, 20s)
  - After each send, checks if campaign is complete and updates campaign status
  - Unexpected errors caught and logged, email marked as failed

### Task 4.3 — Campaign Scheduling Endpoints
- `POST /api/v1/campaigns/{id}/schedule`:
  - Validates campaign is `draft` or `paused`
  - Validates Gmail is authenticated
  - Creates APScheduler jobs for emails with absolute `send_date` steps
  - Skips relative-date steps (resolved lazily when previous step completes)
  - Updates campaign status to `scheduled`
  - Returns `{scheduled_count, skipped_count, next_send_at}`
- `POST /api/v1/campaigns/{id}/pause`:
  - Removes APScheduler jobs for scheduled emails
  - Reverts email statuses from `scheduled` → `pending`, clears `scheduled_at`
  - Updates campaign status to `paused`
  - Returns `{paused_count}`
- `POST /api/v1/campaigns/{id}/cancel`:
  - Removes APScheduler jobs and marks all pending/scheduled emails as `cancelled`
  - Determines final campaign status (`completed` or `failed`)
  - Returns `{cancelled_count, campaign_status}`

### Task 4.4 — Campaign Status Tracking
- `GET /api/v1/campaigns/{id}/status`:
  - Returns real-time counts: `total_emails, sent, failed, pending, scheduled, cancelled`
  - `progress_percent`: sent / total * 100
  - `next_send_at`: earliest scheduled email time
  - `estimated_completion`: latest scheduled email time
- Campaign status auto-transitions (in `_update_campaign_status()`):
  - `scheduled` → `in_progress` when first email is sent/failed
  - `in_progress` → `completed` when no emails are pending/scheduled
  - `in_progress` → `failed` when all emails failed (none sent)

### Task 4.5 — Delivery Status Per Email
- `GET /api/v1/campaigns/{id}/emails` — paginated email list:
  - Fields: id, recipient_email, recipient_name, subject, status, step_order, scheduled_at, sent_at, error_message
  - Filter by `status` query param
  - Sort by `scheduled_at` (default) or `sent_at`
  - Pagination with `page` and `page_size`
- `GET /api/v1/campaigns/{id}/emails/{email_id}` — single email detail:
  - Full rendered content (subject, body_html, body_text)
  - Delivery metadata (gmail_message_id, thread_id, timestamps, error)

### Task 4.6 — Scheduler Tests
- `backend/tests/test_scheduler.py` — 30 tests:
  - **send_email_job**: success (status/message_id/thread_id), failure (error_message), skip cancelled, rate-limited retry, rate-limited exhausted, quota exceeded
  - **Relative step resolution**: step 2 gets scheduled_at computed from step 1's sent_at + relative_days
  - **Campaign status transitions**: scheduled→in_progress, in_progress→completed, in_progress→failed
  - **schedule_campaign**: creates jobs for absolute dates, skips relative
  - **pause_campaign**: reverts to pending, doesn't affect sent
  - **cancel_campaign**: marks pending+scheduled as cancelled
  - **Schedule endpoint**: success, rejects completed, rejects unauthenticated
  - **Pause endpoint**: success, rejects draft
  - **Cancel endpoint**: success, rejects completed
  - **Campaign status endpoint**: accurate counts, 404
  - **Email list/detail**: list with pagination, filter by status, detail, 404
  - **Reply monitoring**: cancel emails for replied threads, check_replies_job updates state, skips unauthenticated

### Task 4.7 — Reply Monitoring Scheduler Job
- `check_replies_job()` — periodic job (every `reply_check_interval_minutes`):
  - Only runs when Gmail is authenticated
  - Loads/creates `ReplyCheckState` for history_id cursor
  - Calls `gmail.check_replies(history_id)` for incremental sync
  - For each replied thread: finds recipient, cancels all remaining unsent emails, removes APScheduler jobs
  - Updates history_id and last_checked_at
  - Handles errors gracefully (logs and skips on failure)
- `start_reply_monitor()` — registers the interval job during startup
- `_cancel_emails_for_replied_threads()` — helper that flushes DB changes before updating campaign status

## New Schemas Added
- `PauseResponse`: `paused_count`
- `CancelResponse`: `cancelled_count, campaign_status`
- `CampaignStatusResponse`: `total_emails, sent, failed, pending, scheduled, cancelled, progress_percent, next_send_at, estimated_completion`
- `EmailStatusResponse`: `id, recipient_email, recipient_name, subject, status, step_order, scheduled_at, sent_at, error_message`
- `EmailListResponse`: `total, page, page_size, items`
- `EmailDetailResponse`: full email detail with body content and delivery metadata

## Verification Commands

All commands run from `backend/`:

```bash
export PATH="$HOME/.local/bin:$PATH"

# Lint
cd backend
uv run ruff check src/ tests/           # All checks passed
uv run ruff format --check src/ tests/  # All files formatted

# Tests
uv run pytest -v                         # 115 passed (85 from Phases 2-3, 30 new in Phase 4)
```

## What's Next — Phase 5 (Frontend Application)

Phase 5 depends on Phase 3 (partial Phase 4). The next agent should:

1. **Read:** `docs/plan/phase-5-frontend.md` for the full task breakdown
2. **Key files to create/modify:**
   - `frontend/src/api/campaigns.ts` — Axios/fetch client + React Query hooks
   - `frontend/src/pages/Dashboard.tsx` — Overview: active campaigns, upcoming sends, stats
   - `frontend/src/pages/CampaignList.tsx` — All campaigns with status indicators
   - `frontend/src/pages/CampaignDetail.tsx` — Single campaign: recipients, schedule, delivery log
   - `frontend/src/pages/CampaignCreate.tsx` — Upload spreadsheet, configure, preview
   - `frontend/src/pages/Settings.tsx` — Gmail auth status, reconnect, preferences
   - `frontend/src/components/` — Layout, StatusBadge, RecipientTable, EmailPreview, FileUpload
   - `frontend/src/types/index.ts` — TypeScript types mirroring backend schemas
3. **Important context:**
   - Backend API is at `http://localhost:8000/api/v1/`
   - Frontend dev server on port 5173, proxied to backend on 8000
   - React Query with 10-second polling for campaign status updates
   - All timestamps in API responses are UTC — frontend converts to local timezone
   - Campaign statuses: draft, scheduled, in_progress, paused, completed, failed
   - Email statuses: pending, scheduled, sent, failed, cancelled
   - Key API endpoints for frontend:
     - `GET /api/v1/campaigns` — list with status filter
     - `POST /api/v1/campaigns` — multipart form (name, description, recipients_file, schedule_file, email_document)
     - `GET /api/v1/campaigns/{id}` — detail with stats
     - `GET /api/v1/campaigns/{id}/status` — real-time progress
     - `POST /api/v1/campaigns/{id}/schedule` — schedule sends
     - `POST /api/v1/campaigns/{id}/pause` — pause
     - `POST /api/v1/campaigns/{id}/cancel` — cancel
     - `GET /api/v1/campaigns/{id}/recipients` — paginated, searchable
     - `GET /api/v1/campaigns/{id}/preview` — email previews
     - `GET /api/v1/campaigns/{id}/emails` — delivery status list
     - `GET /api/v1/campaigns/{id}/emails/{id}` — single email detail
     - `GET /api/v1/auth/status` — auth check
     - `GET /api/v1/auth/login` — OAuth URL
     - `GET /api/v1/auth/quota` — daily send quota
4. **Running commands:** Frontend uses `npm install` and `npm run dev`

## Standing Instructions for Next Phase

When this phase is complete, create a `phase-5-completed.md` document that contains relevant context for the next agent to complete the next phase. Include this same instruction in the phase-5-completed document so the pattern continues without the user needing to repeat the request.

## File Tree (Backend — Phase 4 changes highlighted)

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
│       ├── main.py              ← UPDATED (scheduler lifespan integration)
│       ├── models.py
│       ├── parser.py
│       ├── scheduler.py         ← NEW (APScheduler, send job, reply monitor, campaign lifecycle)
│       ├── schemas.py           ← UPDATED (6 new response schemas for scheduling/status/emails)
│       ├── templates.py
│       └── routers/
│           ├── __init__.py
│           ├── auth.py
│           ├── campaigns.py     ← UPDATED (schedule/pause/cancel/status endpoints)
│           ├── emails.py        ← UPDATED (email list + detail endpoints)
│           └── recipients.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_campaigns.py
    ├── test_gmail.py
    ├── test_parser.py
    ├── test_scheduler.py        ← UPDATED (30 tests: send job, endpoints, status, replies)
    └── test_templates.py
```
