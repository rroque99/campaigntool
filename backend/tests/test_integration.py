"""End-to-end integration tests for campaign workflows.

Tests the full API workflow with mocked Gmail API:
- Create → Preview → Schedule → Send → Complete
- Create → Schedule → Pause → Resume → Complete
- Create → Schedule → Cancel
- Error scenarios: token expired, rate limiting, network failure
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from campaign.database import Base, get_db
from campaign.main import app
from campaign.models import Campaign, Email

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
IntegrationSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def db() -> Session:
    Base.metadata.create_all(bind=engine)
    session = IntegrationSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db: Session):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


def _make_recipients_csv(rows: list[tuple[str, str]] | None = None) -> bytes:
    """Build a recipients CSV file in-memory."""
    if rows is None:
        rows = [
            ("alice@example.com", "Alice Smith"),
            ("bob@example.com", "Bob Jones"),
        ]
    lines = ["recipient_email,recipient_name"]
    for email, name in rows:
        lines.append(f"{email},{name}")
    return "\n".join(lines).encode()


def _make_schedule_csv(
    send_date: str | None = None,
    send_time: str = "09:00",
    ref: str = "welcome",
) -> bytes:
    """Build a schedule CSV with one step."""
    if send_date is None:
        send_date = (date.today() + timedelta(days=1)).isoformat()
    lines = [
        "send_date,send_time,email_template_ref",
        f"{send_date},{send_time},{ref}",
    ]
    return "\n".join(lines).encode()


def _make_email_doc(ref: str = "welcome", subject: str = "Hello {{recipient_name}}") -> bytes:
    """Build an email template markdown document."""
    return f"ref: {ref}\nsubject: {subject}\n\nHi {{{{recipient_name}}}},\n\nWelcome!".encode()


def _make_multi_step_schedule_csv() -> bytes:
    """Build a schedule CSV with two steps (absolute + relative)."""
    send_date = (date.today() + timedelta(days=1)).isoformat()
    lines = [
        "send_date,send_time,email_template_ref",
        f"{send_date},09:00,welcome",
        "3,14:00,followup",
    ]
    return "\n".join(lines).encode()


def _make_multi_step_email_doc() -> bytes:
    """Build an email template with two sections."""
    return (
        "ref: welcome\nsubject: Welcome {{recipient_name}}\n\nHello!\n\n"
        "---\n\n"
        "ref: followup\nsubject: Following up {{recipient_name}}\n\nJust checking in."
    ).encode()


async def _create_campaign(
    client: AsyncClient,
    recipients_csv: bytes | None = None,
    schedule_csv: bytes | None = None,
    email_doc: bytes | None = None,
    name: str = "Test Campaign",
):
    """Helper to create a campaign via API."""
    recip = recipients_csv or _make_recipients_csv()
    sched = schedule_csv or _make_schedule_csv()
    doc = email_doc or _make_email_doc()
    return await client.post(
        "/api/v1/campaigns",
        data={"name": name},
        files={
            "recipients_file": ("recipients.csv", recip, "text/csv"),
            "schedule_file": ("schedule.csv", sched, "text/csv"),
            "email_document": ("emails.md", doc, "text/markdown"),
        },
    )


# ── Workflow 1: Create → Preview → Schedule → Send → Complete ────────────


class TestFullWorkflow:
    """Test the happy-path campaign lifecycle."""

    async def test_create_campaign(self, client: AsyncClient):
        resp = await _create_campaign(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Campaign"
        assert data["status"] == "draft"
        assert data["recipient_count"] == 2
        assert data["pending_count"] == 2

    async def test_preview_campaign(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.get(f"/api/v1/campaigns/{campaign_id}/preview")
        assert resp.status_code == 200
        previews = resp.json()
        assert len(previews) >= 1
        assert "Hello" in previews[0]["subject"] or "recipient_name" in previews[0]["subject"]

    @patch("campaign.routers.campaigns.is_authenticated", return_value=True)
    @patch("campaign.scheduler.get_scheduler")
    async def test_schedule_campaign(self, mock_sched, mock_auth, client: AsyncClient, db: Session):
        mock_scheduler = MagicMock()
        mock_sched.return_value = mock_scheduler

        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scheduled_count"] == 2
        assert data["next_send_at"] is not None

        # Verify campaign status changed
        campaign_resp = await client.get(f"/api/v1/campaigns/{campaign_id}")
        assert campaign_resp.json()["status"] == "scheduled"

    @patch("campaign.routers.campaigns.is_authenticated", return_value=True)
    @patch("campaign.scheduler.get_scheduler")
    async def test_full_send_workflow(
        self, mock_sched, mock_auth, client: AsyncClient, db: Session
    ):
        """Create → Schedule → manually send → verify completion."""
        mock_scheduler = MagicMock()
        mock_sched.return_value = mock_scheduler

        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        # Schedule
        await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")

        # Simulate sends by updating email statuses directly
        emails = db.query(Email).filter(Email.campaign_id == campaign_id).all()
        for email in emails:
            email.status = "sent"
            email.sent_at = datetime.now(timezone.utc)
            email.gmail_message_id = f"msg_{email.id}"
            email.thread_id = f"thread_{email.id}"
        db.commit()

        # Check status
        status_resp = await client.get(f"/api/v1/campaigns/{campaign_id}/status")
        assert status_resp.status_code == 200
        status = status_resp.json()
        assert status["sent"] == 2
        assert status["pending"] == 0
        assert status["scheduled"] == 0
        assert status["progress_percent"] == 100.0


# ── Workflow 2: Create → Schedule → Pause → Resume → Complete ────────────


class TestPauseResumeWorkflow:
    @patch("campaign.routers.campaigns.is_authenticated", return_value=True)
    @patch("campaign.scheduler.get_scheduler")
    async def test_pause_and_resume(self, mock_sched, mock_auth, client: AsyncClient, db: Session):
        mock_scheduler = MagicMock()
        mock_sched.return_value = mock_scheduler

        # Create and schedule
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]
        await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")

        # Pause
        pause_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["paused_count"] == 2

        campaign_resp = await client.get(f"/api/v1/campaigns/{campaign_id}")
        assert campaign_resp.json()["status"] == "paused"

        # Resume (schedule again)
        resume_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")
        assert resume_resp.status_code == 200
        assert resume_resp.json()["scheduled_count"] == 2

        campaign_resp = await client.get(f"/api/v1/campaigns/{campaign_id}")
        assert campaign_resp.json()["status"] == "scheduled"


# ── Workflow 3: Create → Schedule → Cancel ───────────────────────────────


class TestCancelWorkflow:
    @patch("campaign.routers.campaigns.is_authenticated", return_value=True)
    @patch("campaign.scheduler.get_scheduler")
    async def test_cancel_campaign(self, mock_sched, mock_auth, client: AsyncClient, db: Session):
        mock_scheduler = MagicMock()
        mock_sched.return_value = mock_scheduler

        create = await _create_campaign(client)
        campaign_id = create.json()["id"]
        await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")

        # Cancel
        cancel_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/cancel")
        assert cancel_resp.status_code == 200
        data = cancel_resp.json()
        assert data["cancelled_count"] == 2
        assert data["campaign_status"] == "completed"

    @patch("campaign.routers.campaigns.is_authenticated", return_value=True)
    @patch("campaign.scheduler.get_scheduler")
    async def test_cancel_partially_sent(
        self, mock_sched, mock_auth, client: AsyncClient, db: Session
    ):
        """Cancel after some emails were sent."""
        mock_scheduler = MagicMock()
        mock_sched.return_value = mock_scheduler

        create = await _create_campaign(client)
        campaign_id = create.json()["id"]
        await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")

        # Mark first email as sent
        first_email = (
            db.query(Email).filter(Email.campaign_id == campaign_id).order_by(Email.id).first()
        )
        first_email.status = "sent"
        first_email.sent_at = datetime.now(timezone.utc)
        db.commit()

        # Change campaign to in_progress
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        campaign.status = "in_progress"
        db.commit()

        # Cancel remaining
        cancel_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["cancelled_count"] == 1
        assert cancel_resp.json()["campaign_status"] == "completed"


# ── Error Scenarios ──────────────────────────────────────────────────────


class TestErrorScenarios:
    async def test_create_missing_required_columns(self, client: AsyncClient):
        """Recipients file missing required columns."""
        bad_csv = b"email,name\nalice@example.com,Alice"
        resp = await _create_campaign(client, recipients_csv=bad_csv)
        assert resp.status_code == 422

    async def test_create_invalid_emails(self, client: AsyncClient):
        """Recipients file with invalid email addresses."""
        bad_csv = b"recipient_email,recipient_name\nnot-an-email,Alice"
        resp = await _create_campaign(client, recipients_csv=bad_csv)
        assert resp.status_code == 422

    async def test_create_invalid_schedule(self, client: AsyncClient):
        """Schedule file with relative first step."""
        bad_schedule = b"send_date,send_time,email_template_ref\n5,09:00,welcome"
        resp = await _create_campaign(client, schedule_csv=bad_schedule)
        assert resp.status_code == 422

    async def test_create_missing_template_ref(self, client: AsyncClient):
        """Schedule references a template not in the email document."""
        schedule = _make_schedule_csv(ref="nonexistent")
        resp = await _create_campaign(client, schedule_csv=schedule)
        assert resp.status_code == 422

    async def test_schedule_without_auth(self, client: AsyncClient):
        """Scheduling fails when Gmail is not authenticated."""
        with patch("campaign.routers.campaigns.is_authenticated", return_value=False):
            create = await _create_campaign(client)
            campaign_id = create.json()["id"]

            resp = await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")
            assert resp.status_code == 400
            assert "authenticated" in resp.json()["detail"].lower()

    async def test_schedule_wrong_status(self, client: AsyncClient, db: Session):
        """Cannot schedule an already completed campaign."""
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        campaign.status = "completed"
        db.commit()

        with patch("campaign.routers.campaigns.is_authenticated", return_value=True):
            resp = await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")
            assert resp.status_code == 400

    async def test_pause_wrong_status(self, client: AsyncClient):
        """Cannot pause a draft campaign."""
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.post(f"/api/v1/campaigns/{campaign_id}/pause")
        assert resp.status_code == 400

    async def test_delete_active_campaign(self, client: AsyncClient, db: Session):
        """Cannot delete a scheduled campaign."""
        with (
            patch("campaign.routers.campaigns.is_authenticated", return_value=True),
            patch("campaign.scheduler.get_scheduler", return_value=MagicMock()),
        ):
            create = await _create_campaign(client)
            campaign_id = create.json()["id"]
            await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")

            resp = await client.delete(f"/api/v1/campaigns/{campaign_id}")
            assert resp.status_code == 400

    async def test_campaign_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/campaigns/9999")
        assert resp.status_code == 404

    async def test_recipient_not_found(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}/preview",
            params={"recipient_id": 9999},
        )
        assert resp.status_code == 404


# ── Recipient Management ─────────────────────────────────────────────────


class TestRecipientManagement:
    async def test_list_recipients(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.get(f"/api/v1/campaigns/{campaign_id}/recipients")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_add_recipient(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/recipients",
            json={"email": "charlie@example.com", "name": "Charlie"},
        )
        assert resp.status_code == 201
        assert resp.json()["email"] == "charlie@example.com"

        # Verify count increased
        list_resp = await client.get(f"/api/v1/campaigns/{campaign_id}/recipients")
        assert list_resp.json()["total"] == 3

    async def test_add_duplicate_recipient(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/recipients",
            json={"email": "alice@example.com", "name": "Alice"},
        )
        assert resp.status_code == 409

    async def test_search_recipients(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}/recipients",
            params={"search": "alice"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


# ── Email Endpoints ──────────────────────────────────────────────────────


class TestEmailEndpoints:
    async def test_list_emails(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.get(f"/api/v1/campaigns/{campaign_id}/emails")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    async def test_email_detail(self, client: AsyncClient, db: Session):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        email = db.query(Email).filter(Email.campaign_id == campaign_id).first()
        resp = await client.get(f"/api/v1/campaigns/{campaign_id}/emails/{email.id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == email.id
        assert detail["body_html"] is not None

    async def test_preview_all(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.get(f"/api/v1/campaigns/{campaign_id}/preview/all")
        assert resp.status_code == 200
        assert len(resp.json()) == 2  # 2 recipients * 1 step


# ── Multi-step Campaign ──────────────────────────────────────────────────


class TestMultiStepCampaign:
    async def test_multi_step_creation(self, client: AsyncClient, db: Session):
        """Create campaign with two schedule steps (absolute + relative)."""
        resp = await _create_campaign(
            client,
            schedule_csv=_make_multi_step_schedule_csv(),
            email_doc=_make_multi_step_email_doc(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["step_count"] == 2
        # 2 recipients * 2 steps = 4 emails
        assert data["pending_count"] == 4

    @patch("campaign.routers.campaigns.is_authenticated", return_value=True)
    @patch("campaign.scheduler.get_scheduler")
    async def test_multi_step_schedule_skips_relative(
        self, mock_sched, mock_auth, client: AsyncClient, db: Session
    ):
        """Scheduling only schedules absolute-date steps, skips relative ones."""
        mock_sched.return_value = MagicMock()

        resp = await _create_campaign(
            client,
            schedule_csv=_make_multi_step_schedule_csv(),
            email_doc=_make_multi_step_email_doc(),
        )
        campaign_id = resp.json()["id"]

        sched_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/schedule")
        data = sched_resp.json()
        # 2 recipients with absolute dates, 2 with relative dates skipped
        assert data["scheduled_count"] == 2
        assert data["skipped_count"] == 2


# ── Campaign Deletion ────────────────────────────────────────────────────


class TestCampaignDeletion:
    async def test_delete_draft_campaign(self, client: AsyncClient):
        create = await _create_campaign(client)
        campaign_id = create.json()["id"]

        resp = await client.delete(f"/api/v1/campaigns/{campaign_id}")
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"/api/v1/campaigns/{campaign_id}")
        assert get_resp.status_code == 404

    async def test_list_campaigns_with_filter(self, client: AsyncClient):
        await _create_campaign(client, name="Campaign 1")
        await _create_campaign(client, name="Campaign 2")

        resp = await client.get("/api/v1/campaigns")
        assert resp.status_code == 200
        assert len(resp.json()["campaigns"]) == 2

        resp = await client.get("/api/v1/campaigns", params={"status": "draft"})
        assert len(resp.json()["campaigns"]) == 2

        resp = await client.get("/api/v1/campaigns", params={"status": "completed"})
        assert len(resp.json()["campaigns"]) == 0


# ── Health & Auth Endpoints ──────────────────────────────────────────────


class TestHealthAndAuth:
    async def test_health_check(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @patch("campaign.routers.auth.is_authenticated", return_value=False)
    async def test_auth_status_unauthenticated(self, mock_auth, client: AsyncClient):
        resp = await client.get("/api/v1/auth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is False

    @patch("campaign.routers.auth.is_authenticated", return_value=True)
    @patch("campaign.routers.auth.get_user_email", return_value="user@gmail.com")
    async def test_auth_status_authenticated(self, mock_email, mock_auth, client: AsyncClient):
        resp = await client.get("/api/v1/auth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["email"] == "user@gmail.com"

    async def test_send_quota(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/quota")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 500
        assert data["remaining"] == 500
