# Task 1.2 — Backend Python Project Setup

**Phase:** 1 — Project Scaffolding
**Priority:** High
**Status:** Pending

## Description

Create the Python backend project with `pyproject.toml`, install all dependencies, and set up the package structure.

## Steps

1. Create `backend/pyproject.toml`:
   - Name: `gmail-campaign-tool`
   - Version: `0.1.0`
   - Requires Python `>=3.11`
   - Core dependencies:
     - `fastapi>=0.104`
     - `uvicorn[standard]>=0.24`
     - `sqlalchemy>=2.0`
     - `alembic>=1.13`
     - `pydantic>=2.5`
     - `pydantic-settings>=2.1`
     - `google-api-python-client>=2.108`
     - `google-auth-oauthlib>=1.2`
     - `openpyxl>=3.1`
     - `python-docx>=1.1`
     - `markdown>=3.5`
     - `apscheduler>=3.10`
     - `python-multipart>=0.0.6`
   - Dev dependencies (optional `[dev]` extra):
     - `pytest>=7.4`
     - `pytest-mock>=3.12`
     - `pytest-asyncio>=0.23`
     - `httpx>=0.25`
     - `ruff>=0.1`
   - Ruff config: line-length 100, target-version py311
2. Create package structure:
   ```
   backend/src/campaign/__init__.py
   backend/src/campaign/routers/__init__.py
   ```
3. Install dependencies with uv: `cd backend && uv sync`
   - uv will automatically create a `.venv/` and install all dependencies
   - The `uv.lock` lockfile will be generated and should be committed to git
4. Verify: `uv run ruff check src/` and `uv run pytest` both exit cleanly

## Acceptance Criteria

- [ ] `uv sync` completes without errors and creates `backend/.venv/`
- [ ] `uv.lock` is generated and committed to version control
- [ ] `uv run ruff check src/` exits 0
- [ ] `uv run pytest` exits 0 (no tests yet)
- [ ] All dependencies are resolvable
