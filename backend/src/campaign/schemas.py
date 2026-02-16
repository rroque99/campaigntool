from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr

# --- Campaign ---


class CampaignCreate(BaseModel):
    name: str
    description: str | None = None


class CampaignScheduleStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_order: int
    send_date: date | None
    relative_days: int | None
    send_time: time
    email_template_ref: str


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    status: str
    recipients_filename: str | None
    schedule_filename: str | None
    step_count: int = 0
    created_at: datetime
    updated_at: datetime
    recipient_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    pending_count: int = 0


class CampaignListResponse(BaseModel):
    campaigns: list[CampaignResponse]


# --- Recipient ---


class RecipientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str | None
    custom_fields: dict | None
    email_status: str | None = None


class RecipientListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RecipientResponse]


class RecipientCreate(BaseModel):
    email: EmailStr
    name: str | None = None
    custom_fields: dict | None = None


class RecipientCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str | None
    custom_fields: dict | None
    created_at: datetime


# --- Email Preview ---


class EmailPreviewResponse(BaseModel):
    recipient_email: str
    recipient_name: str | None
    subject: str
    body_html: str
    step_order: int | None = None
    scheduled_at: datetime | None = None


# --- Scheduling ---


class ScheduleResponse(BaseModel):
    scheduled_count: int
    skipped_count: int
    next_send_at: datetime | None


class PauseResponse(BaseModel):
    paused_count: int


class CancelResponse(BaseModel):
    cancelled_count: int
    campaign_status: str


# --- Campaign Status ---


class CampaignStatusResponse(BaseModel):
    total_emails: int
    sent: int
    failed: int
    pending: int
    scheduled: int
    cancelled: int
    progress_percent: float
    next_send_at: datetime | None
    estimated_completion: datetime | None


# --- Email Delivery Status ---


class EmailStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_email: str
    recipient_name: str | None
    subject: str | None
    status: str
    step_order: int | None
    scheduled_at: datetime | None
    sent_at: datetime | None
    error_message: str | None


class EmailListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[EmailStatusResponse]


class EmailDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_email: str
    recipient_name: str | None
    subject: str | None
    body_html: str | None
    body_text: str | None
    status: str
    step_order: int | None
    scheduled_at: datetime | None
    sent_at: datetime | None
    error_message: str | None
    gmail_message_id: str | None
    thread_id: str | None


# --- Auth ---


class AuthStatusResponse(BaseModel):
    authenticated: bool
    email: str | None = None


class QuotaResponse(BaseModel):
    sent_today: int
    limit: int
    remaining: int


# --- Reply Detection ---


class ReplyCheckStatusResponse(BaseModel):
    last_checked_at: datetime | None
    history_id: str | None
    replies_detected: int = 0


# --- Errors ---


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
