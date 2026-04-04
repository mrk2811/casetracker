from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas import CaseCreate, CaseUpdate, CaseOut

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _row_to_case(row, next_appearance: Optional[str] = None) -> CaseOut:
    return CaseOut(
        id=row["id"],
        user_id=row["user_id"],
        court_type=row["court_type"],
        county=row["county"],
        index_number=row["index_number"],
        case_year=row["case_year"],
        case_status=row["case_status"],
        plaintiff=row["plaintiff"],
        defendant=row["defendant"],
        plaintiff_firm=row["plaintiff_firm"],
        defendant_firm=row["defendant_firm"],
        justice=row["justice"],
        part=row["part"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        next_appearance=next_appearance,
    )


@router.get("", response_model=list[CaseOut])
async def list_cases(
    court_type: Optional[str] = None,
    county: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = Query(default="next_appearance", pattern="^(next_appearance|county|index_number|created_at)$"),
    user_id: int = Depends(get_current_user_id),
):
    with get_db() as conn:
        query = """
            SELECT c.*,
                   (SELECT MIN(a.appearance_date) FROM appearances a
                    WHERE a.case_id = c.id AND a.appearance_date >= date('now')) as next_appearance
            FROM cases c WHERE c.user_id = ?
        """
        params: list = [user_id]

        if court_type:
            query += " AND c.court_type = ?"
            params.append(court_type)
        if county:
            query += " AND c.county = ?"
            params.append(county)
        if status:
            query += " AND c.case_status = ?"
            params.append(status)

        if sort_by == "next_appearance":
            query += " ORDER BY CASE WHEN next_appearance IS NULL THEN 1 ELSE 0 END, next_appearance ASC"
        elif sort_by == "county":
            query += " ORDER BY c.county ASC"
        elif sort_by == "index_number":
            query += " ORDER BY c.index_number ASC"
        else:
            query += " ORDER BY c.created_at DESC"

        rows = conn.execute(query, params).fetchall()

    return [_row_to_case(row, next_appearance=row["next_appearance"]) for row in rows]


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(data: CaseCreate, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO cases (user_id, court_type, county, index_number, case_year, case_status,
                                  plaintiff, defendant, plaintiff_firm, defendant_firm, justice, part, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, data.court_type, data.county, data.index_number, data.case_year,
                data.case_status, data.plaintiff, data.defendant, data.plaintiff_firm,
                data.defendant_firm, data.justice, data.part, data.notes,
            ),
        )
        case_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()

    return _row_to_case(row)


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(case_id: int, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM cases WHERE id = ? AND user_id = ?", (case_id, user_id)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    with get_db() as conn:
        next_app = conn.execute(
            "SELECT MIN(appearance_date) as next_date FROM appearances WHERE case_id = ? AND appearance_date >= date('now')",
            (case_id,),
        ).fetchone()

    return _row_to_case(row, next_appearance=next_app["next_date"] if next_app else None)


@router.put("/{case_id}", response_model=CaseOut)
async def update_case(case_id: int, data: CaseUpdate, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM cases WHERE id = ? AND user_id = ?", (case_id, user_id)
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Case not found")

        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values())
        values.extend([case_id, user_id])

        conn.execute(
            f"UPDATE cases SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            values,
        )

        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()

    return _row_to_case(row)


@router.delete("/{case_id}", status_code=204)
async def delete_case(case_id: int, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM cases WHERE id = ? AND user_id = ?", (case_id, user_id)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Case not found")
