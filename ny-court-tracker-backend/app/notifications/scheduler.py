"""
Notification scheduler - background jobs for reminders, digests,
auto-priority escalation, and stale case alerts.

Integrates with the existing APScheduler from the scraper module.
"""

import logging
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.notifications.engine import (
    notify_appearance_reminder,
    notify_stale_case,
    notify_priority_escalation,
    get_user_notification_settings,
    create_notification,
)

logger = logging.getLogger(__name__)


def check_appearance_reminders() -> dict:
    """
    Check for upcoming court appearances and send reminders.

    Runs daily. For each user, checks their reminder_days setting
    and sends reminders for appearances coming up within that window.
    Avoids sending duplicate reminders.
    """
    results = {"checked": 0, "reminders_sent": 0, "errors": 0}
    today = datetime.now(timezone.utc).date()

    with get_db() as conn:
        # Get all users with notification settings
        users = conn.execute(
            "SELECT DISTINCT user_id FROM notification_settings WHERE case_updates_enabled = 1"
        ).fetchall()

    for user_row in users:
        user_id = user_row["user_id"]
        try:
            settings = get_user_notification_settings(user_id)
            reminder_days = settings.get("reminder_days", 1)

            # Get upcoming appearances within the reminder window
            target_date = today + timedelta(days=reminder_days)

            with get_db() as conn:
                appearances = conn.execute(
                    """SELECT a.id as appearance_id, a.case_id, a.appearance_date,
                              a.appearance_type, a.appearance_time,
                              c.index_number, c.user_id
                       FROM appearances a
                       JOIN cases c ON a.case_id = c.id
                       WHERE c.user_id = ?
                         AND a.appearance_date = ?
                         AND c.case_status = 'active'""",
                    (user_id, target_date.isoformat()),
                ).fetchall()

                for app in appearances:
                    results["checked"] += 1

                    # Check if reminder already sent
                    existing = conn.execute(
                        """SELECT id FROM notifications
                           WHERE user_id = ? AND appearance_id = ?
                             AND type = 'reminder'
                             AND DATE(created_at) = ?""",
                        (user_id, app["appearance_id"], today.isoformat()),
                    ).fetchone()

                    if existing:
                        continue

                    days_until = (target_date - today).days
                    notify_appearance_reminder(
                        user_id=user_id,
                        case_id=app["case_id"],
                        case_index=app["index_number"],
                        appearance_date=app["appearance_date"],
                        appearance_type=app["appearance_type"],
                        days_until=days_until,
                        appearance_id=app["appearance_id"],
                    )
                    results["reminders_sent"] += 1

            # Also check for today's appearances (day-of reminders)
            with get_db() as conn:
                today_appearances = conn.execute(
                    """SELECT a.id as appearance_id, a.case_id, a.appearance_date,
                              a.appearance_type, c.index_number
                       FROM appearances a
                       JOIN cases c ON a.case_id = c.id
                       WHERE c.user_id = ?
                         AND a.appearance_date = ?
                         AND c.case_status = 'active'""",
                    (user_id, today.isoformat()),
                ).fetchall()

                for app in today_appearances:
                    existing = conn.execute(
                        """SELECT id FROM notifications
                           WHERE user_id = ? AND appearance_id = ?
                             AND type = 'reminder'
                             AND DATE(created_at) = ?
                             AND title LIKE 'TODAY%'""",
                        (user_id, app["appearance_id"], today.isoformat()),
                    ).fetchone()

                    if existing:
                        continue

                    notify_appearance_reminder(
                        user_id=user_id,
                        case_id=app["case_id"],
                        case_index=app["index_number"],
                        appearance_date=app["appearance_date"],
                        appearance_type=app["appearance_type"],
                        days_until=0,
                        appearance_id=app["appearance_id"],
                    )
                    results["reminders_sent"] += 1

        except Exception as e:
            logger.error(f"Reminder check error for user {user_id}: {e}")
            results["errors"] += 1

    logger.info(f"Reminder check complete: {results}")
    return results


def check_auto_priority_escalation() -> dict:
    """
    Auto-escalate case priority when court date is within 7 days.

    Runs daily. Checks all active cases with upcoming appearances
    in the next 7 days and escalates normal-priority cases to high.
    """
    results = {"checked": 0, "escalated": 0, "errors": 0}
    today = datetime.now(timezone.utc).date()
    escalation_window = today + timedelta(days=7)

    with get_db() as conn:
        # Find normal-priority cases with appearances in next 7 days
        cases = conn.execute(
            """SELECT DISTINCT c.id as case_id, c.user_id, c.index_number, c.priority,
                      MIN(a.appearance_date) as next_date
               FROM cases c
               JOIN appearances a ON a.case_id = c.id
               WHERE c.case_status = 'active'
                 AND c.priority = 'normal'
                 AND a.appearance_date BETWEEN ? AND ?
               GROUP BY c.id""",
            (today.isoformat(), escalation_window.isoformat()),
        ).fetchall()

    for case in cases:
        results["checked"] += 1
        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE cases SET priority = 'high', updated_at = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), case["case_id"]),
                )

            days_until = (datetime.strptime(case["next_date"], "%Y-%m-%d").date() - today).days
            notify_priority_escalation(
                user_id=case["user_id"],
                case_id=case["case_id"],
                case_index=case["index_number"],
                reason=f"Court date in {days_until} days ({case['next_date']})",
            )
            results["escalated"] += 1

        except Exception as e:
            logger.error(f"Priority escalation error for case {case['case_id']}: {e}")
            results["errors"] += 1

    logger.info(f"Priority escalation check complete: {results}")
    return results


def check_stale_cases() -> dict:
    """
    Check for cases that haven't been updated recently and alert users.

    A case is considered stale if:
    - High priority: not updated in 8+ hours
    - Normal priority: not updated in 48+ hours

    Only alerts once per day per case.
    """
    results = {"checked": 0, "alerts_sent": 0, "errors": 0}
    now = datetime.now(timezone.utc)
    today = now.date()

    with get_db() as conn:
        cases = conn.execute(
            """SELECT c.id as case_id, c.user_id, c.index_number,
                      c.priority, c.last_checked_at, c.source
               FROM cases c
               WHERE c.case_status = 'active'
                 AND c.last_checked_at IS NOT NULL
                 AND c.source != 'manual'"""
        ).fetchall()

    for case in cases:
        results["checked"] += 1
        try:
            last_checked = datetime.fromisoformat(case["last_checked_at"].replace("Z", "+00:00"))
            if last_checked.tzinfo is None:
                last_checked = last_checked.replace(tzinfo=timezone.utc)

            hours_since = (now - last_checked).total_seconds() / 3600

            # Determine staleness threshold
            threshold = 8 if case["priority"] == "high" else 48
            if hours_since < threshold:
                continue

            # Check if we already alerted today
            with get_db() as conn:
                existing = conn.execute(
                    """SELECT id FROM notifications
                       WHERE user_id = ? AND case_id = ?
                         AND type = 'system'
                         AND title = 'Case Needs Attention'
                         AND DATE(created_at) = ?""",
                    (case["user_id"], case["case_id"], today.isoformat()),
                ).fetchone()

            if existing:
                continue

            notify_stale_case(
                user_id=case["user_id"],
                case_id=case["case_id"],
                case_index=case["index_number"],
                hours_since_update=hours_since,
            )
            results["alerts_sent"] += 1

        except Exception as e:
            logger.error(f"Stale check error for case {case['case_id']}: {e}")
            results["errors"] += 1

    logger.info(f"Stale case check complete: {results}")
    return results


def generate_daily_digest() -> dict:
    """
    Generate and send daily digest notifications to users who have opted in.

    Summarizes:
    - Today's upcoming appearances
    - Recent case updates (last 24 hours)
    - Cases needing attention
    """
    results = {"users_checked": 0, "digests_sent": 0, "errors": 0}
    now = datetime.now(timezone.utc)
    today = now.date()
    yesterday = now - timedelta(hours=24)

    with get_db() as conn:
        users = conn.execute(
            "SELECT user_id FROM notification_settings WHERE digest_frequency = 'daily'"
        ).fetchall()

    for user_row in users:
        user_id = user_row["user_id"]
        results["users_checked"] += 1

        try:
            with get_db() as conn:
                # Today's appearances
                today_apps = conn.execute(
                    """SELECT COUNT(*) as cnt FROM appearances a
                       JOIN cases c ON a.case_id = c.id
                       WHERE c.user_id = ? AND a.appearance_date = ?
                         AND c.case_status = 'active'""",
                    (user_id, today.isoformat()),
                ).fetchone()

                # Recent updates
                recent_events = conn.execute(
                    """SELECT COUNT(*) as cnt FROM case_events ce
                       JOIN cases c ON ce.case_id = c.id
                       WHERE c.user_id = ? AND ce.created_at >= ?""",
                    (user_id, yesterday.isoformat()),
                ).fetchone()

                # Upcoming appearances this week
                week_ahead = today + timedelta(days=7)
                week_apps = conn.execute(
                    """SELECT COUNT(*) as cnt FROM appearances a
                       JOIN cases c ON a.case_id = c.id
                       WHERE c.user_id = ?
                         AND a.appearance_date BETWEEN ? AND ?
                         AND c.case_status = 'active'""",
                    (user_id, today.isoformat(), week_ahead.isoformat()),
                ).fetchone()

            today_count = today_apps["cnt"] if today_apps else 0
            events_count = recent_events["cnt"] if recent_events else 0
            week_count = week_apps["cnt"] if week_apps else 0

            # Only send digest if there's something to report
            if today_count == 0 and events_count == 0 and week_count == 0:
                continue

            parts = []
            if today_count > 0:
                parts.append(f"{today_count} appearance(s) today")
            if events_count > 0:
                parts.append(f"{events_count} case update(s) in the last 24h")
            if week_count > 0:
                parts.append(f"{week_count} appearance(s) this week")

            message = "Daily Summary: " + ", ".join(parts) + "."

            create_notification(
                user_id=user_id,
                notification_type="system",
                title="Daily Digest",
                message=message,
            )
            results["digests_sent"] += 1

        except Exception as e:
            logger.error(f"Digest generation error for user {user_id}: {e}")
            results["errors"] += 1

    logger.info(f"Daily digest complete: {results}")
    return results


def generate_weekly_digest() -> dict:
    """
    Generate and send weekly digest notifications to users who have opted in.

    Summarizes the past week's activity and upcoming week's schedule.
    """
    results = {"users_checked": 0, "digests_sent": 0, "errors": 0}
    now = datetime.now(timezone.utc)
    today = now.date()
    last_week = now - timedelta(days=7)
    next_week = today + timedelta(days=7)

    with get_db() as conn:
        users = conn.execute(
            "SELECT user_id FROM notification_settings WHERE digest_frequency = 'weekly'"
        ).fetchall()

    for user_row in users:
        user_id = user_row["user_id"]
        results["users_checked"] += 1

        try:
            with get_db() as conn:
                # Past week events
                past_events = conn.execute(
                    """SELECT COUNT(*) as cnt FROM case_events ce
                       JOIN cases c ON ce.case_id = c.id
                       WHERE c.user_id = ? AND ce.created_at >= ?""",
                    (user_id, last_week.isoformat()),
                ).fetchone()

                # Upcoming appearances next week
                upcoming = conn.execute(
                    """SELECT COUNT(*) as cnt FROM appearances a
                       JOIN cases c ON a.case_id = c.id
                       WHERE c.user_id = ?
                         AND a.appearance_date BETWEEN ? AND ?
                         AND c.case_status = 'active'""",
                    (user_id, today.isoformat(), next_week.isoformat()),
                ).fetchone()

                # Total active cases
                active_cases = conn.execute(
                    "SELECT COUNT(*) as cnt FROM cases WHERE user_id = ? AND case_status = 'active'",
                    (user_id,),
                ).fetchone()

            events_count = past_events["cnt"] if past_events else 0
            upcoming_count = upcoming["cnt"] if upcoming else 0
            cases_count = active_cases["cnt"] if active_cases else 0

            if events_count == 0 and upcoming_count == 0:
                continue

            parts = []
            parts.append(f"{cases_count} active case(s)")
            if events_count > 0:
                parts.append(f"{events_count} update(s) this week")
            if upcoming_count > 0:
                parts.append(f"{upcoming_count} appearance(s) coming up")

            message = "Weekly Summary: " + ", ".join(parts) + "."

            create_notification(
                user_id=user_id,
                notification_type="system",
                title="Weekly Digest",
                message=message,
            )
            results["digests_sent"] += 1

        except Exception as e:
            logger.error(f"Weekly digest error for user {user_id}: {e}")
            results["errors"] += 1

    logger.info(f"Weekly digest complete: {results}")
    return results


def run_all_notification_checks() -> dict:
    """Run all periodic notification checks. Called by the scheduler."""
    logger.info("Running all notification checks...")
    return {
        "reminders": check_appearance_reminders(),
        "priority_escalation": check_auto_priority_escalation(),
        "stale_cases": check_stale_cases(),
    }
