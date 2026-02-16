# Phase 1 — Project Scaffolding & Infrastructure

**Goal:** Set up the complete project skeleton, tooling, database layer, and development environment so all subsequent phases can build on a solid foundation.

**Dependencies:** None

---

## Tasks

### Task 1.1 — Initialize Git Repository & Project Root

**Priority:** High
**Estimated Effort:** Small

- Initialize a Git repository at the project root
- Create `.gitignore` with entries for:
  - `credentials/` (OAuth secrets)
  - `.venv/` (Python virtual environment)
  - `__pycache__/`, `*.pyc`, `.pytest_cache/`
  - `node_modules/`, `dist/`
  - `.env`, `*.db`, `*.sqlite`
  - `.vite/`, `.ruff_cache/`
- Create the top-level directory structure:
  ```
  backend/
  frontend/
  credentials/.gitkeep
  examples/
  docs/
  ```
- Add `README.md` with basic project description and setup instructions

**Acceptance Criteria:**
- `git init` complete, `.gitignore` covers all sensitive/generated files
- Directory skeleton exists

---

### Task 1.2 — Backend Python Project Setup

**Priority:** High
**Estimated Effort:** Medium

- Create `backend/pyproject.toml` with:
  - Project metadata (name: `gmail-campaign-tool`, version: `0.1.0`, python: `>=3.11`)
  - Dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `pydantic`, `pydantic-settings`, `google-api-python-client`, `google-auth-oauthlib`, `openpyxl`, `python-docx`, `markdown`, `apscheduler`, `python-multipart`
  - Dev dependencies: `pytest`, `pytest-mock`, `pytest-asyncio`, `httpx`, `ruff`
  - Ruff configuration (line-length: 100, target: py311)
- Create the source package structure:
  ```
  backend/src/campaign/__init__.py
  backend/src/campaign/routers/__init__.py
  ```
- Install dependencies with uv: `cd backend && uv sync`

**Acceptance Criteria:**
- `uv sync` completes without errors (creates `.venv/` and installs all dependencies)
- `uv run ruff check src/` runs (no files to lint yet, exits 0)
- `uv run pytest` runs (no tests yet, exits 0)

---

### Task 1.3 — Database Layer (SQLAlchemy + Alembic)

**Priority:** High
**Estimated Effort:** Medium

- Create `backend/src/campaign/database.py`:
  - SQLAlchemy engine pointing to `campaign.db` (configurable via settings)
  - `SessionLocal` session factory
  - `Base` declarative base
  - `get_db()` dependency for FastAPI
- Create `backend/src/campaign/models.py` with ORM models:
  - **Campaign:** `id`, `name`, `description`, `spreadsheet_filename`, `status` (enum: draft, scheduled, in_progress, paused, completed, failed), `created_at`, `updated_at`
  - **Recipient:** `id`, `campaign_id` (FK), `email`, `name`, `custom_fields` (JSON), `created_at`
  - **Email:** `id`, `campaign_id` (FK), `recipient_id` (FK), `subject`, `body_html`, `body_text`, `scheduled_at`, `sent_at`, `status` (enum: pending, scheduled, sent, failed, cancelled), `error_message`, `gmail_message_id`
- Initialize Alembic: `uv run alembic init alembic`
  - Configure `alembic.ini` to use the same DB path
  - Update `env.py` to import `Base.metadata`
- Generate and apply the initial migration

**Acceptance Criteria:**
- `uv run alembic upgrade head` creates the three tables in SQLite
- `uv run alembic downgrade base` cleanly removes them
- Models have proper relationships (Campaign -> Recipients, Campaign -> Emails, Recipient -> Emails)

---

### Task 1.4 — Configuration Module

**Priority:** High
**Estimated Effort:** Small

- Create `backend/src/campaign/config.py`:
  - Use `pydantic-settings` `BaseSettings` class
  - Settings:
    - `database_url`: default `sqlite:///./campaign.db`
    - `credentials_dir`: default `../credentials` (pathlib.Path)
    - `cors_origins`: default `["http://localhost:5173"]`
    - `gmail_scopes`: default `["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]`
    - `daily_send_limit`: default `500`
    - `api_prefix`: default `/api/v1`
  - Load from environment variables and/or `.env` file

**Acceptance Criteria:**
- Settings can be imported and used throughout the backend
- Values can be overridden via environment variables
- Test that default values are correct

---

### Task 1.5 — FastAPI Application Shell

**Priority:** High
**Estimated Effort:** Small

- Create `backend/src/campaign/main.py`:
  - FastAPI app with metadata (title, version, description)
  - Lifespan context manager (placeholder for scheduler start/stop)
  - CORS middleware configured from settings
  - Include router stubs for: `auth`, `campaigns`, `recipients`, `emails`
  - Health check endpoint: `GET /api/v1/health` returning `{"status": "ok"}`
- Create router stub files under `backend/src/campaign/routers/`:
  - `auth.py` — empty router with prefix `/auth`
  - `campaigns.py` — empty router with prefix `/campaigns`
  - `recipients.py` — empty router with prefix `/recipients`
  - `emails.py` — empty router with prefix `/emails`

**Acceptance Criteria:**
- `uv run uvicorn src.campaign.main:app --port 8000` starts without errors
- `GET /api/v1/health` returns `{"status": "ok"}`
- CORS headers present for `localhost:5173`
- Swagger docs available at `/docs`

---

### Task 1.6 — Pydantic Schemas

**Priority:** Medium
**Estimated Effort:** Medium

- Create `backend/src/campaign/schemas.py` with request/response models:
  - **CampaignCreate:** `name`, `description` (optional)
  - **CampaignResponse:** `id`, `name`, `description`, `status`, `spreadsheet_filename`, `created_at`, `updated_at`, `recipient_count`, `sent_count`, `failed_count`
  - **CampaignListResponse:** list of `CampaignResponse`
  - **RecipientResponse:** `id`, `email`, `name`, `custom_fields`, `email_status`
  - **RecipientListResponse:** paginated list with `total`, `page`, `page_size`, `items`
  - **EmailPreviewResponse:** `recipient_email`, `recipient_name`, `subject`, `body_html`
  - **ScheduleRequest:** `send_date` (optional override), `send_time` (optional override)
  - **AuthStatusResponse:** `authenticated` (bool), `email` (optional str)
  - **ErrorResponse:** `detail` (str)

**Acceptance Criteria:**
- All schemas validate correctly with sample data
- Response models can serialize from ORM models (use `model_config = ConfigDict(from_attributes=True)`)

---

### Task 1.7 — Test Infrastructure

**Priority:** Medium
**Estimated Effort:** Small

- Create `backend/tests/conftest.py` with fixtures:
  - In-memory SQLite database for tests
  - `test_db` fixture: creates tables, yields session, tears down
  - `test_client` fixture: FastAPI `TestClient` (httpx) with overridden DB dependency
  - `sample_campaign_data` fixture: dict with valid campaign creation data
- Create placeholder test files:
  - `test_campaigns.py`
  - `test_parser.py`
  - `test_gmail.py`
  - `test_scheduler.py`
  - `test_templates.py`
- Add one smoke test: `test_health_check` — verifies `GET /api/v1/health` returns 200

**Acceptance Criteria:**
- `uv run pytest -v` passes with the smoke test
- Test database is isolated (in-memory, no file artifacts)
- Fixtures are reusable across all test files

---

### Task 1.8 — Frontend Project Setup

**Priority:** Medium
**Estimated Effort:** Medium

- Scaffold React project with Vite: `npm create vite@latest frontend -- --template react-ts`
- Install dependencies:
  - `tailwindcss`, `@tailwindcss/vite`
  - `react-router-dom`
  - `@tanstack/react-query`
  - `@tanstack/react-table`
  - `axios`
- Configure:
  - Tailwind CSS (tailwind.config.js, add to CSS)
  - Vite proxy: `/api` -> `http://localhost:8000`
  - TypeScript strict mode
- Create basic directory structure:
  ```
  frontend/src/api/
  frontend/src/pages/
  frontend/src/components/
  frontend/src/types/
  ```
- Create `frontend/src/types/index.ts` with TypeScript types mirroring backend schemas
- Verify: `npm run dev` starts, `npm run build` succeeds

**Acceptance Criteria:**
- Vite dev server runs on port 5173
- Tailwind CSS utility classes work
- API proxy forwards `/api/*` to `localhost:8000`
- TypeScript compiles with strict mode

---

### Task 1.9 — Example Files

**Priority:** Low
**Estimated Effort:** Small

- Create `examples/sample_campaign.xlsx`:
  - Columns: `recipient_email`, `recipient_name`, `send_date`, `send_time`, `email_template_ref`, `company`, `role`
  - 5 sample rows with realistic but fake data
- Create `examples/sample_emails.md`:
  - 2 email templates separated by `---`
  - Each with frontmatter containing `subject` line
  - Body using `{{recipient_name}}`, `{{company}}`, `{{role}}` template variables

**Acceptance Criteria:**
- Sample spreadsheet opens correctly in Excel/LibreOffice
- Sample email templates parse correctly (tested manually or in Phase 3)
