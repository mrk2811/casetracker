from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas import NotificationSettingsUpdate, NotificationSettingsOut, NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/settings", response_model=NotificationSettingsOut)
async def get_notification_settings(user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM notification_settings WHERE user_id = ?", (user_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Notification settings not found")

    return NotificationSettingsOut(
        id=row["id"],
        user_id=row["user_id"],
        email_enabled=bool(row["email_enabled"]),
        reminder_days=row["reminder_days"],
        case_updates_enabled=bool(row["case_updates_enabled"]),
    )


@router.put("/settings", response_model=NotificationSettingsOut)
async def update_notification_settings(
    data: NotificationSettingsUpdate, user_id: int = Depends(get_current_user_id)
):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM notification_settings WHERE user_id = ?", (user_id,)
        ).fetchone()

        if not existing:
            conn.execute(
                "INSERT INTO notification_settings (user_id) VALUES (?)", (user_id,)
            )

        updates = {}
        if data.email_enabled is not None:
            updates["email_enabled"] = 1 if data.email_enabled else 0
        if data.reminder_days is not None:
            updates["reminder_days"] = data.reminder_days
        if data.case_updates_enabled is not None:
            updates["case_updates_enabled"] = 1 if data.case_updates_enabled else 0

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values())
            values.append(user_id)
            conn.execute(
                f"UPDATE notification_settings SET {set_clause} WHERE user_id = ?",
                values,
            )

        row = conn.execute(
            "SELECT * FROM notification_settings WHERE user_id = ?", (user_id,)
        ).fetchone()

    return NotificationSettingsOut(
        id=row["id"],
        user_id=row["user_id"],
        email_enabled=bool(row["email_enabled"]),
        reminder_days=row["reminder_days"],
        case_updates_enabled=bool(row["case_updates_enabled"]),
    )


@router.get("", response_model=list[NotificationOut])
async def list_notifications(user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()

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
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int, user_id: int = Depends(get_current_user_id)
):
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
    with get_db() as conn:
        conn.execute(
            "UPDATE notifications SET read = 1 WHERE user_id = ? AND read = 0",
            (user_id,),
        )
    return {"status": "ok"}
