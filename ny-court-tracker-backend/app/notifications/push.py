"""
Expo Push Notification service.

Sends push notifications to mobile devices via the Expo Push API.
Manages push token registration and delivery.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.database import get_db

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def register_push_token(
    user_id: int,
    token: str,
    device_name: Optional[str] = None,
    platform: Optional[str] = None,
) -> dict:
    """
    Register or update a push token for a user.

    If the token already exists for this user, update last_used_at.
    If it exists for a different user, reassign it.
    """
    if not token or not token.startswith("ExponentPushToken["):
        return {"error": "Invalid Expo push token format"}

    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        # Check if token already exists
        existing = conn.execute(
            "SELECT id, user_id FROM push_tokens WHERE token = ?",
            (token,),
        ).fetchone()

        if existing:
            # Update existing token
            conn.execute(
                """UPDATE push_tokens
                   SET user_id = ?, device_name = ?, platform = ?,
                       active = 1, last_used_at = ?
                   WHERE token = ?""",
                (user_id, device_name, platform, now, token),
            )
            return {"status": "updated", "token": token}

        # Insert new token
        conn.execute(
            """INSERT INTO push_tokens
               (user_id, token, device_name, platform, active, created_at, last_used_at)
               VALUES (?, ?, ?, ?, 1, ?, ?)""",
            (user_id, token, device_name, platform, now, now),
        )

    return {"status": "registered", "token": token}


def unregister_push_token(user_id: int, token: str) -> dict:
    """Remove a push token for a user."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM push_tokens WHERE user_id = ? AND token = ?",
            (user_id, token),
        )
        if result.rowcount == 0:
            return {"error": "Token not found"}

    return {"status": "removed"}


def deactivate_token(token: str) -> None:
    """Mark a token as inactive (e.g., after delivery failure)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE push_tokens SET active = 0 WHERE token = ?",
            (token,),
        )


def get_user_push_tokens(user_id: int) -> list[str]:
    """Get all active push tokens for a user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT token FROM push_tokens WHERE user_id = ? AND active = 1",
            (user_id,),
        ).fetchall()

    return [row["token"] for row in rows]


def send_push_notification(
    user_id: int,
    title: str,
    body: str,
    data: Optional[dict] = None,
    badge: Optional[int] = None,
) -> dict:
    """
    Send a push notification to all of a user's registered devices.

    Uses the Expo Push API to deliver notifications.
    Returns delivery results.
    """
    tokens = get_user_push_tokens(user_id)
    if not tokens:
        return {"status": "no_tokens", "sent": 0}

    messages = []
    for token in tokens:
        message = {
            "to": token,
            "title": title,
            "body": body,
            "sound": "default",
        }
        if data:
            message["data"] = data
        if badge is not None:
            message["badge"] = badge
        messages.append(message)

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result = response.json()

        # Process results and deactivate failed tokens
        tickets = result.get("data", [])
        sent = 0
        for i, ticket in enumerate(tickets):
            if ticket.get("status") == "ok":
                sent += 1
            elif ticket.get("status") == "error":
                error_type = ticket.get("details", {}).get("error", "")
                if error_type == "DeviceNotRegistered":
                    deactivate_token(tokens[i])
                    logger.info(f"Deactivated unregistered token for user {user_id}")

        return {"status": "sent", "sent": sent, "total_tokens": len(tokens)}

    except httpx.HTTPError as e:
        logger.error(f"Expo Push API error for user {user_id}: {e}")
        return {"status": "error", "error": str(e), "sent": 0}
    except Exception as e:
        logger.error(f"Push notification error for user {user_id}: {e}")
        return {"status": "error", "error": str(e), "sent": 0}


def send_push_to_multiple_users(
    user_ids: list[int],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> dict:
    """Send the same push notification to multiple users."""
    results = {}
    for uid in user_ids:
        results[uid] = send_push_notification(uid, title, body, data)
    return results
