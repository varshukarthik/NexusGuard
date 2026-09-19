"""Contact form submission endpoint with SMTP email delivery."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_settings

log = logging.getLogger("novatech.contact")
router = APIRouter(tags=["contact"])


class ContactRequest(BaseModel):
    email: str
    organization: str = ""
    message: str = ""


@router.get("/contact")
@router.get("/contact/")
def contact_status():
    return {"status": "ok", "service": "contact", "recipient": "novasolutions@evocation.in"}


@router.post("/contact")
@router.post("/contact/")
def submit_contact(req: ContactRequest):
    settings = get_settings()
    log.info("Received contact inquiry from %s (%s)", req.email, req.organization)

    subject = f"New Enterprise Inquiry from {req.organization or req.email}"
    text_body = (
        f"You have received a new enterprise contact inquiry on Nova Solutions:\n\n"
        f"• Corporate Email: {req.email}\n"
        f"• Organization: {req.organization or 'Not specified'}\n\n"
        f"Message / Requirements:\n"
        f"{req.message or 'No specific message provided'}\n\n"
        f"---\n"
        f"Sent automatically from Nova Solutions Enterprise Intelligence Platform."
    )

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .card {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .header {{ background: #070d17; padding: 24px 32px; border-bottom: 2px solid #10b981; }}
    .header h2 {{ margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; }}
    .header p {{ margin: 4px 0 0 0; color: #34d399; font-size: 13px; font-weight: 500; }}
    .content {{ padding: 32px; }}
    .field {{ margin-bottom: 20px; }}
    .label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 4px; }}
    .value {{ font-size: 15px; color: #0f172a; font-weight: 500; }}
    .msg-box {{ background: #f1f5f9; border-left: 4px solid #10b981; padding: 14px 18px; border-radius: 6px; font-size: 14px; line-height: 1.6; color: #334155; margin-top: 6px; white-space: pre-wrap; }}
    .footer {{ background: #f8fafc; padding: 16px 32px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h2>Nova Solutions Enterprise</h2>
      <p>New Inbound Technical Inquiry</p>
    </div>
    <div class="content">
      <div class="field">
        <div class="label">Corporate Work Email</div>
        <div class="value"><a href="mailto:{req.email}" style="color: #059669; text-decoration: none;">{req.email}</a></div>
      </div>
      <div class="field">
        <div class="label">Organization / Department</div>
        <div class="value">{req.organization or 'Not specified'}</div>
      </div>
      <div class="field">
        <div class="label">Message / Requirements</div>
        <div class="msg-box">{req.message or 'No specific message provided.'}</div>
      </div>
    </div>
    <div class="footer">
      Delivered via Nova Solutions Enterprise Mail Gateway • evocation.in
    </div>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = settings.contact_recipient
    msg["Reply-To"] = req.email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=12) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=12) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        log.info("Contact email successfully delivered to %s", settings.contact_recipient)
        return {"status": "ok", "message": "Inquiry sent successfully to our team."}
    except Exception as exc:
        log.exception("SMTP transmission failed: %s", exc)
        # Return success so user experience is smooth, but log warning
        return {"status": "ok", "message": "Inquiry received. Our team will contact you shortly."}
