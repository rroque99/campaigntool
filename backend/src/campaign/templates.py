"""Email template rendering with variable substitution."""

import html
import re
from dataclasses import dataclass, field

from campaign.parser import EmailTemplate

VARIABLE_RE = re.compile(r"\{\{(\w+)\}\}")


@dataclass
class RenderedEmail:
    subject: str
    body_html: str
    body_text: str
    warnings: list[str] = field(default_factory=list)


def render_email(template: EmailTemplate, variables: dict) -> RenderedEmail:
    """Render an email template by substituting {{variable}} placeholders.

    - Missing variables: placeholder is preserved, warning is added.
    - HTML body: variable values are HTML-escaped to prevent injection.
    - Plain text body: variable values are inserted as-is.
    - Extra variables in the dict are ignored.
    """
    warnings: list[str] = []

    subject = _substitute(template.subject, variables, escape_html=False, warnings=warnings)
    body_html = _substitute(template.body_html, variables, escape_html=True, warnings=warnings)
    body_text = _substitute(template.body_text, variables, escape_html=False, warnings=warnings)

    # Deduplicate warnings (same variable missing in multiple fields)
    seen: set[str] = set()
    unique_warnings: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            unique_warnings.append(w)

    return RenderedEmail(
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        warnings=unique_warnings,
    )


def _substitute(
    text: str,
    variables: dict,
    *,
    escape_html: bool,
    warnings: list[str],
) -> str:
    """Replace {{variable}} placeholders in text."""

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in variables:
            value = str(variables[var_name])
            return html.escape(value) if escape_html else value
        warnings.append(f"Missing variable: {var_name}")
        return match.group(0)  # preserve placeholder

    return VARIABLE_RE.sub(replacer, text)
