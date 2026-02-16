"""Campaign CRUD and scheduling endpoints."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from campaign.auth import is_authenticated
from campaign.database import get_db
from campaign.models import Campaign, CampaignEmailTemplate, CampaignScheduleStep, Email, Recipient
from campaign.parser import parse_email_document, parse_recipients_file, parse_schedule_file
from campaign.scheduler import cancel_campaign, pause_campaign, schedule_campaign
from campaign.schemas import (
    CampaignListResponse,
    CampaignResponse,
    CampaignStatusResponse,
    CancelResponse,
    PauseResponse,
    ScheduleResponse,
)
from campaign.templates import render_email

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _campaign_to_response(campaign: Campaign, db: Session) -> CampaignResponse:
    """Build a CampaignResponse with computed stats."""
    recipient_count = (
        db.query(func.count(Recipient.id)).filter(Recipient.campaign_id == campaign.id).scalar()
        or 0
    )
    email_counts = (
        db.query(Email.status, func.count(Email.id))
        .filter(Email.campaign_id == campaign.id)
        .group_by(Email.status)
        .all()
    )
    counts = dict(email_counts)
    step_count = (
        db.query(func.count(CampaignScheduleStep.id))
        .filter(CampaignScheduleStep.campaign_id == campaign.id)
        .scalar()
        or 0
    )

    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        recipients_filename=campaign.recipients_filename,
        schedule_filename=campaign.schedule_filename,
        step_count=step_count,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        recipient_count=recipient_count,
        sent_count=counts.get("sent", 0),
        failed_count=counts.get("failed", 0),
        pending_count=counts.get("pending", 0),
    )


@router.post("", status_code=201, response_model=CampaignResponse)
async def create_campaign(
    name: str = Form(...),
    description: str | None = Form(None),
    recipients_file: UploadFile = File(...),
    schedule_file: UploadFile = File(...),
    email_document: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Create a campaign from uploaded files."""
    # Parse recipients
    recipients_result = parse_recipients_file(recipients_file)
    if recipients_result.errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Recipients file has errors",
                "errors": recipients_result.errors,
            },
        )

    # Parse schedule
    schedule_result = parse_schedule_file(schedule_file)
    if schedule_result.errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Schedule file has errors",
                "errors": schedule_result.errors,
            },
        )

    # Parse email templates
    templates = parse_email_document(email_document)
    if not templates:
        raise HTTPException(
            status_code=422,
            detail={"message": "No email templates found in document"},
        )

    template_map = {t.ref: t for t in templates}

    # Validate schedule refs match templates
    missing_refs = [
        s.email_template_ref
        for s in schedule_result.steps
        if s.email_template_ref not in template_map
    ]
    if missing_refs:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Schedule references templates not found in document",
                "missing_refs": missing_refs,
                "available_refs": list(template_map.keys()),
            },
        )

    # Create campaign
    campaign = Campaign(
        name=name,
        description=description,
        recipients_filename=recipients_file.filename,
        schedule_filename=schedule_file.filename,
        status="draft",
    )
    db.add(campaign)
    db.flush()

    # Store raw email templates for later re-rendering (e.g. when adding new recipients)
    for ref, template in template_map.items():
        db.add(
            CampaignEmailTemplate(
                campaign_id=campaign.id,
                template_ref=ref,
                subject=template.subject,
                body_html=template.body_html,
                body_text=template.body_text,
            )
        )

    # Create schedule steps
    for step_data in schedule_result.steps:
        step = CampaignScheduleStep(
            campaign_id=campaign.id,
            step_order=step_data.step_order,
            send_date=step_data.send_date,
            relative_days=step_data.relative_days,
            send_time=step_data.send_time,
            email_template_ref=step_data.email_template_ref,
        )
        db.add(step)

    # Create recipients and emails (recipient x step)
    for rec_data in recipients_result.recipients:
        recipient = Recipient(
            campaign_id=campaign.id,
            email=rec_data.email,
            name=rec_data.name,
            custom_fields=rec_data.custom_fields,
        )
        db.add(recipient)
        db.flush()

        variables = {
            "recipient_name": rec_data.name or "",
            "recipient_email": rec_data.email,
            **rec_data.custom_fields,
        }

        for step_data in schedule_result.steps:
            template = template_map[step_data.email_template_ref]
            rendered = render_email(template, variables)
            email = Email(
                campaign_id=campaign.id,
                recipient_id=recipient.id,
                subject=rendered.subject,
                body_html=rendered.body_html,
                body_text=rendered.body_text,
                status="pending",
                step_order=step_data.step_order,
            )
            db.add(email)

    db.commit()
    db.refresh(campaign)

    return _campaign_to_response(campaign, db)


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """List all campaigns with summary stats."""
    query = db.query(Campaign)
    if status:
        query = query.filter(Campaign.status == status)
    query = query.order_by(Campaign.created_at.desc())
    campaigns = query.all()

    return CampaignListResponse(campaigns=[_campaign_to_response(c, db) for c in campaigns])


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Get a single campaign with stats."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_to_response(campaign, db)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Delete a campaign. Only allowed for draft, completed, or failed campaigns."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("draft", "completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot delete campaign with status '{campaign.status}'. "
                f"Only draft, completed, or failed campaigns can be deleted."
            ),
        )

    db.delete(campaign)
    db.commit()


@router.post("/{campaign_id}/schedule", response_model=ScheduleResponse)
async def schedule_campaign_endpoint(campaign_id: int, db: Session = Depends(get_db)):
    """Schedule all pending emails for a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("draft", "paused"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot schedule campaign with status '{campaign.status}'. "
                f"Only draft or paused campaigns can be scheduled."
            ),
        )

    if not is_authenticated():
        raise HTTPException(
            status_code=400,
            detail="Gmail is not authenticated. Please complete the OAuth flow first.",
        )

    result = schedule_campaign(db, campaign_id)

    # Update campaign status
    campaign.status = "scheduled"
    db.commit()

    return ScheduleResponse(
        scheduled_count=result["scheduled_count"],
        skipped_count=result["skipped_count"],
        next_send_at=result["next_send_at"],
    )


@router.post("/{campaign_id}/pause", response_model=PauseResponse)
async def pause_campaign_endpoint(campaign_id: int, db: Session = Depends(get_db)):
    """Pause a scheduled or in-progress campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("scheduled", "in_progress"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot pause campaign with status '{campaign.status}'. "
                f"Only scheduled or in-progress campaigns can be paused."
            ),
        )

    paused_count = pause_campaign(db, campaign_id)

    campaign.status = "paused"
    db.commit()

    return PauseResponse(paused_count=paused_count)


@router.post("/{campaign_id}/cancel", response_model=CancelResponse)
async def cancel_campaign_endpoint(campaign_id: int, db: Session = Depends(get_db)):
    """Cancel all remaining unsent emails for a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("draft", "scheduled", "in_progress", "paused"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot cancel campaign with status '{campaign.status}'. "
                f"Only active campaigns can be cancelled."
            ),
        )

    cancelled_count = cancel_campaign(db, campaign_id)

    # Determine final status
    failed_count = (
        db.query(func.count(Email.id))
        .filter(Email.campaign_id == campaign_id, Email.status == "failed")
        .scalar()
        or 0
    )
    sent_count = (
        db.query(func.count(Email.id))
        .filter(Email.campaign_id == campaign_id, Email.status == "sent")
        .scalar()
        or 0
    )

    if failed_count > 0 and sent_count == 0:
        campaign.status = "failed"
    else:
        campaign.status = "completed"
    db.commit()

    return CancelResponse(
        cancelled_count=cancelled_count,
        campaign_status=campaign.status,
    )


@router.get("/{campaign_id}/status", response_model=CampaignStatusResponse)
async def get_campaign_status(campaign_id: int, db: Session = Depends(get_db)):
    """Get real-time campaign progress and email status counts."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    status_counts = dict(
        db.query(Email.status, func.count(Email.id))
        .filter(Email.campaign_id == campaign_id)
        .group_by(Email.status)
        .all()
    )

    total = sum(status_counts.values())
    sent = status_counts.get("sent", 0)
    failed = status_counts.get("failed", 0)
    pending = status_counts.get("pending", 0)
    scheduled = status_counts.get("scheduled", 0)
    cancelled = status_counts.get("cancelled", 0)

    progress_percent = (sent / total * 100) if total > 0 else 0.0

    # Next send time
    next_send_at = (
        db.query(func.min(Email.scheduled_at))
        .filter(
            Email.campaign_id == campaign_id,
            Email.status == "scheduled",
            Email.scheduled_at.is_not(None),
        )
        .scalar()
    )

    # Estimated completion: rough estimate based on remaining scheduled emails
    estimated_completion = None
    if next_send_at and scheduled > 0:
        last_scheduled = (
            db.query(func.max(Email.scheduled_at))
            .filter(
                Email.campaign_id == campaign_id,
                Email.status == "scheduled",
                Email.scheduled_at.is_not(None),
            )
            .scalar()
        )
        if last_scheduled:
            estimated_completion = last_scheduled

    return CampaignStatusResponse(
        total_emails=total,
        sent=sent,
        failed=failed,
        pending=pending,
        scheduled=scheduled,
        cancelled=cancelled,
        progress_percent=round(progress_percent, 1),
        next_send_at=next_send_at,
        estimated_completion=estimated_completion,
    )
