"""
Password reset email sending via Mailgun HTTP API.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = os.environ.get(
    "INBOUND_EMAIL_DOMAIN",
    "sandboxd49565360f644e5385986fc016c23e16.mailgun.org",
)
FROM_EMAIL = f"NY Court Tracker <noreply@{MAILGUN_DOMAIN}>"

# The frontend URL where users enter their reset token
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "https://case-schedule-app-jgutrt5s.devinapps.com",
)


def _build_reset_email_html(reset_token: str, expires_minutes: int = 60) -> str:
    """Build a professional HTML email for password reset."""
    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f9fafb;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
          <!-- Header -->
          <tr>
            <td style="background-color:#18181b;padding:24px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;">NY Court Tracker</h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px 24px;">
              <h2 style="margin:0 0 8px;color:#18181b;font-size:18px;font-weight:600;">Password Reset Request</h2>
              <p style="margin:0 0 20px;color:#6b7280;font-size:14px;line-height:1.5;">
                We received a request to reset your password. Use the code below to set a new password.
              </p>
              <!-- Token Code -->
              <div style="background-color:#f3f4f6;border:1px solid #e5e7eb;border-radius:8px;padding:16px;text-align:center;margin-bottom:20px;">
                <p style="margin:0 0 4px;color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Your Reset Code</p>
                <p style="margin:0;color:#18181b;font-size:24px;font-weight:700;letter-spacing:2px;font-family:monospace;">{reset_token}</p>
              </div>
              <p style="margin:0 0 20px;color:#6b7280;font-size:14px;line-height:1.5;">
                This code will expire in <strong>{expires_minutes} minutes</strong>. Enter it on the Reset Password screen in the app.
              </p>
              <!-- Disclaimer -->
              <div style="border-top:1px solid #e5e7eb;padding-top:16px;margin-top:16px;">
                <p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.5;">
                  If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.
                </p>
              </div>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color:#f9fafb;padding:16px 24px;text-align:center;border-top:1px solid #e5e7eb;">
              <p style="margin:0;color:#9ca3af;font-size:11px;">
                NY Court Tracker &mdash; Track all your court appearances in one place
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_reset_email_text(reset_token: str, expires_minutes: int = 60) -> str:
    """Build a plain text version of the password reset email."""
    return (
        f"NY Court Tracker - Password Reset\n"
        f"{'=' * 40}\n\n"
        f"We received a request to reset your password.\n\n"
        f"Your reset code: {reset_token}\n\n"
        f"This code will expire in {expires_minutes} minutes.\n"
        f"Enter it on the Reset Password screen in the app.\n\n"
        f"If you did not request a password reset, you can safely ignore this email.\n"
        f"Your password will remain unchanged.\n"
    )


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Send a password reset email via Mailgun HTTP API.

    Returns True if the email was sent (or would be sent), False on error.
    """
    if not MAILGUN_API_KEY:
        logger.warning(
            "MAILGUN_API_KEY not set; password reset email not sent to %s",
            to_email,
        )
        return False

    html_body = _build_reset_email_html(reset_token)
    text_body = _build_reset_email_text(reset_token)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": FROM_EMAIL,
                    "to": [to_email],
                    "subject": "Reset Your Password - NY Court Tracker",
                    "text": text_body,
                    "html": html_body,
                },
                timeout=10.0,
            )
            if response.status_code == 200:
                logger.info("Password reset email sent to %s", to_email)
                return True
            else:
                logger.error(
                    "Mailgun returned %s: %s",
                    response.status_code,
                    response.text,
                )
                return False
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False
