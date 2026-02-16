# Phase 3 — Campaign Management Backend

**Goal:** Build the core campaign management features: spreadsheet parsing, document parsing, campaign CRUD, recipient handling, and email template rendering.

**Dependencies:** Phase 1 (database, schemas, FastAPI shell)

---

## Tasks

### Task 3.1 — Recipients & Schedule Parsers (CSV & XLSX)

**Priority:** High
**Estimated Effort:** Medium

- Create `backend/src/campaign/parser.py`:
  - `parse_recipients_file(file: UploadFile) -> RecipientsParseResult` — accepts CSV or XLSX, returns structured data
  - `RecipientsParseResult` model: `recipients: list[RecipientData]`, `errors: list[str]`, `warnings: list[str]`
  - `RecipientData` model: `email`, `name`, `custom_fields: dict`
  - Validation rules for recipients file:
    - Required columns: `recipient_email`, `recipient_name`
    - Extra columns become `custom_fields` entries
    - Validate email format (basic regex)
    - Skip empty rows silently
    - Invalid emails are flagged per-row (don't reject entire file)
  - `parse_schedule_file(file: UploadFile) -> ScheduleParseResult` — accepts CSV or XLSX
  - `ScheduleParseResult` model: `steps: list[ScheduleStepData]`, `errors: list[str]`, `warnings: list[str]`
  - `ScheduleStepData` model: `step_order: int`, `send_date: date | None`, `relative_days: int | None`, `send_time: time`, `email_template_ref: str`
  - Validation rules for schedule file:
    - Required columns: `send_date`, `send_time`, `email_template_ref`
    - `send_date` is either an absolute date (YYYY-MM-DD) or an integer (relative days since previous email sent)
    - First step must have an absolute date (not relative)
    - Validate time format (HH:MM)
    - Flag past absolute dates as warnings
  - Use `openpyxl` for XLSX, `csv` module for CSV
  - Detect file type from extension and content

**Acceptance Criteria:**
- Parses `examples/sample_recipients.xlsx` correctly
- Parses `examples/sample_schedule.xlsx` correctly (including relative-day row)
- Parses equivalent CSV files correctly
- Returns clear errors for missing columns
- Returns warnings for past absolute dates
- Invalid emails are flagged per-row
- `custom_fields` captures all non-standard columns from recipients file
- First step with relative date returns error

---

### Task 3.2 — Email Document Parser

**Priority:** High
**Estimated Effort:** Medium

- Add to `backend/src/campaign/parser.py` (or create `templates.py`):
  - `parse_email_document(file: UploadFile) -> list[EmailTemplate]`
  - Support `.md` (Markdown) and `.docx` (Word) formats
  - **Markdown format:**
    - Multiple emails separated by `---` on its own line
    - Each section starts with frontmatter: `subject: Your Subject Line`
    - Body is rendered from Markdown to HTML
  - **DOCX format:**
    - Use `python-docx` to extract text and basic formatting
    - Same separator and frontmatter convention
  - `EmailTemplate` model: `ref: str` (identifier), `subject: str`, `body_html: str`, `body_text: str`
  - Template refs are either numbered (1, 2, 3...) or named via frontmatter `ref: template_name`

**Acceptance Criteria:**
- Parses `examples/sample_emails.md` into separate email templates
- Each template has subject, HTML body, and plain text fallback
- Template ref identifiers match what's used in the spreadsheet's `email_template_ref` column
- Handles edge cases: missing subject, empty body, malformed frontmatter

---

### Task 3.3 — Email Template Rendering

**Priority:** High
**Estimated Effort:** Small

- Create `backend/src/campaign/templates.py` (if not done in 3.2):
  - `render_email(template: EmailTemplate, variables: dict) -> RenderedEmail`
  - `RenderedEmail` model: `subject: str`, `body_html: str`, `body_text: str`
  - Replace `{{variable_name}}` placeholders with values from the variables dict
  - Apply to both subject and body
  - Handle missing variables: leave placeholder as-is and add a warning
  - Handle extra variables: ignore silently
  - Sanitize values to prevent HTML injection in the HTML body (escape `<`, `>`, `&`, `"`)

**Acceptance Criteria:**
- All `{{variable}}` placeholders are replaced with actual values
- Missing variables produce warnings, not errors
- HTML special characters in variable values are escaped
- Plain text body has variables substituted without HTML escaping

---

### Task 3.4 — Campaign CRUD Endpoints

**Priority:** High
**Estimated Effort:** Large

- Implement `backend/src/campaign/routers/campaigns.py`:
  - `POST /api/v1/campaigns` — multipart form upload:
    - Accepts: campaign name, description, recipients file, schedule file, email document file
    - Parses recipients file and schedule file (Task 3.1) and email document (Task 3.2)
    - Validates that `email_template_ref` values in spreadsheet match parsed templates
    - Creates Campaign record (status: `draft`)
    - Creates Recipient records from parsed recipients data
    - Creates Email records (status: `pending`) by rendering templates for each recipient
    - Creates `CampaignScheduleStep` records from parsed schedule data
    - Generates emails as recipient × schedule step (one email per recipient per step)
    - Stores uploaded files (or just the parsed data — files can be discarded after parsing)
    - Returns `CampaignResponse` with 201 status
  - `GET /api/v1/campaigns` — list all campaigns with summary stats:
    - Total recipients, sent count, failed count, pending count per campaign
    - Support query params: `status` filter, `sort_by`, `order`
    - Returns `CampaignListResponse`
  - `GET /api/v1/campaigns/{id}` — single campaign detail:
    - Includes status breakdown (counts by email status)
    - Returns `CampaignResponse` with extended stats
  - `DELETE /api/v1/campaigns/{id}` — delete campaign and all associated records:
    - Only allowed if status is `draft` or `completed` or `failed`
    - Cascade delete recipients and emails

**Acceptance Criteria:**
- Campaign creation processes spreadsheet and email document end-to-end
- Validation errors return 422 with descriptive messages
- Campaign list returns accurate aggregate stats
- Deletion is prevented for active/scheduled campaigns
- All endpoints use proper Pydantic response models

---

### Task 3.5 — Recipient Endpoints

**Priority:** Medium
**Estimated Effort:** Small

- Implement `backend/src/campaign/routers/recipients.py`:
  - `GET /api/v1/campaigns/{id}/recipients` — paginated recipient list:
    - Query params: `page` (default 1), `page_size` (default 50), `status` filter, `search` (email/name)
    - Each recipient includes their email's delivery status
    - Returns `RecipientListResponse`
  - `GET /api/v1/campaigns/{id}/recipients/{recipient_id}` — single recipient detail with full email record

**Acceptance Criteria:**
- Pagination works correctly (total count, page boundaries)
- Search filters by email and name (case-insensitive partial match)
- Status filter returns only recipients with matching email status

---

### Task 3.6 — Email Preview Endpoint

**Priority:** Medium
**Estimated Effort:** Small

- Implement in `backend/src/campaign/routers/emails.py`:
  - `GET /api/v1/campaigns/{id}/preview` — returns rendered email previews:
    - Query param: `recipient_id` (optional — preview for specific recipient)
    - If no recipient specified, return preview for first recipient as sample
    - Returns `EmailPreviewResponse` with rendered subject, HTML body, recipient info
  - `GET /api/v1/campaigns/{id}/preview/all` — returns previews for all recipients (for review before sending)

**Acceptance Criteria:**
- Preview shows the fully rendered email with all template variables filled
- Preview matches what would actually be sent
- Works for campaigns in `draft` status

---

### Task 3.7 — Parser & Template Tests

**Priority:** High
**Estimated Effort:** Medium

- Create/update `backend/tests/test_parser.py`:
  - Test recipients CSV parsing with valid data
  - Test recipients XLSX parsing with valid data
  - Test schedule CSV parsing with valid data (absolute + relative dates)
  - Test schedule XLSX parsing with valid data
  - Test missing required columns in recipients file → error
  - Test missing required columns in schedule file → error
  - Test invalid email addresses → per-row errors
  - Test first schedule step with relative date → error
  - Test past absolute send dates → warnings
  - Test empty rows are skipped
  - Test extra columns become custom_fields in recipients
- Create/update `backend/tests/test_templates.py`:
  - Test Markdown email document parsing
  - Test template variable substitution
  - Test missing variable handling (warning, placeholder preserved)
  - Test HTML escaping in variable values
  - Test subject line variable substitution
- Create/update `backend/tests/test_campaigns.py`:
  - Test campaign creation endpoint with sample files
  - Test campaign list with status filtering
  - Test campaign deletion rules
  - Test recipient pagination and search
  - Test email preview rendering

**Acceptance Criteria:**
- `uv run pytest -v` passes all tests
- Edge cases for parsing are covered
- Campaign endpoints tested with realistic multipart uploads

---

### Task 3.8 — Manual Recipient Add Endpoint

**Priority:** Medium
**Estimated Effort:** Small

- Implement in `backend/src/campaign/routers/recipients.py`:
  - `POST /api/v1/campaigns/{id}/recipients` — add a single recipient manually:
    - Request body: `RecipientCreate` schema (email, name, custom_fields)
    - Validate campaign exists and is in `draft` status
    - Validate email format
    - Check for duplicate email in this campaign
    - Create Recipient record
    - Generate Email records for all schedule steps (recipient × steps)
    - Returns `RecipientCreateResponse` with 201 status

**Acceptance Criteria:**
- New recipient is created with correct data
- Email records are generated for all schedule steps
- Duplicate email in same campaign returns 409
- Non-draft campaign returns 400
- Invalid email returns 422
