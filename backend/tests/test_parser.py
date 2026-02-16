"""Tests for spreadsheet and document parsing."""

import io
from datetime import date, time
from unittest.mock import MagicMock

import openpyxl

from campaign.parser import (
    parse_email_document,
    parse_recipients_file,
    parse_schedule_file,
)

# ── Helpers ───────────────────────────────────────────────────────────────


def _make_csv_upload(content: str, filename: str = "test.csv") -> MagicMock:
    upload = MagicMock()
    upload.filename = filename
    upload.file = io.BytesIO(content.encode("utf-8"))
    return upload


def _make_xlsx_upload(
    headers: list[str],
    rows: list[list],
    filename: str = "test.xlsx",
) -> MagicMock:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    upload = MagicMock()
    upload.filename = filename
    upload.file = buf
    return upload


def _make_md_upload(content: str, filename: str = "emails.md") -> MagicMock:
    upload = MagicMock()
    upload.filename = filename
    upload.file = io.BytesIO(content.encode("utf-8"))
    return upload


# ── Recipients CSV ────────────────────────────────────────────────────────


class TestParseRecipientsCSV:
    def test_valid_csv(self):
        csv = (
            "recipient_email,recipient_name,company\n"
            "jane@example.com,Jane,Acme\n"
            "bob@example.com,Bob,Globex\n"
        )
        result = parse_recipients_file(_make_csv_upload(csv))
        assert len(result.recipients) == 2
        assert result.errors == []
        assert result.recipients[0].email == "jane@example.com"
        assert result.recipients[0].name == "Jane"
        assert result.recipients[0].custom_fields == {"company": "Acme"}

    def test_missing_required_columns(self):
        csv = "email,name\njane@example.com,Jane\n"
        result = parse_recipients_file(_make_csv_upload(csv))
        assert len(result.errors) == 1
        assert "Missing required columns" in result.errors[0]

    def test_invalid_email(self):
        csv = "recipient_email,recipient_name\nnot-an-email,Jane\n"
        result = parse_recipients_file(_make_csv_upload(csv))
        assert len(result.recipients) == 0
        assert any("invalid email" in e for e in result.errors)

    def test_empty_email(self):
        csv = "recipient_email,recipient_name\n,Jane\n"
        result = parse_recipients_file(_make_csv_upload(csv))
        assert len(result.recipients) == 0
        assert any("empty" in e for e in result.errors)

    def test_skips_empty_rows(self):
        csv = "recipient_email,recipient_name\njane@example.com,Jane\n,,\nbob@example.com,Bob\n"
        result = parse_recipients_file(_make_csv_upload(csv))
        assert len(result.recipients) == 2

    def test_extra_columns_become_custom_fields(self):
        csv = "recipient_email,recipient_name,company,role\njane@example.com,Jane,Acme,CTO\n"
        result = parse_recipients_file(_make_csv_upload(csv))
        assert result.recipients[0].custom_fields == {
            "company": "Acme",
            "role": "CTO",
        }

    def test_empty_file(self):
        result = parse_recipients_file(_make_csv_upload(""))
        assert len(result.errors) > 0


# ── Recipients XLSX ───────────────────────────────────────────────────────


class TestParseRecipientsXLSX:
    def test_valid_xlsx(self):
        upload = _make_xlsx_upload(
            ["recipient_email", "recipient_name", "company"],
            [
                ["jane@example.com", "Jane", "Acme"],
                ["bob@example.com", "Bob", "Globex"],
            ],
        )
        result = parse_recipients_file(upload)
        assert len(result.recipients) == 2
        assert result.errors == []
        assert result.recipients[0].email == "jane@example.com"
        assert result.recipients[0].custom_fields == {"company": "Acme"}

    def test_missing_columns_xlsx(self):
        upload = _make_xlsx_upload(
            ["email", "name"],
            [["jane@example.com", "Jane"]],
        )
        result = parse_recipients_file(upload)
        assert len(result.errors) == 1
        assert "Missing required columns" in result.errors[0]


# ── Schedule CSV ──────────────────────────────────────────────────────────


class TestParseScheduleCSV:
    def test_valid_absolute_and_relative(self):
        csv = "send_date,send_time,email_template_ref\n2026-03-01,09:00,intro\n5,09:00,followup\n"
        result = parse_schedule_file(_make_csv_upload(csv))
        assert len(result.steps) == 2
        assert result.errors == []
        assert result.steps[0].send_date == date(2026, 3, 1)
        assert result.steps[0].relative_days is None
        assert result.steps[0].send_time == time(9, 0)
        assert result.steps[0].email_template_ref == "intro"
        assert result.steps[1].send_date is None
        assert result.steps[1].relative_days == 5
        assert result.steps[1].email_template_ref == "followup"

    def test_missing_columns(self):
        csv = "date,time\n2026-03-01,09:00\n"
        result = parse_schedule_file(_make_csv_upload(csv))
        assert len(result.errors) == 1
        assert "Missing required columns" in result.errors[0]

    def test_first_step_relative_date_error(self):
        csv = "send_date,send_time,email_template_ref\n5,09:00,intro\n"
        result = parse_schedule_file(_make_csv_upload(csv))
        assert any("first schedule step" in e for e in result.errors)

    def test_past_date_warning(self):
        csv = "send_date,send_time,email_template_ref\n2020-01-01,09:00,intro\n"
        result = parse_schedule_file(_make_csv_upload(csv))
        assert len(result.steps) == 1
        assert any("past" in w for w in result.warnings)

    def test_invalid_date(self):
        csv = "send_date,send_time,email_template_ref\nnot-a-date,09:00,intro\n"
        result = parse_schedule_file(_make_csv_upload(csv))
        assert any("Invalid date" in e for e in result.errors)

    def test_invalid_time(self):
        csv = "send_date,send_time,email_template_ref\n2026-03-01,not-a-time,intro\n"
        result = parse_schedule_file(_make_csv_upload(csv))
        assert any("Invalid time" in e for e in result.errors)

    def test_empty_template_ref(self):
        csv = "send_date,send_time,email_template_ref\n2026-03-01,09:00,\n"
        result = parse_schedule_file(_make_csv_upload(csv))
        assert any("email_template_ref is empty" in e for e in result.errors)


# ── Schedule XLSX ─────────────────────────────────────────────────────────


class TestParseScheduleXLSX:
    def test_valid_xlsx(self):
        upload = _make_xlsx_upload(
            ["send_date", "send_time", "email_template_ref"],
            [
                ["2026-03-01", "09:00", "intro"],
                ["5", "09:00", "followup"],
            ],
        )
        result = parse_schedule_file(upload)
        assert len(result.steps) == 2
        assert result.errors == []


# ── Email Document ────────────────────────────────────────────────────────


class TestParseEmailDocument:
    def test_parses_markdown_with_refs(self):
        md = """ref: intro
subject: Hello {{name}}

Hi {{name}}, welcome!

---

ref: followup
subject: Following up

Just checking in.
"""
        result = parse_email_document(_make_md_upload(md))
        assert len(result) == 2
        assert result[0].ref == "intro"
        assert result[0].subject == "Hello {{name}}"
        assert "welcome" in result[0].body_text
        assert "<p>" in result[0].body_html
        assert result[1].ref == "followup"
        assert result[1].subject == "Following up"

    def test_auto_numbered_refs(self):
        md = """subject: First Email

Body 1

---

subject: Second Email

Body 2
"""
        result = parse_email_document(_make_md_upload(md))
        assert result[0].ref == "1"
        assert result[1].ref == "2"

    def test_missing_subject(self):
        md = """ref: nosubject

Just a body with no subject line.
"""
        result = parse_email_document(_make_md_upload(md))
        assert len(result) == 1
        assert result[0].subject == ""
        assert "body" in result[0].body_text.lower()

    def test_empty_document(self):
        result = parse_email_document(_make_md_upload(""))
        assert result == []

    def test_sample_emails_md(self):
        """Parse the actual sample_emails.md from examples/."""
        with open("../examples/sample_emails.md", "rb") as f:
            content = f.read()
        upload = MagicMock()
        upload.filename = "sample_emails.md"
        upload.file = io.BytesIO(content)

        result = parse_email_document(upload)
        assert len(result) == 2
        assert result[0].ref == "intro"
        assert result[1].ref == "followup"
        assert "{{recipient_name}}" in result[0].body_text
        assert "{{company}}" in result[0].subject
