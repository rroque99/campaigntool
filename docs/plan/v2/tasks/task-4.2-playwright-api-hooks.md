# Task 4.2 — Add Playwright API Hooks

## File
`frontend/src/api/campaigns.ts`

## Description
Add React Query hooks for the new Playwright endpoints.

## Acceptance Criteria
- [ ] `usePlaywrightStatus()` hook queries `GET /auth/playwright/status`
- [ ] `usePlaywrightLogin()` mutation calls `POST /auth/playwright/login`
- [ ] Hooks follow existing patterns in the file (same query client, error handling)
