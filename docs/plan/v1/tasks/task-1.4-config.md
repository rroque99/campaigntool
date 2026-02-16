# Task 1.4 — Configuration Module

**Phase:** 1 — Project Scaffolding
**Priority:** High
**Status:** Pending

## Description

Create a centralized configuration module using `pydantic-settings` that loads settings from environment variables and `.env` files.

## Steps

1. Create `backend/src/campaign/config.py`:
   ```python
   from pathlib import Path
   from pydantic_settings import BaseSettings

   class Settings(BaseSettings):
       database_url: str = "sqlite:///./campaign.db"
       credentials_dir: Path = Path("../credentials")
       cors_origins: list[str] = ["http://localhost:5173"]
       gmail_scopes: list[str] = [
           "https://www.googleapis.com/auth/gmail.send",
           "https://www.googleapis.com/auth/gmail.readonly",
       ]
       daily_send_limit: int = 500
       api_prefix: str = "/api/v1"

       model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

   settings = Settings()
   ```
2. Add `.env` to `.gitignore` (should already be there from Task 1.1)
3. Create `backend/.env.example` with documented defaults

## Acceptance Criteria

- [ ] `from campaign.config import settings` works
- [ ] Default values are correct
- [ ] Environment variables override defaults (e.g., `DATABASE_URL=...`)
- [ ] `.env` file is loaded if present
- [ ] `credentials_dir` is a `pathlib.Path`
