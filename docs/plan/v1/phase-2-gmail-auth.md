# Phase 2 — Gmail Authentication & Integration

**Goal:** Implement the full OAuth2 flow for Gmail, token management, and an isolated Gmail API send module so emails can be sent programmatically.

**Dependencies:** Phase 1 (project skeleton, database, FastAPI shell)

---

## Tasks

### Task 2.1 — OAuth2 Flow Implementation

**Priority:** High
**Estimated Effort:** Medium

- Create `backend/src/campaign/auth.py`:
  - Load OAuth client credentials from `credentials/credentials.json`
  - `get_auth_url()` — generate Google OAuth consent URL with required scopes (`gmail.send`, `gmail.readonly`) and redirect URI pointing to callback endpoint
  - `handle_callback(code: str)` — exchange authorization code for tokens, save `token.json` to `credentials/`
  - `get_credentials()` — load `token.json`, check expiry, refresh if needed using refresh token, return valid `google.oauth2.credentials.Credentials`
  - `is_authenticated()` — return `True` if valid (or refreshable) credentials exist
  - `get_user_email()` — use Gmail API to fetch the authenticated user's email address (for display in the UI)
  - `revoke_credentials()` — revoke token and delete `token.json`
- Use `pathlib` for all file path operations
- Never log or expose token values

**Acceptance Criteria:**
- OAuth flow works end-to-end (manual testing with real Google project)
- Token refresh works when access token is expired but refresh token is valid
- When both tokens are expired, `is_authenticated()` returns `False`
- `credentials/` directory contents are never committed to git

---

### Task 2.2 — Auth API Router

**Priority:** High
**Estimated Effort:** Small

- Implement `backend/src/campaign/routers/auth.py`:
  - `GET /api/v1/auth/status` — returns `{"authenticated": bool, "email": str | null}`
  - `GET /api/v1/auth/login` — returns `{"auth_url": str}` (the Google consent URL); frontend will redirect the user
  - `GET /api/v1/auth/callback?code=...` — handles OAuth callback, stores token, redirects to frontend (`http://localhost:5173/settings?auth=success`)
  - `POST /api/v1/auth/logout` — revokes credentials, returns confirmation
- Handle errors: missing `credentials.json`, invalid callback code, token refresh failure

**Acceptance Criteria:**
- `/auth/status` returns correct state before and after authentication
- `/auth/login` returns a valid Google OAuth URL
- `/auth/callback` stores the token and redirects correctly
- Error responses use consistent `ErrorResponse` schema

---

### Task 2.3 — Gmail API Send Module

**Priority:** High
**Estimated Effort:** Medium

- Create `backend/src/campaign/gmail.py`:
  - `build_gmail_service()` — creates the Gmail API service object using credentials from `auth.py`
  - `send_email(to: str, subject: str, body_html: str, body_text: str) -> str` — constructs a MIME message (MIMEMultipart with MIMEText plain + HTML alternatives), base64url encodes it, sends via `service.users().messages().send()`, returns the Gmail message ID
  - `get_send_quota_remaining() -> int` — (best effort) tracks daily sends in the database and returns remaining count against the configured limit
  - Handle errors: invalid credentials, rate limiting (429), recipient errors, network failures
  - Return structured error information, never raw API exceptions
- Use `email.mime.multipart.MIMEMultipart` and `email.mime.text.MIMEText` from stdlib

**Acceptance Criteria:**
- `send_email()` sends a real email when tested manually with valid credentials
- MIME message is properly constructed (multipart/alternative with plain + HTML)
- All Gmail API errors are caught and wrapped in application-level exceptions
- Module has zero imports from other campaign modules except `auth.py` and `config.py`

---

### Task 2.4 — Auth & Gmail Tests

**Priority:** High
**Estimated Effort:** Medium

- Create/update `backend/tests/test_gmail.py`:
  - Mock `google.oauth2.credentials.Credentials` and `build()` service
  - Test `send_email()` constructs correct MIME structure
  - Test `send_email()` returns Gmail message ID on success
  - Test error handling: expired credentials, API errors, network errors
  - Test `get_send_quota_remaining()` returns correct count based on DB records
- Test auth routes:
  - Test `/auth/status` returns unauthenticated when no token exists
  - Test `/auth/callback` with mocked Google response
  - Test `/auth/logout` clears stored credentials
- All tests mock Gmail API calls — never hit the real API

**Acceptance Criteria:**
- `uv run pytest tests/test_gmail.py -v` passes
- 100% of Gmail API interactions are mocked
- Edge cases covered: expired token, missing credentials file, API quota exceeded

---

### Task 2.5 — Daily Send Tracking

**Priority:** Medium
**Estimated Effort:** Small

- Add a utility function or DB query in `gmail.py` (or a helper module):
  - Count emails with `sent_at` in the current UTC day
  - Compare against `settings.daily_send_limit`
  - Return `{"sent_today": int, "limit": int, "remaining": int}`
- Add endpoint: `GET /api/v1/auth/quota` — returns send quota status
- Backend should refuse to schedule emails that would exceed the daily limit

**Acceptance Criteria:**
- Quota endpoint returns accurate counts
- Scheduling logic respects the daily limit
- Quota resets at UTC midnight

---

### Task 2.6 — Reply Detection Module

**Priority:** Medium
**Estimated Effort:** Medium

- Add to `backend/src/campaign/gmail.py`:
  - `check_replies(history_id: str | None) -> ReplyCheckResult` — uses Gmail History API (`history.list`) to detect new messages in campaign threads since `history_id`
  - `ReplyCheckResult` model: `new_history_id: str`, `replied_thread_ids: list[str]`
  - If `history_id` is `None`, fetch current history ID as starting point (no retroactive detection)
  - On detecting a reply in a campaign thread, return the thread ID for cancellation logic
- Update `send_email()` to return `thread_id` alongside `gmail_message_id`:
  - Extract `threadId` from the Gmail API send response
  - Store in the `Email.thread_id` column for later reply matching

**Acceptance Criteria:**
- `check_replies()` returns thread IDs that received replies since last check
- `send_email()` returns both message ID and thread ID
- Handles edge cases: expired history ID (falls back to full resync), no new history
- All Gmail API calls are mockable

---

### Task 2.7 — Reply Detection Tests

**Priority:** Medium
**Estimated Effort:** Small

- Add to `backend/tests/test_gmail.py`:
  - Test `check_replies()` with mocked Gmail History API response
  - Test `check_replies()` with `None` history_id (initial sync)
  - Test `check_replies()` with expired history_id (resync fallback)
  - Test `send_email()` returns thread_id
  - Test no replies detected returns empty list

**Acceptance Criteria:**
- `uv run pytest tests/test_gmail.py -v` passes all new tests
- All Gmail History API calls are mocked
