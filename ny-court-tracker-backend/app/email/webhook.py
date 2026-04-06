"""
Email webhook handler for inbound email services.

Supports SendGrid Inbound Parse webhook format.
Can be extended to support Postmark, Mailgun, etc.

The webhook receives parsed email data from the inbound
email service and processes it through the email parser
and deduplication engine.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.database import get_db
from app.email.parser import parse_multi_case_email, is_court_notification
from app.email.dedup import process_email_events

logger = logging.getLogger(__name__)

# Configurable inbound email domain via environment variable.
# Must be set to a real domain with MX records pointing to your
# inbound email service (e.g. SendGrid Inbound Parse, Postmark, Mailgun).
INBOUND_EMAIL_DOMAIN = os.environ.get("INBOUND_EMAIL_DOMAIN", "")


def get_inbound_domain() -> str:
    """Return the configured inbound email domain, or empty string if not set."""
    return INBOUND_EMAIL_DOMAIN


def is_domain_configured() -> bool:
    """Check whether an inbound email domain has been configured."""
    return bool(INBOUND_EMAIL_DOMAIN)


def generate_inbound_email(user_id: int, domain: Optional[str] = None) -> str:
    """
    Generate a unique inbound email address for a user.
    
    Format: case-{hash}@{domain}
    The hash is deterministic so the same user always gets the same address.
    
    Uses INBOUND_EMAIL_DOMAIN env var by default. Raises ValueError if no
    domain is configured.
    """
    resolved_domain = domain or INBOUND_EMAIL_DOMAIN
    if not resolved_domain:
        raise ValueError(
            "No inbound email domain configured. "
            "Set the INBOUND_EMAIL_DOMAIN environment variable to a domain "
            "with MX records pointing to your inbound email service."
        )
    hash_input = f"courttracker-user-{user_id}-salt-v1"
    user_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
    return f"case-{user_hash}@{resolved_domain}"


def get_user_id_from_inbound_email(inbound_email: str) -> Optional[int]:
    """
    Look up the user ID from an inbound email address.
    
    Returns the user_id if found, None otherwise.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id FROM email_configs WHERE inbound_email = ?",
            (inbound_email,),
        ).fetchone()
        return row["user_id"] if row else None


def setup_user_email(user_id: int, domain: Optional[str] = None) -> dict:
    """
    Set up email integration for a user.
    
    Creates the email_configs record with a unique inbound email address.
    
    Returns:
        Dict with inbound_email and setup instructions
    """
    inbound_email = generate_inbound_email(user_id, domain)

    with get_db() as conn:
        # Check if already set up
        existing = conn.execute(
            "SELECT * FROM email_configs WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if existing:
            return {
                "inbound_email": existing["inbound_email"],
                "forwarding_verified": bool(existing["forwarding_verified"]),
                "provider": existing["provider"],
                "already_setup": True,
            }

        # Create new config
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO email_configs 
               (user_id, inbound_email, forwarding_verified, provider, created_at)
               VALUES (?, ?, 0, 'sendgrid_inbound', ?)""",
            (user_id, inbound_email, now),
        )

    return {
        "inbound_email": inbound_email,
        "forwarding_verified": False,
        "provider": "sendgrid_inbound",
        "already_setup": False,
    }


def verify_forwarding(user_id: int) -> dict:
    """
    Mark email forwarding as verified for a user.
    
    In production, this would be triggered by receiving a
    verification email at the user's inbound address.
    For now, it can be manually triggered or auto-verified
    on first successful email receipt.
    """
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM email_configs WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if not existing:
            return {"verified": False, "error": "Email not set up yet"}

        conn.execute(
            "UPDATE email_configs SET forwarding_verified = 1 WHERE user_id = ?",
            (user_id,),
        )

    return {
        "verified": True,
        "inbound_email": existing["inbound_email"],
    }


def process_sendgrid_webhook(form_data: dict) -> dict:
    """
    Process a SendGrid Inbound Parse webhook payload.
    
    SendGrid sends parsed email data as multipart form data:
    - to: recipient email
    - from: sender email
    - subject: email subject
    - text: plain text body
    - html: HTML body
    - envelope: JSON with to/from
    - headers: raw email headers
    - attachments: number of attachments
    
    Returns:
        Dict with processing results
    """
    recipient = form_data.get("to", "")
    sender = form_data.get("from", "")
    subject = form_data.get("subject", "")
    body_text = form_data.get("text", "")
    body_html = form_data.get("html", "")

    logger.info(f"Received inbound email to={recipient}, from={sender}, subject={subject}")

    # Privacy check: Only process court notifications
    if not is_court_notification(sender, subject, body_text or body_html or ""):
        logger.info(f"Discarding non-court email from {sender}: {subject}")
        return {
            "status": "discarded",
            "reason": "Not a court notification email",
        }

    # Find the user from the recipient address
    # Handle multiple recipients (extract our inbound address)
    inbound_email = _extract_inbound_address(recipient)
    if not inbound_email:
        logger.warning(f"Could not extract inbound address from: {recipient}")
        return {
            "status": "error",
            "reason": "Could not identify recipient user",
        }

    user_id = get_user_id_from_inbound_email(inbound_email)
    if not user_id:
        logger.warning(f"No user found for inbound email: {inbound_email}")
        return {
            "status": "error",
            "reason": f"No user registered for {inbound_email}",
        }

    # Auto-verify forwarding on first successful receipt
    with get_db() as conn:
        config = conn.execute(
            "SELECT forwarding_verified FROM email_configs WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if config and not config["forwarding_verified"]:
            conn.execute(
                "UPDATE email_configs SET forwarding_verified = 1 WHERE user_id = ?",
                (user_id,),
            )
            logger.info(f"Auto-verified forwarding for user {user_id}")

    # Parse the email
    now = datetime.now(timezone.utc).isoformat()
    parsed = parse_multi_case_email(
        sender=sender,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        received_at=now,
    )

    if not parsed.is_court_notification:
        return {
            "status": "discarded",
            "reason": "Email parsed but not identified as court notification",
        }

    if not parsed.events:
        return {
            "status": "parsed",
            "reason": "Court notification parsed but no events extracted",
            "parse_errors": parsed.parse_errors,
        }

    # Log the inbound email
    _log_inbound_email(user_id, sender, subject, body_text, len(parsed.events))

    # Process events through deduplication engine
    results = process_email_events(user_id, parsed.events, source="etrack_email")

    return {
        "status": "processed",
        "events_found": len(parsed.events),
        "results": results,
    }


def _extract_inbound_address(recipient: str) -> Optional[str]:
    """
    Extract the inbound app email address from the recipient field.
    
    The recipient field may contain:
    - Just the email: "case-abc123@courttracker.app"
    - Display name format: "Court Tracker <case-abc123@courttracker.app>"
    - Multiple recipients separated by commas
    """
    import re

    # Find all email addresses in the recipient string
    emails = re.findall(r"[\w.-]+@[\w.-]+", recipient)

    # Find the one that matches our inbound format
    for email in emails:
        if email.startswith("case-"):
            return email

    return emails[0] if emails else None


def _log_inbound_email(
    user_id: int,
    sender: str,
    subject: str,
    body_text: Optional[str],
    events_count: int,
) -> None:
    """Log an inbound email for audit purposes."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO email_log
               (user_id, sender, subject, events_extracted, received_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (user_id, sender, subject, events_count),
        )
