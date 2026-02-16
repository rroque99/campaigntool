# Phase 4 — Scheduling & Email Delivery

**Goal:** Implement the APScheduler-based email scheduling engine, the send pipeline, campaign lifecycle management, and delivery status tracking.

**Dependencies:** Phase 2 (Gmail send module), Phase 3 (campaign & email records in DB)

---

## Tasks

### Task 4.1 — APScheduler Setup & Lifespan Integration

**Priority:** High
**Estimated Effort:** Medium

- Create `backend/src/campaign/scheduler.py`:
  - Initialize `BackgroundScheduler` with SQLAlchemy job store (persists jobs in SQLite so they survive restarts)
  - Configure with `coalesce=True` and `max_instances=1` to prevent duplicate sends
  - `start_scheduler()` — starts the scheduler (called during FastAPI lifespan startup)
  - `stop_scheduler()` — gracefully shuts down the scheduler (called during lifespan shutdown)
  - `get_scheduler()` — returns the scheduler instance for dependency injection
- Update `backend/src/campaign/main.py` lifespan:
  - Call `start_scheduler()` on startup
  - Call `stop_scheduler()` on shutdown
  - Log scheduler state changes

**Acceptance Criteria:**
- Scheduler starts when the FastAPI app starts
- Scheduler stops gracefully when the app shuts down
- Jobs persist across app restarts (stored in SQLite)
- No duplicate job execution

---

### Task 4.2 — Email Send Job Function

**Priority:** High
**Estimated Effort:** Medium

- Add to `backend/src/campaign/scheduler.py`:
  - `send_email_job(email_id: int)` — the function APScheduler calls at the scheduled time:
    1. Load the Email record from DB
    2. Check email status is still `scheduled` (skip if cancelled/sent)
    3. Check daily send quota (skip and reschedule if exceeded)
    4. Call `gmail.send_email()` with the email's subject, HTML body, and plain text body
    5. On success: update email status to `sent`, record `sent_at` and `gmail_message_id`
    5a. Store `thread_id` from Gmail API response on the Email record
    5b. Resolve next relative-date step for this recipient: if the next schedule step uses `relative_days`, compute its `scheduled_at` from this email's `sent_at` + `relative_days` and create the APScheduler job
    6. On failure: update email status to `failed`, record `error_message`
    7. After each send, check if all emails in the campaign are done → update campaign status to `completed`
    8. Use a fresh DB session (not the request session, since this runs in a background thread)
  - Handle thread safety: create a new SQLAlchemy session per job execution
  - Implement retry logic: on transient errors (network, rate limit), retry up to 3 times with exponential backoff

**Acceptance Criteria:**
- Job sends the email and updates DB status on success
- Failed sends are recorded with error messages
- Transient failures trigger retries
- Permanent failures mark the email as `failed`
- Campaign status updates to `completed` when all emails are processed
- Thread-safe DB session usage

---

### Task 4.3 — Campaign Scheduling Endpoints

**Priority:** High
**Estimated Effort:** Medium

- Implement in `backend/src/campaign/routers/campaigns.py`:
  - `POST /api/v1/campaigns/{id}/schedule` — schedule all pending emails:
    - Validate campaign is in `draft` or `paused` status
    - Validate Gmail is authenticated
    - Check daily quota won't be immediately exceeded
    - Note: only emails with an absolute `scheduled_at` are immediately schedulable. Emails for relative-date steps have `scheduled_at = NULL` until the previous step completes
    - For each email record with status `pending`:
      - Create an APScheduler job with `run_date` set to the email's `scheduled_at` time
      - Update email status to `scheduled`
    - Update campaign status to `scheduled`
    - Return summary: `{"scheduled_count": int, "skipped_count": int, "next_send_at": datetime}`
  - `POST /api/v1/campaigns/{id}/pause` — pause scheduled sends:
    - Remove all pending APScheduler jobs for this campaign
    - Update email statuses from `scheduled` back to `pending`
    - Update campaign status to `paused`
    - Already-sent emails are not affected
  - `POST /api/v1/campaigns/{id}/cancel` — cancel all remaining unsent emails:
    - Remove all pending APScheduler jobs for this campaign
    - Update email statuses from `scheduled`/`pending` to `cancelled`
    - Update campaign status to `completed` (or `failed` if any emails failed)

**Acceptance Criteria:**
- Scheduling creates the correct number of APScheduler jobs
- Each job fires at the correct `scheduled_at` time (UTC)
- Pausing removes jobs and reverts email statuses
- Cancelling permanently marks remaining emails as cancelled
- Status transitions are enforced (can't schedule a completed campaign)
- Concurrent schedule/pause/cancel calls are handled safely

---

### Task 4.4 — Campaign Status Tracking

**Priority:** Medium
**Estimated Effort:** Small

- Add to campaign detail response (or new endpoint):
  - `GET /api/v1/campaigns/{id}/status` — real-time campaign progress:
    - `total_emails: int`
    - `sent: int`
    - `failed: int`
    - `pending: int`
    - `scheduled: int`
    - `cancelled: int`
    - `progress_percent: float` (sent / total * 100)
    - `next_send_at: datetime | null`
    - `estimated_completion: datetime | null`
- Campaign status auto-transitions:
  - `scheduled` -> `in_progress` when the first email is sent
  - `in_progress` -> `completed` when all emails are sent/failed/cancelled
  - `in_progress` -> `failed` if a critical error occurs (e.g., auth revoked)

**Acceptance Criteria:**
- Status endpoint returns accurate real-time counts
- Campaign status transitions happen automatically as emails are processed
- Progress percentage is calculated correctly

---

### Task 4.5 — Delivery Status Per Email

**Priority:** Medium
**Estimated Effort:** Small

- Implement in `backend/src/campaign/routers/emails.py`:
  - `GET /api/v1/campaigns/{id}/emails` — paginated list of all emails with delivery status:
    - Fields: recipient email, recipient name, subject, status, scheduled_at, sent_at, error_message
    - Filter by status
    - Sort by scheduled_at or sent_at
  - `GET /api/v1/campaigns/{id}/emails/{email_id}` — single email detail:
    - Full rendered content (subject, body_html, body_text)
    - Delivery metadata (gmail_message_id, timestamps, error details)

**Acceptance Criteria:**
- Email list shows accurate delivery status for each recipient
- Failed emails show descriptive error messages
- Pagination and filtering work correctly

---

### Task 4.6 — Scheduler Tests

**Priority:** High
**Estimated Effort:** Medium

- Create/update `backend/tests/test_scheduler.py`:
  - Test `send_email_job()` with mocked Gmail API:
    - Successful send updates status and records message ID
    - Failed send records error message
    - Cancelled email is skipped
    - Quota exceeded triggers rescheduling
  - Test campaign scheduling endpoint:
    - Creates correct number of APScheduler jobs
    - Rejects scheduling for non-draft campaigns
    - Rejects scheduling when not authenticated
  - Test pause endpoint:
    - Removes jobs and reverts statuses
    - Doesn't affect already-sent emails
  - Test cancel endpoint:
    - Marks remaining emails as cancelled
  - Test campaign status auto-transitions
  - Test retry logic for transient errors

**Acceptance Criteria:**
- `uv run pytest tests/test_scheduler.py -v` passes
- All Gmail API calls are mocked
- Job execution is tested with mocked scheduler
- Status transitions are verified

---

### Task 4.7 — Reply Monitoring Scheduler Job

**Priority:** Medium
**Estimated Effort:** Medium

- Add to `backend/src/campaign/scheduler.py`:
  - `check_replies_job()` — periodic job that runs every `settings.reply_check_interval_minutes`:
    1. Load the `ReplyCheckState` record (create if not exists)
    2. Call `gmail.check_replies(history_id)` to get thread IDs with new replies
    3. For each replied thread ID:
       - Find all Email records with matching `thread_id`
       - Find the recipient for those emails
       - Cancel all remaining unsent emails for that recipient (status → `cancelled`)
       - Remove corresponding APScheduler jobs
    4. Update `ReplyCheckState` with new `history_id` and `last_checked_at`
  - Register the periodic job during scheduler startup (only if Gmail is authenticated)
  - Handle errors gracefully: if Gmail API fails, log and retry on next interval

**Acceptance Criteria:**
- Periodic job runs at configured interval
- Replies are detected and remaining emails cancelled for the replying recipient
- Other recipients' emails are not affected
- Job handles Gmail API errors without crashing
- Job is only active when Gmail is authenticated
