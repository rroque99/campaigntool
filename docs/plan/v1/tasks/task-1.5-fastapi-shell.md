# Task 1.5 — FastAPI Application Shell

**Phase:** 1 — Project Scaffolding
**Priority:** High
**Status:** Pending

## Description

Create the FastAPI application entry point with CORS, router registration, lifespan management, and a health check endpoint.

## Steps

1. Create `backend/src/campaign/main.py`:
   - Import `FastAPI`, settings, and router modules
   - Define `lifespan` async context manager (placeholder for scheduler)
   - Instantiate `FastAPI(title="Gmail Campaign Tool", version="0.1.0", lifespan=lifespan)`
   - Add CORS middleware using `settings.cors_origins`
   - Include routers with `settings.api_prefix`:
     - `auth_router` at `/auth`
     - `campaigns_router` at `/campaigns`
     - `recipients_router` at `/recipients`
     - `emails_router` at `/emails`
   - Add health check: `GET /api/v1/health` -> `{"status": "ok"}`
2. Create router stubs:
   - `backend/src/campaign/routers/auth.py` — `APIRouter(prefix="/auth", tags=["auth"])`
   - `backend/src/campaign/routers/campaigns.py` — `APIRouter(prefix="/campaigns", tags=["campaigns"])`
   - `backend/src/campaign/routers/recipients.py` — `APIRouter(prefix="/recipients", tags=["recipients"])`
   - `backend/src/campaign/routers/emails.py` — `APIRouter(prefix="/emails", tags=["emails"])`
3. Test: `uv run uvicorn src.campaign.main:app --reload --port 8000`

## Acceptance Criteria

- [ ] Server starts without errors on port 8000
- [ ] `GET /api/v1/health` returns `{"status": "ok"}` with 200
- [ ] Swagger docs available at `/docs`
- [ ] CORS headers present for `localhost:5173` origins
- [ ] All router prefixes are correctly registered
