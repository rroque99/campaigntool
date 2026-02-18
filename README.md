# Gmail Email Campaign Tool

Local web application for managing and sending email campaigns via the Gmail API or Playwright browser automation. Built with FastAPI (Python) and React (TypeScript).

## Features

- Upload recipient lists (CSV/XLSX) and email templates (Markdown/DOCX)
- Multi-step campaigns with absolute and relative scheduling
- Email preview with template variable substitution
- Two send backends: **Gmail API** (full-featured) or **Playwright** (browser automation, no API credentials needed)
- Automatic reply detection — remaining emails are cancelled when a recipient replies (Gmail API mode only)
- Quota tracking (Gmail daily send limits)
- Pause, resume, and cancel campaigns in progress
- Single-page React frontend with real-time status updates

## Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **For Gmail API mode**: A Google Cloud project with the Gmail API enabled
- **For Playwright mode**: No Google Cloud project needed — just a Gmail account

## Quick Start

### 1. Set up Gmail OAuth credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select an existing one)
3. Navigate to **APIs & Services > Library**, search for "Gmail API", and enable it
4. Navigate to **APIs & Services > Credentials**
5. Click **Create Credentials > OAuth client ID**
6. Choose **Web application** as the application type
7. Add `http://localhost:8000/api/v1/auth/callback` as an authorized redirect URI
8. Download the JSON file and save it as `credentials/credentials.json`

### 2. Install and start the backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn src.campaign.main:app --reload --port 8000
```

### 3. Install and start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser. Go to **Settings** and connect your Gmail account.

### Alternative: Playwright mode (no API credentials)

If you don't have access to the Gmail API, you can use Playwright to send emails via browser automation.

```bash
cd backend
uv sync --extra dev
uv run playwright install chromium
```

Create a `.env` file in `backend/`:

```
SEND_BACKEND=playwright
```

Start the backend and frontend as above. In the browser, go to **Settings** and click **Open Gmail Login** to authenticate in the Chromium browser window that opens.

> **Note**: Playwright mode requires a visible browser window (Google blocks headless automation). Reply detection is not available in this mode.

### Production (single command)

Build the frontend and serve everything from the backend:

```bash
./start.sh
```

Then open http://localhost:8000.

## Configuration

All settings can be overridden via environment variables or a `.env` file in `backend/`.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./campaign.db` | SQLAlchemy database URL |
| `CREDENTIALS_DIR` | `../credentials` | Path to OAuth credentials directory |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (dev only) |
| `DAILY_SEND_LIMIT` | `500` | Daily email send limit (500 personal, 2000 Workspace) |
| `REPLY_CHECK_INTERVAL_MINUTES` | `2` | How often to check for replies (Gmail API mode only) |
| `ENVIRONMENT` | `development` | Set to `production` to serve frontend from backend |
| `SEND_BACKEND` | `gmail_api` | Send backend: `gmail_api` or `playwright` |
| `PLAYWRIGHT_SEND_DELAY_SECONDS` | `30` | Delay between sends in Playwright mode (avoids abuse detection) |
| `PLAYWRIGHT_PAGE_TIMEOUT_MS` | `15000` | Playwright page action timeout |
| `PLAYWRIGHT_BROWSER` | `chromium` | Browser to use for Playwright |
| `PLAYWRIGHT_SESSION_DIR` | `../credentials/playwright-session` | Persistent browser session directory |

## File Formats

### Recipients file (CSV or XLSX)

Required columns: `recipient_email`, `recipient_name`. Additional columns become template variables.

```csv
recipient_email,recipient_name,company,role
alice@example.com,Alice Smith,Acme Corp,CTO
bob@example.com,Bob Jones,Globex Inc,VP Engineering
```

### Schedule file (CSV or XLSX)

Required columns: `send_date`, `send_time`, `email_template_ref`.

- `send_date`: An absolute date (`2026-03-01`, `03/01/2026`) or a relative integer (days after the previous email was sent to that recipient). The first step **must** use an absolute date.
- `send_time`: Time in `HH:MM`, `HH:MM:SS`, or `HH:MM AM/PM` format (UTC).
- `email_template_ref`: Must match a `ref:` value in the email template document.

```csv
send_date,send_time,email_template_ref
2026-03-01,09:00,intro
5,14:00,followup
```

### Email template document (Markdown or DOCX)

Multiple emails are separated by `---`. Each section starts with frontmatter:

```markdown
ref: intro
subject: Hello {{recipient_name}} from {{company}}

Hi {{recipient_name}},

This is the first email. Any **Markdown** formatting is supported.

---

ref: followup
subject: Following up, {{recipient_name}}

Hi {{recipient_name}},

Just checking in about my previous message.
```

Template variables use `{{variable_name}}` syntax. Values come from the recipient spreadsheet columns.

## API Reference

All endpoints are prefixed with `/api/v1/`. Interactive API docs available at http://localhost:8000/docs when the backend is running.

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/status` | Auth status (includes sender backend info) |
| GET | `/auth/login` | Get OAuth consent URL (Gmail API mode) |
| GET | `/auth/callback` | OAuth callback (automatic redirect) |
| POST | `/auth/logout` | Revoke credentials (Gmail API mode) |
| GET | `/auth/quota` | Daily send quota status |
| GET | `/auth/playwright/status` | Playwright browser session status |
| POST | `/auth/playwright/login` | Launch browser for Gmail login (Playwright mode) |

### Campaigns
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/campaigns` | List all campaigns |
| POST | `/campaigns` | Create campaign (multipart upload) |
| GET | `/campaigns/{id}` | Get campaign details |
| DELETE | `/campaigns/{id}` | Delete campaign (draft/completed/failed only) |
| GET | `/campaigns/{id}/status` | Real-time progress and email counts |
| POST | `/campaigns/{id}/schedule` | Schedule pending emails |
| POST | `/campaigns/{id}/pause` | Pause scheduled/in-progress campaign |
| POST | `/campaigns/{id}/cancel` | Cancel remaining unsent emails |
| GET | `/campaigns/{id}/preview` | Preview emails for first/specific recipient |
| GET | `/campaigns/{id}/preview/all` | Preview all recipient emails |

### Recipients
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/campaigns/{id}/recipients` | Paginated recipient list with search/filter |
| POST | `/campaigns/{id}/recipients` | Add recipient to draft campaign |

### Emails
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/campaigns/{id}/emails` | Paginated email list with status filter |
| GET | `/campaigns/{id}/emails/{email_id}` | Full email detail with delivery metadata |

## Troubleshooting

### "credentials.json not found"
Download your OAuth client credentials from Google Cloud Console and save them to `credentials/credentials.json`.

### "Token refresh failed"
Your OAuth token has expired and cannot be refreshed. Go to Settings and reconnect your Gmail account.

### "Daily send limit reached"
Gmail limits personal accounts to 500 sends/day (2000 for Google Workspace). Emails will be automatically rescheduled for the next day. Adjust the `DAILY_SEND_LIMIT` setting if you have a Workspace account.

### OAuth callback error
Make sure `http://localhost:8000/api/v1/auth/callback` is listed as an authorized redirect URI in your Google Cloud Console OAuth client settings.

### Playwright: "Gmail session expired"
Your browser session cookies have expired. Go to **Settings** and click **Open Gmail Login** to re-authenticate.

### Playwright: browser doesn't open
Make sure you've installed the browser: `cd backend && uv run playwright install chromium`. Playwright mode requires a display — it won't work in headless server environments.

### CORS errors in development
The frontend dev server (port 5173) proxies API requests to the backend (port 8000). Make sure both servers are running. If you see CORS errors, verify that `CORS_ORIGINS` includes `http://localhost:5173`.

## Development

### Backend commands
```bash
cd backend
uv run pytest -v              # Run tests
uv run ruff check src/ tests/ # Lint
uv run ruff format src/ tests/ # Format
uv run alembic upgrade head    # Run migrations
uv run alembic revision --autogenerate -m "description"  # New migration
```

### Frontend commands
```bash
cd frontend
npm run dev    # Dev server (port 5173)
npm run build  # Production build
npm run lint   # Lint
```

## Project Structure

See [CLAUDE.md](CLAUDE.md) for the full project layout, architecture decisions, and database schema.
