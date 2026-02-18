# Task 2.1 — Add Playwright Dependency

## File
`backend/pyproject.toml`

## Description
Add the `playwright` package as an optional dependency so it's only installed when needed.

## Acceptance Criteria
- [ ] `playwright` added to `pyproject.toml` as an optional dependency group (e.g., `[project.optional-dependencies] playwright = ["playwright>=1.40"]`)
- [ ] `uv sync` still works without the optional group
- [ ] `uv sync --extra playwright` installs Playwright
- [ ] Run `uv run playwright install chromium` to install the Chromium browser binary
- [ ] Verify Playwright is functional: `uv run python -c "from playwright.sync_api import sync_playwright; print('OK')"`
- [ ] Document in README that `playwright install chromium` is required after install

## Setup Commands
Run these in order from the `backend/` directory:
```bash
cd backend
uv sync --extra playwright
uv run playwright install chromium
```
