"""Gmail API operations — send emails and check replies.

This module is the sole interface to the Gmail API. All other modules
work with Pydantic schemas and SQLAlchemy models, never raw API responses.
"""

import base64
import logging
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from campaign.auth import AuthError, get_credentials
from campaign.config import settings

logger = logging.getLogger(__name__)


class GmailError(Exception):
    """Raised when Gmail API operations fail."""

    def __init__(self, message: str, error_code: str = "gmail_error"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


@dataclass
class SendResult:
    """Result of a successful email send."""

    message_id: str
    thread_id: str


@dataclass
class ReplyCheckResult:
    """Result of checking for replies via Gmail History API."""

    new_history_id: str
    replied_thread_ids: list[str] = field(default_factory=list)


def build_gmail_service():
    """Create and return a Gmail API service object."""
    try:
        creds = get_credentials()
        return build("gmail", "v1", credentials=creds)
    except AuthError:
        raise
    except Exception as e:
        raise GmailError(f"Failed to build Gmail service: {e}") from e


def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: str,
    thread_id: str | None = None,
) -> SendResult:
    """Send an email via Gmail API.

    Constructs a MIME multipart/alternative message with plain text and HTML parts,
    base64url encodes it, and sends via the Gmail API.

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
            ) from e
        raise GmailError(
            f"Gmail API error ({status_code}): {e}",
            error_code="send_failed",
        ) from e
    except Exception as e:
        raise GmailError(f"Failed to send email: {e}", error_code="send_failed") from e


def get_send_quota_remaining(sent_today: int) -> int:
    """Return remaining sends for today based on tracked count.

    Args:
        sent_today: Number of emails already sent today (from DB query).

    Returns:
        Number of remaining sends allowed today.
    """
    return max(0, settings.daily_send_limit - sent_today)


def check_replies(history_id: str | None) -> ReplyCheckResult:
    """Check for replies to campaign threads using Gmail History API.

    Args:
        history_id: Last known history ID for incremental sync. If None,
            fetches current history ID as a starting point (no retroactive detection).

    Returns:
        ReplyCheckResult with new history ID and list of thread IDs that received replies.

    Raises:
        GmailError: If the Gmail API call fails.
    """
    service = build_gmail_service()

    try:
        if history_id is None:
            # Initial sync: get current history ID as starting point
            profile = service.users().getProfile(userId="me").execute()
            return ReplyCheckResult(
                new_history_id=str(profile["historyId"]),
                replied_thread_ids=[],
            )

        replied_thread_ids: list[str] = []
        page_token = None
        latest_history_id = history_id

        while True:
            kwargs: dict = {
                "userId": "me",
                "startHistoryId": history_id,
                "historyTypes": ["messageAdded"],
            }
            if page_token:
                kwargs["pageToken"] = page_token

            response = service.users().history().list(**kwargs).execute()
            latest_history_id = str(response.get("historyId", history_id))

            for record in response.get("history", []):
                for msg_added in record.get("messagesAdded", []):
                    msg = msg_added.get("message", {})
                    tid = msg.get("threadId")
                    # Only include messages not sent by us (label SENT not present)
                    labels = msg.get("labelIds", [])
                    if tid and "SENT" not in labels:
                        if tid not in replied_thread_ids:
                            replied_thread_ids.append(tid)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return ReplyCheckResult(
            new_history_id=latest_history_id,
            replied_thread_ids=replied_thread_ids,
        )

    except HttpError as e:
        status_code = e.resp.status if e.resp else 0
        if status_code == 404:
            # History ID expired — do a full resync
            logger.warning("History ID expired, performing full resync.")
            profile = service.users().getProfile(userId="me").execute()
            return ReplyCheckResult(
                new_history_id=str(profile["historyId"]),
                replied_thread_ids=[],
            )
        raise GmailError(
            f"Gmail History API error ({status_code}): {e}",
            error_code="history_check_failed",
        ) from e
    except Exception as e:
        raise GmailError(
            f"Failed to check replies: {e}",
            error_code="history_check_failed",
        ) from e
