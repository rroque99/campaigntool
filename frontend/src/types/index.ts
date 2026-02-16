// Campaign statuses
export type CampaignStatus =
  | "draft"
  | "scheduled"
  | "in_progress"
  | "paused"
  | "completed"
  | "failed";

// Email statuses
export type EmailStatus =
  | "pending"
  | "scheduled"
  | "sent"
  | "failed"
  | "cancelled";

// --- Campaign ---

export interface Campaign {
  id: number;
  name: string;
  description: string | null;
  status: CampaignStatus;
  recipients_filename: string | null;
  schedule_filename: string | null;
  step_count: number;
  created_at: string;
  updated_at: string;
  recipient_count: number;
  sent_count: number;
  failed_count: number;
  pending_count: number;
}

export interface CampaignListResponse {
  campaigns: Campaign[];
}

export interface CampaignCreateRequest {
  name: string;
  description?: string;
}

// --- Campaign Schedule Step ---

export interface CampaignScheduleStep {
  id: number;
  step_order: number;
  send_date: string | null;
  relative_days: number | null;
  send_time: string;
  email_template_ref: string;
}

// --- Campaign Status ---

export interface CampaignStatusResponse {
  total_emails: number;
  sent: number;
  failed: number;
  pending: number;
  scheduled: number;
  cancelled: number;
  progress_percent: number;
  next_send_at: string | null;
  estimated_completion: string | null;
}

// --- Recipient ---

export interface Recipient {
  id: number;
  email: string;
  name: string | null;
  custom_fields: Record<string, string> | null;
  email_status: EmailStatus | null;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export type RecipientListResponse = PaginatedResponse<Recipient>;

export interface RecipientCreateRequest {
  email: string;
  name?: string;
  custom_fields?: Record<string, string>;
}

export interface RecipientCreateResponse {
  id: number;
  email: string;
  name: string | null;
  custom_fields: Record<string, string> | null;
  created_at: string;
}

// --- Email ---

export interface EmailStatusItem {
  id: number;
  recipient_email: string;
  recipient_name: string | null;
  subject: string | null;
  status: EmailStatus;
  step_order: number | null;
  scheduled_at: string | null;
  sent_at: string | null;
  error_message: string | null;
}

export type EmailListResponse = PaginatedResponse<EmailStatusItem>;

export interface EmailDetail {
  id: number;
  recipient_email: string;
  recipient_name: string | null;
  subject: string | null;
  body_html: string | null;
  body_text: string | null;
  status: EmailStatus;
  step_order: number | null;
  scheduled_at: string | null;
  sent_at: string | null;
  error_message: string | null;
  gmail_message_id: string | null;
  thread_id: string | null;
}

// --- Email Preview ---

export interface EmailPreview {
  recipient_email: string;
  recipient_name: string | null;
  subject: string;
  body_html: string;
  step_order: number | null;
  scheduled_at: string | null;
}

// --- Scheduling ---

export interface ScheduleResponse {
  scheduled_count: number;
  skipped_count: number;
  next_send_at: string | null;
}

export interface PauseResponse {
  paused_count: number;
}

export interface CancelResponse {
  cancelled_count: number;
  campaign_status: string;
}

// --- Auth ---

export interface AuthStatus {
  authenticated: boolean;
  email: string | null;
}

export interface SendQuota {
  sent_today: number;
  limit: number;
  remaining: number;
}

// --- Reply Detection ---

export interface ReplyCheckStatus {
  last_checked_at: string | null;
  history_id: string | null;
  replies_detected: number;
}

// --- Errors ---

export interface ErrorResponse {
  detail: string;
  error_code?: string;
}
