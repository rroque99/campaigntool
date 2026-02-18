# Phase 4 — Frontend Updates — COMPLETED

## What Was Done

Updated the React frontend to support sender mode display, Playwright session management, conditional UI sections, and warning banners when reply monitoring is unavailable.

### Modified Files

1. **`frontend/src/types/index.ts`** — Added `SendBackend` type union (`"gmail_api" | "playwright"`). Extended `AuthStatus` with:
   - `send_backend: SendBackend`
   - `reply_monitoring_enabled: boolean`
   - `playwright_session_active: boolean`
   - `playwright_session_email: string | null`
   - Added new `PlaywrightStatus` interface (`session_active`, `email`, `last_verified`)

2. **`frontend/src/api/campaigns.ts`** — Added two new hooks:
   - `usePlaywrightStatus()` — `GET /auth/playwright/status`, returns `PlaywrightStatus`
   - `usePlaywrightLogin()` — `POST /auth/playwright/login`, mutation that invalidates auth queries on success

3. **`frontend/src/pages/Settings.tsx`** — Major restructure:
   - New "Email Sender" section at top showing current sender mode (Gmail API or Playwright)
   - Gmail Connection section only shown when `send_backend === "gmail_api"`
   - New Playwright Session section shown when `send_backend === "playwright"`:
     - Green dot + email when session active, with "Re-login" button
     - Gray dot + "No active session" when inactive, with "Open Gmail Login" button
   - Reply monitoring unavailable warning banner in Playwright mode
   - Send Quota section only shown in Gmail API mode
   - Toast on Playwright login launch telling user to complete login in the browser window

4. **`frontend/src/pages/CampaignDetail.tsx`** — Added:
   - `useAuthStatus()` hook call
   - Blue info banner when `reply_monitoring_enabled === false`: "Automatic reply detection is disabled..."
   - Red warning banner when Playwright session expired and campaign is paused/failed: "Gmail session expired. Go to Settings to re-login and resume sending."

5. **`frontend/src/pages/Dashboard.tsx`** — Added:
   - Sender mode pill badge next to "Dashboard" heading (shows "Gmail API" or "Playwright")
   - "Connect Gmail to get started" link now only shown in gmail_api mode
   - Amber warning link when Playwright mode active but session inactive: "Playwright session not active — campaigns cannot send emails"

## Test Results

- **TypeScript**: Compiles with zero errors (`tsc --noEmit`)
- **ESLint**: 0 errors, 2 pre-existing warnings (TanStack Table compatibility)
- **Vite build**: Succeeds, all modules transformed
- **Backend tests**: 142 passed, 1 pre-existing failure (`test_add_to_non_draft_blocked`) — unrelated to Phase 4

## UI Behavior Summary

### Gmail API mode (default)
- Settings: Shows Gmail Connection + Daily Send Quota sections (unchanged from v1)
- Dashboard: Shows "Gmail API" pill, "Connect Gmail" link if not authenticated
- Campaign Detail: No extra banners (reply monitoring is active)

### Playwright mode
- Settings: Shows "Playwright (Browser Automation)" mode, Playwright Session section with login button, reply monitoring warning
- Dashboard: Shows "Playwright" pill, amber warning if session not active
- Campaign Detail: Blue banner about reply detection being disabled. Red banner if session expired and campaign paused/failed, with link to Settings

## Commands

```bash
cd frontend
npx tsc --noEmit                    # Type check
npx eslint src/                     # Lint
npx vite build                      # Production build

cd backend
export PATH="$HOME/.local/bin:$PATH"
uv run pytest -v                    # Backend tests
```

## Branch

All work is on branch `feature/playwright-sender`.

## Continuation Instructions

When this phase is complete, the next agent should implement Phase 5 (Testing & Documentation) as defined in `docs/plan/v2/phase-5-testing.md`. Also look at the detailed tasks for the next phase in docs/plan/v2/tasks for more details. When that phase is complete, create a `phase-5-completed.md` document in `docs/plan/v2/` containing relevant context for the next agent to complete the following phase. Include this same instruction in the completed document so the pattern continues without the user needing to repeat the request.
