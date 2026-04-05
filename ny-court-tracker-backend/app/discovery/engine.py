"""
Case discovery engine - weekly scan of court systems to find new cases.

Searches court systems by attorney name/registration number, compares
results against already-tracked cases, and creates discovery records
with notifications for any new cases found.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.adapters.base import CourtRecord
from app.adapters.registry import get_adapter
from app.database import get_db
from app.notifications.engine import create_notification

logger = logging.getLogger(__name__)


def get_discovery_settings(user_id: int) -> Optional[dict]:
    """Get discovery settings for a user, returns None if not configured."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM discovery_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def create_or_update_discovery_settings(
    user_id: int,
    enabled: bool = True,
    attorney_name: Optional[str] = None,
    attorney_reg_number: Optional[str] = None,
    search_courts: Optional[str] = None,
    search_county: Optional[str] = None,
) -> dict:
    """Create or update discovery settings for a user."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM discovery_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if existing:
            updates = ["enabled = ?"]
            values: list = [1 if enabled else 0]

            if attorney_name is not None:
                updates.append("attorney_name = ?")
                values.append(attorney_name)
            if attorney_reg_number is not None:
                updates.append("attorney_reg_number = ?")
                values.append(attorney_reg_number)
            if search_courts is not None:
                updates.append("search_courts = ?")
                values.append(search_courts)
            if search_county is not None:
                updates.append("search_county = ?")
                values.append(search_county)

            values.append(user_id)
            conn.execute(
                f"UPDATE discovery_settings SET {', '.join(updates)} WHERE user_id = ?",
                values,
            )
        else:
            conn.execute(
                """INSERT INTO discovery_settings
                   (user_id, enabled, attorney_name, attorney_reg_number,
                    search_courts, search_county)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    1 if enabled else 0,
                    attorney_name,
                    attorney_reg_number,
                    search_courts or "ny_webcivil,ny_webcrimin",
                    search_county,
                ),
            )

        row = conn.execute(
            "SELECT * FROM discovery_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    return dict(row) if row else {}


def _get_user_tracked_index_numbers(user_id: int) -> set[str]:
    """Get all index numbers already tracked by a user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT index_number FROM cases WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    return {row["index_number"] for row in rows}


def _get_user_discovered_index_numbers(user_id: int) -> set[str]:
    """Get all index numbers already discovered (pending or dismissed) for a user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT index_number FROM discovered_cases WHERE user_id = ? AND status IN ('pending', 'dismissed')",
            (user_id,),
        ).fetchall()
    return {row["index_number"] for row in rows}


def _create_discovered_case(
    user_id: int,
    record: CourtRecord,
    court_system: str,
) -> Optional[int]:
    """
    Create a discovered case record and notify the user.

    Returns the discovered_case id if created, None if already exists.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Build case description for notification
    parties = ""
    if record.plaintiff and record.defendant:
        parties = f" ({record.plaintiff} v. {record.defendant})"
    elif record.plaintiff:
        parties = f" ({record.plaintiff})"
    elif record.defendant:
        parties = f" (Defendant: {record.defendant})"

    court_label = court_system.replace("ny_", "NY ").replace("webcivil", "WebCivil").replace("webcrimin", "WebCriminal")
    county_str = f" from {record.county}" if record.county else ""

    # Create notification
    notification = create_notification(
        user_id=user_id,
        notification_type="system",
        title="New Case Discovered",
        message=(
            f"We found a new case under your name: "
            f"Case #{record.index_number}{parties}{county_str} "
            f"via {court_label}. Would you like to track it?"
        ),
        send_push=True,
    )

    # Create discovered case record
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """INSERT INTO discovered_cases
                   (user_id, index_number, court_type, county, court_system,
                    plaintiff, defendant, case_status, last_action,
                    last_action_date, source_adapter, status, notification_id,
                    discovered_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (
                    user_id,
                    record.index_number,
                    record.court_type,
                    record.county,
                    court_system,
                    record.plaintiff,
                    record.defendant,
                    record.case_status,
                    record.last_action,
                    record.last_action_date,
                    court_system,
                    notification.get("id"),
                    now,
                ),
            )
            return cursor.lastrowid
        except Exception as e:
            # Unique constraint violation = already discovered
            logger.debug("Discovered case already exists: %s", e)
            return None


async def run_discovery_for_user(user_id: int, settings: dict) -> dict:
    """
    Run case discovery for a single user.

    Searches all configured court systems by attorney name,
    compares against tracked cases, and creates discoveries for new ones.

    Returns stats dict.
    """
    results = {
        "user_id": user_id,
        "courts_searched": 0,
        "cases_found": 0,
        "new_discoveries": 0,
        "errors": [],
    }

    attorney_name = settings.get("attorney_name")
    attorney_reg = settings.get("attorney_reg_number")
    search_courts = (settings.get("search_courts") or "ny_webcivil,ny_webcrimin").split(",")
    search_county = settings.get("search_county")

    if not attorney_name:
        results["errors"].append("No attorney name configured")
        return results

    # Get already-tracked and already-discovered case numbers
    tracked = _get_user_tracked_index_numbers(user_id)
    discovered = _get_user_discovered_index_numbers(user_id)
    known = tracked | discovered

    for court_system in search_courts:
        court_system = court_system.strip()
        if not court_system:
            continue

        adapter = get_adapter(court_system)
        if not adapter:
            results["errors"].append(f"No adapter for {court_system}")
            continue

        results["courts_searched"] += 1

        try:
            records = await adapter.search_by_attorney(
                attorney_name=attorney_name,
                attorney_reg_number=attorney_reg,
                county=search_county,
            )

            results["cases_found"] += len(records)

            for record in records:
                if record.index_number in known:
                    continue

                discovery_id = _create_discovered_case(
                    user_id=user_id,
                    record=record,
                    court_system=court_system,
                )

                if discovery_id:
                    results["new_discoveries"] += 1
                    known.add(record.index_number)

        except Exception as e:
            error_msg = f"Error searching {court_system}: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

    # Update last_run_at
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE discovery_settings SET last_run_at = ? WHERE user_id = ?",
            (now, user_id),
        )

    return results


def run_weekly_discovery() -> dict:
    """
    Run weekly case discovery for all enabled users.

    Called by the scheduler on a weekly basis (Monday 7am ET).
    """
    results = {
        "users_checked": 0,
        "total_discoveries": 0,
        "errors": 0,
    }

    with get_db() as conn:
        users = conn.execute(
            "SELECT * FROM discovery_settings WHERE enabled = 1 AND attorney_name IS NOT NULL"
        ).fetchall()

    if not users:
        logger.info("No users configured for weekly case discovery")
        return results

    logger.info("Running weekly case discovery for %d users", len(users))

    loop = asyncio.new_event_loop()
    try:
        for user_row in users:
            settings = dict(user_row)
            user_id = settings["user_id"]
            results["users_checked"] += 1

            try:
                user_result = loop.run_until_complete(
                    run_discovery_for_user(user_id, settings)
                )
                results["total_discoveries"] += user_result["new_discoveries"]
                if user_result["errors"]:
                    results["errors"] += len(user_result["errors"])
            except Exception as e:
                logger.error("Discovery error for user %d: %s", user_id, e)
                results["errors"] += 1
    finally:
        loop.close()

    logger.info("Weekly discovery complete: %s", results)
    return results


def accept_discovered_case(discovery_id: int, user_id: int) -> dict:
    """
    Accept a discovered case — add it to the user's tracked cases.

    Returns the new case data or error.
    """
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        discovery = conn.execute(
            "SELECT * FROM discovered_cases WHERE id = ? AND user_id = ?",
            (discovery_id, user_id),
        ).fetchone()

        if not discovery:
            return {"error": "Discovery not found"}

        if discovery["status"] != "pending":
            return {"error": f"Discovery already {discovery['status']}"}

        # Check if case already exists for user
        existing = conn.execute(
            "SELECT id FROM cases WHERE user_id = ? AND index_number = ?",
            (user_id, discovery["index_number"]),
        ).fetchone()

        if existing:
            # Mark as accepted but don't create duplicate
            conn.execute(
                "UPDATE discovered_cases SET status = 'accepted', resolved_at = ? WHERE id = ?",
                (now, discovery_id),
            )
            return {
                "status": "accepted",
                "case_id": existing["id"],
                "message": "Case was already being tracked",
            }

        # Create the case
        cursor = conn.execute(
            """INSERT INTO cases
               (user_id, court_type, county, index_number, case_status,
                plaintiff, defendant, source, court_system, verified,
                last_checked_at, last_source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (
                user_id,
                discovery["court_type"],
                discovery["county"] or "",
                discovery["index_number"],
                discovery["case_status"] or "active",
                discovery["plaintiff"],
                discovery["defendant"],
                discovery["source_adapter"] or "manual",
                discovery["court_system"],
                now,
                discovery["source_adapter"],
                now,
                now,
            ),
        )
        new_case_id = cursor.lastrowid

        # Mark discovery as accepted
        conn.execute(
            "UPDATE discovered_cases SET status = 'accepted', resolved_at = ? WHERE id = ?",
            (now, discovery_id),
        )

        # Mark the associated notification as read
        if discovery["notification_id"]:
            conn.execute(
                "UPDATE notifications SET read = 1 WHERE id = ?",
                (discovery["notification_id"],),
            )

    return {
        "status": "accepted",
        "case_id": new_case_id,
        "message": f"Case #{discovery['index_number']} is now being tracked",
    }


def dismiss_discovered_case(discovery_id: int, user_id: int) -> dict:
    """
    Dismiss a discovered case — user doesn't want to track it.
    """
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        discovery = conn.execute(
            "SELECT * FROM discovered_cases WHERE id = ? AND user_id = ?",
            (discovery_id, user_id),
        ).fetchone()

        if not discovery:
            return {"error": "Discovery not found"}

        if discovery["status"] != "pending":
            return {"error": f"Discovery already {discovery['status']}"}

        conn.execute(
            "UPDATE discovered_cases SET status = 'dismissed', resolved_at = ? WHERE id = ?",
            (now, discovery_id),
        )

        # Mark the associated notification as read
        if discovery["notification_id"]:
            conn.execute(
                "UPDATE notifications SET read = 1 WHERE id = ?",
                (discovery["notification_id"],),
            )

    return {
        "status": "dismissed",
        "message": f"Discovery #{discovery_id} dismissed",
    }


def get_pending_discoveries(user_id: int) -> list[dict]:
    """Get all pending discovered cases for a user."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM discovered_cases
               WHERE user_id = ? AND status = 'pending'
               ORDER BY discovered_at DESC""",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_discoveries(user_id: int, status: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Get discovered cases for a user with optional status filter."""
    query = "SELECT * FROM discovered_cases WHERE user_id = ?"
    params: list = [user_id]

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY discovered_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
