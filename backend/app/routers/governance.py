"""Approvals, audit logs, security center, admin metrics and the user profile."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession

from ..config import get_settings
from ..core.errors import AppError
from ..core.middleware import COUNTERS
from ..core.rbac import LEVELS, active_grant_ids, check_access
from ..core.security import Principal, get_principal, require
from ..db import session as dbsession
from ..db.models import (AIAction, ApprovalRequest, AuditLog, Budget, BusinessUnit, Compensation, Contract, CostCenter,
                         Customer, Document, DocumentChunk, DocumentPermission, Expense, ITAsset, ITTicket,
                         LeaveBalance, LeaveRequest, Location, Meeting, MeetingAttendee, Message, MessageFeedback,
                         Opportunity, PerformanceReview, Product, Project, ProjectMember, PurchaseOrder,
                         SecurityAlert, ServiceRequest, Session, SoftwareItem, Task, ToolExecution, User, Vendor,
                         WorkflowExecution)
from ..db.session import get_db
from ..services import audit, llm
from ..services.embeddings import embedder

router = APIRouter(tags=["governance"])
settings = get_settings()


# ---- Profile ----------------------------------------------------------------------------------

@router.get("/users/me")
def me(p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    from ..services.retrieval import DBCorpus
    u = db.get(User, p.user_id)
    mgr = db.get(User, u.manager_id) if u.manager_id else None
    grants = active_grant_ids(db, p)
    metas = [m for m in DBCorpus(db, p.company_id).docs() if m.status in ("published", "superseded")]
    accessible = sum(1 for m in metas if check_access(p, m, status=m.status, grant_ids=grants).allowed)
    if p.is_guest:
        scopes = ["Public"]
    else:
        scopes = []
        for lvl in [lvl for lvl in LEVELS if LEVELS[lvl] <= LEVELS[p.clearance]]:
            if lvl in ("PUBLIC", "INTERNAL") or lvl == "RESTRICTED" or p.department == "Executive":
                scopes.append(lvl.title())
            else:
                scopes.append(f"{p.department} {lvl.title()}")
    return {**p.to_public(), "manager": {"name": mgr.full_name, "email": mgr.email} if mgr else None,
            "location": u.location, "access_scopes": scopes, "documents_accessible": accessible,
            "documents_total": len(metas), "active_grants": sorted(grants),
            "ai_engine": {"provider": "openai" if llm.enabled() else "offline",
                          "model": settings.openai_model if llm.enabled() else "multi-agent planner + extractive RAG",
                          "embeddings": embedder.model_id},
            "database": {"dialect": dbsession.engine.dialect.name, "pgvector": dbsession.PGVECTOR}}


# ---- Approvals --------------------------------------------------------------------------------

def _apr(a: ApprovalRequest, db) -> dict:
    approver = db.get(User, a.approver_id) if a.approver_id else None
    return {"id": a.id, "type": a.type, "title": a.title, "status": a.status, "risk": a.risk,
            "resource_id": a.resource_id, "details": a.details,
            "requester": {"name": a.requester.full_name, "title": a.requester.job_title,
                          "department": a.requester.department.name},
            "approver": approver.full_name if approver else "Reviewer pool", "decision_note": a.decision_note,
            "created_at": a.created_at.isoformat(), "decided_at": a.decided_at.isoformat() if a.decided_at else None}


def _can_decide(p: Principal, a: ApprovalRequest) -> bool:
    if a.requester_id == p.user_id:
        return False  # no self-approval
    if a.approver_id == p.user_id:
        return True
    return a.type == "classification" and p.has("documents:classify_approve")


@router.get("/approvals")
def list_approvals(p: Principal = Depends(require("workspace:use")), db: DBSession = Depends(get_db)):
    q = select(ApprovalRequest).where(ApprovalRequest.company_id == p.company_id)
    if not p.has("documents:classify_approve"):
        q = q.where(or_(ApprovalRequest.approver_id == p.user_id, ApprovalRequest.requester_id == p.user_id))
    rows = db.scalars(q.order_by(ApprovalRequest.created_at.desc()).limit(300)).all()
    inbox = [_apr(a, db) for a in rows if _can_decide(p, a) or (a.approver_id == p.user_id)]
    mine = [_apr(a, db) for a in rows if a.requester_id == p.user_id]
    return {"inbox": inbox, "mine": mine}


class ApprovalIn(BaseModel):
    type: str = Field(pattern="^(document_access|general)$")
    document_id: str | None = Field(default=None, max_length=40)
    justification: str = Field(default="", max_length=500)


@router.post("/approvals")
def create_approval(body: ApprovalIn, request: Request, p: Principal = Depends(require("approvals:create")),
                    db: DBSession = Depends(get_db)):
    if body.type == "document_access":
        d = db.get(Document, body.document_id or "")
        if not d or d.company_id != p.company_id:
            raise AppError(404, "not_found", "Document not found.")
        dup = db.scalar(select(ApprovalRequest).where(ApprovalRequest.requester_id == p.user_id,
                                                      ApprovalRequest.resource_id == d.id,
                                                      ApprovalRequest.status == "pending"))
        if dup:
            return _apr(dup, db)
        a = ApprovalRequest(company_id=p.company_id, type="document_access", requester_id=p.user_id,
                            approver_id=d.owner_id, resource_id=d.id,
                            risk="HIGH" if d.classification == "RESTRICTED" else "MEDIUM",
                            title=f"Access request · {d.title}",
                            details={"justification": body.justification, "classification": d.classification,
                                     "duration_days": 7})
    else:
        u = db.get(User, p.user_id)
        a = ApprovalRequest(company_id=p.company_id, type="general", requester_id=p.user_id, approver_id=u.manager_id,
                            title="General approval request", details={"justification": body.justification})
    db.add(a)
    db.flush()
    audit.record(db, principal=p, action="approval.create", resource=a.title, resource_id=a.id,
                 classification=a.details.get("classification", ""), risk=a.risk, request_id=request.state.request_id)
    return _apr(a, db)


class DecisionIn(BaseModel):
    note: str = Field(default="", max_length=500)
    classification: str | None = Field(default=None, pattern="^(PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED)$")


def _get_decidable(db, p, aid) -> ApprovalRequest:
    a = db.get(ApprovalRequest, aid)
    if not a or a.company_id != p.company_id:
        raise AppError(404, "not_found", "Approval not found.")
    if not _can_decide(p, a):
        raise AppError(403, "forbidden", "You are not an approver for this request.")
    if a.status != "pending":
        raise AppError(409, "already_decided", f"Already {a.status}.")
    return a


@router.post("/approvals/{aid}/approve")
def approve(aid: str, body: DecisionIn, request: Request, p: Principal = Depends(require("workspace:use")),
            db: DBSession = Depends(get_db)):
    a = _get_decidable(db, p, aid)
    now = datetime.now(timezone.utc)
    if a.type == "leave":
        lr = db.get(LeaveRequest, a.resource_id)
        if lr:
            lr.status = "approved"
            b = db.scalar(select(LeaveBalance).where(LeaveBalance.user_id == lr.user_id,
                                                     LeaveBalance.year == lr.start_date.year))
            if b:
                setattr(b, f"{lr.leave_type}_used", getattr(b, f"{lr.leave_type}_used") + lr.days)
    elif a.type == "document_access":
        db.add(DocumentPermission(company_id=p.company_id, document_id=a.resource_id, user_id=a.requester_id,
                                  granted_by=p.user_id, reason=a.details.get("justification", ""),
                                  expires_at=now + timedelta(days=int(a.details.get("duration_days", 7)))))
    elif a.type == "service_request":
        sr = db.get(ServiceRequest, a.resource_id)
        if sr:
            sr.status, sr.updated_at = "approved", now
    elif a.type == "classification":
        d = db.get(Document, a.resource_id)
        final = body.classification or a.details.get("suggested", "INTERNAL")
        if LEVELS[p.clearance] < LEVELS[final]:
            raise AppError(403, "forbidden", f"Your clearance ({p.clearance.title()}) cannot publish a "
                                             f"{final.title()} document.")
        d.classification = final
        if LEVELS[final] >= LEVELS["CONFIDENTIAL"]:
            owner = db.get(User, d.owner_id)
            d.allowed_departments = sorted({owner.department.name, "Executive"})
        else:
            d.allowed_departments = ["*"]
        d.status, d.updated_at = "published", now
        a.details = {**a.details, "final": final}
    a.status, a.decided_by, a.decided_at, a.decision_note = "approved", p.user_id, now, body.note
    audit.record(db, principal=p, action=f"approval.approve", resource=a.title, resource_id=a.resource_id or a.id,
                 classification=a.details.get("final") or a.details.get("classification", ""),
                 permission_result="ALLOWED", result="APPROVED", risk=a.risk, reason=body.note,
                 request_id=request.state.request_id)
    return _apr(a, db)


@router.post("/approvals/{aid}/reject")
def reject(aid: str, body: DecisionIn, request: Request, p: Principal = Depends(require("workspace:use")),
           db: DBSession = Depends(get_db)):
    a = _get_decidable(db, p, aid)
    if a.type == "leave":
        lr = db.get(LeaveRequest, a.resource_id)
        if lr:
            lr.status = "rejected"
    elif a.type == "classification":
        d = db.get(Document, a.resource_id)
        if d:
            d.status = "rejected"
    elif a.type == "service_request":
        sr = db.get(ServiceRequest, a.resource_id)
        if sr:
            sr.status = "rejected"
    a.status, a.decided_by, a.decided_at, a.decision_note = "rejected", p.user_id, datetime.now(timezone.utc), body.note
    audit.record(db, principal=p, action="approval.reject", resource=a.title, resource_id=a.resource_id or a.id,
                 result="REJECTED", risk=a.risk, reason=body.note, request_id=request.state.request_id)
    return _apr(a, db)


# ---- Audit logs -------------------------------------------------------------------------------

def _audit_row(e: AuditLog) -> dict:
    return {"id": e.id, "ts": e.ts.isoformat(), "user_id": e.user_id, "user_name": e.user_name,
            "session_id": e.session_id, "ip": e.ip, "action": e.action, "query": e.query, "resource": e.resource,
            "resource_id": e.resource_id, "classification": e.classification,
            "permission_result": e.permission_result, "tool": e.tool, "result": e.result, "reason": e.reason,
            "risk": e.risk, "request_id": e.request_id, "details": e.details}


@router.get("/audit-logs")
def audit_logs(q: str = "", user: str = "", permission_result: str = "", risk: str = "", action: str = "",
               limit: int = 100, offset: int = 0, p: Principal = Depends(require("audit:read_self")),
               db: DBSession = Depends(get_db)):
    limit = max(1, min(limit, 500))
    stmt = select(AuditLog).where(AuditLog.company_id == p.company_id)
    scope = "organization"
    if not p.has("audit:read_all"):
        stmt = stmt.where(AuditLog.user_id == p.user_id)
        scope = "self"
    if q:
        like = f"%{q.lower()[:100]}%"
        stmt = stmt.where(or_(func.lower(AuditLog.resource).like(like), func.lower(AuditLog.query).like(like),
                              func.lower(AuditLog.action).like(like), func.lower(AuditLog.reason).like(like)))
    if user:
        stmt = stmt.where(func.lower(AuditLog.user_name).like(f"%{user.lower()[:100]}%"))
    if permission_result:
        stmt = stmt.where(AuditLog.permission_result == permission_result.upper())
    if risk:
        stmt = stmt.where(AuditLog.risk == risk.upper())
    if action:
        stmt = stmt.where(AuditLog.action.like(f"{action[:60]}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(AuditLog.ts.desc()).limit(limit).offset(max(0, offset))).all()
    items = [_audit_row(e) for e in rows]
    if scope == "self":
        # Anti-enumeration: users never learn the titles of resources they were denied.
        for it in items:
            if it["permission_result"] == "DENIED" and it["action"].startswith(("document.", "tool.")):
                it["resource"] = f"[{(it['classification'] or 'restricted').lower()} resource withheld]"
                it["details"] = {}
            it["details"] = {k: v for k, v in (it["details"] or {}).items() if k not in ("withheld", "context_manifest")}
    return {"scope": scope, "total": total, "items": items}


# ---- Security center --------------------------------------------------------------------------

@router.get("/security/status")
def security_status(p: Principal = Depends(require("workspace:use"))):
    sim = "Prototype Simulation"
    layers = [
        {"key": "ddos", "name": "DDoS Protection", "status": "ACTIVE", "mode": sim,
         "detail": "Represented only. Production: AWS Shield Advanced / Cloudflare in front of the load balancer."},
        {"key": "waf", "name": "Web Application Firewall", "status": "ACTIVE", "mode": sim,
         "detail": f"Minimal in-app signature rules on URLs (blocked {COUNTERS['waf_blocked']}). Production: AWS WAF "
                   "managed rule sets (OWASP Top 10, bot control)."},
        {"key": "rate", "name": "Rate Limiting", "status": "ACTIVE", "mode": "Enforced in-app",
         "detail": f"Sliding window: {settings.rate_limit_per_minute}/min API, {settings.chat_rate_limit_per_minute}"
                   f"/min AI, {settings.login_rate_limit_per_minute}/min auth. Throttled so far: "
                   f"{COUNTERS['rate_limited']}."},
        {"key": "tls", "name": "TLS 1.3", "status": "ACTIVE", "mode": sim,
         "detail": "Local dev runs over HTTP. Production: TLS terminated at the ALB with ACM certificates + HSTS."},
        {"key": "encryption", "name": "Encryption at Rest", "status": "ACTIVE", "mode": sim,
         "detail": "Production: RDS PostgreSQL with KMS encryption; S3 SSE-KMS for document blobs."},
        {"key": "network", "name": "Private Network (VPC)", "status": "ACTIVE", "mode": sim,
         "detail": "Production: API in private subnets behind ALB; PostgreSQL & AI/RAG services have no public IPs."},
        {"key": "rbac", "name": "RBAC Permission Engine", "status": "ACTIVE", "mode": "Enforced in-app",
         "detail": "Deterministic authorization before retrieval; the LLM never decides access."},
        {"key": "injection", "name": "Prompt-Injection Guard", "status": "ACTIVE", "mode": "Enforced in-app",
         "detail": "Scans user input, retrieved chunks and uploads; flagged content is quarantined."},
        {"key": "dlp", "name": "Data Loss Prevention", "status": "ACTIVE", "mode": "Enforced in-app",
         "detail": "Masks Aadhaar, PAN, card, bank, password and API-key patterns on every AI response."},
        {"key": "audit", "name": "Audit Logging", "status": "ACTIVE", "mode": "Enforced in-app",
         "detail": "Every request, authorization decision, tool call and confirmation is recorded."},
    ]
    return {"layers": layers, "counters": {k: v for k, v in COUNTERS.items() if k != "started"},
            "uptime_seconds": int(datetime.now().timestamp() - COUNTERS["started"])}


def _alert(a: SecurityAlert) -> dict:
    return {"id": a.id, "ts": a.ts.isoformat(), "user_id": a.user_id, "user_name": a.user_name,
            "alert_type": a.alert_type, "title": a.title, "pattern": a.pattern, "risk": a.risk, "status": a.status,
            "event_count": a.event_count, "details": a.details}


@router.get("/security-alerts")
def alerts(status: str = "", p: Principal = Depends(require("security:read")), db: DBSession = Depends(get_db)):
    stmt = select(SecurityAlert).where(SecurityAlert.company_id == p.company_id)
    if status:
        stmt = stmt.where(SecurityAlert.status == status)
    return [_alert(a) for a in db.scalars(stmt.order_by(SecurityAlert.ts.desc()).limit(200)).all()]


class AlertPatch(BaseModel):
    status: str = Field(pattern="^(open|investigating|resolved)$")


@router.patch("/security-alerts/{aid}")
def update_alert(aid: str, body: AlertPatch, request: Request, p: Principal = Depends(require("security:admin")),
                 db: DBSession = Depends(get_db)):
    a = db.get(SecurityAlert, aid)
    if not a or a.company_id != p.company_id:
        raise AppError(404, "not_found", "Alert not found.")
    a.status = body.status
    audit.record(db, principal=p, action="security.alert_update", resource=a.title, resource_id=a.id,
                 result=body.status.upper(), request_id=request.state.request_id, evaluate=False)
    return _alert(a)


@router.get("/security-alerts/{aid}/activity")
def alert_activity(aid: str, p: Principal = Depends(require("security:read")), db: DBSession = Depends(get_db)):
    a = db.get(SecurityAlert, aid)
    if not a or a.company_id != p.company_id:
        raise AppError(404, "not_found", "Alert not found.")
    ts = a.ts if a.ts.tzinfo else a.ts.replace(tzinfo=timezone.utc)
    rows = db.scalars(select(AuditLog).where(AuditLog.company_id == p.company_id, AuditLog.user_id == a.user_id,
                                             AuditLog.ts <= ts + timedelta(hours=1),
                                             AuditLog.ts >= ts - timedelta(days=1))
                      .order_by(AuditLog.ts.desc()).limit(80)).all()
    u = db.get(User, a.user_id) if a.user_id else None
    return {"alert": _alert(a), "events": [_audit_row(e) for e in rows],
            "user": {"name": u.full_name, "title": u.job_title, "department": u.department.name,
                     "clearance": u.clearance, "employee_code": u.employee_code} if u else None,
            "summary": dict(Counter(e.permission_result for e in rows))}


# ---- Admin dashboard --------------------------------------------------------------------------

@router.get("/admin/metrics")
def metrics(p: Principal = Depends(require("admin:dashboard")), db: DBSession = Depends(get_db)):
    cid = p.company_id
    now = datetime.now(timezone.utc)
    week = now - timedelta(days=7)
    logs = db.scalars(select(AuditLog).where(AuditLog.company_id == cid, AuditLog.ts >= week)).all()
    c = lambda cond: sum(1 for e in logs if cond(e))
    days = [(now - timedelta(days=i)).date() for i in range(6, -1, -1)]
    per_day = defaultdict(lambda: {"requests": 0, "denied": 0, "blocked": 0, "queries": 0})
    for e in logs:
        dd = (e.ts if e.ts.tzinfo else e.ts.replace(tzinfo=timezone.utc)).date()
        per_day[dd]["requests"] += 1
        per_day[dd]["denied"] += e.permission_result == "DENIED"
        per_day[dd]["blocked"] += e.permission_result == "BLOCKED"
        per_day[dd]["queries"] += e.action == "ai.chat"
    by_cls = {lvl: {"classification": lvl, "allowed": 0, "denied": 0} for lvl in LEVELS}
    for e in logs:
        if e.classification in by_cls and e.action.startswith(("document", "tool.")):
            by_cls[e.classification]["allowed" if e.permission_result == "ALLOWED" else "denied"] += 1
    tools = Counter(dict(db.execute(select(ToolExecution.tool, func.count()).where(ToolExecution.company_id == cid)
                                    .group_by(ToolExecution.tool)).all()))
    for e in logs:
        if e.action.startswith("ai.action_executed") and e.tool:
            tools[e.tool] += 1
    agents = Counter()
    wf_status = Counter()
    for agents_list, status in db.execute(select(WorkflowExecution.agents, WorkflowExecution.status)
                                          .where(WorkflowExecution.company_id == cid)).all():
        wf_status[status] += 1
        for a in agents_list or []:
            agents[a] += 1
    alerts = db.scalars(select(SecurityAlert).where(SecurityAlert.company_id == cid)).all()
    denied_users = Counter(e.user_name for e in logs if e.permission_result == "DENIED")
    active = db.scalar(select(func.count(func.distinct(Session.user_id))).join(User, User.id == Session.user_id).where(
        Session.company_id == cid, Session.revoked.is_(False), Session.expires_at > now, User.is_guest.is_(False)))
    guest_sessions = db.scalar(select(func.count(Session.id)).join(User, User.id == Session.user_id).where(
        Session.company_id == cid, User.is_guest.is_(True), Session.created_at >= week)) or 0
    doc_cls = dict(db.execute(select(Document.classification, func.count()).where(
        Document.company_id == cid, Document.status.in_(["published", "superseded"])).group_by(
        Document.classification)).all())
    feedback = dict(db.execute(select(MessageFeedback.rating, func.count()).where(MessageFeedback.company_id == cid)
                               .group_by(MessageFeedback.rating)).all())
    tables = [("Employees", User), ("Projects", Project), ("Project members", ProjectMember), ("Tasks", Task),
              ("Meetings", Meeting), ("Documents", Document), ("Document chunks", DocumentChunk),
              ("Leave requests", LeaveRequest), ("Performance reviews", PerformanceReview),
              ("Compensation", Compensation), ("IT tickets", ITTicket), ("IT assets", ITAsset),
              ("Software catalogue", SoftwareItem), ("Budgets", Budget), ("Expenses", Expense),
              ("Cost centres", CostCenter), ("Customers", Customer), ("Opportunities", Opportunity),
              ("Contracts", Contract), ("Products", Product), ("Vendors", Vendor),
              ("Purchase orders", PurchaseOrder), ("Service requests", ServiceRequest), ("Audit events", AuditLog)]
    records = []
    for label, model in tables:
        q = select(func.count()).select_from(model)
        if hasattr(model, "company_id"):
            q = q.where(model.company_id == cid)
        records.append({"table": label, "count": db.scalar(q) or 0})
    successes = wf_status.get("completed", 0) + wf_status.get("awaiting_confirmation", 0)
    failures = sum(v for k, v in wf_status.items() if k not in ("completed", "awaiting_confirmation"))
    return {
        "kpis": {
            "total_users": db.scalar(select(func.count(User.id)).where(User.company_id == cid, User.is_guest.is_(False))),
            "active_users": active, "active_sessions": active, "guest_sessions": guest_sessions,
            "documents": db.scalar(select(func.count(Document.id)).where(Document.company_id == cid)),
            "database_records": sum(r["count"] for r in records),
            "ai_requests": c(lambda e: e.action == "ai.chat"), "queries": c(lambda e: e.action == "ai.chat"),
            "successful_responses": successes, "failed_responses": failures,
            "blocked_requests": c(lambda e: e.permission_result == "BLOCKED"),
            "permission_denials": c(lambda e: e.permission_result == "DENIED"),
            "security_alerts": sum(1 for a in alerts if a.status != "resolved"),
            "high_risk_actions": c(lambda e: e.risk in ("HIGH", "CRITICAL")),
            "audit_events": db.scalar(select(func.count(AuditLog.id)).where(AuditLog.company_id == cid)),
            "positive_feedback": feedback.get(1, 0), "negative_feedback": feedback.get(-1, 0),
        },
        "requests_over_time": [{"date": d.strftime("%d %b"), **per_day[d]} for d in days],
        "access_by_classification": list(by_cls.values()),
        "document_classifications": [{"classification": k, "count": doc_cls.get(k, 0)} for k in LEVELS],
        "tool_usage": [{"tool": k, "count": v} for k, v in tools.most_common(12)],
        "agent_usage": [{"agent": k, "count": v} for k, v in agents.most_common()],
        "response_outcomes": [{"status": k, "count": v} for k, v in wf_status.most_common()],
        "alerts_by_type": [{"type": k, "count": v} for k, v in Counter(a.title for a in alerts).most_common(8)],
        "alerts_by_risk": [{"risk": k, "count": v} for k, v in Counter(a.risk for a in alerts).items()],
        "top_denied_users": [{"user": k, "count": v} for k, v in denied_users.most_common(5)],
        "records_by_table": records,
        "recent_events": [_audit_row(e) for e in db.scalars(select(AuditLog).where(AuditLog.company_id == cid)
                                                           .order_by(AuditLog.ts.desc()).limit(12)).all()],
    }
