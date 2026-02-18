"""Gmail API sender — sends emails via the Gmail API.

Implements the SendBackend protocol. Extracted from gmail.py to allow
alternative sender backends (e.g., Playwright).
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from googleapiclient.errors import HttpError

from campaign.auth import is_authenticated
from campaign.gmail import GmailError, build_gmail_service
from campaign.sender import SendResult

logger = logging.getLogger(__name__)


class GmailAPISender:
    """Sends emails via the Gmail API."""

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str,
        thread_id: str | None = None,
    ) -> SendResult:
        """Send an email via Gmail API.

        Constructs a MIME multipart/alternative message with plain text and HTML
        parts, base64url encodes it, and sends via the Gmail API.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body_html: HTML body content.
            body_text: Plain text body content.
            thread_id: Optional thread ID for reply threading.

        Returns:
            SendResult with Gmail message ID and thread ID.

        Raises:
            GmailError: If the send operation fails.
        """
        service = build_gmail_service()

        message = MIMEMultipart("alternative")
        message["to"] = to
        message["subject"] = subject

        part_text = MIMEText(body_text, "plain")
        part_html = MIMEText(body_html, "html")
        message.attach(part_text)
        message.attach(part_html)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        body: dict = {"raw": raw}
        if thread_id:
            body["threadId"] = thread_id

        try:
            result = service.users().messages().send(userId="me", body=body).execute()
            return SendResult(
                message_id=result["id"],
                thread_id=result["threadId"],
            )
        except HttpError as e:
            status_code = e.resp.status if e.resp else 0
            if status_code == 429:
                raise GmailError(
                    "Gmail API rate limit exceeded. Try again later.",
                    error_code="rate_limited",
                    retryable=True,
                ) from e
            raise GmailError(
                f"Gmail API error ({status_code}): {e}",
                error_code="send_failed",
            ) from e
        except Exception as e:
            raise GmailError(f"Failed to send email: {e}", error_code="send_failed") from e

    def is_ready(self) -> bool:
        """Check if Gmail API credentials are valid."""
        return is_authenticated()

    def get_display_name(self) -> str:
        return "Gmail API"
