"""
Email sending via SMTP only (Resend removed - direct SMTP with any
provider: Gmail, Outlook, a custom domain's mail server, etc.)

Required .env variables:
  SMTP_HOST=smtp.gmail.com          (or your provider's SMTP host)
  SMTP_PORT=587
  SMTP_USER=your_email@gmail.com
  SMTP_PASSWORD=your_app_password   (NOT your normal password - see note below)
  SMTP_FROM=StudyMate <your_email@gmail.com>

Gmail note: Gmail blocks normal password login for SMTP. You need an
"App Password" instead - generate one at myaccount.google.com/apppasswords
(requires 2-factor auth enabled on the Google account first).

If SMTP_HOST is not set, all email functions silently return False and
the caller falls back to showing the content directly in the API
response (dev mode) - the app never breaks from missing email config.
"""

import os
import logging
import smtplib
from email.message import EmailMessage


def send_email(to_address, subject, body_text, body_html=None):
    """
    Sends an email via SMTP. Returns True on success, False if SMTP
    isn't configured or sending fails - caller should fall back to
    dev-mode behavior (e.g. showing a reset link directly) when False.
    """
    smtp_host = os.environ.get("SMTP_HOST")
    if not smtp_host:
        return False

    port = int(os.environ.get("SMTP_PORT", 587))
    username = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_address = os.environ.get("SMTP_FROM", username)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(smtp_host, port) as server:
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
    subject = "Welcome to StudyMate"
    role_tip = (
        "Upload your first course material from your Dashboard to get started."
        if role == "student"
        else "Create your first assignment from the Teacher Dashboard."
    )
    body_text = (
        f"Hi {username},\n\nWelcome to StudyMate!\n\n{role_tip}\n\n"
        f"Good luck with your studies.\n\nThe StudyMate team"
    )
    body_html = f"""
<!DOCTYPE html>
<html><body style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 40px auto; color: #1a1a2e; padding: 0 20px;">
  <p style="font-family: monospace; color: #6366f1; font-size: 11px; letter-spacing: 0.3em; text-transform: uppercase;">StudyMate</p>
  <h1 style="font-size: 24px; margin: 8px 0 16px;">Welcome, {username}!</h1>
  <p style="color: #64748b; line-height: 1.6;">{role_tip}</p>
  <a href="{os.environ.get('FRONTEND_ORIGIN', 'http://localhost:5173')}/dashboard"
     style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0;">
    Go to Dashboard →
  </a>
</body></html>
"""
    return send_email(to_address, subject, body_text, body_html)


def send_login_notification_email(to_address, username, login_time_str):
    """Sent on every successful login - security awareness, lets a user
    notice a login they didn't perform."""
    subject = "New sign-in to your StudyMate account"
    body_text = (
        f"Hi {username},\n\n"
        f"Your StudyMate account was just signed into at {login_time_str}.\n\n"
        f"If this was you, no action is needed. If you don't recognize this, "
        f"reset your password immediately from the login page.\n\n"
        f"The StudyMate team"
    )
    body_html = f"""
<!DOCTYPE html>
<html><body style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 40px auto; color: #1a1a2e; padding: 0 20px;">
  <p style="font-family: monospace; color: #6366f1; font-size: 11px; letter-spacing: 0.3em; text-transform: uppercase;">StudyMate</p>
  <h1 style="font-size: 22px; margin: 8px 0 16px;">New sign-in detected</h1>
  <p style="color: #64748b; line-height: 1.6;">
    Your account, <strong>{username}</strong>, was just signed into at {login_time_str}.
  </p>
  <p style="color: #64748b; line-height: 1.6;">
    If this was you, no action is needed. If you don't recognize this
    activity, reset your password immediately.
  </p>
</body></html>
"""
    return send_email(to_address, subject, body_text, body_html)


def send_achievement_email(to_address, username, achievement_name, achievement_description):
    subject = f"Achievement unlocked: {achievement_name}"
    body_text = (
        f"Hi {username},\n\n"
        f"You just earned a new achievement: {achievement_name}\n"
        f"{achievement_description}\n\n"
        f"Keep it up!\n\nThe StudyMate team"
    )
    body_html = f"""
<!DOCTYPE html>
<html><body style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 40px auto; color: #1a1a2e; padding: 0 20px;">
  <p style="font-family: monospace; color: #6366f1; font-size: 11px; letter-spacing: 0.3em; text-transform: uppercase;">StudyMate</p>
  <h1 style="font-size: 22px; margin: 8px 0 8px;">🏆 Achievement unlocked!</h1>
  <p style="font-size: 18px; font-weight: 600; margin: 16px 0 4px;">{achievement_name}</p>
  <p style="color: #64748b; line-height: 1.6;">{achievement_description}</p>
</body></html>
"""
    return send_email(to_address, subject, body_text, body_html)


def send_password_reset_email(to_address, username, reset_link):
    subject = "Reset your StudyMate password"
    body_text = (
        f"Hi {username},\n\nReset your password here:\n{reset_link}\n\n"
        f"This link expires in 1 hour. If you didn't request this, ignore this email.\n\n"
        f"The StudyMate team"
    )
    body_html = f"""
<!DOCTYPE html>
<html><body style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 40px auto; color: #1a1a2e; padding: 0 20px;">
  <p style="font-family: monospace; color: #6366f1; font-size: 11px; letter-spacing: 0.3em; text-transform: uppercase;">StudyMate</p>
  <h1 style="font-size: 24px; margin: 8px 0 16px;">Reset your password</h1>
  <p style="color: #64748b; line-height: 1.6;">
    Someone requested a password reset for <strong>{username}</strong>.
  </p>
  <a href="{reset_link}"
     style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0;">
    Reset password →
  </a>
  <p style="color: #94a3b8; font-size: 13px;">This link expires in 1 hour.</p>
</body></html>
"""
    return send_email(to_address, subject, body_text, body_html)