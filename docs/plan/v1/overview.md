# Gmail Email Campaign Tool — Implementation Plan

## Overview

This document outlines the full implementation plan for the Gmail Email Campaign Tool, a local web application for managing and sending email campaigns via the Gmail API. The project is split into **6 phases**, each building on the previous one.

## Phases

| Phase | Name | Description | Dependencies |
|-------|------|-------------|--------------|
| 1 | [Project Scaffolding & Infrastructure](phase-1-scaffolding.md) | Set up repos, tooling, database, and project skeleton | None |
| 2 | [Gmail Authentication & Integration](phase-2-gmail-auth.md) | OAuth2 flow, token management, Gmail API send | Phase 1 |
| 3 | [Campaign Management Backend](phase-3-campaign-backend.md) | File parsing, campaign CRUD, recipient handling, email templates | Phase 1 |
| 4 | [Scheduling & Email Delivery](phase-4-scheduling.md) | APScheduler integration, send pipeline, status tracking | Phases 2 & 3 |
| 5 | [Frontend Application](phase-5-frontend.md) | React UI with all pages, components, and API integration | Phase 3 (partial Phase 4) |
| 6 | [Integration, Polish & Deployment](phase-6-integration.md) | End-to-end testing, error handling, production build, docs | Phases 4 & 5 |

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│              React Frontend (Vite)          │
│  Dashboard | Campaigns | Preview | Settings │
│        React Query (polling 10s)            │
└────────────────┬────────────────────────────┘
                 │ HTTP (JSON)
                 ▼
┌─────────────────────────────────────────────┐
│            FastAPI Backend                  │
│  /api/v1/auth  /api/v1/campaigns  ...       │
│                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ │
│  │ Parser    │ │ Templates │ │ Scheduler │ │
│  │ (CSV/XLSX)│ │ (Jinja2)  │ │(APSched)  │ │
│  └───────────┘ └───────────┘ └─────┬─────┘ │
│                                    │        │
│                    ┌───────────────┤        │
│                    │ Reply Monitor │        │
│                    │ (Gmail Hist.) │        │
│                    └───────┬───────┘        │
│                                    │        │
│  ┌─────────────────────────────────┘        │
│  │  gmail.py (isolated Gmail API calls)     │
│  └──────────┬──────────────────────┘        │
│             │                               │
│  ┌──────────▼──────────┐                    │
│  │  SQLite (SQLAlchemy) │                   │
│  │  + Alembic migrations│                   │
│  └─────────────────────┘                    │
└─────────────────────────────────────────────┘
                 │
                 ▼
        Google Gmail API (OAuth2)
```

## Conventions

- All backend code lives under `backend/src/campaign/`
- All frontend code lives under `frontend/src/`
- Every database schema change requires an Alembic migration
- Gmail API calls are isolated in `gmail.py` — never imported elsewhere directly
- OAuth credentials are stored in `credentials/` and `.gitignore`'d
- All timestamps are UTC in the database; the frontend handles timezone display
- Template variables use `{{variable_name}}` syntax
- Campaigns use two input files: a recipients list and a campaign schedule (not a single spreadsheet)
- Schedule `send_date` supports relative values (integer = days after previous email sent)
- Reply detection: if a recipient replies, remaining emails for that recipient are cancelled
