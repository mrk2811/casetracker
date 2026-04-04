from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas import DashboardAppearance

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=list[DashboardAppearance])
async def get_dashboard(
    court_type: Optional[str] = None,
    county: Optional[str] = None,
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
                c.part
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

        query += " ORDER BY a.appearance_date ASC, a.appearance_time ASC"

        rows = conn.execute(query, params).fetchall()

    return [
        DashboardAppearance(
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
        )
        for row in rows
    ]


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
                c.part
            FROM appearances a
            JOIN cases c ON a.case_id = c.id
            WHERE c.user_id = ?
              AND a.appearance_date >= ?
              AND a.appearance_date < ?
            ORDER BY a.appearance_date ASC, a.appearance_time ASC
        """
        rows = conn.execute(query, [user_id, start_date, end_date]).fetchall()

    return [
        DashboardAppearance(
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
        )
        for row in rows
    ]
