# Gmail Email Campaign Tool

Local web application for managing and sending email campaigns via the Gmail API or Playwright browser automation. Built with a FastAPI (Python) backend and React (TypeScript) frontend with Tailwind CSS.

Campaigns are defined by uploading spreadsheets (CSV/XLSX) containing recipients and referencing email content documents. The web UI presents campaign dashboards, email previews, scheduling controls, and delivery status tracking. Emails are scheduled and sent at specified times using APScheduler running within the FastAPI process, since the Gmail API does not expose Gmail's native "schedule send" feature.

## Tech Stack

### Backend (Python 3.11+)
- **Package manager:** uv (manages venv, dependencies, and lockfile)
- **Framework:** FastAPI with Uvicorn
- **Gmail integration:** google-api-python-client, google-auth-oauthlib
- **Browser automation (optional):** playwright (alternative sender backend)
- **Spreadsheet parsing:** openpyxl for .xlsx, built-in csv module for .csv
- **Document parsing:** python-docx for .docx email templates, or Markdown via markdown lib
- **Scheduling:** APScheduler (BackgroundScheduler, runs inside the FastAPI process)
- **Database:** SQLite via SQLAlchemy (local app, no need for Postgres)
- **Data validation:** Pydantic models for all API request/response schemas
- **Testing:** pytest, pytest-mock, httpx (for async test client)
- **Linting:** ruff

### Frontend (TypeScript)
- **Framework:** React 18 with Vite
- **Styling:** Tailwind CSS
- **HTTP client:** Axios or fetch with React Query (TanStack Query) for server state
- **Routing:** React Router
- **Table/data display:** TanStack Table for campaign and recipient lists

## Project Layout

```
gmail-campaign-tool/
├── CLAUDE.md
├── README.md
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── src/
│   │   └── campaign/
│   │       ├── __init__.py
│   │       ├── main.py              # FastAPI app, lifespan (scheduler start/stop), CORS
│   │       ├── config.py            # Settings via pydantic-settings (ports, db path, etc.)
│   │       ├── auth.py              # Gmail OAuth2 flow + token management
│   │       ├── gmail.py             # Gmail API reply detection + quota (send logic extracted)
│   │       ├── sender.py            # SendBackend protocol + SendError/SendResult types
│   │       ├── gmail_sender.py      # Gmail API sender (implements SendBackend)
│   │       ├── playwright_sender.py # Playwright browser automation sender (implements SendBackend)
│   │       ├── sender_factory.py    # Factory: returns sender based on config (singleton)
│   │       ├── parser.py            # Spreadsheet + document parsing
│   │       ├── scheduler.py         # APScheduler job management (uses sender_factory)
│   │       ├── models.py            # SQLAlchemy ORM models
│   │       ├── schemas.py           # Pydantic request/response schemas
│   │       ├── templates.py         # Email template rendering (variable substitution)
│   │       ├── database.py          # SQLAlchemy engine, session factory
│   │       └── routers/
│   │           ├── __init__.py
│   │           ├── campaigns.py     # CRUD + status endpoints for campaigns
│   │           ├── recipients.py    # Recipient list and per-recipient status
│   │           ├── emails.py        # Email preview, send, and delivery status
│   │           └── auth.py          # OAuth flow initiation + callback
│   └── tests/
│       ├── conftest.py
│       ├── test_campaigns.py
│       ├── test_config.py
│       ├── test_gmail.py
│       ├── test_gmail_sender.py
│       ├── test_parser.py
│       ├── test_playwright_sender.py
│       ├── test_scheduler.py
│       ├── test_sender.py
│       └── test_templates.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                     # Axios/fetch client + React Query hooks
│       │   └── campaigns.ts
│       ├── pages/
│       │   ├── Dashboard.tsx        # Overview: active campaigns, upcoming sends, stats
│       │   ├── CampaignList.tsx     # All campaigns with status indicators
│       │   ├── CampaignDetail.tsx   # Single campaign: recipients, schedule, delivery log
│       │   ├── CampaignCreate.tsx   # Upload spreadsheet, configure, preview
│       │   └── Settings.tsx         # Sender mode, Gmail/Playwright auth, preferences
│       ├── components/
│       │   ├── Layout.tsx           # Sidebar nav + main content area
│       │   ├── StatusBadge.tsx      # Reusable status indicator (draft/scheduled/sent/failed)
│       │   ├── RecipientTable.tsx   # Sortable/filterable recipient list
│       │   ├── EmailPreview.tsx     # Rendered email preview with template variables filled
│       │   ├── FileUpload.tsx       # Drag-and-drop spreadsheet upload
│       │   ├── ErrorBoundary.tsx    # React error boundary with retry
│       │   └── Toast.tsx            # Toast notification system with context provider
│       ├── utils/
│       │   └── dates.ts             # parseUTC() helper for API timestamp handling
│       └── types/
│           └── index.ts             # TypeScript types mirroring backend schemas
├── examples/
│   ├── sample_recipients.xlsx
│   ├── sample_schedule.xlsx
│   └── sample_emails.md
└── credentials/                     # .gitignore'd — OAuth client secrets here
    └── .gitkeep
```

## Key Commands

### Backend
- Install uv (if not present): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Install: `cd backend && uv sync`
- Install with Playwright support: `cd backend && uv sync --extra dev && uv run playwright install chromium`
- Run dev server: `cd backend && uv run uvicorn src.campaign.main:app --reload --port 8000`
- Run tests: `cd backend && uv run pytest -v`
- Lint: `cd backend && uv run ruff check src/ tests/`
- Format: `cd backend && uv run ruff format src/ tests/`
- Migrations: `cd backend && uv run alembic upgrade head`
- New migration: `cd backend && uv run alembic revision --autogenerate -m "description"`

### Frontend
- Install: `cd frontend && npm install`
- Run dev server: `cd frontend && npm run dev` (runs on port 5173, proxies API to 8000)
- Build: `cd frontend && npm run build`
- Lint: `cd frontend && npm run lint`

## API Design

All endpoints prefixed with `/api/v1/`. Key routes:

- `GET /api/v1/auth/status` — Check auth status (includes sender backend info, Playwright session)
- `GET /api/v1/auth/login` — Initiate OAuth flow (redirects to Google)
- `GET /api/v1/auth/callback` — OAuth callback handler
- `GET /api/v1/auth/playwright/status` — Check Playwright browser session status
- `POST /api/v1/auth/playwright/login` — Launch Playwright browser for Gmail login
- `GET /api/v1/auth/quota` — Daily send quota status
- `GET /api/v1/campaigns` — List all campaigns with summary stats
- `POST /api/v1/campaigns` — Create campaign (multipart: spreadsheet upload + config)
- `GET /api/v1/campaigns/{id}` — Campaign detail with recipient statuses
- `POST /api/v1/campaigns/{id}/schedule` — Schedule all pending emails
- `POST /api/v1/campaigns/{id}/pause` — Pause scheduled sends
- `POST /api/v1/campaigns/{id}/cancel` — Cancel remaining unsent emails
- `GET /api/v1/campaigns/{id}/preview` — Preview rendered emails before sending
- `GET /api/v1/campaigns/{id}/recipients` — Paginated recipient list with delivery status
- `POST /api/v1/campaigns/{id}/recipients` — Add a recipient manually (any non-terminal status; auto-schedules for active campaigns)

## Database Schema (SQLite)

**campaigns:** id, name, description, recipients_filename, schedule_filename, status (draft|scheduled|in_progress|paused|completed|failed), created_at, updated_at

**recipients:** id, campaign_id (FK), email, name, custom_fields (JSON), created_at

**emails:** id, campaign_id (FK), recipient_id (FK), subject, body_html, body_text, scheduled_at (UTC), sent_at, status (pending|scheduled|sent|failed|cancelled), error_message, gmail_message_id, thread_id, step_order

**campaign_schedule_steps:** id, campaign_id (FK), step_order, send_date (nullable — absolute date), relative_days (nullable — days after previous email sent), send_time, email_template_ref

**campaign_email_templates:** id, campaign_id (FK), template_ref, subject, body_html, body_text — stores raw email template content (with `{{variable}}` placeholders) so new recipients added after campaign creation can have their emails properly rendered

**reply_check_state:** id, last_checked_at, history_id (Gmail History API cursor for incremental sync)

Use Alembic for all schema migrations. Never modify the database schema without a migration.

## Architecture Decisions

- **Sender abstraction**: Email sending uses a `SendBackend` protocol (in `sender.py`). Two implementations: `GmailAPISender` (Gmail API) and `PlaywrightSender` (browser automation). The `sender_factory` returns a singleton based on the `SEND_BACKEND` env var (`gmail_api` or `playwright`). The scheduler uses `get_sender()` to send emails.
- **Playwright sender mode**: Alternative for users without Gmail API access. Automates the Gmail web UI via a headed Chromium browser. Session cookies persist in `credentials/playwright-session/`. Google blocks headless browsers, so the browser must be visible. Reply detection is NOT supported in Playwright mode — the reply monitor job is not started. `SendResult` returns empty `message_id`/`thread_id` since these can't be extracted from the web UI.
- **Playwright settings**: `SEND_BACKEND` (default: `gmail_api`), `PLAYWRIGHT_SEND_DELAY_SECONDS` (default: 30), `PLAYWRIGHT_PAGE_TIMEOUT_MS` (default: 15000), `PLAYWRIGHT_BROWSER` (default: `chromium`), `PLAYWRIGHT_SESSION_DIR` (default: `../credentials/playwright-session`)
- Keep Gmail API calls isolated in `gmail.py` — all other modules work with Pydantic schemas and SQLAlchemy models, never raw API responses
- OAuth credentials (credentials.json, token.json) live in `credentials/` and are .gitignore'd — NEVER commit these
- The backend serves only JSON API responses; the React frontend is a separate dev server in development and static files served by FastAPI in production
- Campaigns use two input files: a **recipients list** (CSV/XLSX with columns: recipient_email, recipient_name, plus custom columns) and a **campaign schedule** (CSV/XLSX with columns: send_date, send_time, email_template_ref). The schedule defines the sequence of emails — every recipient gets the same schedule. `send_date` supports relative values (e.g., `5` = 5 days after the previous email was sent to that recipient); the first step must use an absolute date.
- Email content documents contain multiple emails separated by `---` with frontmatter for subject line
- Template variables use `{{variable_name}}` syntax, populated from spreadsheet columns
- APScheduler runs within the FastAPI lifespan — jobs persist in a separate SQLite database (`scheduler_jobs.db`) to avoid write contention with the main app database
- Frontend polls campaign status via React Query with a 10-second refetch interval (no websockets needed for MVP)
- Schedule times in CSV files are interpreted as the system's local timezone, then converted to UTC for storage. All timestamps stored as UTC in the database; frontend uses `parseUTC()` helper (in `frontend/src/utils/dates.ts`) to correctly interpret API timestamps as UTC before converting to local timezone for display
- Gmail API daily sending limits apply (500/day personal, 2000/day Workspace) — backend tracks daily send count and warns/blocks when approaching limit
- Relative send dates are resolved lazily at send time — when step N completes for a recipient, the next relative-date step's `scheduled_at` is calculated from the actual `sent_at` timestamp
- Reply detection uses the Gmail History API (`history.list`) to detect replies to campaign threads. A periodic job (`check_replies_job`) runs every `reply_check_interval_minutes` (default 2). When a reply is detected for a recipient's thread, all remaining unsent emails for that recipient are cancelled
- Recipients can be added to a campaign at any time (draft, scheduled, in_progress, or paused). When adding to an active campaign, emails are rendered from stored templates (`campaign_email_templates` table) with the new recipient's variables and automatically scheduled. The Add Recipient modal dynamically shows custom field inputs (e.g., company, role) based on existing recipients' custom_fields
- The main SQLite database uses WAL mode and a 30-second busy timeout to handle concurrent access

## Important Constraints

- NEVER store or log email content containing personal data beyond what's needed for sending
- All Gmail API interactions require the `gmail.send` and `gmail.readonly` scopes
- Token refresh must be handled gracefully — if token.json is expired, re-trigger OAuth flow and surface status in the UI
- Use `email.mime` from stdlib to construct messages (MIMEMultipart, MIMEText)
- CORS must be configured to allow frontend dev server (localhost:5173) to reach backend (localhost:8000)
- File uploads are validated server-side — reject recipients files with missing required columns or invalid emails; reject schedule files with missing columns, invalid dates/times, or non-numeric relative days
- Use pathlib for all file path operations

## Testing

- Mock all Gmail API calls and Playwright objects in tests — never hit real APIs or launch real browsers
- Use httpx.AsyncClient as the FastAPI test client
- Use fixtures for sample campaign spreadsheets and email templates
- Test edge cases: missing columns, empty rows, invalid email addresses, past send dates, OAuth token expiry
- Run `uv run pytest -v` before committing any changes
- Frontend: no test framework required for MVP, but keep components small and testable
