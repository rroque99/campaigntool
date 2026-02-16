# Task 1.8 — Frontend Project Setup

**Phase:** 1 — Project Scaffolding
**Priority:** Medium
**Status:** Pending

## Description

Scaffold the React + TypeScript frontend with Vite, Tailwind CSS, and all required libraries.

## Steps

1. Scaffold project: `npm create vite@latest frontend -- --template react-ts`
2. Install production dependencies:
   ```bash
   cd frontend
   npm install react-router-dom @tanstack/react-query @tanstack/react-table axios
   ```
3. Install and configure Tailwind CSS:
   ```bash
   npm install -D tailwindcss @tailwindcss/vite
   ```
   - Add Tailwind plugin to `vite.config.ts`
   - Add `@import "tailwindcss"` to `src/index.css`
4. Configure Vite proxy in `vite.config.ts`:
   ```typescript
   server: {
     proxy: {
       '/api': 'http://localhost:8000'
     }
   }
   ```
5. Enable TypeScript strict mode in `tsconfig.json`
6. Create directory structure:
   ```
   frontend/src/api/
   frontend/src/pages/
   frontend/src/components/
   frontend/src/types/
   ```
7. Create `frontend/src/types/index.ts` with initial type stubs
8. Verify: `npm run dev` and `npm run build`

## Acceptance Criteria

- [ ] Vite dev server runs on port 5173
- [ ] Tailwind CSS classes render correctly
- [ ] API requests to `/api/*` are proxied to `localhost:8000`
- [ ] TypeScript compiles in strict mode
- [ ] `npm run build` produces output in `dist/`
