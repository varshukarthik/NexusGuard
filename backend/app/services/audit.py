"""Audit logging + rule-based anomaly detection.

Every security-relevant decision (authorization allow/deny, tool execution, confirmation, DLP redaction,
prompt-injection block, login) is written here. After each write, anomaly rules are evaluated for the actor.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from ..db.models import AuditLog, SecurityAlert

log = logging.getLogger("novatech.audit")


def record(db: DBSession, *, principal=None, company_id: str | None = None, action: str, resource: str = "",
           resource_id: str = "", classification: str = "", permission_result: str = "N/A", tool: str = "",
           result: str = "SUCCESS", reason: str = "", risk: str = "LOW", query: str = "", details: dict | None = None,
           user_id: str | None = None, user_name: str = "", ip: str = "", session_id: str = "",
           request_id: str = "", commit: bool = True, evaluate: bool = True) -> AuditLog:
    entry = AuditLog(
        company_id=company_id or principal.company_id,
        user_id=user_id or (principal.user_id if principal else None),
        user_name=user_name or (principal.full_name if principal else ""),
        session_id=session_id or (principal.session_id if principal else ""),
        ip=ip or (principal.ip if principal else ""),
        action=action, resource=resource[:300], resource_id=resource_id, classification=classification,
        permission_result=permission_result, tool=tool, result=result, reason=reason[:500], risk=risk,
        query=(query or "")[:2000], details=details or {}, request_id=request_id,
    )
    db.add(entry)
    db.flush()
    if evaluate and entry.user_id:
        try:
            evaluate_rules(db, entry)
        except Exception:  # anomaly detection must never break the request path
            log.exception("anomaly evaluation failed")
    if commit:
        db.commit()
    return entry


# ---- Anomaly rules ----------------------------------------------------------------------------

def _count(db, company_id, user_id, since, *conds) -> int:
    q = select(func.count(AuditLog.id)).where(AuditLog.company_id == company_id, AuditLog.user_id == user_id,
                                              AuditLog.ts >= since, *conds)
    return db.scalar(q) or 0


def _raise(db, entry: AuditLog, alert_type: str, title: str, pattern: str, risk: str, details: dict):
    """Create an alert, or bump the open one of the same type for this user (dedupe window 30 min)."""
    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    existing = db.scalar(select(SecurityAlert).where(
        SecurityAlert.company_id == entry.company_id, SecurityAlert.user_id == entry.user_id,
        SecurityAlert.alert_type == alert_type, SecurityAlert.status != "resolved", SecurityAlert.ts >= since))
    if existing:
        existing.event_count += 1
        existing.pattern = pattern
        existing.risk = risk if _rank(risk) > _rank(existing.risk) else existing.risk
        existing.details = {**(existing.details or {}), **details}
        return existing
    alert = SecurityAlert(company_id=entry.company_id, user_id=entry.user_id, user_name=entry.user_name,
                          alert_type=alert_type, title=title, pattern=pattern, risk=risk, status="open",
                          details=details)
    db.add(alert)
    db.flush()
    return alert


def _rank(r: str) -> int:
    return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}.get(r, 0)


def evaluate_rules(db: DBSession, entry: AuditLog) -> None:
    now = datetime.now(timezone.utc)
    cid, uid = entry.company_id, entry.user_id

    if entry.permission_result == "DENIED":
        n = _count(db, cid, uid, now - timedelta(minutes=10), AuditLog.permission_result == "DENIED")
        if n >= 3:
            _raise(db, entry, "repeated_denials", "Repeated denied requests",
                   f"{n} denied requests in 10 minutes", "HIGH" if n >= 5 else "MEDIUM",
                   {"window": "10m", "count": n, "rule": "R1 denied>=3/10m"})
        if entry.classification == "RESTRICTED":
            r = _count(db, cid, uid, now - timedelta(minutes=30), AuditLog.permission_result == "DENIED",
                       AuditLog.classification == "RESTRICTED")
            if r >= 2:
                _raise(db, entry, "restricted_probing", "Sudden access attempts on restricted data",
                       f"{r} attempts to reach RESTRICTED resources in 30 minutes", "HIGH",
                       {"window": "30m", "count": r, "rule": "R2 restricted_denied>=2/30m"})

    if entry.action in ("document.view", "document.retrieve", "search"):
        n = _count(db, cid, uid, now - timedelta(minutes=5), AuditLog.action.in_(["document.view", "document.retrieve"]))
        if n >= 60:
            _raise(db, entry, "bulk_access", "Large number of document requests",
                   f"{n} document requests in 5 minutes", "HIGH", {"window": "5m", "count": n, "rule": "R3"})
        c = _count(db, cid, uid, now - timedelta(minutes=5), AuditLog.classification.in_(["CONFIDENTIAL", "RESTRICTED"]))
        if c >= 25:
            _raise(db, entry, "sensitive_burst", "Burst of confidential document requests",
                   f"{c} confidential document requests in 5 minutes", "HIGH", {"window": "5m", "count": c, "rule": "R4"})

    if entry.action == "auth.login" and entry.result == "FAILURE":
        n = _count(db, cid, uid, now - timedelta(minutes=15), AuditLog.action == "auth.login", AuditLog.result == "FAILURE")
        if n >= 3:
            _raise(db, entry, "auth_failures", "Repeated authentication failures",
                   f"{n} failed sign-ins in 15 minutes", "HIGH", {"window": "15m", "count": n, "rule": "R5"})

    if entry.action in ("security.prompt_injection", "document.quarantine"):
        _raise(db, entry, "prompt_injection", "Prompt injection detected",
               entry.reason or "Injection pattern detected", "HIGH",
               {"source": entry.action, "resource": entry.resource, "rule": "R6"})

    if entry.action == "security.exfiltration_blocked":
        _raise(db, entry, "exfiltration", "Data exfiltration attempt blocked", entry.reason, "CRITICAL",
               {"rule": "R7"})

    if entry.action == "document.download":
        n = _count(db, cid, uid, now - timedelta(minutes=5), AuditLog.action == "document.download")
        if n >= 10:
            _raise(db, entry, "download_spike", "Unusual download activity",
                   f"{n} document downloads in 5 minutes", "MEDIUM", {"window": "5m", "count": n, "rule": "R8"})
