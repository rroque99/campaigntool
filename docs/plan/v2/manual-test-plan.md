# Manual Test Plan — Playwright Sender Mode

## Prerequisites

- Python 3.11+ with `uv` installed
- Node.js 18+ with `npm`
- Gmail account for testing (use a test account, not production)

## Setup

1. Install backend dependencies with Playwright extra:
   ```bash
   cd backend
   uv sync --extra dev
   uv run playwright install chromium
   ```

2. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

3. Create `.env` file in `backend/`:
   ```
   SEND_BACKEND=playwright
   PLAYWRIGHT_SEND_DELAY_SECONDS=10
   DAILY_SEND_LIMIT=50
   ```

## Test 1: Verify Settings Page Shows Playwright Mode

1. Start backend: `cd backend && uv run uvicorn src.campaign.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173/settings`
4. **Expected:**
   - "Email Sender" section shows "Playwright (Browser Automation)"
   - "Playwright Session" section shows "No active session"
   - "Open Gmail Login" button is visible
   - Gmail Connection and Daily Send Quota sections are NOT shown
   - Amber banner: "Reply monitoring is not available in Playwright mode..."

## Test 2: First-Time Login Flow

1. On the Settings page, click "Open Gmail Login"
2. **Expected:** A Chromium browser window opens and navigates to Gmail
3. Log in to Gmail in the browser (complete 2FA if prompted)
4. After login, return to the Settings page and refresh
5. **Expected:**
   - Session status changes to "Session active (your-email@gmail.com)"
   - Green dot indicator

## Test 3: Dashboard Indicators

1. Navigate to `http://localhost:5173/`
2. **Expected:**
   - "Playwright" pill badge next to "Dashboard" heading
   - If session is not active: amber warning "Playwright session not active..."
   - If session is active: no warning

## Test 4: Send a Test Campaign

1. Create a campaign with 2-3 test recipients (use email addresses you can check)
2. Upload a simple recipients CSV and schedule CSV
3. Schedule the campaign
4. **Expected:**
   - Emails are composed and sent via the Gmail web UI in the browser window
   - Campaign progress updates in the UI
   - Recipient email addresses receive the messages

## Test 5: Campaign Detail — Reply Warning

1. Navigate to any campaign detail page
2. **Expected:** Blue info banner: "Automatic reply detection is disabled..."

## Test 6: Session Persistence Across Restarts

1. Stop the backend server (Ctrl+C)
2. Restart it: `cd backend && uv run uvicorn src.campaign.main:app --reload --port 8000`
3. Open Settings page
4. **Expected:** Session should still show as active (cookies persisted in `credentials/playwright-session/`)

## Test 7: Session Expiry Handling

1. Manually clear the `credentials/playwright-session/` directory
2. Attempt to schedule or resume a campaign
3. **Expected:**
   - Campaign transitions to paused/failed state
   - Campaign detail page shows red warning: "Gmail session expired. Go to Settings to re-login."
   - Settings page shows "No active session"
4. Click "Open Gmail Login" and re-authenticate
5. Resume the campaign
6. **Expected:** Sending resumes normally

## Test 8: Gmail API Mode Unaffected

1. Change `.env` to `SEND_BACKEND=gmail_api` (or remove the variable)
2. Restart backend
3. **Expected:**
   - Settings shows Gmail Connection section (OAuth)
   - Settings shows Daily Send Quota section
   - No Playwright sections visible
   - Dashboard shows "Gmail API" pill
   - Campaign detail has no reply monitoring warning

## Test 9: Reply Monitoring Disabled

1. With `SEND_BACKEND=playwright`, start the backend
2. Check server logs
3. **Expected:** Log message: "Reply monitoring disabled for non-API send backend"
4. Verify no `check_replies_job` appears in scheduler logs
