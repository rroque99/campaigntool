"""Recipient endpoints — list, detail, and manual add."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from campaign.database import get_db
from campaign.models import Campaign, CampaignEmailTemplate, CampaignScheduleStep, Email, Recipient
from campaign.parser import EmailTemplate
from campaign.scheduler import _schedule_send_job
from campaign.schemas import (
    RecipientCreate,
    RecipientCreateResponse,
    RecipientListResponse,
    RecipientResponse,
)
from campaign.templates import render_email

router = APIRouter(tags=["recipients"])


@router.get(
    "/campaigns/{campaign_id}/recipients",
    response_model=RecipientListResponse,
)
async def list_recipients(
    campaign_id: int,
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """List recipients for a campaign with pagination, filtering, and search."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = db.query(Recipient).filter(Recipient.campaign_id == campaign_id)

    # Search by email or name (case-insensitive partial match)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Recipient.email.ilike(pattern),
                Recipient.name.ilike(pattern),
            )
        )

    # Filter by email status
    if status:
        query = query.join(Email, Email.recipient_id == Recipient.id).filter(Email.status == status)
        query = query.distinct()

    total = query.count()
    offset = (page - 1) * page_size
    recipients = query.offset(offset).limit(page_size).all()

    items = []
    for r in recipients:
        # Get the most relevant email status for this recipient
        email_status = (
            db.query(Email.status)
            .filter(Email.recipient_id == r.id)
            .order_by(Email.step_order)
            .first()
        )
        items.append(
            RecipientResponse(
                id=r.id,
                email=r.email,
                name=r.name,
                custom_fields=r.custom_fields,
                email_status=email_status[0] if email_status else None,
            )
        )

    return RecipientListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    "/campaigns/{campaign_id}/recipients/{recipient_id}",
    response_model=RecipientResponse,
)
async def get_recipient(
    campaign_id: int,
    recipient_id: int,
    db: Session = Depends(get_db),
):
    """Get a single recipient with email status."""
    recipient = (
        db.query(Recipient)
        .filter(
            Recipient.id == recipient_id,
            Recipient.campaign_id == campaign_id,
        )
        .first()
    )
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    email_status = (
        db.query(Email.status)
        .filter(Email.recipient_id == recipient.id)
        .order_by(Email.step_order)
        .first()
    )

    return RecipientResponse(
        id=recipient.id,
        email=recipient.email,
        name=recipient.name,
        custom_fields=recipient.custom_fields,
        email_status=email_status[0] if email_status else None,
    )


@router.post(
    "/campaigns/{campaign_id}/recipients",
    status_code=201,
    response_model=RecipientCreateResponse,
)
async def add_recipient(
    campaign_id: int,
    body: RecipientCreate,
    db: Session = Depends(get_db),
):
    """Manually add a recipient to a campaign (any active status)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail="Cannot add recipients to a completed, failed, or cancelled campaign",
        )

    # Check duplicate email
    existing = (
        db.query(Recipient)
        .filter(
            Recipient.campaign_id == campaign_id,
            Recipient.email == str(body.email),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Recipient with email '{body.email}' already exists in this campaign",
        )

    recipient = Recipient(
        campaign_id=campaign_id,
        email=str(body.email),
        name=body.name,
        custom_fields=body.custom_fields,
    )
    db.add(recipient)
    db.flush()

    # Generate Email records for all schedule steps
    steps = (
        db.query(CampaignScheduleStep)
        .filter(CampaignScheduleStep.campaign_id == campaign_id)
        .order_by(CampaignScheduleStep.step_order)
        .all()
    )

    is_active = campaign.status in ("scheduled", "in_progress", "paused")
    new_emails = []

    # Load stored templates for re-rendering with new recipient's variables
    stored_templates = (
        db.query(CampaignEmailTemplate)
        .filter(CampaignEmailTemplate.campaign_id == campaign_id)
        .all()
    )
    template_map = {t.template_ref: t for t in stored_templates}

    # Build template variables for the new recipient
    variables = {
        "recipient_name": body.name or "",
        "recipient_email": str(body.email),
        **(body.custom_fields or {}),
    }

    for step in steps:
        stored = template_map.get(step.email_template_ref)
        if stored:
            template = EmailTemplate(
                ref=stored.template_ref,
                subject=stored.subject,
                body_html=stored.body_html,
                body_text=stored.body_text,
            )
            rendered = render_email(template, variables)
            email = Email(
                campaign_id=campaign_id,
                recipient_id=recipient.id,
                subject=rendered.subject,
                body_html=rendered.body_html,
                body_text=rendered.body_text,
                status="pending",
                step_order=step.step_order,
            )
        else:
            # Fallback: copy from existing email (pre-template campaigns)
            sample_email = (
                db.query(Email)
                .filter(
                    Email.campaign_id == campaign_id,
                    Email.step_order == step.step_order,
                )
                .first()
            )
            email = Email(
                campaign_id=campaign_id,
                recipient_id=recipient.id,
                subject=sample_email.subject if sample_email else "(no template)",
                body_html=sample_email.body_html if sample_email else "",
                body_text=sample_email.body_text if sample_email else "",
                status="pending",
                step_order=step.step_order,
            )
        db.add(email)
        new_emails.append((email, step))

    db.flush()  # assign IDs to new emails

    # For active campaigns, schedule emails with absolute dates immediately
    if is_active and campaign.status != "paused":
        for email, step in new_emails:
            if step.send_date is not None:
                local_dt = datetime.combine(step.send_date, step.send_time).astimezone()
                scheduled_at = local_dt.astimezone(timezone.utc)

                now = datetime.now(timezone.utc)
                if scheduled_at <= now:
                    scheduled_at = now + timedelta(minutes=1)

                email.scheduled_at = scheduled_at
                email.status = "scheduled"
                _schedule_send_job(email.id, scheduled_at)
            # Relative-date steps will be resolved when previous step completes

    db.commit()
    db.refresh(recipient)

    return RecipientCreateResponse(
        id=recipient.id,
        email=recipient.email,
        name=recipient.name,
        custom_fields=recipient.custom_fields,
        created_at=recipient.created_at,
    )
