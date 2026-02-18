"""Email preview and delivery status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from campaign.database import get_db
from campaign.models import Campaign, Email, Recipient
from campaign.schemas import (
    EmailDetailResponse,
    EmailListResponse,
    EmailPreviewResponse,
    EmailStatusResponse,
)

router = APIRouter(tags=["emails"])


@router.get(
    "/campaigns/{campaign_id}/preview",
    response_model=list[EmailPreviewResponse],
)
async def preview_campaign(
    campaign_id: int,
    recipient_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Preview rendered emails for a campaign.

    If recipient_id is provided, returns previews for that recipient.
    Otherwise returns previews for the first recipient as a sample.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if recipient_id:
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
    else:
        recipient = db.query(Recipient).filter(Recipient.campaign_id == campaign_id).first()
        if not recipient:
            raise HTTPException(status_code=404, detail="No recipients in this campaign")

    emails = (
        db.query(Email)
        .filter(
            Email.campaign_id == campaign_id,
            Email.recipient_id == recipient.id,
        )
        .order_by(Email.step_order)
        .all()
    )

    return [
        EmailPreviewResponse(
            recipient_email=recipient.email,
            recipient_name=recipient.name,
            subject=e.subject or "",
            body_html=e.body_html or "",
            step_order=e.step_order,
            scheduled_at=e.scheduled_at,
            status=e.status,
        )
        for e in emails
    ]


@router.get(
    "/campaigns/{campaign_id}/preview/all",
    response_model=list[EmailPreviewResponse],
)
async def preview_all(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """Preview rendered emails for all recipients (for review before sending)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    emails = (
        db.query(Email)
        .join(Recipient, Email.recipient_id == Recipient.id)
        .filter(Email.campaign_id == campaign_id)
        .order_by(Recipient.id, Email.step_order)
        .all()
    )

    # Build a recipient lookup
    recipient_ids = {e.recipient_id for e in emails}
    recipients = db.query(Recipient).filter(Recipient.id.in_(recipient_ids)).all()
    recipient_map = {r.id: r for r in recipients}

    return [
        EmailPreviewResponse(
            recipient_email=recipient_map[e.recipient_id].email,
            recipient_name=recipient_map[e.recipient_id].name,
            subject=e.subject or "",
            body_html=e.body_html or "",
            step_order=e.step_order,
            scheduled_at=e.scheduled_at,
            status=e.status,
        )
        for e in emails
    ]


@router.get(
    "/campaigns/{campaign_id}/emails",
    response_model=EmailListResponse,
)
async def list_emails(
    campaign_id: int,
    status: str | None = None,
    sort_by: str = Query("scheduled_at", pattern="^(scheduled_at|sent_at)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all emails for a campaign with delivery status."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = db.query(Email).filter(Email.campaign_id == campaign_id)
    if status:
        query = query.filter(Email.status == status)

    # Sort
    sort_col = Email.scheduled_at if sort_by == "scheduled_at" else Email.sent_at
    query = query.order_by(sort_col.asc().nullslast(), Email.id)

    total = query.count()
    emails = query.offset((page - 1) * page_size).limit(page_size).all()

    # Build recipient lookup
    recipient_ids = {e.recipient_id for e in emails}
    recipients_list = db.query(Recipient).filter(Recipient.id.in_(recipient_ids)).all()
    recipient_map = {r.id: r for r in recipients_list}

    items = []
    for e in emails:
        r = recipient_map.get(e.recipient_id)
        items.append(
            EmailStatusResponse(
                id=e.id,
                recipient_email=r.email if r else "",
                recipient_name=r.name if r else None,
                subject=e.subject,
                status=e.status,
                step_order=e.step_order,
                scheduled_at=e.scheduled_at,
                sent_at=e.sent_at,
                error_message=e.error_message,
            )
        )

    return EmailListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get(
    "/campaigns/{campaign_id}/emails/{email_id}",
    response_model=EmailDetailResponse,
)
async def get_email_detail(
    campaign_id: int,
    email_id: int,
    db: Session = Depends(get_db),
):
    """Get full detail for a single email including rendered content and delivery metadata."""
    email = db.query(Email).filter(Email.id == email_id, Email.campaign_id == campaign_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    recipient = db.query(Recipient).filter(Recipient.id == email.recipient_id).first()

    return EmailDetailResponse(
        id=email.id,
        recipient_email=recipient.email if recipient else "",
        recipient_name=recipient.name if recipient else None,
        subject=email.subject,
        body_html=email.body_html,
        body_text=email.body_text,
        status=email.status,
        step_order=email.step_order,
        scheduled_at=email.scheduled_at,
        sent_at=email.sent_at,
        error_message=email.error_message,
        gmail_message_id=email.gmail_message_id,
        thread_id=email.thread_id,
    )
