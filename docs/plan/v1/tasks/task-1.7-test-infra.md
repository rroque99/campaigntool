# Task 1.7 — Test Infrastructure

**Phase:** 1 — Project Scaffolding
**Priority:** Medium
**Status:** Pending

## Description

Set up pytest fixtures, test database, test client, and a smoke test to verify the testing pipeline works.

## Steps

1. Create `backend/tests/conftest.py`:
   - In-memory SQLite engine: `create_engine("sqlite:///:memory:")`
   - `test_db` fixture: creates all tables, yields session, drops tables
   - `test_client` fixture: overrides `get_db` dependency, returns `httpx.AsyncClient`
   - `sample_campaign_data` fixture: dict with valid campaign fields
2. Create placeholder test files (empty, with docstrings):
   - `backend/tests/test_campaigns.py`
   - `backend/tests/test_parser.py`
   - `backend/tests/test_gmail.py`
   - `backend/tests/test_scheduler.py`
   - `backend/tests/test_templates.py`
3. Add smoke test in `backend/tests/test_campaigns.py`:
   ```python
   async def test_health_check(test_client):
       response = await test_client.get("/api/v1/health")
       assert response.status_code == 200
       assert response.json() == {"status": "ok"}
   ```
4. Run `uv run pytest -v` and verify it passes

## Acceptance Criteria

- [ ] `uv run pytest -v` passes with the smoke test
- [ ] Test database is in-memory (no file artifacts)
- [ ] Fixtures are importable from conftest across all test files
- [ ] Test client correctly overrides the DB dependency
