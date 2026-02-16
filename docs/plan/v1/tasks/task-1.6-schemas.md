# Task 1.6 — Pydantic Schemas

**Phase:** 1 — Project Scaffolding
**Priority:** Medium
**Status:** Pending

## Description

Define all Pydantic request/response schemas that will be used across the API.

## Steps

1. Create `backend/src/campaign/schemas.py` with the following models:
   - **CampaignCreate:** `name: str`, `description: str | None = None`
   - **CampaignResponse:** `id: int`, `name: str`, `description: str | None`, `status: str`, `spreadsheet_filename: str | None`, `created_at: datetime`, `updated_at: datetime`, `recipient_count: int = 0`, `sent_count: int = 0`, `failed_count: int = 0`, `pending_count: int = 0`
   - **CampaignListResponse:** `campaigns: list[CampaignResponse]`
   - **RecipientResponse:** `id: int`, `email: str`, `name: str | None`, `custom_fields: dict`, `email_status: str | None`
   - **RecipientListResponse:** `total: int`, `page: int`, `page_size: int`, `items: list[RecipientResponse]`
   - **EmailPreviewResponse:** `recipient_email: str`, `recipient_name: str | None`, `subject: str`, `body_html: str`
   - **ScheduleRequest:** `send_date: date | None = None`, `send_time: time | None = None`
   - **ScheduleResponse:** `scheduled_count: int`, `skipped_count: int`, `next_send_at: datetime | None`
   - **AuthStatusResponse:** `authenticated: bool`, `email: str | None = None`
   - **QuotaResponse:** `sent_today: int`, `limit: int`, `remaining: int`
   - **ErrorResponse:** `detail: str`, `error_code: str | None = None`
2. Add `model_config = ConfigDict(from_attributes=True)` to response models
3. Verify serialization from ORM models works

## Acceptance Criteria

- [ ] All schemas validate with sample data
- [ ] Response models serialize from SQLAlchemy ORM objects
- [ ] Datetime fields serialize as ISO 8601 strings
