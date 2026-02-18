"""Tests for APScheduler job management, scheduling endpoints, and reply monitoring."""

from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from campaign.gmail import ReplyCheckResult
from campaign.models import (
    Campaign,
    CampaignScheduleStep,
    Email,
    Recipient,
    ReplyCheckState,
)
from campaign.scheduler import (
    _cancel_emails_for_replied_threads,
    _update_campaign_status,
    cancel_campaign,
    check_replies_job,
    pause_campaign,
    schedule_campaign,
    send_email_job,
)
from campaign.sender import SendError, SendResult

# ── Helpers ───────────────────────────────────────────────────────────────

SAMPLE_EMAILS_MD = b"""ref: intro
subject: Hello {{recipient_name}}

Hi {{recipient_name}} from {{company}}!

---

ref: followup
subject: Following up {{recipient_name}}

Just checking in, {{recipient_name}}.
"""

SAMPLE_RECIPIENTS_CSV = (
    b"recipient_email,recipient_name,company\n"
    b"jane@example.com,Jane,Acme\n"
    b"bob@example.com,Bob,Globex\n"
)

SAMPLE_SCHEDULE_CSV = (
    b"send_date,send_time,email_template_ref\n2026-03-01,09:00,intro\n5,09:00,followup\n"
)


def _create_campaign_with_emails(db, *, status="draft", email_status="pending"):
    """Create a campaign with 1 recipient and 2 schedule steps (1 absolute, 1 relative)."""
    campaign = Campaign(name="Test Campaign", status=status)
    db.add(campaign)
    db.flush()

    step1 = CampaignScheduleStep(
        campaign_id=campaign.id,
        step_order=1,
        send_date=date(2026, 3, 1),
        relative_days=None,
        send_time=time(9, 0),
        email_template_ref="intro",
    )
    step2 = CampaignScheduleStep(
        campaign_id=campaign.id,
        step_order=2,
        send_date=None,
        relative_days=5,
        send_time=time(9, 0),
        email_template_ref="followup",
    )
    db.add_all([step1, step2])

    recipient = Recipient(
        campaign_id=campaign.id,
        email="jane@example.com",
        name="Jane",
        custom_fields={"company": "Acme"},
    )
    db.add(recipient)
    db.flush()

    email1 = Email(
        campaign_id=campaign.id,
        recipient_id=recipient.id,
        subject="Hello Jane",
        body_html="<p>Hi Jane from Acme!</p>",
        body_text="Hi Jane from Acme!",
        status=email_status,
        step_order=1,
        scheduled_at=datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
    )
    email2 = Email(
        campaign_id=campaign.id,
        recipient_id=recipient.id,
        subject="Following up Jane",
        body_html="<p>Just checking in, Jane.</p>",
        body_text="Just checking in, Jane.",
        status="pending",
        step_order=2,
    )
    db.add_all([email1, email2])
    db.commit()

    return campaign, recipient, email1, email2


class _NoCloseSession:
    """Wraps a session to prevent close() from being called (for testing)."""

    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        if name == "close":
            return lambda: None  # No-op close
        return getattr(self._session, name)


# ── send_email_job tests ─────────────────────────────────────────────────


@patch("campaign.scheduler.get_scheduler")
@patch("campaign.scheduler.get_sender")
def test_send_email_job_success(mock_get_sender, mock_get_sched, test_db):
    """Successful send updates status and records message/thread IDs."""
    mock_sender = MagicMock()
    mock_sender.send_email.return_value = SendResult(message_id="msg_123", thread_id="thread_456")
    mock_get_sender.return_value = mock_sender
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )
    email1_id = email1.id

    with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
        send_email_job(email1_id)

    test_db.refresh(email1)
    assert email1.status == "sent"
    assert email1.gmail_message_id == "msg_123"
    assert email1.thread_id == "thread_456"
    assert email1.sent_at is not None


@patch("campaign.scheduler.get_scheduler")
@patch("campaign.scheduler.get_sender")
def test_send_email_job_failure(mock_get_sender, mock_get_sched, test_db):
    """Failed send records error message."""
    mock_sender = MagicMock()
    mock_sender.send_email.side_effect = SendError("Auth revoked", error_code="send_failed")
    mock_get_sender.return_value = mock_sender
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )
    email1_id = email1.id

    with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
        send_email_job(email1_id)

    test_db.refresh(email1)
    assert email1.status == "failed"
    assert "Auth revoked" in email1.error_message


@patch("campaign.scheduler.get_scheduler")
@patch("campaign.scheduler.get_sender")
def test_send_email_job_skips_cancelled(mock_get_sender, mock_get_sched, test_db):
    """Cancelled emails are skipped."""
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )
    email1.status = "cancelled"
    test_db.commit()

    with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
        send_email_job(email1.id)

    mock_get_sender.return_value.send_email.assert_not_called()


@patch("campaign.scheduler.get_scheduler")
@patch("campaign.scheduler.get_sender")
def test_send_email_job_rate_limited_retries(mock_get_sender, mock_get_sched, test_db):
    """Retryable error triggers retry via rescheduling."""
    mock_sender = MagicMock()
    mock_sender.send_email.side_effect = SendError(
        "Rate limited", error_code="rate_limited", retryable=True
    )
    mock_get_sender.return_value = mock_sender
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )
    email1_id = email1.id

    with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
        send_email_job(email1_id, retry_count=0)

    # Should have scheduled a retry job
    mock_scheduler.add_job.assert_called_once()
    call_args = mock_scheduler.add_job.call_args
    assert call_args[1]["id"] == f"retry_email_{email1_id}_1"

    # Email should still be scheduled (not failed yet)
    test_db.refresh(email1)
    assert email1.status == "scheduled"


@patch("campaign.scheduler.get_scheduler")
@patch("campaign.scheduler.get_sender")
def test_send_email_job_rate_limited_exhausted(mock_get_sender, mock_get_sched, test_db):
    """Retryable error with retries exhausted marks email as failed."""
    mock_sender = MagicMock()
    mock_sender.send_email.side_effect = SendError(
        "Rate limited", error_code="rate_limited", retryable=True
    )
    mock_get_sender.return_value = mock_sender
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )
    email1_id = email1.id

    with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
        send_email_job(email1_id, retry_count=3)  # MAX_RETRIES = 3

    test_db.refresh(email1)
    assert email1.status == "failed"
    assert "Rate limited" in email1.error_message


@patch("campaign.scheduler.get_scheduler")
@patch("campaign.scheduler.get_sender")
def test_send_email_job_quota_exceeded(mock_get_sender, mock_get_sched, test_db):
    """Quota exceeded reschedules email for tomorrow."""
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )
    email1_id = email1.id

    with patch("campaign.scheduler.settings") as mock_settings:
        mock_settings.daily_send_limit = 0  # Effectively 0 quota

        with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
            send_email_job(email1_id)

    # Email should still be scheduled, not failed
    test_db.refresh(email1)
    assert email1.status == "scheduled"
    mock_get_sender.return_value.send_email.assert_not_called()


# ── Resolve next relative step ───────────────────────────────────────────


@patch("campaign.scheduler.get_scheduler")
@patch("campaign.scheduler.get_sender")
def test_send_email_resolves_next_relative_step(mock_get_sender, mock_get_sched, test_db):
    """After sending step 1, step 2 (relative) gets scheduled_at resolved."""
    mock_sender = MagicMock()
    mock_sender.send_email.return_value = SendResult(message_id="msg_1", thread_id="thread_1")
    mock_get_sender.return_value = mock_sender
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )

    with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
        send_email_job(email1.id)

    test_db.refresh(email2)
    assert email2.status == "scheduled"
    assert email2.scheduled_at is not None
    # Should be ~5 days after email1's sent_at (interpreted as UTC, converted to local)
    test_db.refresh(email1)
    sent_local = email1.sent_at.replace(tzinfo=timezone.utc).astimezone()
    expected_date = sent_local.date() + timedelta(days=5)
    assert email2.scheduled_at.date() == expected_date


# ── Campaign status transitions ──────────────────────────────────────────


def test_update_campaign_status_to_in_progress(test_db):
    """Campaign transitions from scheduled to in_progress when first email is sent."""
    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )
    email1.status = "sent"
    email1.sent_at = datetime.now(timezone.utc)
    test_db.commit()

    _update_campaign_status(test_db, campaign.id)

    test_db.refresh(campaign)
    assert campaign.status == "in_progress"


def test_update_campaign_status_to_completed(test_db):
    """Campaign transitions to completed when all emails are sent/failed/cancelled."""
    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="in_progress", email_status="sent"
    )
    email1.sent_at = datetime.now(timezone.utc)
    email2.status = "sent"
    email2.sent_at = datetime.now(timezone.utc)
    test_db.commit()

    _update_campaign_status(test_db, campaign.id)

    test_db.refresh(campaign)
    assert campaign.status == "completed"


def test_update_campaign_status_to_failed(test_db):
    """Campaign transitions to failed when all emails failed (none sent)."""
    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="in_progress", email_status="failed"
    )
    email2.status = "failed"
    test_db.commit()

    _update_campaign_status(test_db, campaign.id)

    test_db.refresh(campaign)
    assert campaign.status == "failed"


# ── schedule_campaign ────────────────────────────────────────────────────


@patch("campaign.scheduler.get_scheduler")
def test_schedule_campaign(mock_get_sched, test_db):
    """schedule_campaign creates jobs for absolute-date emails and skips relative ones."""
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(test_db)

    result = schedule_campaign(test_db, campaign.id)

    assert result["scheduled_count"] == 1  # Only step 1 (absolute date)
    assert result["skipped_count"] == 1  # Step 2 is relative
    assert result["next_send_at"] is not None

    test_db.refresh(email1)
    assert email1.status == "scheduled"

    test_db.refresh(email2)
    assert email2.status == "pending"  # Still pending (relative)


# ── pause_campaign ───────────────────────────────────────────────────────


@patch("campaign.scheduler.get_scheduler")
def test_pause_campaign(mock_get_sched, test_db):
    """pause_campaign reverts scheduled emails to pending and removes jobs."""
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )

    paused_count = pause_campaign(test_db, campaign.id)

    assert paused_count == 1  # Only email1 was scheduled
    test_db.refresh(email1)
    assert email1.status == "pending"
    assert email1.scheduled_at is None


@patch("campaign.scheduler.get_scheduler")
def test_pause_does_not_affect_sent(mock_get_sched, test_db):
    """Pausing doesn't affect already-sent emails."""
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="in_progress", email_status="sent"
    )
    email1.sent_at = datetime.now(timezone.utc)
    test_db.commit()

    paused_count = pause_campaign(test_db, campaign.id)

    assert paused_count == 0  # No scheduled emails to pause
    test_db.refresh(email1)
    assert email1.status == "sent"


# ── cancel_campaign ──────────────────────────────────────────────────────


@patch("campaign.scheduler.get_scheduler")
def test_cancel_campaign(mock_get_sched, test_db):
    """cancel_campaign marks pending and scheduled emails as cancelled."""
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="scheduled", email_status="scheduled"
    )

    cancelled_count = cancel_campaign(test_db, campaign.id)

    assert cancelled_count == 2  # Both email1 (scheduled) and email2 (pending)
    test_db.refresh(email1)
    assert email1.status == "cancelled"
    test_db.refresh(email2)
    assert email2.status == "cancelled"


# ── Scheduling endpoint tests (via HTTP) ─────────────────────────────────


@pytest.mark.asyncio
@patch("campaign.routers.campaigns.is_authenticated", return_value=True)
@patch("campaign.routers.campaigns.schedule_campaign")
async def test_schedule_endpoint(mock_schedule, mock_auth, test_client, test_db):
    """POST /campaigns/{id}/schedule schedules a draft campaign."""
    campaign = Campaign(name="Test", status="draft")
    test_db.add(campaign)
    test_db.commit()

    mock_schedule.return_value = {
        "scheduled_count": 5,
        "skipped_count": 0,
        "next_send_at": datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
    }

    response = await test_client.post(f"/api/v1/campaigns/{campaign.id}/schedule")
    assert response.status_code == 200
    data = response.json()
    assert data["scheduled_count"] == 5
    assert data["skipped_count"] == 0

    test_db.refresh(campaign)
    assert campaign.status == "scheduled"


@pytest.mark.asyncio
@patch("campaign.routers.campaigns.is_authenticated", return_value=True)
@patch("campaign.routers.campaigns.schedule_campaign")
async def test_schedule_endpoint_rejects_completed(mock_schedule, mock_auth, test_client, test_db):
    """Cannot schedule a completed campaign."""
    campaign = Campaign(name="Test", status="completed")
    test_db.add(campaign)
    test_db.commit()

    response = await test_client.post(f"/api/v1/campaigns/{campaign.id}/schedule")
    assert response.status_code == 400


@pytest.mark.asyncio
@patch("campaign.routers.campaigns._is_sender_ready", return_value=False)
async def test_schedule_endpoint_rejects_unauthenticated(mock_ready, test_client, test_db):
    """Cannot schedule when sender is not ready."""
    campaign = Campaign(name="Test", status="draft")
    test_db.add(campaign)
    test_db.commit()

    response = await test_client.post(f"/api/v1/campaigns/{campaign.id}/schedule")
    assert response.status_code == 400
    assert "not ready" in response.json()["detail"].lower()


@pytest.mark.asyncio
@patch("campaign.routers.campaigns.pause_campaign")
async def test_pause_endpoint(mock_pause, test_client, test_db):
    """POST /campaigns/{id}/pause pauses a scheduled campaign."""
    campaign = Campaign(name="Test", status="scheduled")
    test_db.add(campaign)
    test_db.commit()

    mock_pause.return_value = 3

    response = await test_client.post(f"/api/v1/campaigns/{campaign.id}/pause")
    assert response.status_code == 200
    assert response.json()["paused_count"] == 3

    test_db.refresh(campaign)
    assert campaign.status == "paused"


@pytest.mark.asyncio
@patch("campaign.routers.campaigns.pause_campaign")
async def test_pause_endpoint_rejects_draft(mock_pause, test_client, test_db):
    """Cannot pause a draft campaign."""
    campaign = Campaign(name="Test", status="draft")
    test_db.add(campaign)
    test_db.commit()

    response = await test_client.post(f"/api/v1/campaigns/{campaign.id}/pause")
    assert response.status_code == 400


@pytest.mark.asyncio
@patch("campaign.routers.campaigns.cancel_campaign")
async def test_cancel_endpoint(mock_cancel, test_client, test_db):
    """POST /campaigns/{id}/cancel cancels a campaign."""
    campaign = Campaign(name="Test", status="scheduled")
    test_db.add(campaign)
    test_db.commit()

    mock_cancel.return_value = 5

    response = await test_client.post(f"/api/v1/campaigns/{campaign.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["cancelled_count"] == 5
    assert data["campaign_status"] == "completed"


@pytest.mark.asyncio
@patch("campaign.routers.campaigns.cancel_campaign")
async def test_cancel_endpoint_rejects_completed(mock_cancel, test_client, test_db):
    """Cannot cancel a completed campaign."""
    campaign = Campaign(name="Test", status="completed")
    test_db.add(campaign)
    test_db.commit()

    response = await test_client.post(f"/api/v1/campaigns/{campaign.id}/cancel")
    assert response.status_code == 400


# ── Campaign status endpoint ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_campaign_status_endpoint(test_client, test_db):
    """GET /campaigns/{id}/status returns accurate counts."""
    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="in_progress", email_status="sent"
    )
    email1.sent_at = datetime.now(timezone.utc)
    test_db.commit()

    response = await test_client.get(f"/api/v1/campaigns/{campaign.id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["total_emails"] == 2
    assert data["sent"] == 1
    assert data["pending"] == 1
    assert data["progress_percent"] == 50.0


@pytest.mark.asyncio
async def test_campaign_status_not_found(test_client, test_db):
    response = await test_client.get("/api/v1/campaigns/999/status")
    assert response.status_code == 404


# ── Email list/detail endpoint tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_email_list_endpoint(test_client, test_db):
    """GET /campaigns/{id}/emails returns paginated email list."""
    campaign, recipient, email1, email2 = _create_campaign_with_emails(test_db)

    response = await test_client.get(f"/api/v1/campaigns/{campaign.id}/emails")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_email_list_filter_by_status(test_client, test_db):
    """Email list supports status filtering."""
    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, email_status="scheduled"
    )

    response = await test_client.get(f"/api/v1/campaigns/{campaign.id}/emails?status=scheduled")
    data = response.json()
    assert data["total"] == 1  # Only email1 is scheduled; email2 is pending


@pytest.mark.asyncio
async def test_email_detail_endpoint(test_client, test_db):
    """GET /campaigns/{id}/emails/{email_id} returns full detail."""
    campaign, recipient, email1, email2 = _create_campaign_with_emails(test_db)

    response = await test_client.get(f"/api/v1/campaigns/{campaign.id}/emails/{email1.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "Hello Jane"
    assert data["body_html"] is not None
    assert data["recipient_email"] == "jane@example.com"


@pytest.mark.asyncio
async def test_email_detail_not_found(test_client, test_db):
    campaign, _, _, _ = _create_campaign_with_emails(test_db)
    response = await test_client.get(f"/api/v1/campaigns/{campaign.id}/emails/999")
    assert response.status_code == 404


# ── Reply monitoring ─────────────────────────────────────────────────────


@patch("campaign.scheduler.get_scheduler")
def test_cancel_emails_for_replied_threads(mock_get_sched, test_db):
    """Reply detection cancels unsent emails for the replying recipient."""
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="in_progress", email_status="sent"
    )
    email1.sent_at = datetime.now(timezone.utc)
    email1.thread_id = "thread_abc"
    test_db.commit()

    _cancel_emails_for_replied_threads(test_db, ["thread_abc"])

    test_db.refresh(email2)
    assert email2.status == "cancelled"


@patch("campaign.scheduler.get_scheduler")
@patch("campaign.scheduler.check_replies")
@patch("campaign.scheduler.is_authenticated", return_value=True)
def test_check_replies_job(mock_auth, mock_check, mock_get_sched, test_db):
    """check_replies_job updates history_id and cancels replied recipients."""
    mock_scheduler = MagicMock()
    mock_get_sched.return_value = mock_scheduler

    campaign, recipient, email1, email2 = _create_campaign_with_emails(
        test_db, status="in_progress", email_status="sent"
    )
    email1.sent_at = datetime.now(timezone.utc)
    email1.thread_id = "thread_xyz"
    test_db.commit()

    state = ReplyCheckState(history_id="100")
    test_db.add(state)
    test_db.commit()

    mock_check.return_value = ReplyCheckResult(
        new_history_id="200",
        replied_thread_ids=["thread_xyz"],
    )

    with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
        check_replies_job()

    test_db.refresh(state)
    assert state.history_id == "200"
    assert state.last_checked_at is not None

    test_db.refresh(email2)
    assert email2.status == "cancelled"


@patch("campaign.scheduler.check_replies")
@patch("campaign.scheduler.is_authenticated", return_value=False)
def test_check_replies_job_skips_unauthenticated(mock_auth, mock_check, test_db):
    """check_replies_job skips when not authenticated."""
    with patch("campaign.scheduler.SessionLocal", return_value=_NoCloseSession(test_db)):
        check_replies_job()

    mock_check.assert_not_called()
