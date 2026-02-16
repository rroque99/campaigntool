"""APScheduler integration — job management, email send pipeline, reply monitoring.

The scheduler runs within the FastAPI process. Jobs persist in SQLite so they
survive restarts. All Gmail API calls go through gmail.py.
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func

from campaign.auth import is_authenticated
from campaign.config import settings
from campaign.database import SessionLocal
from campaign.gmail import GmailError, check_replies, send_email
from campaign.models import (
    Campaign,
    CampaignScheduleStep,
    Email,
    Recipient,
    ReplyCheckState,
)

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

# Maximum retries for transient send errors
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 5


def get_scheduler() -> BackgroundScheduler:
    """Return the scheduler instance. Raises RuntimeError if not started."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call start_scheduler() first.")
    return _scheduler


def start_scheduler() -> None:
    """Initialize and start the APScheduler BackgroundScheduler."""
    global _scheduler

    # Use a separate SQLite database for APScheduler jobs to avoid
    # "database is locked" contention with the main app database.
    scheduler_db_url = settings.database_url.replace("campaign.db", "scheduler_jobs.db")
    jobstores = {
        "default": SQLAlchemyJobStore(url=scheduler_db_url),
    }
    job_defaults = {
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 3600,  # allow 1 hour of misfire grace
    }

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        job_defaults=job_defaults,
        timezone="UTC",
    )

    _scheduler.add_listener(_on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    _scheduler.start()
    logger.info("Scheduler started.")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped.")
        _scheduler = None


def _on_job_event(event):
    """Log job execution and error events."""
    if event.exception:
        logger.error("Job %s raised an exception: %s", event.job_id, event.exception)
    else:
        logger.info("Job %s executed successfully.", event.job_id)


# ---------------------------------------------------------------------------
# Email send job
# ---------------------------------------------------------------------------


def send_email_job(email_id: int, retry_count: int = 0) -> None:
    """APScheduler job: send a single email and update its status.

    Uses a fresh DB session (runs in a background thread). On transient
    failures, reschedules itself with exponential backoff up to MAX_RETRIES.
    """
    db = SessionLocal()
    try:
        email = db.query(Email).filter(Email.id == email_id).first()
        if email is None:
            logger.warning("send_email_job: Email %d not found, skipping.", email_id)
            return

        # Only send if still scheduled
        if email.status != "scheduled":
            logger.info(
                "send_email_job: Email %d status is '%s', skipping.", email_id, email.status
            )
            return

        # Check daily quota
        today_utc = datetime.now(timezone.utc).date()
        sent_today = (
            db.query(func.count(Email.id))
            .filter(Email.status == "sent", func.date(Email.sent_at) == today_utc)
            .scalar()
            or 0
        )
        if sent_today >= settings.daily_send_limit:
            logger.warning(
                "Daily send limit (%d) reached. Rescheduling email %d for tomorrow.",
                settings.daily_send_limit,
                email_id,
            )
            tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
            reschedule_time = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
            _schedule_send_job(email_id, reschedule_time)
            return

        # Load recipient for the to address
        recipient = db.query(Recipient).filter(Recipient.id == email.recipient_id).first()
        if recipient is None:
            email.status = "failed"
            email.error_message = "Recipient not found"
            db.commit()
            return

        # Send via Gmail API
        try:
            result = send_email(
                to=recipient.email,
                subject=email.subject or "",
                body_html=email.body_html or "",
                body_text=email.body_text or "",
                thread_id=email.thread_id,
            )
            email.status = "sent"
            email.sent_at = datetime.now(timezone.utc)
            email.gmail_message_id = result.message_id
            email.thread_id = result.thread_id
            db.commit()

            logger.info("Email %d sent successfully (message_id=%s).", email_id, result.message_id)

            # Resolve next relative-date step for this recipient
            _resolve_next_relative_step(db, email)

            # Check if campaign is complete
            _update_campaign_status(db, email.campaign_id)

        except GmailError as e:
            if e.error_code == "rate_limited" and retry_count < MAX_RETRIES:
                delay = RETRY_BASE_DELAY_SECONDS * (2**retry_count)
                logger.warning(
                    "Transient error sending email %d (attempt %d/%d): %s. Retrying in %ds.",
                    email_id,
                    retry_count + 1,
                    MAX_RETRIES,
                    e.message,
                    delay,
                )
                retry_time = datetime.now(timezone.utc) + timedelta(seconds=delay)
                scheduler = get_scheduler()
                scheduler.add_job(
                    send_email_job,
                    "date",
                    run_date=retry_time,
                    args=[email_id, retry_count + 1],
                    id=f"retry_email_{email_id}_{retry_count + 1}",
                    replace_existing=True,
                )
                return

            # Permanent failure or retries exhausted
            email.status = "failed"
            email.error_message = e.message
            db.commit()
            logger.error("Email %d failed permanently: %s", email_id, e.message)

            _update_campaign_status(db, email.campaign_id)

    except Exception:
        logger.exception("Unexpected error in send_email_job for email %d", email_id)
        try:
            email = db.query(Email).filter(Email.id == email_id).first()
            if email and email.status == "scheduled":
                email.status = "failed"
                email.error_message = "Unexpected scheduler error"
                db.commit()
        except Exception:
            logger.exception("Failed to update email status after error")
    finally:
        db.close()


def _resolve_next_relative_step(db, sent_email: Email) -> None:
    """After an email is sent, resolve the next relative-date step for this recipient.

    If the next schedule step uses relative_days, compute scheduled_at from
    the actual sent_at + relative_days and create the APScheduler job.
    """
    current_step_order = sent_email.step_order
    if current_step_order is None:
        return

    next_step = (
        db.query(CampaignScheduleStep)
        .filter(
            CampaignScheduleStep.campaign_id == sent_email.campaign_id,
            CampaignScheduleStep.step_order == current_step_order + 1,
        )
        .first()
    )

    if next_step is None or next_step.relative_days is None:
        return  # No next step, or next step uses absolute date

    # Find the email record for this recipient + next step
    next_email = (
        db.query(Email)
        .filter(
            Email.campaign_id == sent_email.campaign_id,
            Email.recipient_id == sent_email.recipient_id,
            Email.step_order == current_step_order + 1,
        )
        .first()
    )

    if next_email is None or next_email.status not in ("pending", "scheduled"):
        return

    # Compute scheduled_at from sent_at + relative_days + send_time
    # Interpret send_time as local system time
    sent_local = sent_email.sent_at.astimezone()
    base_date = sent_local.date() + timedelta(days=next_step.relative_days)
    local_dt = datetime.combine(base_date, next_step.send_time).astimezone()
    scheduled_at = local_dt.astimezone(timezone.utc)

    # If the computed time is in the past, send ASAP (1 minute from now)
    now = datetime.now(timezone.utc)
    if scheduled_at <= now:
        scheduled_at = now + timedelta(minutes=1)

    next_email.scheduled_at = scheduled_at
    next_email.status = "scheduled"
    db.commit()

    _schedule_send_job(next_email.id, scheduled_at)
    logger.info(
        "Resolved relative step %d for recipient %d: scheduled_at=%s",
        next_step.step_order,
        sent_email.recipient_id,
        scheduled_at.isoformat(),
    )


def _update_campaign_status(db, campaign_id: int) -> None:
    """Update campaign status based on email statuses.

    Transitions:
    - scheduled -> in_progress when at least one email is sent/failed
    - in_progress -> completed when all emails are sent/failed/cancelled
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign is None:
        return

    status_counts = dict(
        db.query(Email.status, func.count(Email.id))
        .filter(Email.campaign_id == campaign_id)
        .group_by(Email.status)
        .all()
    )

    sent = status_counts.get("sent", 0)
    failed = status_counts.get("failed", 0)
    pending = status_counts.get("pending", 0)
    scheduled = status_counts.get("scheduled", 0)

    # If any email has been sent/failed, campaign is in_progress
    if campaign.status == "scheduled" and (sent > 0 or failed > 0):
        campaign.status = "in_progress"
        db.commit()

    # If no emails are pending or scheduled, campaign is done
    if campaign.status in ("scheduled", "in_progress") and pending == 0 and scheduled == 0:
        if failed > 0 and sent == 0:
            campaign.status = "failed"
        else:
            campaign.status = "completed"
        db.commit()


# ---------------------------------------------------------------------------
# Scheduling helpers
# ---------------------------------------------------------------------------


def _schedule_send_job(email_id: int, run_date: datetime) -> str:
    """Add an APScheduler job to send an email at the given time.

    Returns the job ID.
    """
    scheduler = get_scheduler()
    job_id = f"send_email_{email_id}"
    scheduler.add_job(
        send_email_job,
        "date",
        run_date=run_date,
        args=[email_id],
        id=job_id,
        replace_existing=True,
    )
    return job_id


def schedule_campaign(db, campaign_id: int) -> dict:
    """Schedule all pending emails with absolute dates for a campaign.

    Returns dict with scheduled_count, skipped_count, next_send_at.
    """
    emails = (
        db.query(Email)
        .filter(
            Email.campaign_id == campaign_id,
            Email.status == "pending",
        )
        .all()
    )

    # Load schedule steps for this campaign
    steps = (
        db.query(CampaignScheduleStep).filter(CampaignScheduleStep.campaign_id == campaign_id).all()
    )
    step_map = {s.step_order: s for s in steps}

    scheduled_count = 0
    skipped_count = 0
    next_send_at = None

    for email in emails:
        step = step_map.get(email.step_order)
        if step is None:
            skipped_count += 1
            continue

        # Only schedule emails whose step has an absolute send_date
        if step.send_date is not None:
            # Interpret schedule times as local system time, then convert to UTC.
            local_dt = datetime.combine(step.send_date, step.send_time).astimezone()
            scheduled_at = local_dt.astimezone(timezone.utc)

            # If the time is in the past, schedule for 1 minute from now
            now = datetime.now(timezone.utc)
            if scheduled_at <= now:
                scheduled_at = now + timedelta(minutes=1)

            email.scheduled_at = scheduled_at
            email.status = "scheduled"
            _schedule_send_job(email.id, scheduled_at)
            scheduled_count += 1

            if next_send_at is None or scheduled_at < next_send_at:
                next_send_at = scheduled_at
        else:
            # Relative date — will be resolved when previous step completes
            skipped_count += 1

    db.commit()
    return {
        "scheduled_count": scheduled_count,
        "skipped_count": skipped_count,
        "next_send_at": next_send_at,
    }


def pause_campaign(db, campaign_id: int) -> int:
    """Pause a campaign: remove APScheduler jobs and revert scheduled emails to pending.

    Returns count of paused emails.
    """
    scheduler = get_scheduler()

    emails = (
        db.query(Email)
        .filter(
            Email.campaign_id == campaign_id,
            Email.status == "scheduled",
        )
        .all()
    )

    paused_count = 0
    for email in emails:
        job_id = f"send_email_{email.id}"
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass  # Job may have already fired or been removed
        email.status = "pending"
        email.scheduled_at = None
        paused_count += 1

    db.commit()
    return paused_count


def cancel_campaign(db, campaign_id: int) -> int:
    """Cancel all remaining unsent emails for a campaign.

    Returns count of cancelled emails.
    """
    scheduler = get_scheduler()

    emails = (
        db.query(Email)
        .filter(
            Email.campaign_id == campaign_id,
            Email.status.in_(["pending", "scheduled"]),
        )
        .all()
    )

    cancelled_count = 0
    for email in emails:
        if email.status == "scheduled":
            job_id = f"send_email_{email.id}"
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass
        email.status = "cancelled"
        cancelled_count += 1

    db.commit()
    return cancelled_count


# ---------------------------------------------------------------------------
# Reply monitoring job
# ---------------------------------------------------------------------------


def check_replies_job() -> None:
    """Periodic job: check for replies and cancel remaining emails for replying recipients.

    Uses the Gmail History API via gmail.check_replies(). Runs every
    reply_check_interval_minutes.
    """
    if not is_authenticated():
        logger.debug("check_replies_job: Not authenticated, skipping.")
        return

    db = SessionLocal()
    try:
        # Load or create reply check state
        state = db.query(ReplyCheckState).first()
        if state is None:
            state = ReplyCheckState()
            db.add(state)
            db.flush()

        try:
            result = check_replies(state.history_id)
        except GmailError as e:
            logger.error("check_replies_job: Gmail API error: %s", e.message)
            return

        state.history_id = result.new_history_id
        state.last_checked_at = datetime.now(timezone.utc)

        if result.replied_thread_ids:
            logger.info(
                "check_replies_job: Found replies in %d threads.", len(result.replied_thread_ids)
            )
            _cancel_emails_for_replied_threads(db, result.replied_thread_ids)

        db.commit()

    except Exception:
        logger.exception("Unexpected error in check_replies_job")
    finally:
        db.close()


def _cancel_emails_for_replied_threads(db, thread_ids: list[str]) -> None:
    """Cancel unsent emails for recipients who replied (matched by thread_id)."""
    scheduler = get_scheduler()

    # Find emails with matching thread_ids
    replied_emails = (
        db.query(Email).filter(Email.thread_id.in_(thread_ids), Email.status == "sent").all()
    )

    logger.info(
        "Reply thread matching: %d thread_ids received, %d sent emails matched.",
        len(thread_ids),
        len(replied_emails),
    )
    if not replied_emails:
        logger.info("No sent emails match replied thread_ids: %s", thread_ids)

    # Collect unique recipient IDs and campaign IDs from replied threads
    recipient_campaign_pairs = set()
    for email in replied_emails:
        recipient_campaign_pairs.add((email.recipient_id, email.campaign_id))

    # Cancel all remaining unsent emails for those recipients
    for recipient_id, campaign_id in recipient_campaign_pairs:
        unsent_emails = (
            db.query(Email)
            .filter(
                Email.recipient_id == recipient_id,
                Email.campaign_id == campaign_id,
                Email.status.in_(["pending", "scheduled"]),
            )
            .all()
        )

        if not unsent_emails:
            logger.info(
                "No unsent emails found for recipient %d in campaign %d (all already sent).",
                recipient_id,
                campaign_id,
            )

        for email in unsent_emails:
            if email.status == "scheduled":
                job_id = f"send_email_{email.id}"
                try:
                    scheduler.remove_job(job_id)
                except Exception:
                    pass
            email.status = "cancelled"
            logger.info(
                "Cancelled email %d for recipient %d (reply detected in thread).",
                email.id,
                recipient_id,
            )

    db.flush()

    # Update campaign statuses
    campaign_ids = {cid for _, cid in recipient_campaign_pairs}
    for cid in campaign_ids:
        _update_campaign_status(db, cid)


def start_reply_monitor() -> None:
    """Register the reply monitoring periodic job."""
    scheduler = get_scheduler()
    scheduler.add_job(
        check_replies_job,
        "interval",
        minutes=settings.reply_check_interval_minutes,
        id="check_replies",
        replace_existing=True,
    )
    logger.info("Reply monitor started (every %d minutes).", settings.reply_check_interval_minutes)
