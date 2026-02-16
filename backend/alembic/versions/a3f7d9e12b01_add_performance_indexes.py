"""add performance indexes

Revision ID: a3f7d9e12b01
Revises: 22b8bcf2936d
Create Date: 2026-02-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a3f7d9e12b01'
down_revision: Union[str, Sequence[str], None] = '22b8bcf2936d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for common query patterns."""
    op.create_index('ix_recipients_campaign_id', 'recipients', ['campaign_id'])
    op.create_index('ix_recipients_email', 'recipients', ['email'])
    op.create_index('ix_emails_campaign_id', 'emails', ['campaign_id'])
    op.create_index('ix_emails_status', 'emails', ['status'])
    op.create_index('ix_emails_scheduled_at', 'emails', ['scheduled_at'])
    op.create_index('ix_emails_campaign_status', 'emails', ['campaign_id', 'status'])
    op.create_index('ix_emails_recipient_id', 'emails', ['recipient_id'])


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('ix_emails_recipient_id', 'emails')
    op.drop_index('ix_emails_campaign_status', 'emails')
    op.drop_index('ix_emails_scheduled_at', 'emails')
    op.drop_index('ix_emails_status', 'emails')
    op.drop_index('ix_emails_campaign_id', 'emails')
    op.drop_index('ix_recipients_email', 'recipients')
    op.drop_index('ix_recipients_campaign_id', 'recipients')
