"""
Deduplication and reconciliation engine.

Handles the case where both scraper and email provide data
for the same case. The core rule: Email (push) always wins
over scraper (pull) as it's direct from the court system.

Dedup key: (case_number, court, county, event_date, event_type)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.database import get_db
from app.email.parser import ParsedEmailEvent

logger = logging.getLogger(__name__)


def find_matching_case(
    user_id: int,
    index_number: Optional[str],
    county: Optional[str] = None,
    court_type: Optional[str] = None,
) -> Optional[dict]:
    """
    Find a tracked case matching the given parameters.
    
    Args:
        user_id: The user who owns the case
        index_number: Case index number
        county: County name (optional, for disambiguation)
        court_type: Court type (optional, for disambiguation)
    
    Returns:
        Case row dict or None
    """
    if not index_number:
        return None

    with get_db() as conn:
        # Try exact match first
        query = "SELECT * FROM cases WHERE user_id = ? AND index_number = ?"
        params: list = [user_id, index_number]

        if county:
            query += " AND LOWER(county) = LOWER(?)"
            params.append(county)

        if court_type:
            query += " AND court_type = ?"
            params.append(court_type)

        row = conn.execute(query, params).fetchone()

        if row:
            return dict(row)

        # Try partial match on index number (sometimes formats differ)
        # e.g., "123456/2026" vs "123456"
        base_number = index_number.split("/")[0] if "/" in index_number else index_number
        query = "SELECT * FROM cases WHERE user_id = ? AND index_number LIKE ?"
        params = [user_id, f"%{base_number}%"]

        if county:
            query += " AND LOWER(county) = LOWER(?)"
            params.append(county)

        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def is_duplicate_event(case_id: int, event: ParsedEmailEvent) -> bool:
    """
    Check if an event already exists for this case.
    
    Dedup key: (case_id, event_date, event_type)
    """
    with get_db() as conn:
        query = """
            SELECT COUNT(*) as cnt FROM case_events
            WHERE case_id = ? AND event_type = ?
        """
        params: list = [case_id, event.event_type]

        if event.event_date:
            query += " AND event_date = ?"
            params.append(event.event_date)

        row = conn.execute(query, params).fetchone()
        return row["cnt"] > 0


def reconcile_event(
    case_id: int,
    event: ParsedEmailEvent,
    source: str = "etrack_email",
) -> dict:
    """
    Reconcile an email event with existing case data.
    
    Rules:
    1. If email update exists, it wins (source of truth)
    2. If only scraper data exists, email overwrites it
    3. If both exist with conflicting data, email wins and a note is logged
    
    Args:
        case_id: The case to update
        event: Parsed email event
        source: Data source identifier
    
    Returns:
        Dict with reconciliation result
    """
    result = {
        "action": "none",
        "case_id": case_id,
        "event_type": event.event_type,
        "details": "",
    }

    # Check for duplicate
    if is_duplicate_event(case_id, event):
        # Check if existing event was from scraper - if so, update source
        with get_db() as conn:
            existing = conn.execute(
                """SELECT * FROM case_events 
                   WHERE case_id = ? AND event_type = ? AND event_date = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (case_id, event.event_type, event.event_date),
            ).fetchone()

            if existing and existing["source"] != "etrack_email":
                # Email wins - update the source and description
                conn.execute(
                    """UPDATE case_events 
                       SET source = ?, description = ?, source_raw = ?
                       WHERE id = ?""",
                    (source, event.description, event.raw_text, existing["id"]),
                )
                result["action"] = "updated_source"
                result["details"] = f"Updated event source from {existing['source']} to {source}"
                logger.info(
                    f"Reconciled event for case {case_id}: "
                    f"email overwrote {existing['source']} data"
                )
            else:
                result["action"] = "skipped_duplicate"
                result["details"] = "Event already exists from email source"

        return result

    # New event - insert it
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO case_events 
               (case_id, event_type, event_date, description, source, source_raw, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                case_id,
                event.event_type,
                event.event_date,
                event.description,
                source,
                event.raw_text,
                now,
            ),
        )

        # Update case last_checked_at and last_source
        conn.execute(
            """UPDATE cases 
               SET last_checked_at = ?, last_source = ?, updated_at = ?
               WHERE id = ?""",
            (now, source, now, case_id),
        )

    result["action"] = "created"
    result["details"] = f"New {event.event_type} event from {source}"
    logger.info(f"Created new event for case {case_id}: {event.event_type}")

    return result


def process_email_events(
    user_id: int,
    events: list[ParsedEmailEvent],
    source: str = "etrack_email",
) -> list[dict]:
    """
    Process a list of parsed email events for a user.
    
    For each event:
    1. Find the matching tracked case
    2. Check for duplicates
    3. Reconcile with existing data (email wins)
    4. Create case events and update case freshness
    5. Create notifications for the user
    
    Args:
        user_id: The user who received the email
        events: List of parsed events from the email
        source: Data source identifier
    
    Returns:
        List of reconciliation results
    """
    results = []

    for event in events:
        # Find matching case
        case = find_matching_case(
            user_id=user_id,
            index_number=event.index_number,
            county=event.county,
            court_type=event.court_type,
        )

        if not case:
            results.append({
                "action": "no_match",
                "index_number": event.index_number,
                "event_type": event.event_type,
                "details": f"No tracked case found for index {event.index_number}",
            })
            logger.info(
                f"No matching case for user {user_id}, "
                f"index {event.index_number}"
            )
            continue

        # Reconcile the event
        reconcile_result = reconcile_event(case["id"], event, source)
        results.append(reconcile_result)

        # If event was created or updated, also handle appearance updates
        if (
            event.event_type == "appearance_scheduled"
            and event.event_date
            and reconcile_result["action"] in ("created", "updated_source")
        ):
            _upsert_appearance(case["id"], event, source)

        # Create notification for the user
        if reconcile_result["action"] in ("created", "updated_source"):
            _create_notification(user_id, case["id"], event)

    return results


def _upsert_appearance(case_id: int, event: ParsedEmailEvent, source: str) -> None:
    """Create or update an appearance from an email event."""
    with get_db() as conn:
        # Check if appearance already exists for this date
        existing = conn.execute(
            """SELECT id FROM appearances 
               WHERE case_id = ? AND appearance_date = ?""",
            (case_id, event.event_date),
        ).fetchone()

        now = datetime.now(timezone.utc).isoformat()

        if existing:
            # Update existing appearance with email data (email wins)
            updates = {"source": source, "updated_at": now}
            if event.event_time:
                updates["appearance_time"] = event.event_time
            if event.location:
                updates["location"] = event.location
            if event.description:
                updates["notes"] = event.description

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [existing["id"]]
            conn.execute(
                f"UPDATE appearances SET {set_clause} WHERE id = ?",
                values,
            )
            logger.info(f"Updated appearance {existing['id']} from email")
        else:
            # Create new appearance
            conn.execute(
                """INSERT INTO appearances 
                   (case_id, appearance_date, appearance_time, appearance_type,
                    location, notes, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    case_id,
                    event.event_date,
                    event.event_time,
                    event.event_type,
                    event.location,
                    event.description,
                    source,
                    now,
                    now,
                ),
            )
            logger.info(f"Created new appearance for case {case_id} from email")


def _create_notification(user_id: int, case_id: int, event: ParsedEmailEvent) -> None:
    """Create an in-app notification for a case event from email."""
    # Map event types to notification titles
    title_map = {
        "filing": "New Filing Detected",
        "appearance_scheduled": "Court Date Scheduled",
        "decision": "Decision Issued",
        "status_change": "Case Status Changed",
        "update": "Case Update",
    }

    title = title_map.get(event.event_type, "Case Update")
    message = event.description or "Update received via court notification email"

    if event.index_number:
        message = f"Case #{event.index_number}: {message}"

    with get_db() as conn:
        conn.execute(
            """INSERT INTO notifications 
               (user_id, case_id, type, title, message, created_at)
               VALUES (?, ?, 'update', ?, ?, CURRENT_TIMESTAMP)""",
            (user_id, case_id, title, message),
        )
