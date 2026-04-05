import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas import (
    CaseCreate, CaseUpdate, CaseOut, FreshnessInfo,
    CaseSearchRequest, CaseSearchResponse, CaseSearchResult,
    CaseVerifyRequest, CaseEventOut,
)
from app.adapters.registry import get_adapter

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _compute_freshness(last_checked_at: Optional[str], last_source: Optional[str]) -> Optional[FreshnessInfo]:
    """Compute freshness indicator for a case."""
    if not last_checked_at:
        return FreshnessInfo(status="unknown")

    try:
        checked_time = datetime.fromisoformat(last_checked_at.replace("Z", "+00:00"))
        if checked_time.tzinfo is None:
            checked_time = checked_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        hours = (now - checked_time).total_seconds() / 3600.0

        if hours < 6:
            status = "fresh"
        elif hours < 24:
            status = "stale"
        else:
            status = "outdated"

        return FreshnessInfo(
            last_checked_at=last_checked_at,
            last_source=last_source,
            hours_since_check=round(hours, 1),
            status=status,
        )
    except (ValueError, TypeError):
        return FreshnessInfo(status="unknown")


def _row_to_case(row, next_appearance: Optional[str] = None) -> CaseOut:
    freshness = _compute_freshness(
        row["last_checked_at"] if "last_checked_at" in row.keys() else None,
        row["last_source"] if "last_source" in row.keys() else None,
    )
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
        priority=row["priority"] if "priority" in row.keys() else "normal",
        source=row["source"] if "source" in row.keys() else "manual",
        last_checked_at=row["last_checked_at"] if "last_checked_at" in row.keys() else None,
        last_source=row["last_source"] if "last_source" in row.keys() else None,
        verified=bool(row["verified"]) if "verified" in row.keys() else False,
        court_system=row["court_system"] if "court_system" in row.keys() else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        next_appearance=next_appearance,
        freshness=freshness,
    )


@router.get("", response_model=list[CaseOut])
async def list_cases(
    court_type: Optional[str] = None,
    county: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,
    verified: Optional[bool] = None,
    sort_by: str = Query(default="next_appearance", pattern="^(next_appearance|county|index_number|created_at|priority)$"),
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
        if priority:
            query += " AND c.priority = ?"
            params.append(priority)
        if source:
            query += " AND c.source = ?"
            params.append(source)
        if verified is not None:
            query += " AND c.verified = ?"
            params.append(1 if verified else 0)

        if sort_by == "next_appearance":
            query += " ORDER BY CASE WHEN next_appearance IS NULL THEN 1 ELSE 0 END, next_appearance ASC"
        elif sort_by == "county":
            query += " ORDER BY c.county ASC"
        elif sort_by == "index_number":
            query += " ORDER BY c.index_number ASC"
        elif sort_by == "priority":
            query += " ORDER BY CASE WHEN c.priority = 'high' THEN 0 ELSE 1 END, c.created_at DESC"
        else:
            query += " ORDER BY c.created_at DESC"

        rows = conn.execute(query, params).fetchall()

    return [_row_to_case(row, next_appearance=row["next_appearance"]) for row in rows]


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(data: CaseCreate, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO cases (user_id, court_type, county, index_number, case_year, case_status,
                                  plaintiff, defendant, plaintiff_firm, defendant_firm, justice, part, notes,
                                  priority, source, court_system, search_params, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, data.court_type, data.county, data.index_number, data.case_year,
                data.case_status, data.plaintiff, data.defendant, data.plaintiff_firm,
                data.defendant_firm, data.justice, data.part, data.notes,
                data.priority, data.source, data.court_system, data.search_params,
                1 if data.verified else 0,
            ),
        )
        case_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()

    return _row_to_case(row)


@router.post("/search", response_model=CaseSearchResponse)
async def search_cases(
    data: CaseSearchRequest,
    user_id: int = Depends(get_current_user_id),
):
    """
    Search court system for case verification.
    Returns matching cases so user can verify before tracking.
    """
    adapter = get_adapter(data.court_system)
    if not adapter:
        # Scraper not yet implemented — return a message guiding manual entry
        return CaseSearchResponse(
            results=[],
            court_system=data.court_system,
            message="Court system scraper is not yet available. Please add the case manually and it will be verified when the scraper is implemented.",
        )

    from app.adapters.base import SearchParams
    params = SearchParams(
        index_number=data.index_number,
        court_type=data.court_type,
        county=data.county,
    )
    records = await adapter.search(params)

    results = [
        CaseSearchResult(
            index_number=r.index_number,
            court_type=r.court_type,
            county=r.county,
            case_year=r.case_year,
            case_status=r.case_status,
            plaintiff=r.plaintiff,
            defendant=r.defendant,
            plaintiff_firm=r.plaintiff_firm,
            defendant_firm=r.defendant_firm,
            justice=r.justice,
            part=r.part,
            last_action=r.last_action,
            last_action_date=r.last_action_date,
            source=r.source.value,
        )
        for r in records
    ]

    if results:
        message = f"Found {len(results)} case(s). Please verify the details before tracking."
    else:
        message = "No cases found via scraper. You can still add the case manually."

    return CaseSearchResponse(
        results=results,
        court_system=data.court_system,
        message=message,
    )


@router.post("/verify", response_model=CaseOut, status_code=201)
async def verify_and_create_case(
    data: CaseVerifyRequest,
    user_id: int = Depends(get_current_user_id),
):
    """
    Create a case after user has verified the details from search results.
    Marks the case as verified and records the source.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO cases (user_id, court_type, county, index_number, case_year, case_status,
                                  plaintiff, defendant, plaintiff_firm, defendant_firm, justice, part, notes,
                                  priority, source, court_system, search_params, verified, last_checked_at, last_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, ?)""",
            (
                user_id, data.court_type, data.county, data.index_number, data.case_year,
                data.case_status, data.plaintiff, data.defendant, data.plaintiff_firm,
                data.defendant_firm, data.justice, data.part, data.notes,
                data.priority, data.court_system + "_scraper", data.court_system,
                data.search_params, data.court_system + "_scraper",
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


@router.get("/{case_id}/events", response_model=list[CaseEventOut])
async def list_case_events(case_id: int, user_id: int = Depends(get_current_user_id)):
    """List all events/filings for a case."""
    with get_db() as conn:
        case = conn.execute(
            "SELECT id FROM cases WHERE id = ? AND user_id = ?", (case_id, user_id)
        ).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        rows = conn.execute(
            "SELECT * FROM case_events WHERE case_id = ? ORDER BY event_date DESC, created_at DESC",
            (case_id,),
        ).fetchall()

    return [
        CaseEventOut(
            id=row["id"],
            case_id=row["case_id"],
            event_type=row["event_type"],
            event_date=row["event_date"],
            description=row["description"],
            source=row["source"] or "manual",
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/{case_id}/freshness", response_model=FreshnessInfo)
async def get_case_freshness(case_id: int, user_id: int = Depends(get_current_user_id)):
    """Get freshness indicator for a case."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT last_checked_at, last_source FROM cases WHERE id = ? AND user_id = ?",
            (case_id, user_id),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    return _compute_freshness(row["last_checked_at"], row["last_source"])


@router.put("/{case_id}/priority", response_model=CaseOut)
async def update_case_priority(
    case_id: int,
    priority: str = Query(pattern="^(normal|high)$"),
    user_id: int = Depends(get_current_user_id),
):
    """Update case priority level."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM cases WHERE id = ? AND user_id = ?", (case_id, user_id)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Case not found")

        conn.execute(
            "UPDATE cases SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (priority, case_id),
        )
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()

    return _row_to_case(row)


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
