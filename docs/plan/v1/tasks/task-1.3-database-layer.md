# Task 1.3 — Database Layer (SQLAlchemy + Alembic)

**Phase:** 1 — Project Scaffolding
**Priority:** High
**Status:** Pending

## Description

Set up SQLAlchemy ORM with all three database models (Campaign, Recipient, Email) and configure Alembic for migrations.

## Steps

1. Create `backend/src/campaign/database.py`:
   - SQLAlchemy `create_engine` with SQLite URL from config
   - `SessionLocal` via `sessionmaker`
   - `Base = declarative_base()`
   - `get_db()` generator for FastAPI dependency injection
2. Create `backend/src/campaign/models.py`:
   - **Campaign** model:
     - `id: Integer, primary_key`
     - `name: String(255), not null`
     - `description: Text, nullable`
     - `spreadsheet_filename: String(255)`
     - `status: String(20), default="draft"` — values: draft, scheduled, in_progress, paused, completed, failed
     - `created_at: DateTime, default=utcnow`
     - `updated_at: DateTime, default=utcnow, onupdate=utcnow`
     - Relationships: `recipients` (one-to-many), `emails` (one-to-many)
   - **Recipient** model:
     - `id: Integer, primary_key`
     - `campaign_id: Integer, ForeignKey("campaigns.id")`
     - `email: String(255), not null`
     - `name: String(255)`
     - `custom_fields: JSON`
     - `created_at: DateTime, default=utcnow`
     - Relationships: `campaign` (many-to-one), `emails` (one-to-many)
   - **Email** model:
     - `id: Integer, primary_key`
     - `campaign_id: Integer, ForeignKey("campaigns.id")`
     - `recipient_id: Integer, ForeignKey("recipients.id")`
     - `subject: String(500)`
     - `body_html: Text`
     - `body_text: Text`
     - `scheduled_at: DateTime`
     - `sent_at: DateTime, nullable`
     - `status: String(20), default="pending"` — values: pending, scheduled, sent, failed, cancelled
     - `error_message: Text, nullable`
     - `gmail_message_id: String(255), nullable`
     - Relationships: `campaign` (many-to-one), `recipient` (many-to-one)
3. Initialize Alembic:
   - `cd backend && alembic init alembic`
   - Edit `alembic.ini`: set `sqlalchemy.url`
   - Edit `alembic/env.py`: import `Base.metadata` from models
4. Generate initial migration:
   - `uv run alembic revision --autogenerate -m "initial schema"`
5. Apply migration:
   - `uv run alembic upgrade head`
6. Verify tables exist in SQLite

## Acceptance Criteria

- [ ] `uv run alembic upgrade head` creates campaigns, recipients, and emails tables
- [ ] `uv run alembic downgrade base` removes them
- [ ] Foreign key relationships are correct
- [ ] Cascade delete configured (deleting campaign removes recipients and emails)
- [ ] JSON column works for `custom_fields`
