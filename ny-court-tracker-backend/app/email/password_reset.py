"""Password reset email sender using Mailgun API."""

import os
import logging

import httpx

logger = logging.getLogger(__name__)

MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = os.environ.get("INBOUND_EMAIL_DOMAIN", "")
FROM_EMAIL = os.environ.get("PASSWORD_RESET_FROM_EMAIL", f"noreply@{MAILGUN_DOMAIN}")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://case-schedule-app-jgutrt5s.devinapps.com")


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send a password reset email to the user.

    Returns True if the email was sent successfully (or if no API key is configured,
    logs the token for testing purposes).
    """
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    subject = "NY Court Tracker - Password Reset Request"

    html_body = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #18181b; font-size: 24px;">NY Court Tracker</h1>
        </div>
        <div style="background: #f9fafb; border-radius: 12px; padding: 30px; border: 1px solid #e5e7eb;">
            <h2 style="color: #18181b; font-size: 20px; margin-top: 0;">Password Reset Request</h2>
            <p style="color: #374151; font-size: 16px; line-height: 1.6;">
                We received a request to reset your password. Use the code below to reset it.
                This code expires in <strong>1 hour</strong>.
            </p>
            <div style="background: #18181b; color: #fff; padding: 16px 24px; border-radius: 8px; text-align: center; margin: 24px 0; font-size: 28px; letter-spacing: 4px; font-family: monospace;">
                {reset_token}
            </div>
            <p style="color: #374151; font-size: 16px; line-height: 1.6;">
                Or click the link below to reset your password:
            </p>
            <div style="text-align: center; margin: 24px 0;">
                <a href="{reset_link}" style="background: #18181b; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: 600;">
                    Reset Password
                </a>
            </div>
            <p style="color: #6b7280; font-size: 14px; line-height: 1.6;">
                If you didn't request this password reset, you can safely ignore this email.
                Your password will remain unchanged.
            </p>
        </div>
        <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 30px;">
            NY Court Tracker &mdash; Track all your court appearances in one place
        </p>
    </body>
    </html>
    """

    text_body = f"""NY Court Tracker - Password Reset

We received a request to reset your password.

Your reset code is: {reset_token}

Or use this link: {reset_link}

This code expires in 1 hour.

If you didn't request this password reset, you can safely ignore this email.
"""

    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
        logger.warning(
            "Mailgun not configured. Password reset token for %s: %s",
            to_email,
            reset_token,
        )
        return True

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": FROM_EMAIL,
                    "to": to_email,
                    "subject": subject,
                    "text": text_body,
                    "html": html_body,
                },
            )
        if response.status_code == 200:
            logger.info("Password reset email sent to %s", to_email)
            return True
        else:
            logger.error(
                "Failed to send password reset email: %s %s",
                response.status_code,
                response.text,
            )
            return False
    except Exception:
        logger.exception("Error sending password reset email to %s", to_email)
        return False
