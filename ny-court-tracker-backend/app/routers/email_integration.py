"""
Email integration API endpoints.

Handles email setup, forwarding verification, webhook reception,
and email configuration management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from typing import Optional

from app.database import get_db
from app.auth import get_current_user_id
from app.email.webhook import (
    setup_user_email,
    verify_forwarding,
    process_sendgrid_webhook,
    get_user_id_from_inbound_email,
)
from app.schemas import (
    EmailSetupResponse,
    EmailConfigOut,
    EmailSetupGuide,
    EmailVerifyResponse,
    EmailWebhookResponse,
    EmailLogOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])


@router.post("/setup", response_model=EmailSetupResponse)
async def setup_email(user_id: int = Depends(get_current_user_id)):
    """
    Set up email integration for the current user.
    
    Creates a unique inbound email address for the user
    and returns setup instructions for eTrack forwarding.
    """
    result = setup_user_email(user_id)
    return EmailSetupResponse(**result)


@router.get("/config", response_model=EmailConfigOut)
async def get_email_config(user_id: int = Depends(get_current_user_id)):
    """Get the current user's email integration configuration."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM email_configs WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Email integration not set up")

    return EmailConfigOut(
        id=row["id"],
        user_id=row["user_id"],
        inbound_email=row["inbound_email"],
        forwarding_verified=bool(row["forwarding_verified"]),
        provider=row["provider"],
        created_at=row["created_at"],
    )


@router.post("/verify", response_model=EmailVerifyResponse)
async def verify_email_forwarding(user_id: int = Depends(get_current_user_id)):
    """
    Mark email forwarding as verified.
    
    In production, this is auto-triggered when the first
    court notification email is received. Can also be
    manually triggered for testing.
    """
    result = verify_forwarding(user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return EmailVerifyResponse(**result)


@router.delete("/config")
async def delete_email_config(user_id: int = Depends(get_current_user_id)):
    """Remove email integration for the current user."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM email_configs WHERE user_id = ?",
            (user_id,),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Email integration not set up")

    return {"status": "deleted"}


@router.get("/setup-guide", response_model=EmailSetupGuide)
async def get_setup_guide(user_id: int = Depends(get_current_user_id)):
    """
    Get step-by-step instructions for setting up eTrack email forwarding.
    
    Returns personalized instructions including the user's
    unique inbound email address.
    """
    with get_db() as conn:
        config = conn.execute(
            "SELECT * FROM email_configs WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    inbound_email = config["inbound_email"] if config else None

    steps = [
        {
            "step": 1,
            "title": "Create an eTrack Account",
            "description": "If you don't already have one, visit the NY Courts eTrack system and create an account.",
            "url": "https://iapps.courts.state.ny.us/webcivil/etrackLogin",
            "completed": False,
        },
        {
            "step": 2,
            "title": "Set Up Email Notifications in eTrack",
            "description": "Log into eTrack, go to your notification preferences, and enable email notifications for your tracked cases.",
            "url": None,
            "completed": False,
        },
        {
            "step": 3,
            "title": "Set Up Email Forwarding",
            "description": (
                f"In your email client (Gmail, Outlook, etc.), set up a rule to forward "
                f"court notification emails to your unique Case Tracker address: {inbound_email or '[Set up email first]'}"
            ) if inbound_email else (
                "First, tap 'Set Up Email' to get your unique forwarding address, "
                "then set up forwarding in your email client."
            ),
            "url": None,
            "completed": bool(config and config["forwarding_verified"]) if config else False,
        },
        {
            "step": 4,
            "title": "Verify Forwarding",
            "description": "Forward a court notification email to verify the connection. We'll automatically detect and confirm it.",
            "url": None,
            "completed": bool(config and config["forwarding_verified"]) if config else False,
        },
    ]

    gmail_instructions = (
        "1. Open Gmail Settings (gear icon) > See all settings\n"
        "2. Go to 'Filters and Blocked Addresses' tab\n"
        "3. Click 'Create a new filter'\n"
        "4. In 'From' field, enter: noreply@nycourts.gov\n"
        "   (or the sender of your court notification emails)\n"
        f"5. Click 'Create filter' and check 'Forward it to: {inbound_email or '[your Case Tracker email]'}'\n"
        "6. Click 'Create filter'\n\n"
        "Alternatively, you can forward ALL emails matching 'court notification' in the subject."
    )

    outlook_instructions = (
        "1. Open Outlook Settings > Mail > Rules\n"
        "2. Click 'Add new rule'\n"
        "3. Name it 'Court Notifications to Case Tracker'\n"
        "4. Condition: 'From' contains 'nycourts.gov'\n"
        f"5. Action: 'Forward to' > {inbound_email or '[your Case Tracker email]'}\n"
        "6. Click 'Save'"
    )

    return EmailSetupGuide(
        inbound_email=inbound_email,
        forwarding_verified=bool(config and config["forwarding_verified"]) if config else False,
        steps=steps,
        gmail_instructions=gmail_instructions,
        outlook_instructions=outlook_instructions,
        privacy_note=(
            "We only parse court notification emails. All other emails "
            "forwarded to this address are automatically discarded without "
            "being read or stored. Your privacy is our top priority."
        ),
    )


@router.get("/log", response_model=list[EmailLogOut])
async def get_email_log(
    limit: int = 20,
    user_id: int = Depends(get_current_user_id),
):
    """Get the email processing log for the current user."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM email_log 
               WHERE user_id = ? 
               ORDER BY received_at DESC 
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()

    return [
        EmailLogOut(
            id=row["id"],
            sender=row["sender"],
            subject=row["subject"],
            events_extracted=row["events_extracted"],
            received_at=row["received_at"],
        )
        for row in rows
    ]


# ─── Webhook Endpoints (no auth - called by email service) ───

@router.post("/webhook/sendgrid", response_model=EmailWebhookResponse)
async def sendgrid_webhook(request: Request):
    """
    SendGrid Inbound Parse webhook endpoint.
    
    This endpoint receives POST requests from SendGrid when
    an email is received at any of our inbound addresses.
    
    No authentication required (SendGrid can't send bearer tokens).
    In production, validate using SendGrid's webhook signature.
    """
    try:
        form = await request.form()
        form_data = {key: form[key] for key in form}

        result = process_sendgrid_webhook(form_data)

        return EmailWebhookResponse(
            status=result.get("status", "error"),
            events_found=result.get("events_found", 0),
            message=result.get("reason", ""),
            results=result.get("results", []),
        )

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return EmailWebhookResponse(
            status="error",
            events_found=0,
            message=str(e),
        )


@router.post("/webhook/test")
async def test_webhook(
    sender: str = Form("noreply@nycourts.gov"),
    subject: str = Form("Court Notification - Case Update"),
    text: str = Form(""),
    to: Optional[str] = Form(None),
    user_id: int = Depends(get_current_user_id),
):
    """
    Test endpoint to simulate receiving a court notification email.
    
    Useful for testing the email parsing pipeline without
    actually sending an email through SendGrid.
    """
    # Get user's inbound email
    with get_db() as conn:
        config = conn.execute(
            "SELECT inbound_email FROM email_configs WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not config:
        raise HTTPException(
            status_code=400,
            detail="Email integration not set up. Call POST /api/email/setup first.",
        )

    recipient = to or config["inbound_email"]

    form_data = {
        "to": recipient,
        "from": sender,
        "subject": subject,
        "text": text,
        "html": "",
    }

    result = process_sendgrid_webhook(form_data)
    return result
