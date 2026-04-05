"""
Scraper scheduler - manages cron jobs for periodic case updates.

Uses APScheduler for background job scheduling:
- Normal priority cases: 2x/day (6am ET + 12:30pm ET with randomized offsets)
- High priority cases: every 2-4 hours (4x/day minimum)
- Randomized timing offsets to avoid detection
"""

import asyncio
import logging
import random
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Scheduler instance (singleton)
_scheduler: Optional[AsyncIOScheduler] = None
_is_running = False


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="US/Eastern")
    return _scheduler


async def scrape_case(case_id: int, db_path: str) -> dict:
    """
    Scrape a single case and update the database.

    Returns a dict with scrape job result info.
    """
    from app.adapters.registry import get_adapter

    job_result = {
        "case_id": case_id,
        "status": "failed",
        "error_message": None,
        "last_action": None,
    }

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get case details
        cursor.execute(
            "SELECT id, index_number, court_type, county, source FROM cases WHERE id = ?",
            (case_id,)
        )
        case = cursor.fetchone()
        if not case:
            job_result["error_message"] = f"Case {case_id} not found"
            conn.close()
            return job_result

        # Create scrape job record
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """INSERT INTO scrape_jobs (case_id, court_system, status, started_at, created_at)
               VALUES (?, ?, 'running', ?, ?)""",
            (case_id, case["source"] or "unknown", now, now)
        )
        job_id = cursor.lastrowid
        conn.commit()

        # Get the appropriate adapter
        source = case["source"] or ""
        if "webcrimin" in source.lower() or case["court_type"] == "criminal":
            adapter = get_adapter("ny_webcrimin")
        else:
            adapter = get_adapter("ny_webcivil")

        if not adapter:
            error_msg = f"No adapter found for source: {source}"
            cursor.execute(
                """UPDATE scrape_jobs SET status='failed', error_message=?, completed_at=?
                   WHERE id=?""",
                (error_msg, datetime.now(timezone.utc).isoformat(), job_id)
            )
            conn.commit()
            conn.close()
            job_result["error_message"] = error_msg
            return job_result

        # Perform the scrape
        record = await adapter.get_case_details(
            case["index_number"],
            case["court_type"],
            case["county"],
        )

        completed_at = datetime.now(timezone.utc).isoformat()

        if record:
            # Update case with fresh data
            update_fields = []
            update_values = []

            if record.last_action:
                job_result["last_action"] = record.last_action

            if record.case_status:
                update_fields.append("case_status = ?")
                update_values.append(record.case_status)
            if record.justice:
                update_fields.append("justice = ?")
                update_values.append(record.justice)
            if record.plaintiff_firm:
                update_fields.append("plaintiff_firm = ?")
                update_values.append(record.plaintiff_firm)
            if record.defendant_firm:
                update_fields.append("defendant_firm = ?")
                update_values.append(record.defendant_firm)

            # Always update freshness
            update_fields.append("last_checked_at = ?")
            update_values.append(completed_at)
            update_fields.append("last_source = ?")
            update_values.append(record.source.value if record.source else source)

            if update_fields:
                update_values.append(case_id)
                cursor.execute(
                    f"UPDATE cases SET {', '.join(update_fields)} WHERE id = ?",
                    update_values,
                )

            # Record success
            result_text = f"Last action: {record.last_action}" if record.last_action else "No new actions found"
            cursor.execute(
                """UPDATE scrape_jobs SET status='completed', result=?, completed_at=?
                   WHERE id=?""",
                (result_text, completed_at, job_id)
            )
            job_result["status"] = "completed"
        else:
            cursor.execute(
                """UPDATE scrape_jobs SET status='completed', result='No data returned', completed_at=?
                   WHERE id=?""",
                (completed_at, job_id)
            )
            job_result["status"] = "completed"
            job_result["error_message"] = "No data returned from scraper"

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error("Error scraping case %d: %s", case_id, e)
        job_result["error_message"] = str(e)
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """UPDATE scrape_jobs SET status='failed', error_message=?, completed_at=?
                   WHERE case_id=? AND status='running'""",
                (str(e), datetime.now(timezone.utc).isoformat(), case_id)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    return job_result


async def scrape_all_cases(priority: str, db_path: str) -> None:
    """
    Scrape all cases with the given priority level.

    Args:
        priority: 'normal' or 'high'
        db_path: Path to the SQLite database
    """
    # Add randomized delay (0-30 min for normal, 0-15 min for high)
    max_delay = 30 * 60 if priority == "normal" else 15 * 60
    delay = random.randint(0, max_delay)
    logger.info(
        "Starting %s priority scrape batch (delay: %d seconds)", priority, delay
    )
    await asyncio.sleep(delay)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM cases WHERE priority = ? AND source != 'manual'",
            (priority,)
        )
        cases = cursor.fetchall()
        conn.close()

        logger.info("Found %d %s priority cases to scrape", len(cases), priority)

        results = []
        for case in cases:
            result = await scrape_case(case["id"], db_path)
            results.append(result)
            # Random delay between cases (2-8 seconds)
            await asyncio.sleep(random.uniform(2, 8))

        succeeded = sum(1 for r in results if r["status"] == "completed")
        failed = sum(1 for r in results if r["status"] == "failed")
        logger.info(
            "Scrape batch complete: %d succeeded, %d failed out of %d total",
            succeeded, failed, len(results),
        )

    except Exception as e:
        logger.error("Error in scrape_all_cases: %s", e)


def setup_scheduler(db_path: str) -> AsyncIOScheduler:
    """
    Set up the scraper scheduler with cron jobs.

    Schedule:
    - Normal priority: 6:00 AM ET and 12:30 PM ET (with randomized offset applied in job)
    - High priority: Every 3 hours starting at 6:00 AM ET (with randomized offset)
    """
    scheduler = get_scheduler()

    if scheduler.running:
        logger.info("Scheduler already running, skipping setup")
        return scheduler

    # Normal priority: 2x/day at 6am and 12:30pm ET
    scheduler.add_job(
        scrape_all_cases,
        CronTrigger(hour=6, minute=0, timezone="US/Eastern"),
        args=["normal", db_path],
        id="scrape_normal_morning",
        name="Normal priority scrape (morning)",
        replace_existing=True,
    )
    scheduler.add_job(
        scrape_all_cases,
        CronTrigger(hour=12, minute=30, timezone="US/Eastern"),
        args=["normal", db_path],
        id="scrape_normal_afternoon",
        name="Normal priority scrape (afternoon)",
        replace_existing=True,
    )

    # High priority: every 3 hours (6am, 9am, 12pm, 3pm, 6pm, 9pm ET)
    scheduler.add_job(
        scrape_all_cases,
        CronTrigger(hour="6,9,12,15,18,21", minute=0, timezone="US/Eastern"),
        args=["high", db_path],
        id="scrape_high_priority",
        name="High priority scrape (every 3 hours)",
        replace_existing=True,
    )

    logger.info("Scraper scheduler configured with cron jobs")
    return scheduler


def start_scheduler(db_path: str) -> None:
    """Start the scheduler if not already running."""
    global _is_running
    scheduler = setup_scheduler(db_path)
    if not _is_running:
        scheduler.start()
        _is_running = True
        logger.info("Scraper scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler."""
    global _is_running, _scheduler
    if _scheduler and _is_running:
        _scheduler.shutdown()
        _is_running = False
        logger.info("Scraper scheduler stopped")


def get_scheduler_status() -> dict:
    """Get current scheduler status and next scheduled runs."""
    scheduler = get_scheduler()
    jobs = []

    if scheduler.running:
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
            })

    return {
        "running": scheduler.running if _scheduler else False,
        "jobs": jobs,
    }
