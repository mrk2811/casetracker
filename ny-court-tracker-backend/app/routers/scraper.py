"""
API endpoints for scraper control, status reporting, and scrape history.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db, DB_PATH
from app.auth import get_current_user_id
from app.scraper.scheduler import (
    get_scheduler_status,
    scrape_case,
    scrape_all_cases,
)

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


class ScrapeJobResponse(BaseModel):
    id: int
    case_id: int
    court_system: str
    status: str
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class ScraperStatusResponse(BaseModel):
    scheduler_running: bool
    jobs: list[dict]
    total_scrape_jobs: int
    recent_failures: int


class ManualScrapeRequest(BaseModel):
    case_id: int


class ManualScrapeResponse(BaseModel):
    status: str
    case_id: int
    last_action: Optional[str] = None
    error_message: Optional[str] = None


@router.get("/status", response_model=ScraperStatusResponse)
async def get_scraper_status_endpoint(
    user_id: int = Depends(get_current_user_id),
):
    """Get current scraper status and next scheduled runs."""
    scheduler_status = get_scheduler_status()

    with get_db() as conn:
        total_jobs = conn.execute("SELECT COUNT(*) FROM scrape_jobs").fetchone()[0]
        recent_failures = conn.execute(
            """SELECT COUNT(*) FROM scrape_jobs
               WHERE status = 'failed'
               AND created_at > datetime('now', '-24 hours')"""
        ).fetchone()[0]

    return ScraperStatusResponse(
        scheduler_running=scheduler_status["running"],
        jobs=scheduler_status["jobs"],
        total_scrape_jobs=total_jobs,
        recent_failures=recent_failures,
    )


@router.post("/trigger-manual", response_model=ManualScrapeResponse)
async def trigger_manual_scrape(
    request: ManualScrapeRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Manually trigger a scrape for a specific case."""
    with get_db() as conn:
        case = conn.execute(
            "SELECT id FROM cases WHERE id = ? AND user_id = ?",
            (request.case_id, user_id),
        ).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

    result = await scrape_case(request.case_id, DB_PATH)

    return ManualScrapeResponse(
        status=result["status"],
        case_id=result["case_id"],
        last_action=result.get("last_action"),
        error_message=result.get("error_message"),
    )


@router.get("/history/{case_id}", response_model=list[ScrapeJobResponse])
async def get_scrape_history(
    case_id: int,
    limit: int = 20,
    user_id: int = Depends(get_current_user_id),
):
    """Get scrape job history for a specific case."""
    with get_db() as conn:
        # Verify case belongs to user
        if not conn.execute(
            "SELECT id FROM cases WHERE id = ? AND user_id = ?",
            (case_id, user_id),
        ).fetchone():
            raise HTTPException(status_code=404, detail="Case not found")

        jobs = conn.execute(
            """SELECT id, case_id, court_system, status, scheduled_at, started_at,
                      completed_at, result, error_message, created_at
               FROM scrape_jobs
               WHERE case_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (case_id, limit),
        ).fetchall()

    return [
        ScrapeJobResponse(
            id=job[0],
            case_id=job[1],
            court_system=job[2],
            status=job[3],
            scheduled_at=job[4],
            started_at=job[5],
            completed_at=job[6],
            result=job[7],
            error_message=job[8],
            created_at=job[9],
        )
        for job in jobs
    ]


@router.post("/trigger-batch")
async def trigger_batch_scrape(
    priority: str = "normal",
    user_id: int = Depends(get_current_user_id),
):
    """Trigger a batch scrape for all cases of a given priority (admin/testing)."""
    if priority not in ("normal", "high"):
        raise HTTPException(status_code=400, detail="Priority must be 'normal' or 'high'")

    import asyncio
    asyncio.create_task(scrape_all_cases(priority, DB_PATH))

    return {"status": "started", "priority": priority}
