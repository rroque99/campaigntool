# Phase 1 — Completed

**Status:** Done
**Date:** 2026-02-14

## What Was Built

All 9 tasks in Phase 1 are complete. The project skeleton is fully set up and ready for feature development.

### Task 1.1 — Git Repository & Project Root
- Git repo initialized at project root
- `.gitignore` covers: `.venv/`, `credentials/`, `__pycache__/`, `node_modules/`, `dist/`, `.env`, `*.db`, IDE files
- Directory skeleton: `backend/`, `frontend/`, `credentials/.gitkeep`, `examples/`, `docs/`
- `README.md` with setup instructions

### Task 1.2 — Backend Python Project Setup
- `backend/pyproject.toml` with all dependencies (FastAPI, SQLAlchemy, Alembic, Google API client, APScheduler, openpyxl, python-docx, etc.)
- Dev dependencies: pytest, pytest-mock, pytest-asyncio, httpx, ruff
- Build system: hatchling
- **uv installed** at `~/.local/bin/uv` — must be on PATH (`export PATH="$HOME/.local/bin:$PATH"`)
- `uv sync --all-extras` creates `.venv/` and installs everything
- `uv.lock` generated
- Python version: 3.14.3 (auto-selected by uv — all packages compatible)

### Task 1.3 — Database Layer
- `backend/src/campaign/database.py` — SQLAlchemy engine, `SessionLocal`, `Base`, `get_db()` dependency
- `backend/src/campaign/models.py` — 3 ORM models:
  - **Campaign:** id, name, description, spreadsheet_filename, status, created_at, updated_at
  - **Recipient:** id, campaign_id (FK), email, name, custom_fields (JSON), created_at
  - **Email:** id, campaign_id (FK), recipient_id (FK), subject, body_html, body_text, scheduled_at, sent_at, status, error_message, gmail_message_id
- Relationships: Campaign->Recipients (cascade delete), Campaign->Emails (cascade delete), Recipient->Emails (cascade delete)
- Alembic initialized with `prepend_sys_path = . src` in `alembic.ini`
- Initial migration generated and verified (upgrade + downgrade work)
- **Note:** `alembic.ini` has `sqlalchemy.url = sqlite:///./campaign.db` — the `env.py` imports `Base.metadata` from `campaign.database`

### Task 1.4 — Configuration Module
- `backend/src/campaign/config.py` — pydantic-settings `BaseSettings`
- Settings: `database_url`, `credentials_dir`, `cors_origins`, `gmail_scopes`, `daily_send_limit`, `api_prefix`
- Loads from env vars and `.env` file
- Singleton: `from campaign.config import settings`

### Task 1.5 — FastAPI Application Shell
- `backend/src/campaign/main.py` — FastAPI app with lifespan, CORS, router registration
- 4 router stubs: `routers/auth.py`, `routers/campaigns.py`, `routers/recipients.py`, `routers/emails.py`
- Health endpoint: `GET /api/v1/health` → `{"status": "ok"}`
- CORS configured for `http://localhost:5173`
- Swagger docs at `/docs`
- Lifespan has placeholder comments for scheduler start/stop (Phase 4)

### Task 1.6 — Pydantic Schemas
- `backend/src/campaign/schemas.py` — all request/response models:
  - CampaignCreate, CampaignResponse, CampaignListResponse
  - RecipientResponse, RecipientListResponse
  - EmailPreviewResponse
  - ScheduleRequest, ScheduleResponse
  - AuthStatusResponse, QuotaResponse
  - ErrorResponse
- Response models use `ConfigDict(from_attributes=True)` for ORM serialization

### Task 1.7 — Test Infrastructure
- `backend/tests/conftest.py` — in-memory SQLite, `test_db` fixture, `test_client` fixture (httpx `AsyncClient`), `sample_campaign_data` fixture
- Placeholder test files: `test_campaigns.py`, `test_parser.py`, `test_gmail.py`, `test_scheduler.py`, `test_templates.py`
- Smoke test: `test_health_check` — passes

### Task 1.8 — Frontend Project Setup
- Vite + React 18 + TypeScript (strict mode)
- Tailwind CSS via `@tailwindcss/vite` plugin
- Dependencies: react-router-dom, @tanstack/react-query, @tanstack/react-table, axios
- Vite proxy: `/api` → `http://localhost:8000`
- `frontend/src/types/index.ts` — all TypeScript types mirroring backend schemas
- `npm run build` produces clean output in `dist/`
- Boilerplate cleaned up (minimal `App.tsx`, no `App.css`)

### Task 1.9 — Example Files
- `examples/sample_campaign.xlsx` — 5 rows with columns: recipient_email, recipient_name, send_date, send_time, email_template_ref, company, role
- `examples/sample_emails.md` — 2 templates ("intro" and "followup") with `{{variable}}` placeholders

## Verification Commands

All commands run from `backend/`:

```bash
export PATH="$HOME/.local/bin:$PATH"

# Backend
cd backend
uv run ruff check src/ tests/           # All checks passed
uv run ruff format --check src/ tests/  # 18 files already formatted
uv run pytest -v                         # 1 passed
uv run alembic upgrade head             # Creates tables
uv run alembic downgrade base           # Drops tables cleanly

# Frontend (from frontend/)
cd ../frontend
npm run build                            # Builds successfully
```

## What's Next — Phase 2 (Gmail Authentication & Integration)

Phase 2 depends only on Phase 1. The next agent should:

1. **Read:** `docs/plan/phase-2-gmail-auth.md` for the full task breakdown
2. **Key files to modify:**
   - `backend/src/campaign/auth.py` (new) — OAuth2 flow, token management
   - `backend/src/campaign/gmail.py` (new) — Gmail API send operations
   - `backend/src/campaign/routers/auth.py` — add auth endpoints to the existing stub
   - `backend/tests/test_gmail.py` — add Gmail tests to the existing placeholder
3. **Important context:**
   - The `credentials/` directory is where `credentials.json` (OAuth client secret) and `token.json` (user token) live
   - `config.py` already has `credentials_dir` and `gmail_scopes` settings
   - The auth router stub already exists at `routers/auth.py` — just add endpoints to it
   - All Gmail API calls must be mocked in tests
4. **Running commands:** Always prefix with `export PATH="$HOME/.local/bin:$PATH"` and run from `backend/` directory using `uv run`

## Requirement Changes Applied Post-Phase-1

The following requirement changes were applied after Phase 1 was completed (2026-02-15):

### 1. Split Campaign Spreadsheet into Two Files
- **Before:** Single spreadsheet with columns: recipient_email, recipient_name, send_date, send_time, email_template_ref, plus custom fields
- **After:** Two separate files:
  - **Recipients list** (CSV/XLSX): recipient_email, recipient_name, plus custom columns
  - **Campaign schedule** (CSV/XLSX): send_date, send_time, email_template_ref
- The schedule defines the sequence of emails — every recipient gets the same schedule
- `send_date` supports relative values (integer = days after previous email was sent)
- Models updated: `Campaign.spreadsheet_filename` replaced with `recipients_filename` + `schedule_filename`
- New model: `CampaignScheduleStep` (id, campaign_id, step_order, send_date, relative_days, send_time, email_template_ref)
- New Alembic migration generated
- Example files replaced: `sample_campaign.xlsx` → `sample_recipients.xlsx` + `sample_schedule.xlsx`

### 2. Manual Recipient Addition
- New API endpoint: `POST /api/v1/campaigns/{id}/recipients`
- New schemas: `RecipientCreate`, `RecipientCreateResponse`
- Frontend: "Add Recipient" button + modal on Campaign Detail page (draft campaigns only)

### 3. Reply Detection
- If a recipient replies to any campaign email, all remaining unsent emails for that recipient are cancelled
- New `Email.thread_id` column stores Gmail thread ID from send response
- New `ReplyCheckState` model tracks Gmail History API cursor for incremental sync
- New scheduler job `check_replies_job()` runs periodically (configurable interval, default 15 min)
- New config setting: `reply_check_interval_minutes`

## File Tree (Backend)

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
│       ├── config.py
│       ├── database.py
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       └── routers/
│           ├── __init__.py
│           ├── auth.py
│           ├── campaigns.py
│           ├── emails.py
│           └── recipients.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_campaigns.py
    ├── test_gmail.py
    ├── test_parser.py
    ├── test_scheduler.py
    └── test_templates.py
```
