# Phase 5 — Frontend Application

**Goal:** Build the full React frontend with all pages, components, and API integration for managing campaigns through a web UI.

**Dependencies:** Phase 3 (campaign CRUD API), partial Phase 4 (scheduling endpoints)

---

## Tasks

### Task 5.1 — App Shell & Routing

**Priority:** High
**Estimated Effort:** Small

- Set up `frontend/src/App.tsx`:
  - React Router with routes:
    - `/` — Dashboard
    - `/campaigns` — Campaign list
    - `/campaigns/new` — Create campaign
    - `/campaigns/:id` — Campaign detail
    - `/settings` — Settings (auth management)
  - Wrap app in `QueryClientProvider` (React Query)
- Create `frontend/src/components/Layout.tsx`:
  - Sidebar navigation with links to Dashboard, Campaigns, Settings
  - Active route highlighting
  - Main content area with responsive layout
  - App title/logo at top of sidebar
- Style with Tailwind CSS — clean, professional, minimal design

**Acceptance Criteria:**
- All routes render their respective page components
- Sidebar navigation works with active state
- Layout is responsive (sidebar collapses on mobile)
- React Query provider is configured with 10-second default refetch interval

---

### Task 5.2 — API Client & React Query Hooks

**Priority:** High
**Estimated Effort:** Medium

- Create `frontend/src/api/client.ts`:
  - Axios instance with base URL `/api/v1`
  - Response interceptor for error handling
- Create `frontend/src/api/campaigns.ts`:
  - `useAuthStatus()` — query hook for `GET /auth/status`
  - `useCampaigns(filters?)` — query hook for `GET /campaigns`
  - `useCampaign(id)` — query hook for `GET /campaigns/:id`
  - `useCreateCampaign()` — mutation hook for `POST /campaigns`
  - `useScheduleCampaign()` — mutation hook for `POST /campaigns/:id/schedule`
  - `usePauseCampaign()` — mutation hook for `POST /campaigns/:id/pause`
  - `useCancelCampaign()` — mutation hook for `POST /campaigns/:id/cancel`
  - `useRecipients(campaignId, params)` — query hook for `GET /campaigns/:id/recipients`
  - `useEmailPreview(campaignId, recipientId?)` — query hook for `GET /campaigns/:id/preview`
  - `useSendQuota()` — query hook for `GET /auth/quota`
- Configure automatic refetching for active campaigns (10-second interval)

**Acceptance Criteria:**
- All API endpoints are covered by React Query hooks
- Loading, error, and success states are handled
- Cache invalidation triggers on mutations (e.g., creating a campaign refreshes the list)
- Refetch interval is active for campaign detail when status is `scheduled` or `in_progress`

---

### Task 5.3 — Dashboard Page

**Priority:** Medium
**Estimated Effort:** Medium

- Create `frontend/src/pages/Dashboard.tsx`:
  - Summary cards at the top:
    - Total campaigns
    - Active campaigns (scheduled + in_progress)
    - Emails sent today (from quota endpoint)
    - Daily quota remaining
  - Recent campaigns section:
    - Last 5 campaigns with status badges, progress bars, and quick action links
  - Upcoming sends section:
    - Next 10 scheduled emails with recipient, subject, and scheduled time
  - Empty state when no campaigns exist (with CTA to create one)

**Acceptance Criteria:**
- Dashboard loads data from API and displays accurately
- Summary stats update on refetch
- Clicking a campaign navigates to its detail page
- Empty state guides new users

---

### Task 5.4 — Campaign List Page

**Priority:** High
**Estimated Effort:** Medium

- Create `frontend/src/pages/CampaignList.tsx`:
  - Table using TanStack Table with columns:
    - Name (linked to detail page)
    - Status (with `StatusBadge` component)
    - Recipients (count)
    - Sent / Total (progress)
    - Created date
    - Actions (view, delete)
  - Status filter tabs or dropdown: All, Draft, Scheduled, In Progress, Completed, Failed
  - Sort by name, status, created date, progress
  - "Create Campaign" button in header
  - Delete confirmation dialog for draft/completed/failed campaigns

**Acceptance Criteria:**
- Campaign table renders with correct data
- Filtering and sorting work
- Status badges show correct colors/styles per status
- Delete only available for deletable statuses
- Table handles empty state

---

### Task 5.5 — Campaign Creation Page

**Priority:** High
**Estimated Effort:** Large

- Create `frontend/src/pages/CampaignCreate.tsx` — multi-step form:
  - **Step 1 — Campaign Info:**
    - Campaign name (required)
    - Description (optional)
  - **Step 2 — Upload Files:**
    - Drag-and-drop file upload component (`FileUpload.tsx`) for recipients file (CSV/XLSX)
    - Drag-and-drop file upload for campaign schedule file (CSV/XLSX)
    - Drag-and-drop file upload for email template document (MD/DOCX)
    - Show file name and size after selection
    - Client-side validation: file type check, size limit (10MB)
  - **Step 3 — Review & Preview:**
    - Show parsed recipient count and any warnings/errors from the server
    - Show detected email templates with subjects
    - Email preview panel: select a recipient to see their rendered email
    - Use the `EmailPreview` component
  - **Step 4 — Confirm:**
    - Summary of campaign: name, recipient count, template count, earliest/latest send dates
    - "Create Campaign" button
    - On success, redirect to campaign detail page
- Create `frontend/src/components/FileUpload.tsx`:
  - Drag-and-drop zone with click-to-browse fallback
  - File type filtering (accept only CSV, XLSX, MD, DOCX)
  - Upload progress indicator
  - Remove file button

**Acceptance Criteria:**
- Multi-step form navigates forward and back
- File upload works via drag-and-drop and click
- Server-side validation errors are displayed clearly per step
- Preview shows correctly rendered email
- Campaign creation completes and redirects to detail page

---

### Task 5.6 — Campaign Detail Page

**Priority:** High
**Estimated Effort:** Large

- Create `frontend/src/pages/CampaignDetail.tsx`:
  - **Header section:**
    - Campaign name, description, status badge
    - Action buttons based on status:
      - Draft: "Schedule", "Add Recipient", "Delete"
      - Scheduled: "Pause", "Cancel"
      - Paused: "Resume" (re-schedule), "Cancel"
      - In Progress: "Pause" (if supported)
      - Completed/Failed: "Delete"
    - Confirmation dialogs for destructive actions
  - **Progress section:**
    - Visual progress bar (sent / total)
    - Stat cards: Sent, Failed, Pending, Scheduled, Cancelled
    - Auto-updates via polling when campaign is active
  - **Recipients section:**
    - Embedded `RecipientTable` component with pagination
    - Click a recipient to see their email preview
  - **Add Recipient modal:**
    - Triggered by "Add Recipient" button (only visible for draft campaigns)
    - Form fields: email (required), name (optional), custom fields (key-value pairs)
    - Calls `POST /api/v1/campaigns/{id}/recipients`
    - On success, refreshes recipient table
    - Shows validation errors inline
  - **Activity log:** (stretch goal)
    - Timeline of events: created, scheduled, emails sent, errors
- Create `frontend/src/components/EmailPreview.tsx`:
  - Renders email HTML in a sandboxed container (iframe or shadow DOM)
  - Shows subject, from, to fields
  - Toggle between HTML and plain text views
- Create `frontend/src/components/RecipientTable.tsx`:
  - TanStack Table with columns: Name, Email, Status, Scheduled At, Sent At
  - Pagination controls
  - Search/filter by email or name
  - Status filter
  - Row click opens email preview

**Acceptance Criteria:**
- Detail page shows all campaign information accurately
- Action buttons are contextual based on campaign status
- Progress updates automatically for active campaigns
- Recipient table paginated and searchable
- Email preview renders HTML safely
- Confirmation dialogs prevent accidental actions

---

### Task 5.7 — Settings Page

**Priority:** Medium
**Estimated Effort:** Small

- Create `frontend/src/pages/Settings.tsx`:
  - **Gmail Connection section:**
    - Show authentication status (connected/disconnected)
    - If connected: show authenticated email, "Disconnect" button
    - If disconnected: "Connect Gmail" button → redirects to OAuth login URL
    - Handle `?auth=success` query param (show success toast after OAuth callback redirect)
  - **Send Quota section:**
    - Display daily send quota: used / limit
    - Visual bar showing usage
  - **About section:**
    - App version, link to documentation

**Acceptance Criteria:**
- Gmail auth status is accurately displayed
- Connect button initiates OAuth flow
- Disconnect button revokes credentials
- Quota display updates on page load
- Success toast appears after OAuth callback redirect

---

### Task 5.8 — StatusBadge Component

**Priority:** Medium
**Estimated Effort:** Small

- Create `frontend/src/components/StatusBadge.tsx`:
  - Props: `status: CampaignStatus | EmailStatus`
  - Visual styles per status:
    - Draft: gray
    - Scheduled: blue
    - In Progress: yellow/amber with pulse animation
    - Paused: orange
    - Completed: green
    - Failed: red
    - Sent: green
    - Pending: gray
    - Cancelled: gray with strikethrough
  - Consistent sizing and padding

**Acceptance Criteria:**
- Each status has a distinct, accessible color
- Component is reusable for both campaign and email statuses
- Renders inline (suitable for tables and headers)

---

### Task 5.9 — TypeScript Types

**Priority:** High
**Estimated Effort:** Small

- Update `frontend/src/types/index.ts` to mirror all backend schemas:
  - `Campaign`, `CampaignStatus`
  - `CampaignScheduleStep`
  - `Recipient`
  - `RecipientCreateRequest`, `RecipientCreateResponse`
  - `Email`, `EmailStatus`
  - `EmailPreview` (with `step_order`, `scheduled_at`)
  - `AuthStatus`
  - `SendQuota`
  - `ReplyCheckStatus`
  - `PaginatedResponse<T>`
  - `ErrorResponse`
  - API request types for create, schedule, etc.

**Acceptance Criteria:**
- All API responses have corresponding TypeScript types
- Types are used consistently across all API hooks and components
- No `any` types in API layer
