# Task 2.5 — Implement Selector Resilience

## File
`backend/src/campaign/playwright_sender.py`

## Description
Gmail's DOM uses obfuscated class names that change without notice. Implement a multi-selector fallback strategy for all key UI interactions.

## Acceptance Criteria
- [ ] Each UI interaction (compose, to, subject, body, send, confirmation) has a list of fallback selectors
- [ ] Selectors prioritize stable attributes: `aria-label`, `role`, `name`, `data-tooltip`
- [ ] When primary selector fails, next selector is tried automatically
- [ ] When all selectors fail, a descriptive `SendError` is raised indicating which interaction failed
- [ ] Selector lists are defined as module-level constants for easy maintenance
