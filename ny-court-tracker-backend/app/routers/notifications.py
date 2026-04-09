"""
Notification API endpoints.

Handles notification listing, settings, push token management,
per-case notification preferences, and unread counts.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas import (
    NotificationSettingsUpdate,
    NotificationSettingsOut,
    NotificationOut,
    PushTokenRegister,
    PushTokenOut,
    UnreadCountOut,
    CaseNotificationPrefsUpdate,
    CaseNotificationPrefsOut,
)
from app.notifications.push import register_push_token, unregister_push_token
from app.notifications.engine import get_unread_count, get_user_notification_settings

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ─── Notification Settings ───

@router.get("/settings", response_model=NotificationSettingsOut)
async def get_notification_settings_endpoint(user_id: int = Depends(get_current_user_id)):
    """Get notification settings for the current user."""
    settings = get_user_notification_settings(user_id)
    return NotificationSettingsOut(
        id=settings["id"],
        user_id=settings["user_id"],
        email_enabled=bool(settings["email_enabled"]),
        push_enabled=bool(settings.get("push_enabled", True)),
        reminder_days=settings["reminder_days"],
        case_updates_enabled=bool(settings["case_updates_enabled"]),
        digest_frequency=settings.get("digest_frequency", "off"),
        digest_time=settings.get("digest_time", "08:00"),
    )


@router.put("/settings", response_model=NotificationSettingsOut)
async def update_notification_settings(
    data: NotificationSettingsUpdate, user_id: int = Depends(get_current_user_id)
):
    """Update notification settings for the current user."""
    get_user_notification_settings(user_id)

    updates = {}
    if data.email_enabled is not None:
        updates["email_enabled"] = 1 if data.email_enabled else 0
    if data.push_enabled is not None:
        updates["push_enabled"] = 1 if data.push_enabled else 0
    if data.reminder_days is not None:
        updates["reminder_days"] = data.reminder_days
    if data.case_updates_enabled is not None:
        updates["case_updates_enabled"] = 1 if data.case_updates_enabled else 0
    if data.digest_frequency is not None:
        if data.digest_frequency not in ("off", "daily", "weekly"):
            raise HTTPException(status_code=400, detail="digest_frequency must be 'off', 'daily', or 'weekly'")
        updates["digest_frequency"] = data.digest_frequency
    if data.digest_time is not None:
        updates["digest_time"] = data.digest_time

    if updates:
        with get_db() as conn:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values())
            values.append(user_id)
            conn.execute(
                f"UPDATE notification_settings SET {set_clause} WHERE user_id = ?",
                values,
            )

    settings = get_user_notification_settings(user_id)
    return NotificationSettingsOut(
        id=settings["id"],
        user_id=settings["user_id"],
        email_enabled=bool(settings["email_enabled"]),
        push_enabled=bool(settings.get("push_enabled", True)),
        reminder_days=settings["reminder_days"],
        case_updates_enabled=bool(settings["case_updates_enabled"]),
        digest_frequency=settings.get("digest_frequency", "off"),
        digest_time=settings.get("digest_time", "08:00"),
    )


# ─── Notification List ───

@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    notification_type: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    user_id: int = Depends(get_current_user_id),
):
    """
    List notifications with optional filters.

    - notification_type: 'reminder', 'update', or 'system'
    - unread_only: only return unread notifications
    - limit: max number to return (default 50)
    """
    query = "SELECT * FROM notifications WHERE user_id = ?"
    params: list = [user_id]

    if notification_type:
        query += " AND type = ?"
        params.append(notification_type)

    if unread_only:
        query += " AND read = 0"

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        NotificationOut(
            id=row["id"],
            user_id=row["user_id"],
            case_id=row["case_id"],
            appearance_id=row["appearance_id"],
            type=row["type"],
            title=row["title"],
            message=row["message"],
            read=bool(row["read"]),
            push_sent=bool(row["push_sent"]) if "push_sent" in row.keys() else False,
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/unread-count", response_model=UnreadCountOut)
async def get_unread_notification_count(user_id: int = Depends(get_current_user_id)):
    """Get the count of unread notifications."""
    count = get_unread_count(user_id)
    return UnreadCountOut(count=count)


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int, user_id: int = Depends(get_current_user_id)
):
    """Mark a single notification as read."""
    with get_db() as conn:
        result = conn.execute(
            "UPDATE notifications SET read = 1 WHERE id = ? AND user_id = ?",
            (notification_id, user_id),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "ok"}


@router.put("/read-all")
async def mark_all_read(user_id: int = Depends(get_current_user_id)):
    """Mark all notifications as read."""
    with get_db() as conn:
        conn.execute(
            "UPDATE notifications SET read = 1 WHERE user_id = ? AND read = 0",
            (user_id,),
        )
    return {"status": "ok"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int, user_id: int = Depends(get_current_user_id)
):
    """Delete a single notification."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM notifications WHERE id = ? AND user_id = ?",
            (notification_id, user_id),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "deleted"}


@router.delete("")
async def clear_all_notifications(user_id: int = Depends(get_current_user_id)):
    """Delete all notifications for the current user."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM notifications WHERE user_id = ?",
            (user_id,),
        )
    return {"status": "cleared"}


# ─── Push Token Management ───

@router.post("/push-token")
async def register_token(
    data: PushTokenRegister, user_id: int = Depends(get_current_user_id)
):
    """Register an Expo push notification token for the current user."""
    result = register_push_token(
        user_id=user_id,
        token=data.token,
        device_name=data.device_name,
        platform=data.platform,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/push-token")
async def unregister_token(
    token: str, user_id: int = Depends(get_current_user_id)
):
    """Remove a push notification token."""
    result = unregister_push_token(user_id, token)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/push-tokens", response_model=list[PushTokenOut])
async def list_push_tokens(user_id: int = Depends(get_current_user_id)):
    """List all push tokens for the current user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM push_tokens WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

    return [
        PushTokenOut(
            id=row["id"],
            user_id=row["user_id"],
            token=row["token"],
            device_name=row["device_name"],
            platform=row["platform"],
            active=bool(row["active"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


# ─── Per-Case Notification Preferences ───

@router.get("/case/{case_id}/prefs", response_model=CaseNotificationPrefsOut)
async def get_case_prefs(case_id: int, user_id: int = Depends(get_current_user_id)):
    """Get notification preferences for a specific case."""
    with get_db() as conn:
        case = conn.execute(
            "SELECT id FROM cases WHERE id = ? AND user_id = ?",
            (case_id, user_id),
        ).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        row = conn.execute(
            "SELECT * FROM case_notification_prefs WHERE case_id = ? AND user_id = ?",
            (case_id, user_id),
        ).fetchone()

    if row:
        return CaseNotificationPrefsOut(
            case_id=row["case_id"],
            user_id=row["user_id"],
            push_enabled=bool(row["push_enabled"]),
            email_enabled=bool(row["email_enabled"]),
            priority_override=row["priority_override"],
        )

    return CaseNotificationPrefsOut(
        case_id=case_id,
        user_id=user_id,
        push_enabled=True,
        email_enabled=True,
        priority_override=None,
    )


@router.put("/case/{case_id}/prefs", response_model=CaseNotificationPrefsOut)
async def update_case_prefs(
    case_id: int,
    data: CaseNotificationPrefsUpdate,
    user_id: int = Depends(get_current_user_id),
):
    """Update notification preferences for a specific case."""
    with get_db() as conn:
        case = conn.execute(
            "SELECT id FROM cases WHERE id = ? AND user_id = ?",
            (case_id, user_id),
        ).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        existing = conn.execute(
            "SELECT * FROM case_notification_prefs WHERE case_id = ? AND user_id = ?",
            (case_id, user_id),
        ).fetchone()

        push_val = 1 if (data.push_enabled if data.push_enabled is not None else True) else 0
        email_val = 1 if (data.email_enabled if data.email_enabled is not None else True) else 0
        priority_val = data.priority_override

        if existing:
            if data.push_enabled is not None:
                push_val = 1 if data.push_enabled else 0
            else:
                push_val = existing["push_enabled"]
            if data.email_enabled is not None:
                email_val = 1 if data.email_enabled else 0
            else:
                email_val = existing["email_enabled"]
            if data.priority_override is None:
                priority_val = existing["priority_override"]

            conn.execute(
                """UPDATE case_notification_prefs
                   SET push_enabled = ?, email_enabled = ?, priority_override = ?
                   WHERE case_id = ? AND user_id = ?""",
                (push_val, email_val, priority_val, case_id, user_id),
            )
        else:
            conn.execute(
                """INSERT INTO case_notification_prefs
                   (case_id, user_id, push_enabled, email_enabled, priority_override)
                   VALUES (?, ?, ?, ?, ?)""",
                (case_id, user_id, push_val, email_val, priority_val),
            )

    return CaseNotificationPrefsOut(
        case_id=case_id,
        user_id=user_id,
        push_enabled=bool(push_val),
        email_enabled=bool(email_val),
        priority_override=priority_val,
    )


# ─── Manual Trigger (for testing) ───

@router.post("/trigger-checks")
async def trigger_notification_checks(user_id: int = Depends(get_current_user_id)):
    """Manually trigger all notification checks (for testing)."""
    from app.notifications.scheduler import run_all_notification_checks
    results = run_all_notification_checks()
    return {"status": "completed", "results": results}
