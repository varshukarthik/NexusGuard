"""Security alert email service for unauthorized data access events."""
from __future__ import annotations

import logging
import smtplib
import threading
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from ..config import get_settings

log = logging.getLogger("novatech.security_alerts")

# In-memory deduplication cache: (user_id, query) -> timestamp
_recent_alerts: dict[str, float] = {}
_cache_lock = threading.Lock()


def _is_duplicate(key: str, window_seconds: float = 3.0) -> bool:
    now = time.time()
    with _cache_lock:
        # Cleanup expired items
        expired = [k for k, t in _recent_alerts.items() if now - t > 180]
        for k in expired:
            _recent_alerts.pop(k, None)
        prev = _recent_alerts.get(key)
        if prev and (now - prev) < window_seconds:
            return True
        _recent_alerts[key] = now
        return False


def send_unauthorized_access_alert(
    *,
    user_name: str = "Unknown User",
    user_id: str = "unknown",
    role: str = "Standard User",
    clearance: str = "PUBLIC",
    query: str = "",
    resource: str = "Restricted Resource",
    classification: str = "RESTRICTED",
    reason: str = "Insufficient clearance / role permission",
    request_id: str = "",
    ip: str = "",
) -> bool:
    """Send an immediate security incident alert email to the admin."""
    settings = get_settings()
    recipient = settings.admin_alert_email
    if not recipient:
        log.warning("Admin alert email recipient not configured. Skipping alert.")
        return False

    dedup_key = f"{user_id}:{query[:60]}"
    if _is_duplicate(dedup_key, window_seconds=10.0):
        log.info("Suppressed duplicate security alert email for user %s within cooldown window.", user_id)
        return False

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"🚨 [SECURITY ALERT] Unauthorized Data Access Blocked — {user_name} ({classification})"

    plain_body = f"""=======================================================
NOVA SOLUTIONS ENTERPRISE SECURITY GATEWAY
AUTOMATED SECURITY INCIDENT ALERT
=======================================================

Incident Type: Unauthorized Data Access Attempt
Timestamp:     {now_utc}
Request ID:    {request_id or 'N/A'}

USER PROFILE
-------------------------------------------------------
Full Name:        {user_name}
User ID / Code:   {user_id}
Assigned Role:    {role}
Clearance Level:  {clearance.upper()}
Network IP:       {ip or 'Unknown'}

INCIDENT DETAILS
-------------------------------------------------------
Chat Prompt / Query:
"{query}"

Target Resource:
{resource}

Classification Tier:
{classification}

Enforcement Decision:
ACCESS DENIED & DATA WITHHELD

Policy Violation / Reason:
{reason}

-------------------------------------------------------
Enforced automatically by NovaTech Solutions Zero-Trust Policy Engine.
Log recorded in enterprise audit ledger.
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #0c121e;
      margin: 0;
      padding: 24px;
      color: #e2e8f0;
    }}
    .card {{
      max-width: 620px;
      margin: 0 auto;
      background: #111a2e;
      border-radius: 12px;
      border: 1px solid #ef4444;
      overflow: hidden;
      box-shadow: 0 10px 25px -5px rgba(239, 68, 68, 0.25);
    }}
    .header {{
      background: linear-gradient(135deg, #1e1b4b 0%, #3f121d 100%);
      padding: 24px 32px;
      border-bottom: 2px solid #ef4444;
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    .header-badge {{
      background: #ef4444;
      color: #ffffff;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 6px;
      display: inline-block;
      margin-bottom: 8px;
    }}
    .header h2 {{
      margin: 0;
      color: #ffffff;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.01em;
    }}
    .header p {{
      margin: 4px 0 0 0;
      color: #fca5a5;
      font-size: 13px;
    }}
    .content {{
      padding: 32px;
    }}
    .section-title {{
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #94a3b8;
      border-bottom: 1px solid #1e293b;
      padding-bottom: 6px;
      margin-top: 20px;
      margin-bottom: 14px;
    }}
    .field-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-bottom: 12px;
    }}
    .field {{
      background: #0d1527;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid #1e293b;
    }}
    .label {{
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748b;
      margin-bottom: 4px;
    }}
    .value {{
      font-size: 14px;
      color: #f1f5f9;
      font-weight: 600;
    }}
    .tag-restricted {{
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.4);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 700;
      display: inline-block;
    }}
    .query-box {{
      background: #080c16;
      border-left: 4px solid #ef4444;
      padding: 14px 18px;
      border-radius: 6px;
      font-size: 14px;
      line-height: 1.6;
      color: #fca5a5;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      margin-top: 6px;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .reason-box {{
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      padding: 12px 16px;
      border-radius: 6px;
      font-size: 13px;
      color: #fecaca;
      margin-top: 8px;
    }}
    .status-badge {{
      background: #ef4444;
      color: #ffffff;
      padding: 3px 10px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.05em;
    }}
    .footer {{
      background: #0a0f1d;
      padding: 16px 32px;
      border-top: 1px solid #1e293b;
      font-size: 12px;
      color: #64748b;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div>
        <div class="header-badge">Security Guard Alert</div>
        <h2>Unauthorized Data Access Blocked</h2>
        <p>A user query attempted to retrieve data outside their authorized clearance tier.</p>
      </div>
    </div>
    <div class="content">
      <div class="section-title">Actor Profile</div>
      <div class="field-grid">
        <div class="field">
          <div class="label">User Name</div>
          <div class="value">{user_name}</div>
        </div>
        <div class="field">
          <div class="label">User / Employee ID</div>
          <div class="value">{user_id}</div>
        </div>
        <div class="field">
          <div class="label">Role</div>
          <div class="value">{role}</div>
        </div>
        <div class="field">
          <div class="label">Security Clearance</div>
          <div class="value"><span class="tag-restricted">{clearance.upper()}</span></div>
        </div>
      </div>

      <div class="section-title">Incident Details</div>
      <div class="field" style="margin-bottom: 12px;">
        <div class="label">Submitted Chat Query</div>
        <div class="query-box">{query}</div>
      </div>

      <div class="field-grid">
        <div class="field">
          <div class="label">Target Protected Resource</div>
          <div class="value">{resource}</div>
        </div>
        <div class="field">
          <div class="label">Data Classification</div>
          <div class="value"><span class="tag-restricted">{classification}</span></div>
        </div>
      </div>

      <div class="section-title">Zero-Trust Decision</div>
      <div class="reason-box">
        <strong>Enforcement Status:</strong> <span class="status-badge">DENIED / WITHHELD</span><br>
        <strong>Policy Details:</strong> {reason}
      </div>
      
      <div style="margin-top: 18px; font-size: 12px; color: #94a3b8;">
        <strong>Timestamp:</strong> {now_utc} &nbsp;•&nbsp; <strong>Request ID:</strong> <code>{request_id or 'N/A'}</code>
      </div>
    </div>
    <div class="footer">
      NovaTech Solutions Enterprise Intelligence Platform • Zero-Trust Access Gateway
    </div>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"NovaTech Security Gateway <{settings.smtp_user}>"
    msg["To"] = recipient
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="evocation.in")
    msg["X-Priority"] = "1"
    msg["Importance"] = "High"
    msg["X-Mailer"] = "NovaTech-Security-Gateway/1.0"

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    delivered, route = dispatch_smtp_message(msg, recipient)
    return delivered


def dispatch_smtp_message(msg: MIMEMultipart, recipient: str) -> tuple[bool, str]:
    """Transmits an email message trying cascading fallback routes:

    1. Optional HTTPS Email API (Resend / SendGrid - unblockable by cloud free-tier firewalls)
    2. Domain on Port 465 (SSL)
    3. Domain on Port 587 (STARTTLS)
    4. Direct Host IP on Port 587 (STARTTLS - avoids DNS latency)
    5. Direct Host IP on Port 465 (SSL)
    """
    settings = get_settings()

    # Route 1: HTTPS API (Resend) if configured
    if settings.resend_api_key:
        try:
            import json
            import urllib.request
            sender = f"NovaTech Security Gateway <{settings.smtp_user}>"
            html_content = ""
            text_content = ""
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    html_content = part.get_payload(decode=True).decode("utf-8", errors="replace")
                elif part.get_content_type() == "text/plain":
                    text_content = part.get_payload(decode=True).decode("utf-8", errors="replace")

            req_payload = {
                "from": sender,
                "to": [recipient],
                "subject": msg["Subject"],
                "text": text_content,
                "html": html_content or text_content,
            }
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps(req_payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status in (200, 201):
                    log.info("Email dispatched successfully via Resend HTTPS API to %s", recipient)
                    return True, "Resend HTTPS API (Port 443)"
        except Exception as exc:
            log.warning("Resend HTTPS API route failed: %s", exc)

    # Route 2: HTTPS API (SendGrid) if configured
    if settings.sendgrid_api_key:
        try:
            import json
            import urllib.request
            html_content = ""
            text_content = ""
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    html_content = part.get_payload(decode=True).decode("utf-8", errors="replace")
                elif part.get_content_type() == "text/plain":
                    text_content = part.get_payload(decode=True).decode("utf-8", errors="replace")

            req_payload = {
                "personalizations": [{"to": [{"email": recipient}]}],
                "from": {"email": settings.smtp_user, "name": "NovaTech Security Gateway"},
                "subject": msg["Subject"],
                "content": [
                    {"type": "text/plain", "value": text_content or "NovaTech Security Alert"},
                    {"type": "text/html", "value": html_content or text_content},
                ],
            }
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=json.dumps(req_payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status in (200, 202):
                    log.info("Email dispatched successfully via SendGrid HTTPS API to %s", recipient)
                    return True, "SendGrid HTTPS API (Port 443)"
        except Exception as exc:
            log.warning("SendGrid HTTPS API route failed: %s", exc)

    candidates = [
        (settings.smtp_host, 465, True, f"{settings.smtp_host}:465 (SSL)"),
        (settings.smtp_host, 587, False, f"{settings.smtp_host}:587 (STARTTLS)"),
        ("37.114.37.231", 587, False, "37.114.37.231:587 (Direct IP STARTTLS)"),
        ("37.114.37.231", 465, True, "37.114.37.231:465 (Direct IP SSL)"),
    ]

    errors: list[str] = []
    for host, port, use_ssl, label in candidates:
        try:
            log.debug("Attempting SMTP delivery to %s via %s", recipient, label)
            if use_ssl:
                with smtplib.SMTP_SSL(host, port, timeout=8) as server:
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=8) as server:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.send_message(msg)
            log.info("Email successfully dispatched to %s via %s", recipient, label)
            return True, label
        except Exception as exc:
            err_msg = f"{label} failed: {type(exc).__name__} ({exc})"
            log.warning("SMTP route %s failed: %s", label, exc)
            errors.append(err_msg)

    log.error("All SMTP routes failed for recipient %s. Errors: %s", recipient, "; ".join(errors))
    return False, "All routes failed: " + "; ".join(errors)


def send_unauthorized_access_alert_async(**kwargs) -> None:
    """Dispatches the security alert email in a background daemon thread without blocking chat."""
    thread = threading.Thread(target=send_unauthorized_access_alert, kwargs=kwargs, daemon=True)
    thread.start()
