"""Tests for campaign, recipient, and email preview endpoints."""

import pytest

from campaign.models import Campaign

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


def _make_files():
    """Return (recipients, schedule, emails) as tuples for multipart upload."""
    return {
        "recipients_file": ("recipients.csv", SAMPLE_RECIPIENTS_CSV, "text/csv"),
        "schedule_file": ("schedule.csv", SAMPLE_SCHEDULE_CSV, "text/csv"),
        "email_document": ("emails.md", SAMPLE_EMAILS_MD, "text/markdown"),
    }


# ── Health Check ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_check(test_client):
    response = await test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── Campaign Creation ─────────────────────────────────────────────────────


class TestCreateCampaign:
    @pytest.mark.anyio
    async def test_create_campaign_success(self, test_client):
        files = _make_files()
        response = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Test Campaign", "description": "A test"},
            files=files,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Campaign"
        assert data["status"] == "draft"
        assert data["recipient_count"] == 2
        assert data["pending_count"] == 4  # 2 recipients x 2 steps
        assert data["step_count"] == 2

    @pytest.mark.anyio
    async def test_create_campaign_bad_recipients(self, test_client):
        files = _make_files()
        files["recipients_file"] = (
            "bad.csv",
            b"email,name\njane@example.com,Jane\n",
            "text/csv",
        )
        response = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Bad"},
            files=files,
        )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_create_campaign_bad_schedule(self, test_client):
        files = _make_files()
        files["schedule_file"] = (
            "bad.csv",
            b"send_date,send_time,email_template_ref\n5,09:00,intro\n",
            "text/csv",
        )
        response = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Bad"},
            files=files,
        )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_create_campaign_missing_template_ref(self, test_client):
        files = _make_files()
        # Schedule references "nonexistent" template
        files["schedule_file"] = (
            "bad.csv",
            b"send_date,send_time,email_template_ref\n2026-03-01,09:00,nonexistent\n",
            "text/csv",
        )
        response = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Bad"},
            files=files,
        )
        assert response.status_code == 422
        assert "missing_refs" in response.json()["detail"]


# ── Campaign List ─────────────────────────────────────────────────────────


class TestListCampaigns:
    @pytest.mark.anyio
    async def test_list_empty(self, test_client):
        response = await test_client.get("/api/v1/campaigns")
        assert response.status_code == 200
        assert response.json()["campaigns"] == []

    @pytest.mark.anyio
    async def test_list_with_campaigns(self, test_client):
        # Create a campaign first
        await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Campaign 1"},
            files=_make_files(),
        )
        response = await test_client.get("/api/v1/campaigns")
        assert response.status_code == 200
        campaigns = response.json()["campaigns"]
        assert len(campaigns) == 1
        assert campaigns[0]["name"] == "Campaign 1"

    @pytest.mark.anyio
    async def test_list_filter_by_status(self, test_client, test_db):
        # Create campaigns with different statuses
        c1 = Campaign(name="Draft", status="draft")
        c2 = Campaign(name="Completed", status="completed")
        test_db.add_all([c1, c2])
        test_db.commit()

        response = await test_client.get("/api/v1/campaigns?status=draft")
        campaigns = response.json()["campaigns"]
        assert len(campaigns) == 1
        assert campaigns[0]["name"] == "Draft"


# ── Campaign Detail ───────────────────────────────────────────────────────


class TestGetCampaign:
    @pytest.mark.anyio
    async def test_get_campaign(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Detail Test"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.get(f"/api/v1/campaigns/{campaign_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Detail Test"

    @pytest.mark.anyio
    async def test_get_campaign_not_found(self, test_client):
        response = await test_client.get("/api/v1/campaigns/9999")
        assert response.status_code == 404


# ── Campaign Deletion ─────────────────────────────────────────────────────


class TestDeleteCampaign:
    @pytest.mark.anyio
    async def test_delete_draft_campaign(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "To Delete"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.delete(f"/api/v1/campaigns/{campaign_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_resp = await test_client.get(f"/api/v1/campaigns/{campaign_id}")
        assert get_resp.status_code == 404

    @pytest.mark.anyio
    async def test_delete_active_campaign_blocked(self, test_client, test_db):
        campaign = Campaign(name="Active", status="in_progress")
        test_db.add(campaign)
        test_db.commit()

        response = await test_client.delete(f"/api/v1/campaigns/{campaign.id}")
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_delete_not_found(self, test_client):
        response = await test_client.delete("/api/v1/campaigns/9999")
        assert response.status_code == 404


# ── Recipient List ────────────────────────────────────────────────────────


class TestRecipientEndpoints:
    @pytest.mark.anyio
    async def test_list_recipients(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Recipient Test"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.get(f"/api/v1/campaigns/{campaign_id}/recipients")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert len(data["items"]) == 2

    @pytest.mark.anyio
    async def test_list_recipients_search(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Search Test"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.get(f"/api/v1/campaigns/{campaign_id}/recipients?search=jane")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "jane@example.com"

    @pytest.mark.anyio
    async def test_list_recipients_pagination(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Page Test"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.get(
            f"/api/v1/campaigns/{campaign_id}/recipients?page=1&page_size=1"
        )
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["page"] == 1

    @pytest.mark.anyio
    async def test_get_single_recipient(self, test_client, test_db):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Single Rec"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        # Get the first recipient
        list_resp = await test_client.get(f"/api/v1/campaigns/{campaign_id}/recipients")
        recipient_id = list_resp.json()["items"][0]["id"]

        response = await test_client.get(
            f"/api/v1/campaigns/{campaign_id}/recipients/{recipient_id}"
        )
        assert response.status_code == 200
        assert response.json()["id"] == recipient_id


# ── Manual Recipient Add ──────────────────────────────────────────────────


class TestAddRecipient:
    @pytest.mark.anyio
    async def test_add_recipient_to_draft(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Add Rec Test"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.post(
            f"/api/v1/campaigns/{campaign_id}/recipients",
            json={
                "email": "new@example.com",
                "name": "New Person",
                "custom_fields": {"company": "NewCo"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert data["name"] == "New Person"

        # Verify recipient count increased
        detail = await test_client.get(f"/api/v1/campaigns/{campaign_id}")
        assert detail.json()["recipient_count"] == 3

    @pytest.mark.anyio
    async def test_add_duplicate_email(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Dup Test"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.post(
            f"/api/v1/campaigns/{campaign_id}/recipients",
            json={"email": "jane@example.com", "name": "Jane Again"},
        )
        assert response.status_code == 409

    @pytest.mark.anyio
    async def test_add_to_non_draft_blocked(self, test_client, test_db):
        campaign = Campaign(name="Active", status="in_progress")
        test_db.add(campaign)
        test_db.commit()

        response = await test_client.post(
            f"/api/v1/campaigns/{campaign.id}/recipients",
            json={"email": "new@example.com", "name": "New"},
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_add_generates_email_records(self, test_client, test_db):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Email Gen Test"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        await test_client.post(
            f"/api/v1/campaigns/{campaign_id}/recipients",
            json={"email": "new2@example.com", "name": "New2"},
        )

        # New recipient should have 2 email records (one per step)
        detail = await test_client.get(f"/api/v1/campaigns/{campaign_id}")
        # 3 recipients x 2 steps = 6 pending
        assert detail.json()["pending_count"] == 6


# ── Email Preview ─────────────────────────────────────────────────────────


class TestEmailPreview:
    @pytest.mark.anyio
    async def test_preview_default_first_recipient(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Preview Test"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.get(f"/api/v1/campaigns/{campaign_id}/preview")
        assert response.status_code == 200
        previews = response.json()
        assert len(previews) == 2  # 2 schedule steps
        assert previews[0]["recipient_email"] in [
            "jane@example.com",
            "bob@example.com",
        ]
        assert previews[0]["subject"]  # should have a rendered subject

    @pytest.mark.anyio
    async def test_preview_specific_recipient(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Preview Spec"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        # Get recipients
        rec_resp = await test_client.get(f"/api/v1/campaigns/{campaign_id}/recipients")
        recipient_id = rec_resp.json()["items"][0]["id"]

        response = await test_client.get(
            f"/api/v1/campaigns/{campaign_id}/preview?recipient_id={recipient_id}"
        )
        assert response.status_code == 200
        previews = response.json()
        assert len(previews) == 2

    @pytest.mark.anyio
    async def test_preview_all(self, test_client):
        create_resp = await test_client.post(
            "/api/v1/campaigns",
            data={"name": "Preview All"},
            files=_make_files(),
        )
        campaign_id = create_resp.json()["id"]

        response = await test_client.get(f"/api/v1/campaigns/{campaign_id}/preview/all")
        assert response.status_code == 200
        previews = response.json()
        assert len(previews) == 4  # 2 recipients x 2 steps

    @pytest.mark.anyio
    async def test_preview_not_found(self, test_client):
        response = await test_client.get("/api/v1/campaigns/9999/preview")
        assert response.status_code == 404
