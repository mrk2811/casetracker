from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas import AppearanceCreate, AppearanceUpdate, AppearanceOut

router = APIRouter(tags=["appearances"])


def _row_to_appearance(row) -> AppearanceOut:
    return AppearanceOut(
        id=row["id"],
        case_id=row["case_id"],
        appearance_date=row["appearance_date"],
        appearance_time=row["appearance_time"],
        appearance_type=row["appearance_type"],
        location=row["location"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _verify_case_ownership(conn, case_id: int, user_id: int):
    case = conn.execute(
        "SELECT id FROM cases WHERE id = ? AND user_id = ?", (case_id, user_id)
    ).fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")


@router.get("/api/cases/{case_id}/appearances", response_model=list[AppearanceOut])
async def list_appearances(case_id: int, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        _verify_case_ownership(conn, case_id, user_id)
        rows = conn.execute(
            "SELECT * FROM appearances WHERE case_id = ? ORDER BY appearance_date ASC",
            (case_id,),
        ).fetchall()

    return [_row_to_appearance(row) for row in rows]


@router.post("/api/cases/{case_id}/appearances", response_model=AppearanceOut, status_code=201)
async def create_appearance(
    case_id: int, data: AppearanceCreate, user_id: int = Depends(get_current_user_id)
):
    with get_db() as conn:
        _verify_case_ownership(conn, case_id, user_id)
        cursor = conn.execute(
            """INSERT INTO appearances (case_id, appearance_date, appearance_time, appearance_type, location, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                case_id, data.appearance_date.isoformat(), data.appearance_time,
                data.appearance_type, data.location, data.notes,
            ),
        )
        app_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM appearances WHERE id = ?", (app_id,)).fetchone()

    return _row_to_appearance(row)


@router.put("/api/appearances/{appearance_id}", response_model=AppearanceOut)
async def update_appearance(
    appearance_id: int, data: AppearanceUpdate, user_id: int = Depends(get_current_user_id)
):
    with get_db() as conn:
        app_row = conn.execute("SELECT * FROM appearances WHERE id = ?", (appearance_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="Appearance not found")

        _verify_case_ownership(conn, app_row["case_id"], user_id)

        updates = {}
        for k, v in data.model_dump().items():
            if v is not None:
                if k == "appearance_date":
                    updates[k] = v.isoformat()
                else:
                    updates[k] = v

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values())
        values.append(appearance_id)

        conn.execute(
            f"UPDATE appearances SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )

        row = conn.execute("SELECT * FROM appearances WHERE id = ?", (appearance_id,)).fetchone()

    return _row_to_appearance(row)


@router.delete("/api/appearances/{appearance_id}", status_code=204)
async def delete_appearance(appearance_id: int, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        app_row = conn.execute("SELECT * FROM appearances WHERE id = ?", (appearance_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="Appearance not found")

        _verify_case_ownership(conn, app_row["case_id"], user_id)
        conn.execute("DELETE FROM appearances WHERE id = ?", (appearance_id,))
