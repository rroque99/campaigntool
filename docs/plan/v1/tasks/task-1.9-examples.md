# Task 1.9 — Example Files

**Phase:** 1 — Project Scaffolding
**Priority:** Low
**Status:** Pending

## Description

Create sample spreadsheet and email template files that demonstrate the expected format and can be used for testing.

## Steps

1. Delete `examples/sample_campaign.xlsx` (replaced by split files below)

2. Create `examples/sample_recipients.xlsx`:
   - Columns: `recipient_email`, `recipient_name`, `company`, `role`
   - 5 sample rows:
     | recipient_email | recipient_name | company | role |
     |---|---|---|---|
     | jane@example.com | Jane Smith | Acme Corp | CTO |
     | bob@example.com | Bob Johnson | Globex | VP Engineering |
     | alice@example.com | Alice Williams | Initech | Director |
     | charlie@example.com | Charlie Brown | Umbrella | CEO |
     | diana@example.com | Diana Prince | Wayne Ent | CTO |

3. Create `examples/sample_schedule.xlsx`:
   - Columns: `send_date`, `send_time`, `email_template_ref`
   - 2 rows:
     | send_date | send_time | email_template_ref |
     |---|---|---|
     | 2026-03-01 | 09:00 | intro |
     | 5 | 09:00 | followup |
   - Row 1: absolute date (first email)
   - Row 2: relative date — 5 days after the previous email was sent

4. Keep `examples/sample_emails.md` unchanged (already has "intro" and "followup" templates)

## Acceptance Criteria

- [ ] Both XLSX files open correctly in spreadsheet applications
- [ ] Recipients file has recipient_email, recipient_name, and custom columns
- [ ] Schedule file has send_date, send_time, email_template_ref columns
- [ ] Schedule file row 2 uses relative date format (integer)
- [ ] Email templates contain `{{variable}}` placeholders matching spreadsheet columns
- [ ] Two distinct templates with different `ref` identifiers
- [ ] Send dates are in the future
