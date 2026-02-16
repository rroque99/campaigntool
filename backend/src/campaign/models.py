from datetime import date, datetime, time, timezone

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from campaign.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipients_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schedule_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    recipients: Mapped[list["Recipient"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    emails: Mapped[list["Email"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    schedule_steps: Mapped[list["CampaignScheduleStep"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class Recipient(Base):
    __tablename__ = "recipients"
    __table_args__ = (
        Index("ix_recipients_campaign_id", "campaign_id"),
        Index("ix_recipients_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    campaign: Mapped["Campaign"] = relationship(back_populates="recipients")
    emails: Mapped[list["Email"]] = relationship(
        back_populates="recipient", cascade="all, delete-orphan"
    )


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        Index("ix_emails_campaign_id", "campaign_id"),
        Index("ix_emails_status", "status"),
        Index("ix_emails_scheduled_at", "scheduled_at"),
        Index("ix_emails_campaign_status", "campaign_id", "status"),
        Index("ix_emails_recipient_id", "recipient_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("recipients.id"), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    step_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="emails")
    recipient: Mapped["Recipient"] = relationship(back_populates="emails")


class CampaignScheduleStep(Base):
    __tablename__ = "campaign_schedule_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    send_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    relative_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    send_time: Mapped[time] = mapped_column(Time, nullable=False)
    email_template_ref: Mapped[str] = mapped_column(String(255), nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="schedule_steps")


class CampaignEmailTemplate(Base):
    """Stores the raw email template content so new recipients can be rendered later."""

    __tablename__ = "campaign_email_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    template_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)

    campaign: Mapped["Campaign"] = relationship()


class ReplyCheckState(Base):
    __tablename__ = "reply_check_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    history_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
