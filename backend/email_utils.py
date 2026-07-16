"""
Email sending via Resend's HTTP API.


Render (and many PaaS platforms) block outbound raw SMTP traffic on
standard plans - a plain smtplib connection to Gmail/any SMTP host
fails with "Network is unreachable" no matter how correctly it's
configured, since it's a network-level restriction, not a credentials
or code issue. Resend sends over a normal HTTPS API call instead,
which works the same as any other outbound API call this app already
makes (Gemini, R2, etc.) - no special network access needed.

If RESEND_API_KEY is not set, all email functions silently return False
and the caller falls back to showing the content directly in the API
response (dev mode) - the app never breaks from missing email config.
"""

import os
import logging
import requests


def send_email(to_address, subject, body_text, body_html=None):
    """
    Sends an email via Resend's HTTP API. Returns True on success, False
    if Resend isn't configured or sending fails - caller should fall
    back to dev-mode behavior (e.g. showing a reset link directly) when
    False.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return False

    from_address = os.environ.get("RESEND_FROM", "StudyMate <onboarding@resend.dev>")

    payload = {
        "from": from_address,
        "to": [to_address],
        "subject": subject,
        "text": body_text,
    }
    if body_html:
        payload["html"] = body_html

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=10,
        )
        if response.status_code >= 400:
            logging.error(f"Resend email failed: {response.status_code} {response.text}")
            return False
        return True
    except Exception as e:
        logging.error(f"Resend email failed: {e}")
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