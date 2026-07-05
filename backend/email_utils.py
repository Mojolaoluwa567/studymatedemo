"""
Email sending via Resend (primary) with SMTP fallback.

Priority:
1. If RESEND_API_KEY is set → use Resend (transactional, reliable, free tier is 100 emails/day)
2. If SMTP_HOST is set → use stdlib smtplib
3. Neither → dev mode (returns False so callers show the link directly in the API response)

Set RESEND_FROM_EMAIL in .env to control the sender (e.g. "StudyMate <hello@yourdomain.com>").
Resend requires a verified domain on their end; for testing use their sandbox address.
"""

import os
import logging
import smtplib
from email.message import EmailMessage


def send_email(to_address, subject, body_text, body_html=None):
    """
    Sends an email. Returns True on success, False if no provider is
    configured (caller should fall back to dev mode).
    body_html is optional but improves the email appearance when provided.
    """
    resend_key = os.environ.get("RESEND_API_KEY")
    if resend_key:
        return _send_via_resend(to_address, subject, body_text, body_html, resend_key)

    smtp_host = os.environ.get("SMTP_HOST")
    if smtp_host:
        return _send_via_smtp(to_address, subject, body_text, smtp_host)

    return False  # dev mode - caller handles this


def _send_via_resend(to_address, subject, body_text, body_html, api_key):
    try:
        import resend
        resend.api_key = api_key
        from_addr = os.environ.get(
            "RESEND_FROM_EMAIL", "StudyMate <onboarding@resend.dev>"
        )
        payload = {
            "from": from_addr,
            "to": [to_address],
            "subject": subject,
            "text": body_text,
        }
        if body_html:
            payload["html"] = body_html
        resend.Emails.send(payload)
        return True
    except Exception as e:
        logging.error(f"Resend email failed: {e}")
        return False


def _send_via_smtp(to_address, subject, body_text, host):
    port = int(os.environ.get("SMTP_PORT", 587))
    username = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_address = os.environ.get("SMTP_FROM", username)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    msg.set_content(body_text)

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as e:
        logging.error(f"SMTP email failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

def send_welcome_email(to_address, username, role):
    """Sent immediately after a new account is created."""
    subject = "Welcome to StudyMate"
    role_tip = (
        "Upload your first course material from your Dashboard to get started."
        if role == "student"
        else "Create your first assignment from the Teacher Dashboard — "
             "generate a quiz from your course material and share the join code "
             "with your students."
    )
    body_text = (
        f"Hi {username},\n\n"
        f"Welcome to StudyMate!\n\n"
        f"{role_tip}\n\n"
        f"StudyMate turns your course material into real exam practice — "
        f"questions generated strictly from what you uploaded, graded instantly.\n\n"
        f"Good luck with your studies.\n\n"
        f"The StudyMate team"
    )
    body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
             max-width: 560px; margin: 40px auto; color: #1a1a2e; padding: 0 20px;">
  <p style="font-family: monospace; color: #6366f1; font-size: 11px;
             letter-spacing: 0.3em; text-transform: uppercase;">StudyMate</p>
  <h1 style="font-size: 24px; margin: 8px 0 16px;">Welcome, {username}!</h1>
  <p style="color: #64748b; line-height: 1.6;">{role_tip}</p>
  <p style="color: #64748b; line-height: 1.6;">
    StudyMate turns your course material into real exam practice — questions
    generated strictly from what you uploaded, graded instantly.
  </p>
  <a href="{os.environ.get('FRONTEND_ORIGIN', 'http://localhost:5173')}/dashboard"
     style="display: inline-block; background: #6366f1; color: white;
            padding: 12px 24px; border-radius: 8px; text-decoration: none;
            font-weight: 600; margin: 20px 0;">
    Go to Dashboard →
  </a>
  <p style="color: #94a3b8; font-size: 13px; margin-top: 40px;">
    Good luck with your studies.
  </p>
</body>
</html>
"""
    return send_email(to_address, subject, body_text, body_html)


def send_password_reset_email(to_address, username, reset_link):
    """Sent when a user requests a password reset."""
    subject = "Reset your StudyMate password"
    body_text = (
        f"Hi {username},\n\n"
        f"Someone requested a password reset for your StudyMate account.\n\n"
        f"Reset your password here:\n{reset_link}\n\n"
        f"This link expires in 1 hour. If you didn't request this, "
        f"you can ignore this email.\n\n"
        f"The StudyMate team"
    )
    body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
             max-width: 560px; margin: 40px auto; color: #1a1a2e; padding: 0 20px;">
  <p style="font-family: monospace; color: #6366f1; font-size: 11px;
             letter-spacing: 0.3em; text-transform: uppercase;">StudyMate</p>
  <h1 style="font-size: 24px; margin: 8px 0 16px;">Reset your password</h1>
  <p style="color: #64748b; line-height: 1.6;">
    Someone requested a password reset for <strong>{username}</strong>.
    Click the button below to set a new password.
  </p>
  <a href="{reset_link}"
     style="display: inline-block; background: #6366f1; color: white;
            padding: 12px 24px; border-radius: 8px; text-decoration: none;
            font-weight: 600; margin: 20px 0;">
    Reset password →
  </a>
  <p style="color: #94a3b8; font-size: 13px;">
    This link expires in 1 hour. If you didn't request this, you can
    safely ignore this email.
  </p>
</body>
</html>
"""
    return send_email(to_address, subject, body_text, body_html)
