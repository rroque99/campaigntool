# Phase 4 — Frontend Updates

## Goal

Update the React frontend to support sender mode selection, Playwright session management, and display appropriate warnings when reply monitoring is unavailable.

## Tasks

### Task 4.1 — Update TypeScript types

**File:** `frontend/src/types/index.ts`

Add/update types to reflect the new backend responses:

```typescript
interface AuthStatus {
  authenticated: boolean;
  email: string | null;
  send_backend: "gmail_api" | "playwright";
  reply_monitoring_enabled: boolean;
  playwright_session_active: boolean;
  playwright_session_email: string | null;
}

interface PlaywrightStatus {
  session_active: boolean;
  email: string | null;
  last_verified: string | null;
}
```

### Task 4.2 — Add Playwright API hooks

**File:** `frontend/src/api/campaigns.ts`

Add React Query hooks:

```typescript
// Check Playwright session status
export function usePlaywrightStatus() { ... }

// Trigger Playwright login (opens browser)
export function usePlaywrightLogin() { ... }
```

### Task 4.3 — Update Settings page — Sender Mode section

**File:** `frontend/src/pages/Settings.tsx`

Add a new "Email Sender" section at the top of the Settings page:

1. **Display current sender mode**: Show whether the app is using "Gmail API" or "Playwright (Browser Automation)" — this is read from the backend config, not user-togglable at runtime (requires env var / restart).

2. **For Gmail API mode** (existing behavior):
   - Show the current Gmail connection section (unchanged)
   - Show the quota section (unchanged)

3. **For Playwright mode**:
   - Show Playwright session status (active/inactive, email if known)
   - "Open Gmail Login" button — calls `POST /auth/playwright/login` which launches the browser window for the user to log in
   - Warning banner: "Reply monitoring is not available in Playwright mode. Recipients who reply will not have their remaining emails automatically cancelled."

### Task 4.4 — Update Settings page — conditional sections

When `send_backend == "playwright"`:
- Hide the Gmail API OAuth connection section (not needed)
- Hide the Gmail quota section (no API quota applies)
- Show the Playwright session section instead

When `send_backend == "gmail_api"`:
- Show existing OAuth and quota sections (unchanged)
- Hide Playwright section

### Task 4.5 — Add reply monitoring warning on Campaign Detail page

**File:** `frontend/src/pages/CampaignDetail.tsx`

When `reply_monitoring_enabled == false` (from auth status), show an info banner on the campaign detail page:

> "Automatic reply detection is disabled. Emails will not be automatically cancelled if recipients reply. You can manually cancel individual recipients from the recipient list."

### Task 4.6 — Update Dashboard stats

**File:** `frontend/src/pages/Dashboard.tsx`

- Show the current sender mode in the dashboard header or sidebar (small indicator)
- If Playwright mode and session is not active, show a warning: "Playwright session not active — campaigns cannot send emails"

### Task 4.7 — Handle Playwright session expiry in UI

When a campaign fails because of a Playwright session expiry:
- The campaign status will show as `paused` or `failed` with an error message from the backend
- Display a clear call-to-action: "Gmail session expired. Go to Settings to re-login."
- The Settings page "Open Gmail Login" button re-establishes the session

## Deliverables

- Updated TypeScript types
- New React Query hooks for Playwright endpoints
- Updated Settings page with conditional sender sections
- Warning banners on Campaign Detail and Dashboard
- Session expiry handling in the UI
