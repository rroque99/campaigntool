"""Tests for email template rendering."""

from campaign.parser import EmailTemplate
from campaign.templates import render_email


class TestRenderEmail:
    def test_basic_substitution(self):
        template = EmailTemplate(
            ref="test",
            subject="Hello {{name}}",
            body_html="<p>Hi {{name}} from {{company}}</p>",
            body_text="Hi {{name}} from {{company}}",
        )
        result = render_email(template, {"name": "Jane", "company": "Acme"})
        assert result.subject == "Hello Jane"
        assert result.body_html == "<p>Hi Jane from Acme</p>"
        assert result.body_text == "Hi Jane from Acme"
        assert result.warnings == []

    def test_missing_variable_preserved(self):
        template = EmailTemplate(
            ref="test",
            subject="Hello {{name}}",
            body_html="<p>{{unknown}} placeholder</p>",
            body_text="{{unknown}} placeholder",
        )
        result = render_email(template, {"name": "Jane"})
        assert result.subject == "Hello Jane"
        assert "{{unknown}}" in result.body_html
        assert "{{unknown}}" in result.body_text
        assert any("unknown" in w for w in result.warnings)

    def test_html_escaping(self):
        template = EmailTemplate(
            ref="test",
            subject="{{name}}",
            body_html="<p>{{name}}</p>",
            body_text="{{name}}",
        )
        result = render_email(template, {"name": '<script>alert("xss")</script>'})
        # HTML body should be escaped
        assert "<script>" not in result.body_html
        assert "&lt;script&gt;" in result.body_html
        # Plain text should NOT be escaped
        assert "<script>" in result.body_text

    def test_extra_variables_ignored(self):
        template = EmailTemplate(
            ref="test",
            subject="Hi",
            body_html="<p>Body</p>",
            body_text="Body",
        )
        result = render_email(template, {"name": "Jane", "extra": "ignored"})
        assert result.warnings == []
        assert result.subject == "Hi"

    def test_subject_substitution(self):
        template = EmailTemplate(
            ref="test",
            subject="Welcome {{name}} at {{company}}",
            body_html="<p>...</p>",
            body_text="...",
        )
        result = render_email(template, {"name": "Bob", "company": "Globex"})
        assert result.subject == "Welcome Bob at Globex"

    def test_deduplicated_warnings(self):
        template = EmailTemplate(
            ref="test",
            subject="{{missing}}",
            body_html="<p>{{missing}}</p>",
            body_text="{{missing}}",
        )
        result = render_email(template, {})
        # "missing" appears in subject, body_html, and body_text
        # but warning should be deduplicated
        assert result.warnings.count("Missing variable: missing") == 1

    def test_ampersand_escaped_in_html(self):
        template = EmailTemplate(
            ref="test",
            subject="{{co}}",
            body_html="<p>{{co}}</p>",
            body_text="{{co}}",
        )
        result = render_email(template, {"co": "A&B Corp"})
        assert "&amp;" in result.body_html
        assert "A&B Corp" in result.body_text
