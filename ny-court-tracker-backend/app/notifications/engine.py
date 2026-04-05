"""
Notification engine - centralized notification creation and dispatch.

All notification creation flows through this engine to ensure:
1. User preferences are checked before sending
2. Per-case notification preferences are respected
3. Push notifications are sent when appropriate
4. Notifications are logged in the database
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.database import get_db
from app.notifications.push import send_push_notification

logger = logging.getLogger(__name__)


def get_user_notification_settings(user_id: int) -> dict:
    """Get notification settings for a user, creating defaults if needed."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM notification_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if not row:
            conn.execute(
                """INSERT INTO notification_settings
                   (user_id, email_enabled, push_enabled, reminder_days,
                    case_updates_enabled, digest_frequency, digest_time)
                   VALUES (?, 1, 1, 1, 1, 'off', '08:00')""",
                (user_id,),
            )
            row = conn.execute(
                "SELECT * FROM notification_settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()

    return dict(row) if row else {}


def get_case_notification_prefs(user_id: int, case_id: int) -> dict:
    """Get per-case notification preferences, falling back to global settings."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM case_notification_prefs WHERE case_id = ? AND user_id = ?",
            (case_id, user_id),
        ).fetchone()

    if row:
        return {
            "push_enabled": bool(row["push_enabled"]),
            "email_enabled": bool(row["email_enabled"]),
            "priority_override": row["priority_override"],
        }

    # Fall back to global settings
    settings = get_user_notification_settings(user_id)
    return {
        "push_enabled": bool(settings.get("push_enabled", True)),
        "email_enabled": bool(settings.get("email_enabled", True)),
        "priority_override": None,
    }


def get_unread_count(user_id: int) -> int:
    """Get the count of unread notifications for a user."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND read = 0",
            (user_id,),
        ).fetchone()
    return row["cnt"] if row else 0


def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    case_id: Optional[int] = None,
    appearance_id: Optional[int] = None,
    send_push: bool = True,
) -> dict:
    """
    Create a notification and optionally send a push notification.

    This is the central function all notification triggers should use.
    It checks user preferences before sending push notifications.

    Args:
        user_id: The user to notify
        notification_type: 'reminder', 'update', or 'system'
        title: Notification title
        message: Notification body text
        case_id: Optional associated case
        appearance_id: Optional associated appearance
        send_push: Whether to attempt sending a push notification

    Returns:
        Dict with notification details and push delivery status
    """
    now = datetime.now(timezone.utc).isoformat()

    # Get user settings
    settings = get_user_notification_settings(user_id)

    # Check if case-level prefs override
    case_prefs = None
    if case_id:
        case_prefs = get_case_notification_prefs(user_id, case_id)

    # Determine if we should send push
    should_push = send_push
    if should_push:
        # Check global push setting
        if not settings.get("push_enabled", True):
            should_push = False
        # Check notification type preferences
        if notification_type == "update" and not settings.get("case_updates_enabled", True):
            should_push = False
        # Check per-case preferences
        if case_prefs and not case_prefs.get("push_enabled", True):
            should_push = False

    push_sent = False
    push_result = None

    if should_push:
        # Build push data payload for deep linking
        push_data = {"type": notification_type}
        if case_id:
            push_data["case_id"] = case_id
        if appearance_id:
            push_data["appearance_id"] = appearance_id

        # Get unread count for badge
        badge_count = get_unread_count(user_id) + 1

        push_result = send_push_notification(
            user_id=user_id,
            title=title,
            body=message,
            data=push_data,
            badge=badge_count,
        )
        push_sent = push_result.get("status") == "sent" and push_result.get("sent", 0) > 0

    # Create notification record in database
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO notifications
               (user_id, case_id, appearance_id, type, title, message, read, push_sent, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (user_id, case_id, appearance_id, notification_type, title, message,
             1 if push_sent else 0, now),
        )
        notification_id = cursor.lastrowid

    result = {
        "id": notification_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "push_sent": push_sent,
    }
    if push_result:
        result["push_result"] = push_result

    return result


# ─── Notification Trigger Functions ───


def notify_new_filing(user_id: int, case_id: int, case_index: str, description: str) -> dict:
    """Trigger notification for a new filing on a tracked case."""
    return create_notification(
        user_id=user_id,
        notification_type="update",
        title="New Filing Detected",
        message=f"Case {case_index}: {description}",
        case_id=case_id,
    )


def notify_court_date_scheduled(
    user_id: int,
    case_id: int,
    case_index: str,
    appearance_date: str,
    appearance_type: Optional[str] = None,
    appearance_id: Optional[int] = None,
) -> dict:
    """Trigger notification for a new court date being scheduled."""
    type_str = f" ({appearance_type})" if appearance_type else ""
    return create_notification(
        user_id=user_id,
        notification_type="update",
        title="Court Date Scheduled",
        message=f"Case {case_index}: {appearance_date}{type_str}",
        case_id=case_id,
        appearance_id=appearance_id,
    )


def notify_court_date_changed(
    user_id: int,
    case_id: int,
    case_index: str,
    old_date: str,
    new_date: str,
    appearance_id: Optional[int] = None,
) -> dict:
    """Trigger notification for a court date being changed."""
    return create_notification(
        user_id=user_id,
        notification_type="update",
        title="Court Date Changed",
        message=f"Case {case_index}: Changed from {old_date} to {new_date}",
        case_id=case_id,
        appearance_id=appearance_id,
    )


def notify_case_update(
    user_id: int,
    case_id: int,
    case_index: str,
    update_description: str,
    source: str = "unknown",
) -> dict:
    """Trigger notification for a general case update."""
    return create_notification(
        user_id=user_id,
        notification_type="update",
        title="Case Update",
        message=f"Case {case_index}: {update_description} (via {source})",
        case_id=case_id,
    )


def notify_appearance_reminder(
    user_id: int,
    case_id: int,
    case_index: str,
    appearance_date: str,
    appearance_type: Optional[str] = None,
    days_until: int = 1,
    appearance_id: Optional[int] = None,
) -> dict:
    """Trigger a court appearance reminder notification."""
    type_str = appearance_type or "Court Appearance"
    if days_until == 0:
        title = f"TODAY: {type_str}"
        message = f"Case {case_index}: {type_str} is today ({appearance_date})"
    elif days_until == 1:
        title = f"Tomorrow: {type_str}"
        message = f"Case {case_index}: {type_str} is tomorrow ({appearance_date})"
    else:
        title = f"Upcoming: {type_str} in {days_until} days"
        message = f"Case {case_index}: {type_str} on {appearance_date}"

    return create_notification(
        user_id=user_id,
        notification_type="reminder",
        title=title,
        message=message,
        case_id=case_id,
        appearance_id=appearance_id,
    )


def notify_stale_case(
    user_id: int,
    case_id: int,
    case_index: str,
    hours_since_update: float,
) -> dict:
    """Trigger notification for a case that hasn't been updated in a while."""
    return create_notification(
        user_id=user_id,
        notification_type="system",
        title="Case Needs Attention",
        message=f"Case {case_index}: Not updated for {int(hours_since_update)} hours. Check eTrack or trigger a manual refresh.",
        case_id=case_id,
    )


def notify_priority_escalation(
    user_id: int,
    case_id: int,
    case_index: str,
    reason: str,
) -> dict:
    """Trigger notification when a case is auto-escalated to high priority."""
    return create_notification(
        user_id=user_id,
        notification_type="system",
        title="Priority Escalated",
        message=f"Case {case_index} auto-escalated to HIGH priority: {reason}",
        case_id=case_id,
    )
