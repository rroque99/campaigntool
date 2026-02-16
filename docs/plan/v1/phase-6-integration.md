# Phase 6 — Integration, Polish & Deployment

**Goal:** Bring everything together with end-to-end testing, error handling improvements, production build configuration, and final polish.

**Dependencies:** Phase 4 (scheduling complete), Phase 5 (frontend complete)

---

## Tasks

### Task 6.1 — End-to-End Integration Testing

**Priority:** High
**Estimated Effort:** Medium

- Verify the full workflow end-to-end (with mocked Gmail API):
  1. Start backend and frontend dev servers
  2. Authenticate via OAuth (mocked or test credentials)
  3. Create a campaign by uploading spreadsheet + email document
  4. Preview rendered emails for multiple recipients
  5. Schedule the campaign
  6. Verify APScheduler jobs are created at correct times
  7. Simulate job execution (fast-forward or trigger manually)
  8. Verify email statuses update to `sent`
  9. Verify campaign status transitions to `completed`
  10. Pause and cancel flows
- Write integration tests in `backend/tests/` that cover the full API workflow:
  - Create → Preview → Schedule → Send → Complete
  - Create → Schedule → Pause → Resume → Complete
  - Create → Schedule → Cancel
- Test error scenarios:
  - OAuth token expired mid-campaign
  - Gmail API rate limiting during batch sends
  - Network failure during send

**Acceptance Criteria:**
- All integration tests pass
- Full workflow is documented and reproducible
- Error recovery works for all tested failure modes

---

### Task 6.2 — Error Handling & User Feedback

**Priority:** High
**Estimated Effort:** Medium

- **Backend improvements:**
  - Global exception handler in FastAPI for unhandled errors
  - Consistent error response format: `{"detail": str, "error_code": str}`
  - Specific error codes for: `AUTH_REQUIRED`, `AUTH_EXPIRED`, `QUOTA_EXCEEDED`, `INVALID_FILE`, `CAMPAIGN_NOT_FOUND`, `INVALID_STATUS_TRANSITION`
  - Validation error formatting for multipart uploads
  - Logging: add structured logging for all critical operations (sends, errors, status changes)
- **Frontend improvements:**
  - Global error boundary component
  - Toast notification system for:
    - Success: campaign created, emails scheduled
    - Error: API errors, upload failures, auth issues
    - Warning: approaching quota limit, past send dates
  - Inline form validation with error messages
  - Loading skeletons for data-heavy pages
  - Empty states for all list views
  - Network error handling with retry UI

**Acceptance Criteria:**
- No raw error messages or stack traces visible to users
- All error states have user-friendly messages
- Toast notifications appear for all async operations
- Loading states prevent layout shifts

---

### Task 6.3 — Production Build Configuration

**Priority:** Medium
**Estimated Effort:** Medium

- **Frontend production build:**
  - `npm run build` outputs to `frontend/dist/`
  - Configure FastAPI to serve the `dist/` directory as static files in production
  - Add fallback route for SPA client-side routing (serve `index.html` for unknown paths)
- **Backend production setup:**
  - Environment-based configuration (development vs production)
  - In production: serve static frontend, disable CORS (same origin), use file-based logging
  - Add `start.py` or shell script for one-command startup:
    ```bash
    cd backend && uvicorn src.campaign.main:app --host 0.0.0.0 --port 8000
    ```
  - Document required environment variables
- **Database:**
  - Ensure Alembic migrations run on startup (or document the manual step)
  - Add backup reminder/mechanism for SQLite database file

**Acceptance Criteria:**
- `npm run build` produces optimized bundle
- FastAPI serves the frontend in production mode
- Single command starts the full application
- Environment variables are documented

---

### Task 6.4 — Security Review

**Priority:** High
**Estimated Effort:** Small

- Review and verify:
  - OAuth credentials are never logged or exposed in API responses
  - `credentials/` directory is in `.gitignore`
  - CORS is properly restricted (only `localhost:5173` in dev, same-origin in prod)
  - File upload validation: type checking, size limits, no path traversal
  - SQL injection prevention (SQLAlchemy parameterized queries — should be automatic)
  - XSS prevention in email preview (sandboxed iframe)
  - Template variable injection prevention (HTML escaping)
  - No personal data logged beyond operational necessity
  - Rate limiting on auth endpoints (prevent brute force on callback)

**Acceptance Criteria:**
- No credentials in source control or logs
- All OWASP top 10 relevant risks are mitigated
- File uploads are safe
- Email preview cannot execute arbitrary JavaScript

---

### Task 6.5 — Performance & Reliability

**Priority:** Medium
**Estimated Effort:** Small

- **Database:**
  - Add indexes on: `emails.campaign_id`, `emails.status`, `emails.scheduled_at`, `recipients.campaign_id`, `recipients.email`
  - Verify cascade deletes work correctly
- **Scheduling:**
  - Verify scheduler handles app restart gracefully (jobs resume from SQLite)
  - Test concurrent campaign scheduling
  - Verify no duplicate sends on scheduler recovery
- **Frontend:**
  - Verify React Query caching and deduplication work
  - Optimize large recipient tables (virtual scrolling if > 1000 rows)
  - Lazy load route components for faster initial load

**Acceptance Criteria:**
- Database queries use indexes for common access patterns
- Scheduler recovery doesn't produce duplicate sends
- Frontend performs well with 500+ recipients in a campaign

---

### Task 6.6 — Documentation

**Priority:** Medium
**Estimated Effort:** Small

- Update `README.md` with:
  - Project description and features
  - Prerequisites (Python 3.11+, Node 18+, Google Cloud project with Gmail API)
  - Setup instructions:
    1. Clone repository
    2. Set up Google Cloud OAuth credentials
    3. Install backend and frontend dependencies
    4. Run database migrations
    5. Start development servers
  - Production deployment instructions
  - Configuration reference (environment variables)
  - Spreadsheet format specification
  - Email template format specification
  - API endpoint reference (or link to Swagger docs)
  - Troubleshooting common issues (OAuth errors, quota limits)

**Acceptance Criteria:**
- A new developer can set up and run the project following only the README
- All configuration options are documented
- File format specifications are clear with examples

---

### Task 6.7 — Final Verification Checklist

**Priority:** High
**Estimated Effort:** Small

- Run through the complete checklist before considering the project done:
  - [ ] `uv sync` succeeds (creates venv and installs dependencies)
  - [ ] `uv run alembic upgrade head` creates the schema
  - [ ] `uv run pytest -v` passes all tests
  - [ ] `uv run ruff check src/ tests/` reports no issues
  - [ ] `uv run ruff format --check src/ tests/` reports no formatting issues
  - [ ] `npm install` succeeds
  - [ ] `npm run build` produces working bundle
  - [ ] `npm run lint` reports no issues
  - [ ] OAuth flow works end-to-end
  - [ ] Campaign creation with file uploads works (recipients + schedule + email doc)
  - [ ] Three-file upload works (recipients, schedule, email doc)
  - [ ] Manual recipient addition works via API and UI
  - [ ] Relative send dates resolve correctly after previous email sent
  - [ ] Reply detection cancels remaining emails for replied recipients
  - [ ] Email preview renders correctly
  - [ ] Scheduling creates jobs at correct times
  - [ ] Emails send successfully (manual test with real Gmail)
  - [ ] Pause and cancel work correctly
  - [ ] Campaign status transitions are accurate
  - [ ] Frontend displays real-time updates during sending
  - [ ] No credentials in git history
  - [ ] README is complete and accurate

**Acceptance Criteria:**
- All checklist items pass
- Project is ready for use
