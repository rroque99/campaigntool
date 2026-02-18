# Task 3.2 — Update Sender Factory with Singleton Management

## File
`backend/src/campaign/sender_factory.py`

## Description
The Playwright sender needs a persistent browser instance. Update the factory to manage sender lifecycle as a singleton.

## Acceptance Criteria
- [ ] `get_sender()` returns a cached singleton instance
- [ ] `shutdown_sender()` cleans up resources and resets the singleton
- [ ] Singleton is created on first call to `get_sender()`
- [ ] Thread-safe (scheduler calls from background threads)
