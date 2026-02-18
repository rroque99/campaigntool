"""Gmail API operations — reply detection and quota management.

Send logic has been extracted to gmail_sender.py. This module retains
Gmail API operations that are specific to the API backend: reply checking
via the History API and send quota tracking.
"""

import logging
from dataclasses import dataclass, field

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from campaign.auth import AuthError, get_credentials
from campaign.config import settings
from campaign.sender import SendError

logger = logging.getLogger(__name__)


class GmailError(SendError):
    """Raised when Gmail API operations fail.

    Subclass of SendError so the scheduler can catch all sender errors
    with a single base class.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "gmail_error",
        retryable: bool = False,
    ):
        super().__init__(message=message, error_code=error_code, retryable=retryable)


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
