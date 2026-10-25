"""Email delivery.

Priority:
  1. SendGrid (if SENDGRID_API_KEY and SENDGRID_FROM_EMAIL are set)
  2. SMTP   (if SMTP_HOST is set)
  3. Console (default — logs email content to stdout, nothing is sent)
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings


def _default_html(body_text: str) -> str:
    return (
        '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
        'background:#f6f3ec;padding:24px;">'
        '<div style="max-width:600px;margin:0 auto;background:#ffffff;'
        'border-radius:12px;padding:24px;border:1px solid #dce3df;">'
        '<p style="margin:0 0 12px;font-size:12px;letter-spacing:2px;'
        'color:#987631;font-weight:900;text-transform:uppercase;">'
        'MAAT MOVERS</p>'
        f'<p style="margin:0;font-size:16px;color:#101b17;line-height:1.5;">{body_text}</p>'
        '</div></div>'
    )


def _send_via_sendgrid(
    to_email: str, subject: str, body_text: str, body_html: Optional[str]
) -> bool:
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError:
        print("[email] sendgrid package not installed")
        return False

    from_email = settings.SENDGRID_FROM_EMAIL
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body_text,
        html_content=body_html or _default_html(body_text),
    )
    try:
        client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        resp = client.send(message)
        print(f"[email] sendgrid sent to={to_email} status={resp.status_code}")
        return 200 <= resp.status_code < 300
    except Exception as e:
        print(f"[email] sendgrid error to={to_email}: {e}")
        return False


def _send_via_smtp(
    to_email: str, subject: str, body_text: str, body_html: Optional[str]
) -> bool:
    try:
        from_email = settings.SMTP_FROM or settings.SMTP_USER or "noreply@maatmovers.example"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html or _default_html(body_text), "html"))
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as s:
            if settings.SMTP_TLS:
                s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASS)
            s.sendmail(from_email, [to_email], msg.as_string())
        print(f"[email] smtp sent to={to_email}")
        return True
    except Exception as e:
        print(f"[email] smtp error to={to_email}: {e}")
        return False


def send_email(
    to_email: str, subject: str, body_text: str, body_html: Optional[str] = None
) -> bool:
    """Dispatch an email via SendGrid, SMTP, or console fallback."""
    if settings.SENDGRID_API_KEY and settings.SENDGRID_FROM_EMAIL:
        return _send_via_sendgrid(to_email, subject, body_text, body_html)
    if settings.SMTP_HOST:
        return _send_via_smtp(to_email, subject, body_text, body_html)
    print(f"[email][console] to={to_email} subject={subject!r} body={body_text!r}")
    return True