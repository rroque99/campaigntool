# Task 1.1 — Initialize Git Repository & Project Root

**Phase:** 1 — Project Scaffolding
**Priority:** High
**Status:** Pending

## Description

Set up the Git repository, create `.gitignore`, and establish the top-level directory structure for the entire project.

## Steps

1. Run `git init` in the project root
2. Create `.gitignore` with the following entries:
   ```
   # Credentials
   credentials/
   !credentials/.gitkeep

   # Python
   .venv/
   __pycache__/
   *.pyc
   .pytest_cache/
   *.egg-info/
   .ruff_cache/

   # Node
   node_modules/
   dist/

   # Environment
   .env
   .env.*

   # Database
   *.db
   *.sqlite

   # IDE
   .vscode/
   .idea/

   # Vite
   .vite/
   ```
3. Create directory skeleton:
   ```
   backend/src/campaign/routers/
   frontend/src/
   credentials/
   examples/
   docs/
   ```
4. Add `.gitkeep` files to empty directories
5. Create initial `README.md`
6. Make initial commit

## Acceptance Criteria

- [x] Git repository initialized
- [ ] `.gitignore` covers all sensitive and generated files
- [ ] Directory skeleton exists
- [ ] Initial commit is clean
