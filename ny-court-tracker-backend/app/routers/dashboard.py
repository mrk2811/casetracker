from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas import DashboardAppearance, FreshnessInfo

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _compute_freshness(last_checked_at: Optional[str], last_source: Optional[str]) -> Optional[FreshnessInfo]:
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


def _row_to_dashboard(row) -> DashboardAppearance:
    freshness = _compute_freshness(
        row["last_checked_at"] if "last_checked_at" in row.keys() else None,
        row["last_source"] if "last_source" in row.keys() else None,
    )
    return DashboardAppearance(
        appearance_id=row["appearance_id"],
        case_id=row["case_id"],
        appearance_date=row["appearance_date"],
        appearance_time=row["appearance_time"],
        appearance_type=row["appearance_type"],
        location=row["location"],
        court_type=row["court_type"],
        county=row["county"],
        index_number=row["index_number"],
        case_status=row["case_status"],
        plaintiff=row["plaintiff"],
        defendant=row["defendant"],
        justice=row["justice"],
        part=row["part"],
        priority=row["priority"] if "priority" in row.keys() else "normal",
        source=row["source"] if "source" in row.keys() else "manual",
        freshness=freshness,
    )


@router.get("", response_model=list[DashboardAppearance])
async def get_dashboard(
    court_type: Optional[str] = None,
    county: Optional[str] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,
    days_ahead: int = Query(default=90, ge=1, le=365),
    user_id: int = Depends(get_current_user_id),
):
    with get_db() as conn:
        query = """
            SELECT
                a.id as appearance_id,
                c.id as case_id,
                a.appearance_date,
                a.appearance_time,
                a.appearance_type,
                a.location,
                c.court_type,
                c.county,
                c.index_number,
                c.case_status,
                c.plaintiff,
                c.defendant,
                c.justice,
                c.part,
                c.priority,
                c.source,
                c.last_checked_at,
                c.last_source
            FROM appearances a
            JOIN cases c ON a.case_id = c.id
            WHERE c.user_id = ?
              AND a.appearance_date >= date('now')
              AND a.appearance_date <= date('now', '+' || ? || ' days')
        """
        params: list = [user_id, days_ahead]

        if court_type:
            query += " AND c.court_type = ?"
            params.append(court_type)
        if county:
            query += " AND c.county = ?"
            params.append(county)
        if priority:
            query += " AND c.priority = ?"
            params.append(priority)
        if source:
            query += " AND c.source = ?"
            params.append(source)

        query += " ORDER BY a.appearance_date ASC, a.appearance_time ASC"

        rows = conn.execute(query, params).fetchall()

    return [_row_to_dashboard(row) for row in rows]


@router.get("/calendar", response_model=list[DashboardAppearance])
async def get_calendar(
    month: Optional[int] = None,
    year: Optional[int] = None,
    user_id: int = Depends(get_current_user_id),
):
    with get_db() as conn:
        if month and year:
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"
        else:
            query_date = """
                SELECT date('now', 'start of month') as start_date,
                       date('now', 'start of month', '+1 month') as end_date
            """
            date_row = conn.execute(query_date).fetchone()
            start_date = date_row["start_date"]
            end_date = date_row["end_date"]

        query = """
            SELECT
                a.id as appearance_id,
                c.id as case_id,
                a.appearance_date,
                a.appearance_time,
                a.appearance_type,
                a.location,
                c.court_type,
                c.county,
                c.index_number,
                c.case_status,
                c.plaintiff,
                c.defendant,
                c.justice,
                c.part,
                c.priority,
                c.source,
                c.last_checked_at,
                c.last_source
            FROM appearances a
            JOIN cases c ON a.case_id = c.id
            WHERE c.user_id = ?
              AND a.appearance_date >= ?
              AND a.appearance_date < ?
            ORDER BY a.appearance_date ASC, a.appearance_time ASC
        """
        rows = conn.execute(query, [user_id, start_date, end_date]).fetchall()

    return [_row_to_dashboard(row) for row in rows]
