"""Agent tools. Each tool:
  • has a least-privilege permission requirement (core.rbac.TOOL_POLICIES) checked server-side on every call,
  • receives the caller's identity from the server-side Principal — never from the model's arguments,
  • reads structured data only after record-level authorization (core.rbac.check_record),
  • if state-changing, is NOT executed; it becomes an AIAction awaiting explicit human confirmation.
"""
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession

from ..core.rbac import (LEVELS, TOOL_ALIASES, TOOL_POLICIES, allowed_levels, check_access, check_record, check_tool,
                         is_guest)
from ..core.security import Principal
from ..db.models import (AIAction, ApprovalRequest, ConnectorItem, Department, Document, DocumentChunk, EmailOutbox, ITAsset,
                         ITTicket, LeaveBalance, LeaveRequest, Meeting, MeetingAttendee, PerformanceReview,
                         Compensation, Project, ProjectMember, PurchaseOrder, ServiceRequest, SoftwareItem, Task,
                         ToolExecution, User)
from . import audit
from .nlp import fmt_date, parse_date, today
from .retrieval import (DocMeta, Evidence, RetrievalResult, authorized_metas, retrieve_for_principal)

COMPANY_DOMAIN = "novatech.demo"
POLICY_TYPES = {"Policy", "Procedure", "Process", "Guide", "Guideline", "FAQ", "Checklist", "Standard", "Handbook",
                "Register", "Overview", "Calendar", "Knowledge Article", "Training"}
ACTIVE = ("In Progress", "Planning", "On Hold")


@dataclass
class ToolContext:
    db: DBSession
    principal: Principal
    conversation_id: str | None = None
    request_id: str = ""
    retrievals: list[RetrievalResult] = field(default_factory=list)
    actions: list[AIAction] = field(default_factory=list)
    security_events: list[dict] = field(default_factory=list)
    denials: list[dict] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)      # structured-data citations
    recent_docs: list[str] = field(default_factory=list)   # conversation context ("this document")
    recent_projects: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)

    def cite(self, kind: str, rid: str, title: str, classification: str, updated=None, extra: str = ""):
        if any(r["id"] == rid for r in self.records):
            return
        self.records.append({"type": kind, "id": rid, "title": title, "classification": classification,
                             "updated": updated.isoformat() if hasattr(updated, "isoformat") else updated,
                             "detail": extra})


@dataclass
class ToolOutcome:
    tool: str
    status: str  # ok | pending_confirmation | denied | error | blocked | not_found
    summary: str
    llm_view: str
    data: dict = field(default_factory=dict)
    action: AIAction | None = None


# ---- OpenAI function schemas (identity is never a parameter the model controls) ---------------

def _fn(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required, "additionalProperties": False}}}


_S = {"type": "string"}
DATASETS = ["projects", "tasks", "employees", "tickets", "opportunities", "contracts", "customers", "purchase_orders",
            "vendors", "budgets", "expenses", "leave_requests"]
TOOL_SCHEMAS = {
    "search_knowledge": _fn("search_knowledge", "Hybrid (semantic + keyword) search over ALL NovaTech Solutions "
                            "knowledge the user may read: policies, procedures, guides, FAQs, project charters, "
                            "status reports, announcements. Returns excerpts with document ids for citation.",
                            {"query": _S, "department": {"type": "string", "description": "optional owning department"}},
                            ["query", "department"]),
    "search_documents": _fn("search_documents", "Search company documents the user is authorized to read "
                            "(same as search_knowledge without filters).", {"query": _S}, ["query"]),
    "search_policies": _fn("search_policies", "Search only policies, procedures, guides, FAQs and checklists.",
                           {"query": _S}, ["query"]),
    "search_repositories": _fn(
        "search_repositories",
        "Search indexed code repositories, source files, functions, and developer documentation within user's clearance. "
        "Returns code excerpts, symbols, line numbers, and GitHub deep links for technical questions.",
        {"query": _S, "repository_id": {"type": "string", "description": "optional repository id"}},
        ["query"]
    ),
    "get_leave_policy": _fn("get_leave_policy", "Get the current leave policy (entitlements, carry-forward, how to "
                            "apply).", {}, []),
    "summarize_document": _fn("summarize_document", "Load one authorized document in full so it can be summarized. "
                              "Pass a document id (DOC-1234) or a title/topic query.",
                              {"document": _S}, ["document"]),
    "compare_documents": _fn("compare_documents", "Compare two documents, or the current and previous version of a "
                             "policy. Pass ids or a topic (e.g. 'project management policy').",
                             {"document_a": _S, "document_b": _S}, ["document_a", "document_b"]),
    "latest_updates": _fn("latest_updates", "List the most recently updated authorized documents of a type.",
                          {"doc_type": {"type": "string", "enum": ["Policy", "Procedure", "Announcement", "Guide", "any"]},
                           "limit": {"type": "integer"}}, ["doc_type", "limit"]),
    "get_department": _fn("get_department", "Department facts: purpose, head, business unit, headcount, projects.",
                          {"department": _S}, ["department"]),
    "analytics_query": _fn("analytics_query", "Run an aggregate query over structured records the user may see. "
                           "Use for counts, percentages, rankings, lists of projects (delayed, approaching deadline), "
                           "pipeline, budgets, headcount. Never estimate numbers yourself.",
                           {"dataset": {"type": "string", "enum": DATASETS},
                            "metric": {"type": "string", "enum": ["count", "list", "sum", "avg_progress",
                                                                  "percentage", "utilization"]},
                            "group_by": {"type": "string", "description": "field to group by, e.g. department, status, "
                                                                            "health, region, stage, category, or ''"},
                            "status": {"type": "string", "description": "status filter or '' (e.g. 'In Progress', "
                                                                         "'Completed', 'delayed', 'approaching_deadline', 'open')"},
                            "department": {"type": "string", "description": "department filter or ''"}},
                           ["dataset", "metric", "group_by", "status", "department"]),
    "get_project": _fn("get_project", "Project details (status, health, manager, members, milestones, risks, tasks). "
                       "Pass a project id (PRJ-1234) or name.", {"project": _S}, ["project"]),
    "get_my_projects": _fn("get_my_projects", "Projects the current user is assigned to.",
                           {"filter": {"type": "string", "enum": ["all", "active", "delayed", "approaching_deadline"]}},
                           ["filter"]),
    "get_pending_tasks": _fn("get_pending_tasks", "The user's open tasks, today's meetings, approvals waiting on them "
                             "and pending confirmations — for work summaries and priorities.",
                             {"scope": {"type": "string", "enum": ["me", "team"]}}, ["scope"]),
    "get_my_requests": _fn("get_my_requests", "Status of the user's leave requests, IT tickets, service requests and "
                           "approvals.", {}, []),
    "get_employee": _fn("get_employee", "Look up an employee. 'me' for the current user, 'manager' for their manager, "
                        "or a name / employee id. include: profile|compensation|performance|leave (sensitive sections "
                        "are authorized server-side).",
                        {"employee": _S, "include": {"type": "string", "enum": ["profile", "compensation",
                                                                               "performance", "leave", "team"]}},
                        ["employee", "include"]),
    "search_software": _fn("search_software", "Search the internal software catalogue (approval requirements, "
                           "platforms).", {"query": _S}, ["query"]),
    "get_leave_balance": _fn("get_leave_balance", "Get leave balance. 'me' for the current employee.",
                             {"employee": _S}, ["employee"]),
    "create_leave_request": _fn("create_leave_request", "Prepare a leave request for the current employee. The user "
                                "must confirm before it is submitted.",
                                {"start_date": {"type": "string", "description": "YYYY-MM-DD"},
                                 "end_date": {"type": "string", "description": "YYYY-MM-DD; same as start for one day"},
                                 "leave_type": {"type": "string", "enum": ["casual", "sick", "earned"]},
                                 "reason": _S}, ["start_date", "end_date", "leave_type", "reason"]),
    "create_it_ticket": _fn("create_it_ticket", "Prepare an IT support ticket (requires user confirmation).",
                            {"title": _S, "description": _S,
                             "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                             "category": {"type": "string", "enum": ["Hardware", "Software", "Network", "Access",
                                                                     "Other"]}},
                            ["title", "description", "priority", "category"]),
    "create_request": _fn("create_request", "Prepare an access / software / document / procurement / general request "
                          "(requires user confirmation).",
                          {"request_type": {"type": "string", "enum": ["access", "software", "document", "procurement",
                                                                       "general"]},
                           "title": _S, "justification": _S, "estimated_cost": {"type": "number"}},
                          ["request_type", "title", "justification", "estimated_cost"]),
    "draft_email": _fn("draft_email", "Draft an email. recipient may be 'manager', a colleague's name or an internal "
                       "email. Produces a preview the user can approve for sending.",
                       {"recipient": _S, "subject": _S, "body": _S}, ["recipient", "subject", "body"]),
    "send_email": _fn("send_email", "Send an email (always requires explicit user confirmation).",
                      {"recipient": _S, "subject": _S, "body": _S}, ["recipient", "subject", "body"]),
    "request_approval": _fn("request_approval", "Request access to a withheld document (type document_access with "
                            "document_id) or a general approval.",
                            {"request_type": {"type": "string", "enum": ["document_access", "general"]},
                             "document_id": _S, "justification": _S},
                            ["request_type", "document_id", "justification"]),
    "delete_document": _fn("delete_document", "Archive (delete) a document. Requires elevated permission and "
                           "confirmation.", {"document_id": _S}, ["document_id"]),
    # Enterprise Connectors & Skills Tools
    "search_jira_issues": _fn("search_jira_issues", "Search Jira issues, bugs, and backlog items in connected Jira projects. Returns status, priority, and assignees.",
                              {"query": _S, "project": {"type": "string", "description": "project key e.g. NOVA"}, "status": {"type": "string"}}, ["query"]),
    "create_jira_issue": _fn("create_jira_issue", "Propose creating a new Jira ticket (requires human confirmation).",
                             {"title": _S, "description": _S, "project": {"type": "string"}, "priority": {"type": "string", "enum": ["Critical", "High", "Medium", "Low"]}},
                             ["title", "description"]),
    "search_teams_messages": _fn("search_teams_messages", "Search conversations and messages in connected Microsoft Teams channels.",
                                 {"query": _S, "channel": {"type": "string"}}, ["query"]),
    "post_teams_message": _fn("post_teams_message", "Post a message to a Microsoft Teams channel (requires human confirmation).",
                              {"channel": _S, "message": _S}, ["channel", "message"]),
    "search_emails": _fn("search_emails", "Search Outlook emails, threads, and communications.",
                         {"query": _S, "sender": {"type": "string"}}, ["query"]),
    "lookup_entra_identity": _fn("lookup_entra_identity", "Look up enterprise identity, directory groups, and roles in Microsoft Entra ID.",
                                 {"query": _S}, ["query"]),
    "scan_vulnerabilities": _fn("scan_vulnerabilities", "Run Security Analysis skill to detect vulnerabilities, authorization flaws, and secrets in the codebase.",
                                {"target": _S}, ["target"]),
    "get_repo_architecture": _fn("get_repo_architecture", "Run Repository Analysis skill to get architecture overview, tech stack, and components of a repository.",
                                 {"repo_name": _S}, ["repo_name"]),
    "generate_enterprise_report": _fn("generate_enterprise_report", "Run Report Generation skill to synthesize findings across systems into an executive report.",
                                      {"report_type": _S}, ["report_type"]),
}

TOOL_AGENT = {
    "search_knowledge": "Knowledge Agent", "search_documents": "Knowledge Agent", "search_policies": "Knowledge Agent",
    "search_repositories": "Knowledge Agent",
    "get_leave_policy": "HR Agent", "get_leave_balance": "HR Agent", "get_employee": "HR Agent",
    "create_leave_request": "Workflow Agent", "create_it_ticket": "Workflow Agent", "create_request": "Workflow Agent",
    "draft_email": "Workflow Agent", "send_email": "Workflow Agent", "request_approval": "Workflow Agent",
    "delete_document": "Workflow Agent", "get_my_requests": "Workflow Agent", "search_software": "IT Agent",
    "get_project": "Project Agent", "get_my_projects": "Project Agent", "summarize_document": "Document Agent",
    "compare_documents": "Document Agent", "latest_updates": "Document Agent", "analytics_query": "Analytics Agent",
    "get_pending_tasks": "Productivity Agent", "get_department": "Knowledge Agent",
    # Enterprise Connectors & Skills mappings
    "search_jira_issues": "Jira Management Agent",
    "create_jira_issue": "Jira Management Agent",
    "search_teams_messages": "Security Analysis Agent",
    "post_teams_message": "Workflow Agent",
    "search_emails": "Productivity Agent",
    "lookup_entra_identity": "Security Analysis Agent",
    "scan_vulnerabilities": "Security Analysis Agent",
    "get_repo_architecture": "Repository Analysis Agent",
    "generate_enterprise_report": "Report Generation Agent",
}


def schemas_for(p: Principal) -> list[dict]:
    """Least privilege: the model only *sees* tools this user is allowed to use."""
    return [s for name, s in TOOL_SCHEMAS.items() if check_tool(p.permissions, name).allowed]


# ---- helpers ----------------------------------------------------------------------------------

def _user(db, p: Principal) -> User:
    return db.get(User, p.user_id)


def resolve_employee(db: DBSession, p: Principal, who: str | None) -> User | None:
    w = (who or "me").strip().lower()
    if w in ("me", "myself", "self", "i", "", p.full_name.lower(), p.email.lower()):
        return _user(db, p)
    if "manager" in w or w in ("my boss", "boss", "lead", "my lead"):
        me = _user(db, p)
        return db.get(User, me.manager_id) if me.manager_id else None
    q = select(User).where(User.company_id == p.company_id, User.is_active.is_(True), User.is_guest.is_(False))
    m = re.search(r"\bnt-\d{3,6}\b", w)
    if m:
        return db.scalar(q.where(func.lower(User.employee_code) == m.group(0)))
    rows = db.scalars(q.where(or_(func.lower(User.full_name) == w, func.lower(User.email) == w))).all()
    if not rows:
        rows = db.scalars(q.where(func.lower(User.full_name).contains(w)).limit(5)).all()
    if not rows and w.split():
        rows = db.scalars(q.where(func.lower(User.full_name).startswith(w.split()[0] + " ")).limit(5)).all()
    return rows[0] if rows else None


def _log_exec(ctx: ToolContext, tool: str, args: dict, status: str, summary: str, started: float, action_id=None):
    ctx.db.add(ToolExecution(company_id=ctx.principal.company_id, user_id=ctx.principal.user_id, tool=tool,
                             args={k: v for k, v in (args or {}).items() if isinstance(v, (str, int, float))},
                             status=status, result_summary=summary[:500], action_id=action_id,
                             duration_ms=int((time.time() - started) * 1000)))


def _dynamic_risk(tool: str, args: dict, base: str) -> str:
    """Raise a tool's static policy risk when the actual destination/data makes it more sensitive."""
    rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    r = rank.get(base, 1)
    raw = str(args).lower()
    if tool in {"send_email", "draft_email"} and re.search(r"@(?!novatech\.demo\b)[\w.-]+\.", raw):
        r = max(r, 3)
    if tool == "delete_document":
        r = max(r, 2)
    if tool == "create_request" and re.search(r"\b(production|admin|privileged|restricted)\b", raw):
        r = max(r, 2)
    if re.search(r"\b(restricted|salary|bank|secret|private key|api key)\b", raw):
        r = max(r, 3)
    return next(k for k, v in rank.items() if v == r)


def _pending(ctx: ToolContext, tool: str, args: dict, preview: dict, title: str) -> AIAction:
    pol = TOOL_POLICIES[tool]
    dynamic_risk = _dynamic_risk(tool, args, pol["risk"])
    act = AIAction(company_id=ctx.principal.company_id, user_id=ctx.principal.user_id,
                   conversation_id=ctx.conversation_id, tool=tool, args=args, risk=dynamic_risk,
                   preview={"title": title, **preview}, status="pending_confirmation")
    ctx.db.add(act)
    ctx.db.flush()
    ctx.actions.append(act)
    audit.record(ctx.db, principal=ctx.principal, action="ai.action_proposed", tool=tool, resource=title,
                 resource_id=act.id, permission_result="ALLOWED", result="PENDING_CONFIRMATION",
                 risk=dynamic_risk, reason="Risk policy requires human confirmation", commit=False,
                 request_id=ctx.request_id)
    return act


def _denied(ctx: ToolContext, tool: str, reason: str, resource="", classification="", risk="MEDIUM") -> ToolOutcome:
    audit.record(ctx.db, principal=ctx.principal, action=f"tool.{tool}", tool=tool, resource=resource,
                 classification=classification, permission_result="DENIED", result="DENIED", reason=reason,
                 risk=risk, commit=False, request_id=ctx.request_id)
    ctx.denials.append({"tool": tool, "reason": reason, "resource": resource, "classification": classification})
    return ToolOutcome(tool, "denied", reason, f"DENIED by permission engine: {reason}")


def _allowed_read(ctx: ToolContext, tool: str, resource: str, rid: str, classification: str, reason: str = ""):
    audit.record(ctx.db, principal=ctx.principal, action=f"tool.{tool}", tool=tool, resource=resource,
                 resource_id=rid, classification=classification, permission_result="ALLOWED", reason=reason,
                 commit=False, request_id=ctx.request_id)


def _can_see_budget(p: Principal, dept: str) -> bool:
    return (LEVELS[p.clearance] >= LEVELS["CONFIDENTIAL"] and not is_guest(p)
            and (p.department in (dept, "Finance", "Executive")))


def my_project_ids(db, p: Principal) -> set[str]:
    if is_guest(p):
        return set()
    return set(db.scalars(select(ProjectMember.project_id).where(ProjectMember.user_id == p.user_id)).all())


def project_visible(ctx: ToolContext, proj: Project, mine: set[str] | None = None):
    mine = my_project_ids(ctx.db, ctx.principal) if mine is None else mine
    owners = [ctx.principal.user_id] if proj.id in mine or proj.manager_id == ctx.principal.user_id else []
    return check_record(ctx.principal, proj, owner_ids=owners)


# ---- knowledge tools --------------------------------------------------------------------------

def _audit_retrieval(ctx: ToolContext, res: RetrievalResult, query: str, tool: str):
    p = ctx.principal
    for ev in res.evidence:
        audit.record(ctx.db, principal=p, action="document.retrieve", resource=ev.doc.title, resource_id=ev.doc.id,
                     classification=ev.doc.classification, permission_result="ALLOWED", tool=tool,
                     query=query, reason="Authorized for RAG context", commit=False, request_id=ctx.request_id)
    for w in res.withheld:
        risk = "HIGH" if w["classification"] == "RESTRICTED" else "MEDIUM"
        audit.record(ctx.db, principal=p, action="document.retrieve", resource=w["title"], resource_id=w["doc_id"],
                     classification=w["classification"], permission_result="DENIED", tool=tool,
                     query=query, result="DENIED", reason=f"Insufficient permissions — {w['reason']}", risk=risk,
                     commit=False, request_id=ctx.request_id)
    for q in res.quarantined:
        audit.record(ctx.db, principal=p, action="security.prompt_injection", resource=q["title"],
                     resource_id=q["doc_id"], permission_result="BLOCKED", tool=tool, result="BLOCKED",
                     reason=f"Retrieved content quarantined ({q['categories']})", risk="HIGH", query=query,
                     commit=False, request_id=ctx.request_id)
        ctx.security_events.append({"type": "prompt_injection", "source": "retrieved_document",
                                    "doc_id": q["doc_id"], "title": q["title"], "categories": q["categories"]})


def _search(ctx: ToolContext, tool: str, query: str, filters: dict | None = None, k: int = 4) -> ToolOutcome:
    res = retrieve_for_principal(ctx.db, ctx.principal, query, k_docs=k, filters=filters)
    ctx.retrievals.append(res)
    _audit_retrieval(ctx, res, query, tool)
    for e in res.evidence:
        if e.doc.id not in ctx.recent_docs:
            ctx.recent_docs.insert(0, e.doc.id)
    summary = (f"{len(res.evidence)} authorized document(s) · {len(res.withheld)} withheld · "
               f"{res.authorized_docs:,} of {res.authorized_docs + res.denied_docs:,} documents in your access scope")
    return ToolOutcome(tool, "ok" if res.evidence else "not_found", summary, res.llm_context(),
                       {"sources": [e.source() for e in res.evidence], "withheld": len(res.withheld)})


def t_search_knowledge(ctx: ToolContext, query: str, department: str = "") -> ToolOutcome:
    f = {"only_departments": {department}} if department and department.strip() else None
    out = _search(ctx, "search_knowledge", query, f)
    if out.status == "not_found" and f:  # department hint too narrow → retry across all authorized knowledge
        out = _search(ctx, "search_knowledge", query)
    return out


def t_search_documents(ctx: ToolContext, query: str) -> ToolOutcome:
    return _search(ctx, "search_documents", query)


def t_search_policies(ctx: ToolContext, query: str, department: str = "") -> ToolOutcome:
    boost = {"boost_departments": {department}} if department else {}
    out = _search(ctx, "search_policies", query, {"only_doc_types": POLICY_TYPES, **boost})
    if out.status == "not_found":
        out = _search(ctx, "search_policies", query, {"exclude_doc_types": {"Status Report"}, **boost})
    return out


def t_search_repositories(ctx: ToolContext, query: str, repository_id: str = "") -> ToolOutcome:
    from .repo_retrieval import retrieve_repository_chunks
    rid = repository_id.strip() if repository_id else None
    res = retrieve_repository_chunks(ctx.db, ctx.principal, query, repository_id=rid, limit=5)
    for h in res.hits:
        ctx.cite("repository_file", h.chunk_id, f"{h.repo_name}:{h.file_path}", h.classification,
                 extra=f"Lines {h.start_line}–{h.end_line} ({h.symbol}) [{h.github_url}]")

    if not res.hits:
        if res.denied_repos > 0:
            summary = f"0 results · {res.denied_repos} repository/repositories withheld by clearance policy"
            return ToolOutcome(
                "search_repositories", "denied", summary,
                f"ACCESS NOTICE: {res.denied_repos} relevant code repository/repositories exist that your role lacks clearance to view.",
                data={"withheld": res.denied_repos}
            )
        return ToolOutcome("search_repositories", "ok", "No matching code found across authorized repositories.",
                           "No matching code snippets or repository documentation found.")

    summary = f"{len(res.hits)} code excerpt(s) · {res.authorized_repos} repository/repositories authorized"
    return ToolOutcome("search_repositories", "ok", summary, res.llm_context(),
                       data={"hits": [h.to_citation() for h in res.hits], "withheld": len(res.withheld_repos)})


def t_get_leave_policy(ctx: ToolContext) -> ToolOutcome:
    return _search(ctx, "get_leave_policy", "leave policy casual sick earned leave entitlement carry forward request",
                   {"only_doc_types": {"Policy", "Procedure"}}, k=2)


def _full_text(ctx: ToolContext, doc_id: str) -> str:
    rows = ctx.db.scalars(select(DocumentChunk.content).where(DocumentChunk.document_id == doc_id,
                                                             DocumentChunk.company_id == ctx.principal.company_id)
                          .order_by(DocumentChunk.chunk_index)).all()
    return "\n\n".join(rows)


def resolve_document(ctx: ToolContext, ref: str, *, prefer_policy: bool = True,
                     department: str = "") -> tuple[DocMeta | None, str]:
    """Resolve an id / 'this document' / title query to ONE authorized document. Returns (meta, reason)."""
    p = ctx.principal
    ref = (ref or "").strip()
    m = re.search(r"\b(DOC|ORB)-\d+\b", ref, re.I)
    if not m and (not ref or re.fullmatch(r"(this|that|the|it|same)( (document|doc|policy|file|one))?", ref.lower())):
        if ctx.recent_docs:
            ref = ctx.recent_docs[0]
            m = re.search(r"\b(DOC|ORB)-\d+\b", ref)
        else:
            return None, "no_context"
    if m:
        doc = ctx.db.get(Document, m.group(0).upper())
        if not doc or doc.company_id != p.company_id or doc.status == "archived":
            return None, "not_found"
        from ..core.rbac import active_grant_ids
        dec = check_access(p, doc, status=doc.status, grant_ids=active_grant_ids(ctx.db, p))
        if not dec.allowed:
            _denied(ctx, "summarize_document", dec.reason, resource="document (withheld)", classification=doc.classification,
                    risk="HIGH" if doc.classification == "RESTRICTED" else "MEDIUM")
            return None, "denied"
        return next((x for x in authorized_metas(ctx.db, p) if x.id == doc.id), None), "ok"
    boost = {"boost_departments": {department}} if department else {}
    out = _search(ctx, "search_policies" if prefer_policy else "search_knowledge", ref,
                  {"only_doc_types": POLICY_TYPES, **boost} if prefer_policy else boost or None, k=2)
    res = ctx.retrievals[-1]
    if not res.evidence and prefer_policy:
        _search(ctx, "search_knowledge", ref, None, k=2)
        res = ctx.retrievals[-1]
    ev = next((e for e in res.evidence if e.is_latest), res.evidence[0] if res.evidence else None)
    return (ev.doc, "ok") if ev else (None, "denied" if res.only_restricted_answer() else "not_found")


def t_summarize_document(ctx: ToolContext, document: str = "", department: str = "") -> ToolOutcome:
    meta, why = resolve_document(ctx, document, department=department)
    if not meta:
        msg = {"no_context": "Which document should I summarize? Give its id (e.g. DOC-1043) or its name.",
               "denied": "That document is outside your access level.",
               "not_found": "I couldn't find that document in the NovaTech Solutions knowledge base."}[why]
        return ToolOutcome("summarize_document", "denied" if why == "denied" else "not_found", msg, msg)
    text = _full_text(ctx, meta.id)
    ev = Evidence(meta, [text], 1.0)
    ctx.retrievals.append(RetrievalResult(query=document, evidence=[ev], authorized_docs=1))
    ctx.recent_docs.insert(0, meta.id)
    _allowed_read(ctx, "summarize_document", meta.title, meta.id, meta.classification, "Authorized full-document read")
    view = (f'<authorized_context><document id="{meta.id}" title="{meta.title}" classification="{meta.classification}"'
            f' owner_department="{meta.department}" version="{meta.version}" effective_date="{meta.effective_date}">'
            f"\n{text[:9000]}\n</document></authorized_context>")
    return ToolOutcome("summarize_document", "ok", f"Loaded {meta.title} ({meta.id})", view,
                       {"doc": meta.public(), "text": text})


def t_compare_documents(ctx: ToolContext, document_a: str = "", document_b: str = "") -> ToolOutcome:
    p = ctx.principal
    a_meta, _ = resolve_document(ctx, document_a)
    b_meta = None
    if document_b and document_b.strip() and document_b.strip().lower() not in ("previous", "older", "prior", "old"):
        b_meta, _ = resolve_document(ctx, document_b)
    if a_meta and not b_meta:  # compare with the previous authorized version in the same family
        fam = sorted([m for m in authorized_metas(ctx.db, p) if m.family_key == a_meta.family_key],
                     key=lambda m: (m.effective_date, m.version))
        if len(fam) >= 2:
            a_meta, b_meta = fam[-1], fam[-2]
    if not a_meta or not b_meta:
        msg = "I need two authorized documents (or two versions of one policy) to compare."
        return ToolOutcome("compare_documents", "not_found", msg, msg)
    ta, tb = _full_text(ctx, a_meta.id), _full_text(ctx, b_meta.id)
    ctx.retrievals.append(RetrievalResult(query=f"{document_a} vs {document_b}", authorized_docs=2,
                                          evidence=[Evidence(a_meta, [ta], 1.0), Evidence(b_meta, [tb], 0.99)]))
    for m in (a_meta, b_meta):
        _allowed_read(ctx, "compare_documents", m.title, m.id, m.classification, "Authorized comparison")
    view = "\n".join(f'<document id="{m.id}" title="{m.title}" version="{m.version}" effective_date="{m.effective_date}">'
                     f"\n{t[:5000]}\n</document>" for m, t in ((a_meta, ta), (b_meta, tb)))
    return ToolOutcome("compare_documents", "ok", f"Compared {a_meta.id} with {b_meta.id}",
                       f"<authorized_context>\n{view}\n</authorized_context>",
                       {"a": a_meta.public(), "b": b_meta.public(), "text_a": ta, "text_b": tb})


def t_latest_updates(ctx: ToolContext, doc_type: str = "Policy", limit: int = 8) -> ToolOutcome:
    types = None if (doc_type or "any").lower() == "any" else ({"Policy", "Standard"} if doc_type == "Policy"
                                                              else {doc_type})
    metas = [m for m in authorized_metas(ctx.db, ctx.principal) if m.status == "published"
             and (types is None or m.doc_type in types)]
    metas.sort(key=lambda m: (m.updated_at or datetime.min.replace(tzinfo=timezone.utc)).isoformat()
               if m.updated_at else m.effective_date.isoformat(), reverse=True)
    top = metas[:max(1, min(int(limit or 8), 15))]
    for m in top:
        ctx.cite("document", m.id, m.title, m.classification, m.updated_at or m.effective_date, m.department)
    view = "\n".join(f"- {m.id} {m.title} v{m.version} ({m.classification}, {m.department}) updated "
                     f"{(m.updated_at or m.effective_date).strftime('%d %b %Y')}" for m in top)
    return ToolOutcome("latest_updates", "ok" if top else "not_found", f"{len(top)} recent {doc_type} update(s)",
                       view or "No documents found.", {"items": [m.public() for m in top]})


def t_get_department(ctx: ToolContext, department: str) -> ToolOutcome:
    from .retrieval import DEPT_WORDS
    p = ctx.principal
    key = (department or "").strip().lower()
    name = DEPT_WORDS.get(key) or next((d for d in DEPT_WORDS.values() if d.lower() == key), None) or department
    dep = ctx.db.scalar(select(Department).where(Department.company_id == p.company_id,
                                                 func.lower(Department.name) == name.lower(),
                                                 Department.is_public.is_(True)))
    if not dep:
        return ToolOutcome("get_department", "not_found", "Department not found", f"No department named '{department}'.")
    data = {"department": dep.name, "description": dep.description, "business_unit": dep.business_unit,
            "location": dep.location}
    if not is_guest(p):
        head = ctx.db.get(User, dep.head_id) if dep.head_id else None
        data["head"] = f"{head.full_name} ({head.job_title})" if head else None
        data["headcount"] = ctx.db.scalar(select(func.count(User.id)).where(User.department_id == dep.id,
                                                                           User.is_active.is_(True))) or 0
        mine = my_project_ids(ctx.db, p)
        projs = ctx.db.scalars(select(Project).where(Project.company_id == p.company_id, Project.department == dep.name,
                                                     Project.classification.in_(allowed_levels(p)))).all()
        vis = [x for x in projs if project_visible(ctx, x, mine).allowed]
        data["active_projects"] = sum(1 for x in vis if x.status in ("In Progress", "Planning"))
        data["visible_projects"] = len(vis)
    ctx.cite("department", dep.code, dep.name, "PUBLIC" if is_guest(p) else "INTERNAL")
    _allowed_read(ctx, "get_department", f"Department {dep.name}", dep.code, "INTERNAL")
    view = "; ".join(f"{k}: {v}" for k, v in data.items() if v not in (None, ""))
    return ToolOutcome("get_department", "ok", f"{dep.name} department", view, data)


# ---- people -----------------------------------------------------------------------------------

def t_get_employee(ctx: ToolContext, employee: str = "me", include: str = "profile") -> ToolOutcome:
    p = ctx.principal
    target = resolve_employee(ctx.db, p, employee)
    if not target or target.company_id != p.company_id:
        return ToolOutcome("get_employee", "not_found", "Employee not found", "No matching employee found.")
    mgr = ctx.db.get(User, target.manager_id) if target.manager_id else None
    is_self = target.id == p.user_id
    is_manager = target.manager_id == p.user_id
    hr = p.has("directory:read_sensitive")
    include = (include or "profile").lower()
    info = {"name": target.full_name, "employee_id": target.employee_code, "email": target.email,
            "department": target.department.name, "job_title": target.job_title, "location": target.location,
            "manager": mgr.full_name if mgr else None, "manager_email": mgr.email if mgr else None,
            "skills": ", ".join(target.skills or []), "employment_status": target.employment_status}
    if include == "team":
        reports = ctx.db.scalars(select(User).where(User.manager_id == target.id, User.is_active.is_(True))
                                 .order_by(User.full_name)).all()
        info["direct_reports"] = [f"{r.full_name} — {r.job_title}" for r in reports]
    sensitive_ok = is_self or hr
    if sensitive_ok and include == "profile":
        info.update({"phone": target.phone, "pan": target.pan_number,
                     "bank_account": f"account {target.bank_account}" if target.bank_account else None,
                     "joined_on": target.joined_on.isoformat() if target.joined_on else None,
                     "clearance": target.clearance})
    if include == "compensation":
        row = ctx.db.scalar(select(Compensation).where(Compensation.user_id == target.id))
        dec = check_record(p, row, owner_ids=[target.id]) if row else None
        if not dec or not dec.allowed:
            return _denied(ctx, "get_employee", "Compensation data is Confidential — only the employee and HR can "
                           "view it.", resource="Compensation record (withheld)", classification="CONFIDENTIAL",
                           risk="HIGH" if not is_self else "MEDIUM")
        info.update({"band": row.band, "base_salary": f"₹{row.base_salary:,.0f} per year",
                     "effective": row.effective_date.isoformat()})
        ctx.cite("compensation", row.id, f"Compensation — {target.full_name}", "CONFIDENTIAL", row.effective_date)
    if include == "performance":
        rows = ctx.db.scalars(select(PerformanceReview).where(PerformanceReview.user_id == target.id)
                              .order_by(PerformanceReview.cycle.desc())).all()
        ok = rows and check_record(p, rows[0], owner_ids=[target.id, rows[0].reviewer_id]).allowed
        if not ok:
            return _denied(ctx, "get_employee", "Performance reviews are Confidential — visible only to the employee, "
                           "their manager and HR.", resource="Performance review (withheld)",
                           classification="CONFIDENTIAL", risk="HIGH")
        info["reviews"] = [f"{r.cycle}: {r.rating}" for r in rows]
        ctx.cite("performance", rows[0].id, f"Performance reviews — {target.full_name}", "CONFIDENTIAL")
    if include == "leave":
        return t_get_leave_balance(ctx, employee)
    _allowed_read(ctx, "get_employee", f"Employee profile: {target.full_name}", target.employee_code,
                  "CONFIDENTIAL" if (sensitive_ok and not is_self) or include in ("compensation", "performance")
                  else "INTERNAL", "self" if is_self else ("HR" if hr else "manager" if is_manager else "directory"))
    ctx.cite("employee", target.employee_code, target.full_name, "INTERNAL", None, target.job_title)
    view = "\n".join(f"{k}: {v}" for k, v in info.items() if v)
    return ToolOutcome("get_employee", "ok", f"Profile of {target.full_name}"
                       + ("" if sensitive_ok else " (directory fields)"), view, info)


def _balance(db, user_id, year) -> LeaveBalance | None:
    return db.scalar(select(LeaveBalance).where(LeaveBalance.user_id == user_id, LeaveBalance.year == year))


def t_get_leave_balance(ctx: ToolContext, employee: str = "me") -> ToolOutcome:
    p = ctx.principal
    target = resolve_employee(ctx.db, p, employee)
    if not target:
        return ToolOutcome("get_leave_balance", "error", "Employee not found", "No matching employee found.")
    if target.id != p.user_id and not (p.has("leave:read_all") or
                                       (p.has("leave:read_team") and target.manager_id == p.user_id)):
        return _denied(ctx, "get_leave_balance", f"You may only view your own leave balance (requested "
                                                 f"{target.full_name}).", resource=f"Leave balance: {target.full_name}",
                       classification="CONFIDENTIAL")
    b = _balance(ctx.db, target.id, today().year)
    if not b:
        return ToolOutcome("get_leave_balance", "error", "No balance on record", "No leave balance on record.")
    pending = ctx.db.scalar(select(func.coalesce(func.sum(LeaveRequest.days), 0)).where(
        LeaveRequest.user_id == target.id, LeaveRequest.status == "pending_manager_approval")) or 0
    data = {"employee": target.full_name, "year": b.year,
            "casual": {"total": b.casual_total, "used": b.casual_used, "remaining": b.casual_total - b.casual_used},
            "sick": {"total": b.sick_total, "used": b.sick_used, "remaining": b.sick_total - b.sick_used},
            "earned": {"total": b.earned_total, "used": b.earned_used, "remaining": b.earned_total - b.earned_used},
            "pending_requests_days": float(pending)}
    audit.record(ctx.db, principal=p, action="tool.get_leave_balance", tool="get_leave_balance",
                 resource=f"Leave balance: {target.full_name}", resource_id=target.employee_code,
                 classification="INTERNAL", permission_result="ALLOWED", commit=False, request_id=ctx.request_id)
    ctx.cite("leave_balance", f"LB-{target.employee_code}", f"Leave balance {b.year} — {target.full_name}", "INTERNAL")
    view = (f"Leave balance {b.year} for {target.full_name}: casual {data['casual']['remaining']:g} of "
            f"{b.casual_total:g} remaining; sick {data['sick']['remaining']:g} of {b.sick_total:g}; earned "
            f"{data['earned']['remaining']:g} of {b.earned_total:g}. Pending requests: {float(pending):g} day(s).")
    return ToolOutcome("get_leave_balance", "ok", f"Casual {data['casual']['remaining']:g} remaining", view, data)


# ---- projects & productivity ------------------------------------------------------------------

def _project_row(proj: Project, db) -> dict:
    return {"id": proj.id, "name": proj.name, "department": proj.department, "status": proj.status,
            "health": proj.health, "progress": proj.progress, "priority": proj.priority, "manager": proj.owner_name,
            "deadline": proj.deadline.isoformat() if proj.deadline else None,
            "classification": proj.classification, "risks": proj.risks or [], "milestones": proj.milestones or [],
            "delayed": is_delayed(proj)}


def is_delayed(proj) -> bool:
    if proj.status in ("Completed", "Cancelled"):
        return False
    return bool((proj.deadline and proj.deadline < today()) or proj.health == "Red")


def resolve_project(ctx: ToolContext, ref: str) -> Project | None:
    p = ctx.principal
    ref = (ref or "").strip()
    m = re.search(r"\bPRJ-[A-Z0-9]+\b", ref, re.I)
    if m:
        proj = ctx.db.get(Project, m.group(0).upper())
        return proj if proj and proj.company_id == p.company_id else None
    if re.fullmatch(r"(this|that|the|it)( project)?", ref.lower()) and ctx.recent_projects:
        return ctx.db.get(Project, ctx.recent_projects[0])
    name = re.sub(r"\b(project|status|the|latest|of|for)\b", " ", ref.lower())
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        return None
    q = select(Project).where(Project.company_id == p.company_id)
    exact = ctx.db.scalar(q.where(func.lower(Project.name).in_([ref.lower(), name, f"project {name}"])))
    if exact:
        return exact
    rows = ctx.db.scalars(q.where(func.lower(Project.name).contains(name)).limit(20)).all()
    if not rows:
        return None
    rows.sort(key=lambda r: (len(r.name), r.id))
    return rows[0]


def t_get_project(ctx: ToolContext, project: str) -> ToolOutcome:
    p = ctx.principal
    proj = resolve_project(ctx, project)
    if not proj:
        return ToolOutcome("get_project", "not_found", "Project not found",
                           f"No project matching '{project}' was found in the NovaTech Solutions project records.")
    dec = project_visible(ctx, proj)
    if not dec.allowed:
        return _denied(ctx, "get_project", dec.reason, resource="Project record (withheld)",
                       classification=proj.classification,
                       risk="HIGH" if proj.classification == "RESTRICTED" else "MEDIUM")
    members = ctx.db.execute(select(User.full_name, User.job_title, ProjectMember.project_role)
                             .join(ProjectMember, ProjectMember.user_id == User.id)
                             .where(ProjectMember.project_id == proj.id).order_by(User.full_name)).all()
    tasks = ctx.db.scalars(select(Task).where(Task.project_id == proj.id)).all()
    open_t = [t for t in tasks if t.status != "done"]
    overdue = [t for t in open_t if t.due_date and t.due_date < today()]
    data = _project_row(proj, ctx.db)
    data.update({"summary": proj.summary, "start_date": proj.start_date.isoformat() if proj.start_date else None,
                 "technologies": proj.technologies or [], "budget_category": proj.budget_category,
                 "business_unit": proj.business_unit,
                 "members": [{"name": n, "title": t, "role": r} for n, t, r in members] if not is_guest(p) else [],
                 "tasks_total": len(tasks), "tasks_open": len(open_t), "tasks_overdue": len(overdue)})
    if _can_see_budget(p, proj.department):
        data["budget"] = f"₹{proj.budget_amount / 1e5:,.1f} lakh"
    ctx.recent_projects.insert(0, proj.id)
    ctx.cite("project", proj.id, proj.name, proj.classification, proj.updated_on, f"{proj.status} · {proj.health}")
    _allowed_read(ctx, "get_project", f"Project {proj.name}", proj.id, proj.classification, dec.rule)
    view = (f"Project {proj.name} ({proj.id}, {proj.classification}) — {proj.status}, health {proj.health}, "
            f"{proj.progress}% complete, manager {proj.owner_name}, deadline {data['deadline']}, priority "
            f"{proj.priority}. {proj.summary} Milestones: " + "; ".join(f"{m['name']} ({m['due']}, {m['state']})"
                                                                       for m in proj.milestones or []) +
            ". Risks: " + "; ".join(f"{r['risk']} [{r['severity']}] mitigation: {r['mitigation']}"
                                    for r in proj.risks or []) +
            (f". Members: " + ", ".join(f"{n} ({r})" for n, _, r in members) if data["members"] else "") +
            f". Tasks: {len(open_t)} open, {len(overdue)} overdue.")
    return ToolOutcome("get_project", "ok", f"{proj.name}: {proj.health} · {proj.progress}%", view, data)


def t_get_my_projects(ctx: ToolContext, filter: str = "all") -> ToolOutcome:
    p = ctx.principal
    rows = ctx.db.execute(select(Project, ProjectMember.project_role).join(
        ProjectMember, ProjectMember.project_id == Project.id).where(ProjectMember.user_id == p.user_id)).all()
    out = []
    for proj, role in rows:
        if not check_record(p, proj, owner_ids=[p.user_id]).allowed:
            continue
        r = _project_row(proj, ctx.db)
        r["my_role"] = role
        if filter == "active" and proj.status not in ACTIVE:
            continue
        if filter == "delayed" and not r["delayed"]:
            continue
        if filter == "approaching_deadline" and not (proj.status in ACTIVE and proj.deadline and
                                                     0 <= (proj.deadline - today()).days <= 45):
            continue
        out.append(r)
        ctx.cite("project", proj.id, proj.name, proj.classification, proj.updated_on, f"{proj.status} · {proj.health}")
        ctx.recent_projects.append(proj.id)
    order = {"Red": 0, "Amber": 1, "Green": 2}
    out.sort(key=lambda r: (r["status"] not in ACTIVE, order.get(r["health"], 3), r["deadline"] or "9999"))
    _allowed_read(ctx, "get_my_projects", "My project assignments", p.employee_code, "INTERNAL", f"filter={filter}")
    view = "\n".join(f"- {r['id']} {r['name']} — {r['status']}, {r['health']}, {r['progress']}%, deadline "
                     f"{r['deadline']}, my role {r['my_role']}, manager {r['manager']}"
                     + (f"; risks: " + "; ".join(x['risk'] for x in r['risks']) if r["delayed"] else "")
                     for r in out) or "No matching projects."
    return ToolOutcome("get_my_projects", "ok", f"{len(out)} project(s) ({filter})", view, {"projects": out})


def t_get_pending_tasks(ctx: ToolContext, scope: str = "me") -> ToolOutcome:
    p = ctx.principal
    d0 = today()
    ids = [p.user_id]
    if scope == "team" and p.has("leave:read_team"):
        ids += list(ctx.db.scalars(select(User.id).where(User.manager_id == p.user_id)).all())
    tasks = ctx.db.scalars(select(Task).where(Task.company_id == p.company_id, Task.assignee_id.in_(ids),
                                              Task.status != "done").order_by(Task.due_date)).all()
    items = [{"id": t.id, "title": t.title, "project": t.project, "project_id": t.project_id, "priority": t.priority,
              "status": t.status, "due": t.due_date.isoformat() if t.due_date else None,
              "overdue": bool(t.due_date and t.due_date < d0),
              "due_soon": bool(t.due_date and 0 <= (t.due_date - d0).days <= 2)} for t in tasks]
    start = datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
    mtgs = ctx.db.scalars(select(Meeting).join(MeetingAttendee, MeetingAttendee.meeting_id == Meeting.id)
                          .where(MeetingAttendee.user_id == p.user_id, Meeting.starts_at >= start,
                                 Meeting.starts_at < start + timedelta(days=2)).order_by(Meeting.starts_at)).all()
    meetings = [{"id": m.id, "title": m.title, "starts_at": m.starts_at.isoformat(), "location": m.location,
                 "project_id": m.project_id, "agenda": m.agenda} for m in mtgs]
    approvals = ctx.db.scalar(select(func.count(ApprovalRequest.id)).where(
        ApprovalRequest.approver_id == p.user_id, ApprovalRequest.status == "pending")) or 0
    pending_actions = ctx.db.scalar(select(func.count(AIAction.id)).where(
        AIAction.user_id == p.user_id, AIAction.status == "pending_confirmation")) or 0
    for t in items[:12]:
        ctx.cite("task", t["id"], t["title"], "INTERNAL", t["due"], t["project"])
    _allowed_read(ctx, "get_pending_tasks", "My work items", p.employee_code, "INTERNAL", f"scope={scope}")
    view = ("Open tasks:\n" + "\n".join(f"- [{t['id']}] {t['title']} · {t['project']} · {t['priority']} · "
                                        f"{t['status']} · due {t['due']}{' · OVERDUE' if t['overdue'] else ''}"
                                        for t in items[:25]) +
            "\nMeetings (today/tomorrow):\n" + "\n".join(f"- {m['title']} at {m['starts_at']}" for m in meetings) +
            f"\nApprovals waiting for you: {approvals}. AI actions awaiting your confirmation: {pending_actions}.")
    return ToolOutcome("get_pending_tasks", "ok", f"{len(items)} open task(s) · {len(meetings)} meeting(s)", view,
                       {"tasks": items, "meetings": meetings, "approvals_waiting": approvals,
                        "pending_actions": pending_actions})


def t_get_my_requests(ctx: ToolContext) -> ToolOutcome:
    p = ctx.principal
    lr = ctx.db.scalars(select(LeaveRequest).where(LeaveRequest.user_id == p.user_id)
                        .order_by(LeaveRequest.created_at.desc()).limit(10)).all()
    tk = ctx.db.scalars(select(ITTicket).where(ITTicket.user_id == p.user_id)
                        .order_by(ITTicket.created_at.desc()).limit(10)).all()
    sr = ctx.db.scalars(select(ServiceRequest).where(ServiceRequest.requester_id == p.user_id)
                        .order_by(ServiceRequest.created_at.desc()).limit(10)).all()
    ap = ctx.db.scalars(select(ApprovalRequest).where(ApprovalRequest.requester_id == p.user_id)
                        .order_by(ApprovalRequest.created_at.desc()).limit(10)).all()
    items = ([{"kind": "Leave", "id": x.id, "title": f"{x.leave_type.title()} leave {x.start_date:%d %b}"
               + ("" if x.start_date == x.end_date else f" → {x.end_date:%d %b}"), "status": x.status,
               "date": x.created_at.date().isoformat()} for x in lr] +
             [{"kind": "IT ticket", "id": x.id, "title": x.title, "status": x.status,
               "date": x.created_at.date().isoformat()} for x in tk] +
             [{"kind": f"{x.request_type.title()} request", "id": x.id, "title": x.title, "status": x.status,
               "date": x.created_at.date().isoformat()} for x in sr] +
             [{"kind": "Approval", "id": x.id, "title": x.title, "status": x.status,
               "date": x.created_at.date().isoformat()} for x in ap if x.type == "document_access"])
    items.sort(key=lambda x: x["date"], reverse=True)
    for it in items[:10]:
        ctx.cite("request", it["id"], it["title"], "INTERNAL", it["date"], f"{it['kind']} · {it['status']}")
    _allowed_read(ctx, "get_my_requests", "My requests", p.employee_code, "INTERNAL")
    view = "\n".join(f"- {i['kind']} {i['id']}: {i['title']} — {i['status']} ({i['date']})" for i in items) or \
        "No requests found."
    return ToolOutcome("get_my_requests", "ok", f"{len(items)} request(s)", view, {"items": items})


def t_search_software(ctx: ToolContext, query: str = "") -> ToolOutcome:
    rows = ctx.db.scalars(select(SoftwareItem).where(SoftwareItem.company_id == ctx.principal.company_id,
                                                     SoftwareItem.classification.in_(allowed_levels(ctx.principal)))
                          .order_by(SoftwareItem.name)).all()
    q = (query or "").lower()
    toks = [t for t in re.findall(r"[a-z0-9+.#]+", q) if len(t) >= 3 and t not in {
        "software", "available", "what", "which", "the", "can", "install", "use", "for", "employees", "approved",
        "tools", "apps", "list", "need", "approval", "allowed", "are", "catalog", "catalogue", "our", "company",
        "all", "any", "does", "require", "requires", "application", "applications", "get", "how"}]
    hits = [r for r in rows if not toks or any(t in f"{r.name} {r.category} {r.vendor}".lower() for t in toks)]
    if not hits:
        hits = rows
    for r in hits[:15]:
        ctx.cite("software", r.id, r.name, r.classification, None, r.category)
    data = [{"name": r.name, "category": r.category, "approval_required": r.approval_required,
             "platforms": r.platforms, "licence": r.license_type, "description": r.description} for r in hits]
    view = "\n".join(f"- {d['name']} ({d['category']}) — {'needs approval' if d['approval_required'] else 'self-service'}"
                     f"; {', '.join(d['platforms'])}" for d in data[:40])
    return ToolOutcome("search_software", "ok", f"{len(data)} catalogue item(s)", view,
                       {"items": data, "matched": bool(toks) and len(hits) != len(rows)})


# ---- actions (human-in-the-loop) ---------------------------------------------------------------

def _parse_iso_or_nl(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip()[:10])
    except Exception:
        return parse_date(value or "")


def _workdays(a: date, b: date) -> float:
    n, d = 0, a
    while d <= b:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return float(n)


def t_create_leave_request(ctx: ToolContext, start_date: str, end_date: str | None = None, leave_type: str = "casual",
                           reason: str = "Personal work") -> ToolOutcome:
    p = ctx.principal
    s = _parse_iso_or_nl(start_date)
    e = _parse_iso_or_nl(end_date) if end_date else s
    if not s or not e:
        return ToolOutcome("create_leave_request", "error", "Could not understand the date",
                           "ERROR: invalid date. Ask the user for the date.")
    if s < today():
        return ToolOutcome("create_leave_request", "error", "Date is in the past", "ERROR: leave date is in the past.")
    if e < s:
        return ToolOutcome("create_leave_request", "error", "Invalid date range",
                           "ERROR: leave end date cannot be earlier than start date.")
    lt = leave_type if leave_type in ("casual", "sick", "earned") else "casual"
    days = _workdays(s, e) or 1.0
    b = _balance(ctx.db, p.user_id, s.year)
    remaining = (getattr(b, f"{lt}_total") - getattr(b, f"{lt}_used")) if b else 0
    if days > remaining:
        return ToolOutcome("create_leave_request", "error", "Insufficient balance",
                           f"ERROR: insufficient {lt} leave ({remaining:g} remaining, {days:g} requested).")
    me = _user(ctx.db, p)
    mgr = ctx.db.get(User, me.manager_id) if me.manager_id else None
    date_label = fmt_date(s) if s == e else f"{fmt_date(s)} → {fmt_date(e)}"
    reason_clean = (reason.strip() if isinstance(reason, str) and reason.strip() else "Personal work")[:300]
    args = {"start_date": s.isoformat(), "end_date": e.isoformat(), "leave_type": lt, "reason": reason_clean,
            "days": days}
    preview = {"fields": [["Action", "Submit leave request"], ["Date", date_label], ["Type", lt.title()],
                          ["Working days", f"{days:g}"], ["Reason", reason_clean],
                          ["Approver", mgr.full_name if mgr else "HR"],
                          ["Balance after approval", f"{remaining - days:g} {lt} day(s)"]]}
    if s.weekday() >= 5:
        preview["warning"] = "The selected date falls on a weekend."
    act = _pending(ctx, "create_leave_request", args, preview, "Submit leave request")
    return ToolOutcome("create_leave_request", "pending_confirmation", f"Prepared: {lt} leave on {date_label}",
                       f"PENDING_USER_CONFIRMATION (action {act.id}): {lt} leave {date_label}, {days:g} day(s). "
                       "Tell the user to review and approve the action card.", args, act)


PRIORITY_WORD = {"P1": "Critical", "P2": "High", "P3": "Medium", "P4": "Low"}


def t_create_it_ticket(ctx: ToolContext, title: str, description: str, priority: str = "P3",
                       category: str = "Other") -> ToolOutcome:
    priority = priority if priority in ("P1", "P2", "P3", "P4") else "P3"
    category = category if category in ("Hardware", "Software", "Network", "Access", "Other") else "Other"
    args = {"title": title[:150], "description": description[:2000], "priority": priority, "category": category}
    preview = {"fields": [["Action", "Create IT support ticket"], ["Issue", args["title"]], ["Category", category],
                          ["Priority", f"{PRIORITY_WORD[priority]} ({priority})"], ["Description", args["description"]],
                          ["Queue", "IT Service Desk (Information Technology)"]]}
    act = _pending(ctx, "create_it_ticket", args, preview, "Create IT support ticket")
    return ToolOutcome("create_it_ticket", "pending_confirmation", f"Prepared ticket: {args['title']}",
                       f"PENDING_USER_CONFIRMATION (action {act.id}) for IT ticket '{args['title']}' "
                       f"priority {PRIORITY_WORD[priority]}.", args, act)


REQUEST_ROUTING = {"access": "Your manager, then the system owner", "software": "Your manager (paid licences) / IT",
                   "document": "HR Operations", "procurement": "Budget owner, then Procurement (Operations)",
                   "general": "Your manager"}


def t_create_request(ctx: ToolContext, request_type: str, title: str, justification: str = "",
                     estimated_cost: float = 0) -> ToolOutcome:
    rt = request_type if request_type in REQUEST_ROUTING else "general"
    args = {"request_type": rt, "title": title[:180], "justification": (justification or "")[:500],
            "estimated_cost": float(estimated_cost or 0)}
    fields = [["Action", f"Submit {rt} request"], ["Request", args["title"]],
              ["Justification", args["justification"] or "—"], ["Approval route", REQUEST_ROUTING[rt]]]
    if rt == "procurement" and args["estimated_cost"]:
        fields.append(["Estimated cost", f"₹{args['estimated_cost']:,.0f}"])
        lim = args["estimated_cost"]
        fields.append(["Approval level", "Line manager" if lim <= 50000 else "Department head" if lim <= 500000
                       else "Department head + Finance Manager" if lim <= 5000000 else "COO + Procurement Committee"])
    if rt == "software":
        sw = ctx.db.scalar(select(SoftwareItem).where(func.lower(SoftwareItem.name).contains(
            re.sub(r"^(software request:\s*)", "", args["title"].lower())[:40])))
        if sw:
            fields.append(["Catalogue", f"{sw.name} — {'approval required' if sw.approval_required else 'self-service'}"])
    act = _pending(ctx, "create_request", args, {"fields": fields}, f"Submit {rt} request")
    return ToolOutcome("create_request", "pending_confirmation", f"Prepared {rt} request",
                       f"PENDING_USER_CONFIRMATION (action {act.id}) for {rt} request '{args['title']}'.", args, act)


def _email_common(ctx: ToolContext, tool: str, recipient: str, subject: str, body: str) -> ToolOutcome:
    p = ctx.principal
    r = (recipient or "").strip()
    if "@" in r and not r.lower().endswith("@" + COMPANY_DOMAIN):
        audit.record(ctx.db, principal=p, action="security.exfiltration_blocked", tool=tool, resource=r,
                     permission_result="BLOCKED", result="BLOCKED", risk="HIGH",
                     reason=f"External recipient '{r}' blocked by outbound email policy", commit=False,
                     request_id=ctx.request_id)
        ctx.security_events.append({"type": "exfiltration_blocked", "recipient": r})
        return ToolOutcome(tool, "blocked", "External recipient blocked",
                           "BLOCKED: the AI assistant may only email internal @novatech.demo recipients.")
    target = resolve_employee(ctx.db, p, r)
    if not target:
        return ToolOutcome(tool, "error", "Recipient not found", f"ERROR: no employee matches '{r}'.")
    for a in ctx.actions:  # de-duplicate draft+send within the same turn
        if a.tool == "send_email" and a.status == "pending_confirmation":
            return ToolOutcome(tool, "pending_confirmation", "Email already awaiting confirmation",
                               f"PENDING_USER_CONFIRMATION (action {a.id}).", a.args, a)
    args = {"recipient_email": target.email, "recipient_name": target.full_name, "subject": subject[:200],
            "body": body[:4000]}
    preview = {"fields": [["Action", "Send email"], ["From", p.email], ["To", f"{target.full_name} <{target.email}>"],
                          ["Subject", args["subject"]]], "body": args["body"], "editable": ["subject", "body"]}
    act = _pending(ctx, "send_email", args, preview, "Send email")
    return ToolOutcome(tool, "pending_confirmation", f"Draft to {target.full_name} ready for review",
                       f"Draft prepared and PENDING_USER_CONFIRMATION (action {act.id}) to {target.full_name}. "
                       "Do not claim it was sent.", {**args, "recipient": recipient}, act)


def t_draft_email(ctx, recipient, subject, body):
    return _email_common(ctx, "draft_email", recipient, subject, body)


def t_send_email(ctx, recipient, subject, body):
    return _email_common(ctx, "send_email", recipient, subject, body)


def t_request_approval(ctx: ToolContext, request_type: str, document_id: str = "", justification: str = "") -> ToolOutcome:
    p = ctx.principal
    if request_type == "document_access":
        doc = ctx.db.get(Document, document_id)
        if not doc or doc.company_id != p.company_id:
            return ToolOutcome("request_approval", "error", "Document not found", "ERROR: unknown document id.")
        args = {"request_type": "document_access", "document_id": doc.id, "justification": justification[:500]}
        preview = {"fields": [["Action", "Request document access"], ["Document", doc.id],
                              ["Classification", doc.classification], ["Approver", "Document owner"],
                              ["Justification", justification[:500] or "—"], ["Duration", "7 days, read-only"]]}
    else:
        args = {"request_type": "general", "document_id": "", "justification": justification[:500]}
        preview = {"fields": [["Action", "Request approval"], ["Details", justification[:500]]]}
    act = _pending(ctx, "request_approval", args, preview, "Create approval request")
    return ToolOutcome("request_approval", "pending_confirmation", "Approval request prepared",
                       f"PENDING_USER_CONFIRMATION (action {act.id}).", args, act)


def t_delete_document(ctx: ToolContext, document_id: str) -> ToolOutcome:
    p = ctx.principal
    doc = ctx.db.get(Document, document_id)
    if not doc or doc.company_id != p.company_id:
        return ToolOutcome("delete_document", "error", "Document not found", "ERROR: unknown document id.")
    dec = check_access(p, doc, status=doc.status)
    if not dec.allowed:
        return _denied(ctx, "delete_document", dec.reason, resource="document (withheld)",
                       classification=doc.classification, risk="HIGH")
    args = {"document_id": doc.id}
    preview = {"fields": [["Action", "Archive document (delete)"], ["Document", f"{doc.title} ({doc.id})"],
                          ["Classification", doc.classification]],
               "warning": "Archived documents are removed from search and RAG for all employees."}
    act = _pending(ctx, "delete_document", args, preview, "Delete document")
    return ToolOutcome("delete_document", "pending_confirmation", f"Deletion of {doc.id} awaiting confirmation",
                       f"PENDING_USER_CONFIRMATION (action {act.id}).", args, act)


def t_analytics_query(ctx: ToolContext, dataset: str, metric: str = "count", group_by: str = "", status: str = "",
                      department: str = "") -> ToolOutcome:
    from .analytics import run_query
    return run_query(ctx, dataset, metric, group_by, status, department)


# ---- Enterprise Connectors & Skills Tools ----------------------------------------------------

def t_search_jira_issues(ctx: ToolContext, query: str = "", project: str = "NOVA", status: str = "") -> ToolOutcome:
    from .connectors.permission_engine import check_connector_access
    from .connectors.providers.jira_provider import JiraProvider
    dec = check_connector_access(ctx.db, ctx.principal, "conn_jira", "READ", project, "Jira Management Agent")
    if not dec.allowed:
        return _denied(ctx, "search_jira_issues", dec.reason, resource=f"jira:{project}", classification=dec.classification)
    issues = JiraProvider.search_issues(ctx.db, ctx.principal.company_id, query=query, project=project, status=status)
    for iss in issues[:10]:
        ctx.cite("jira", iss["key"], f"{iss['key']}: {iss['title']}", "INTERNAL", None, f"{iss['priority']} · {iss['status']}")
    view = "Jira issues:\n" + "\n".join(f"- [{i['key']}] {i['title']} ({i['status']} · Priority: {i['priority']} · Assignee: {i['assignee']})" for i in issues) if issues else "No Jira issues found."
    return ToolOutcome("search_jira_issues", "ok", f"{len(issues)} Jira issue(s)", view, {"issues": issues})


def t_create_jira_issue(ctx: ToolContext, title: str, description: str, project: str = "NOVA", priority: str = "High") -> ToolOutcome:
    from .connectors.permission_engine import check_connector_access
    from .connectors.providers.jira_provider import JiraProvider
    dec = check_connector_access(ctx.db, ctx.principal, "conn_jira", "CREATE", project, "Jira Management Agent")
    if not dec.allowed:
        return _denied(ctx, "create_jira_issue", dec.reason, resource=f"jira:{project}", classification=dec.classification)
    args = {"title": title[:160], "description": description[:2000], "project": project, "priority": priority}
    preview = JiraProvider.prepare_create_issue_proposal(project, args["title"], args["description"], priority)
    act = _pending(ctx, "create_jira_issue", args, preview, f"Create Jira issue in {project}")
    return ToolOutcome("create_jira_issue", "pending_confirmation", f"Prepared Jira ticket: {args['title']}",
                       f"PENDING_USER_CONFIRMATION (action {act.id}) for Jira ticket '{args['title']}' in {project}. Tell the user to review and confirm the action card.", args, act)


def t_search_teams_messages(ctx: ToolContext, query: str = "", channel: str = "#security-eng") -> ToolOutcome:
    from .connectors.permission_engine import check_connector_access
    from .connectors.providers.teams_provider import TeamsProvider
    dec = check_connector_access(ctx.db, ctx.principal, "conn_teams", "READ", channel, "Security Analysis Agent")
    if not dec.allowed:
        return _denied(ctx, "search_teams_messages", dec.reason, resource=f"teams:{channel}", classification=dec.classification)
    msgs = TeamsProvider.search_messages(ctx.db, ctx.principal.company_id, query=query, channel=channel)
    for m in msgs[:6]:
        ctx.cite("teams", m["id"], f"{m['channel']}: {m['author']}", "INTERNAL", None, m["message"][:80])
    view = "Teams discussions:\n" + "\n".join(f"- [{m['channel']}] {m['author']}: {m['message']}" for m in msgs) if msgs else "No Teams messages found."
    return ToolOutcome("search_teams_messages", "ok", f"{len(msgs)} Teams message(s)", view, {"messages": msgs})


def t_post_teams_message(ctx: ToolContext, channel: str, message: str) -> ToolOutcome:
    from .connectors.permission_engine import check_connector_access
    from .connectors.providers.teams_provider import TeamsProvider
    dec = check_connector_access(ctx.db, ctx.principal, "conn_teams", "CREATE", channel)
    if not dec.allowed:
        return _denied(ctx, "post_teams_message", dec.reason, resource=f"teams:{channel}", classification=dec.classification)
    args = {"channel": channel, "message": message[:1000]}
    preview = TeamsProvider.prepare_post_message_proposal(channel, args["message"])
    act = _pending(ctx, "post_teams_message", args, preview, f"Post message to {channel}")
    return ToolOutcome("post_teams_message", "pending_confirmation", f"Prepared message for {channel}",
                       f"PENDING_USER_CONFIRMATION (action {act.id}) for Teams post to {channel}.", args, act)


def t_search_emails(ctx: ToolContext, query: str = "", sender: str = "") -> ToolOutcome:
    from .connectors.permission_engine import check_connector_access
    from .connectors.providers.outlook_provider import OutlookProvider
    dec = check_connector_access(ctx.db, ctx.principal, "conn_outlook", "READ", agent_name="Productivity Agent")
    if not dec.allowed:
        return _denied(ctx, "search_emails", dec.reason, resource="outlook:mailbox", classification=dec.classification)
    emails = OutlookProvider.search_emails(ctx.db, ctx.principal.company_id, query=query, sender=sender)
    for e in emails[:6]:
        ctx.cite("email", e["id"], f"Email: {e['subject']}", "INTERNAL", None, f"From: {e['sender']}")
    view = "Outlook emails:\n" + "\n".join(f"- [{e['sender']}] {e['subject']}: {e['body_preview']}" for e in emails) if emails else "No emails found."
    return ToolOutcome("search_emails", "ok", f"{len(emails)} email(s)", view, {"emails": emails})


def t_lookup_entra_identity(ctx: ToolContext, query: str = "me") -> ToolOutcome:
    from .connectors.permission_engine import check_connector_access
    from .connectors.providers.entra_provider import EntraProvider
    dec = check_connector_access(ctx.db, ctx.principal, "conn_entra", "READ", agent_name="Security Analysis Agent")
    if not dec.allowed:
        return _denied(ctx, "lookup_entra_identity", dec.reason, resource="entra:directory", classification=dec.classification)
    target = ctx.principal.email if query in ("me", "myself", "self") else query
    ident = EntraProvider.lookup_identity(ctx.db, ctx.principal.company_id, target)
    if not ident:
        return ToolOutcome("lookup_entra_identity", "not_found", "Identity not found", "No matching Entra ID user found.")
    view = f"Entra ID Profile for {ident['displayName']} ({ident['userPrincipalName']}):\n- Member of: {', '.join(ident['memberOf'])}\n- MFA: {ident['mfaStatus']}\n- Conditional Access: {ident['conditionalAccess']}"
    return ToolOutcome("lookup_entra_identity", "ok", f"Entra profile: {ident['displayName']}", view, ident)


def t_scan_vulnerabilities(ctx: ToolContext, target: str = "authentication service") -> ToolOutcome:
    from .skills.skills_registry import SkillsRegistry
    res = SkillsRegistry.run_security_analysis(ctx.db, ctx.principal, {"target": target})
    view = f"Security Vulnerability Scan for {target}:\n- Risk Score: {res['risk_score']}/10\n" + "\n".join(
        f"- [{f['severity']}] {f['title']} ({f['cwe']}) in {f['affected_file']}:{f['line']} -> {f['recommended_remediation']}" for f in res["findings"]
    )
    return ToolOutcome("scan_vulnerabilities", "ok", f"{len(res['findings'])} vulnerability finding(s)", view, res)


def t_get_repo_architecture(ctx: ToolContext, repo_name: str = "novatech/enterprise-agent") -> ToolOutcome:
    from .skills.skills_registry import SkillsRegistry
    res = SkillsRegistry.run_repo_analysis(ctx.db, ctx.principal, {"repo_name": repo_name})
    arch = res["architecture"]
    view = f"Repository Architecture Overview for {repo_name}:\n- Frontend: {arch['Frontend']['framework']}\n- Backend: {arch['Backend']['framework']}\n- Database: {arch['Database']['orm']}\n- CI/CD: {arch['CI/CD & Testing']['ci_pipeline']}"
    return ToolOutcome("get_repo_architecture", "ok", f"Architecture of {repo_name}", view, res)


def t_generate_enterprise_report(ctx: ToolContext, report_type: str = "Security Assessment & Engineering Status Report") -> ToolOutcome:
    from .skills.skills_registry import SkillsRegistry
    res = SkillsRegistry.run_report_generation(ctx.db, ctx.principal, {"report_type": report_type})
    view = f"# {res['report_title']}\n\n**Executive Summary:**\n{res['executive_summary']}\n\n**Evidence:**\n" + "\n".join(
        f"- [{row['Source']}] {row['Reference']} — Status: {row['Status']} (Owner: {row['Owner']})" for row in res["evidence_table"]
    )
    return ToolOutcome("generate_enterprise_report", "ok", f"Generated {report_type}", view, res)


IMPL = {
    "search_knowledge": t_search_knowledge, "search_documents": t_search_documents,
    "search_policies": t_search_policies, "search_repositories": t_search_repositories,
    "get_leave_policy": t_get_leave_policy,
    "summarize_document": t_summarize_document, "compare_documents": t_compare_documents,
    "latest_updates": t_latest_updates, "get_department": t_get_department, "analytics_query": t_analytics_query,
    "get_project": t_get_project, "get_my_projects": t_get_my_projects, "get_pending_tasks": t_get_pending_tasks,
    "get_my_requests": t_get_my_requests, "get_employee": t_get_employee, "search_software": t_search_software,
    "get_leave_balance": t_get_leave_balance, "create_leave_request": t_create_leave_request,
    "create_it_ticket": t_create_it_ticket, "create_request": t_create_request, "draft_email": t_draft_email,
    "send_email": t_send_email, "request_approval": t_request_approval, "delete_document": t_delete_document,
    # Connector & Skill tools
    "search_jira_issues": t_search_jira_issues, "create_jira_issue": t_create_jira_issue,
    "search_teams_messages": t_search_teams_messages, "post_teams_message": t_post_teams_message,
    "search_emails": t_search_emails, "lookup_entra_identity": t_lookup_entra_identity,
    "scan_vulnerabilities": t_scan_vulnerabilities, "get_repo_architecture": t_get_repo_architecture,
    "generate_enterprise_report": t_generate_enterprise_report,
}


def run_tool(ctx: ToolContext, name: str, args: dict) -> ToolOutcome:
    started = time.time()
    name = TOOL_ALIASES.get(name, name)
    dec = check_tool(ctx.principal.permissions, name)
    if not dec.allowed:
        out = _denied(ctx, name, dec.reason, resource=f"tool:{name}")
        _log_exec(ctx, name, args, "denied", dec.reason, started)
        return out
    fn = IMPL[name]
    ctx.tools_used.append(name)
    try:
        clean = {k: v for k, v in (args or {}).items() if isinstance(v, (str, int, float)) and k in
                 fn.__code__.co_varnames[:fn.__code__.co_argcount]}
        out = fn(ctx, **clean)
    except TypeError:
        out = ToolOutcome(name, "error", "Invalid tool arguments", "ERROR: invalid arguments for tool.")
    except Exception:
        import logging
        logging.getLogger("novatech.tools").exception("tool %s failed", name)
        out = ToolOutcome(name, "error", "Tool execution failed", "ERROR: tool failed; apologise and suggest retrying.")
    _log_exec(ctx, name, args, out.status, out.summary, started, out.action.id if out.action else None)
    return out


# ---- Executing a confirmed action ------------------------------------------------------------

def _next_id(prefix: str, db: DBSession | None = None, model: type | None = None) -> str:
    for _ in range(15):
        nid = f"{prefix}-{random.randint(10000, 99999)}"
        if db and model and db.get(model, nid):
            continue
        return nid
    return f"{prefix}-{random.randint(100000, 999999)}"


def execute_action(db: DBSession, p: Principal, act: AIAction, overrides: dict | None = None) -> dict:
    """Runs a previously-proposed action using the SERVER-STORED arguments (the client cannot swap them)."""
    dec = check_tool(p.permissions, act.tool)
    if not dec.allowed:
        raise PermissionError(dec.reason)
    a = dict(act.args)
    if overrides and act.tool == "send_email":
        for k in ("subject", "body"):
            if isinstance(overrides.get(k), str) and overrides[k].strip():
                a[k] = overrides[k][:4000]
    me = db.get(User, p.user_id)
    if act.tool == "create_leave_request":
        s, e = date.fromisoformat(a["start_date"]), date.fromisoformat(a["end_date"])
        lr = LeaveRequest(id=_next_id("LR", db, LeaveRequest), company_id=p.company_id, user_id=p.user_id, leave_type=a["leave_type"],
                          start_date=s, end_date=e, days=a["days"], reason=a["reason"])
        db.add(lr)
        apr = ApprovalRequest(company_id=p.company_id, type="leave", requester_id=p.user_id,
                              approver_id=me.manager_id, resource_id=lr.id, risk="LOW",
                              title=f"{a['leave_type'].title()} leave · {fmt_date(s)}"
                                    + ("" if s == e else f" → {fmt_date(e)}"),
                              details={"days": a["days"], "reason": a["reason"], "leave_type": a["leave_type"],
                                       "start_date": a["start_date"], "end_date": a["end_date"]})
        db.add(apr)
        mgr = db.get(User, me.manager_id) if me.manager_id else None
        return {"reference": lr.id, "message": f"Leave request {lr.id} submitted and routed to "
                                               f"{mgr.full_name if mgr else 'HR'} for approval.",
                "approval_id": apr.id}
    if act.tool == "create_it_ticket":
        t = ITTicket(id=_next_id("INC", db, ITTicket), company_id=p.company_id, user_id=p.user_id, title=a["title"],
                     description=a["description"], priority=a["priority"], category=a.get("category", "Other"))
        db.add(t)
        sla = {"P1": "1 hour", "P2": "4 hours", "P3": "1 business day", "P4": "3 business days"}[a["priority"]]
        return {"reference": t.id, "message": f"Ticket {t.id} created in the IT Service Desk queue (SLA {sla})."}
    if act.tool == "create_request":
        now = datetime.now(timezone.utc)
        sr = ServiceRequest(id=_next_id("REQ", db, ServiceRequest), company_id=p.company_id, requester_id=p.user_id,
                            request_type=a["request_type"], title=a["title"],
                            details={"justification": a.get("justification", ""),
                                     "estimated_cost": a.get("estimated_cost", 0)},
                            status="submitted", approver_id=me.manager_id, created_at=now, updated_at=now)
        db.add(sr)
        if me.manager_id:
            db.add(ApprovalRequest(company_id=p.company_id, type="service_request", requester_id=p.user_id,
                                   approver_id=me.manager_id, resource_id=sr.id,
                                   risk="MEDIUM" if a["request_type"] in ("access", "procurement") else "LOW",
                                   title=f"{a['request_type'].title()} request · {a['title']}",
                                   details={"justification": a.get("justification", ""),
                                            "request_type": a["request_type"],
                                            "estimated_cost": a.get("estimated_cost", 0)}))
        return {"reference": sr.id, "message": f"Request {sr.id} submitted — routed to "
                                               f"{REQUEST_ROUTING[a['request_type']].lower()}."}
    if act.tool == "send_email":
        e = EmailOutbox(company_id=p.company_id, sender_id=p.user_id, recipient_email=a["recipient_email"],
                        recipient_name=a["recipient_name"], subject=a["subject"], body=a["body"])
        db.add(e)
        db.flush()
        return {"reference": e.id, "message": f"Email sent to {a['recipient_name']} (simulated delivery — "
                                              "prototype outbox, no real mail leaves the system)."}
    if act.tool == "request_approval":
        if a["request_type"] == "document_access":
            doc = db.get(Document, a["document_id"])
            apr = ApprovalRequest(company_id=p.company_id, type="document_access", requester_id=p.user_id,
                                  approver_id=doc.owner_id, resource_id=doc.id,
                                  risk="HIGH" if doc.classification == "RESTRICTED" else "MEDIUM",
                                  title=f"Access request · {doc.title}",
                                  details={"justification": a["justification"], "classification": doc.classification,
                                           "duration_days": 7})
        else:
            apr = ApprovalRequest(company_id=p.company_id, type="general", requester_id=p.user_id,
                                  approver_id=me.manager_id, title="General approval request",
                                  details={"justification": a["justification"]})
        db.add(apr)
        db.flush()
        return {"reference": apr.id, "message": "Approval request created and routed to the approver."}
    if act.tool == "delete_document":
        doc = db.get(Document, a["document_id"])
        doc.status = "archived"
        doc.updated_at = datetime.now(timezone.utc)
        return {"reference": doc.id, "message": f"{doc.title} archived and removed from search."}
    if act.tool == "create_jira_issue":
        item_id = _next_id("JIRA", db, ConnectorItem)
        project = a.get("project", "NOVA")
        ci = ConnectorItem(
            id=item_id, company_id=p.company_id, connector_id="conn_jira", provider="jira",
            item_type="jira_issue", external_id=f"{project}-{random.randint(430, 990)}",
            title=a["title"], content=a["description"],
            metadata_json={"priority": a.get("priority", "High"), "status": "Open", "assignee": p.full_name, "sprint": "Sprint 44"},
            classification="INTERNAL", url=f"https://novatech.atlassian.net/browse/{project}",
            author=p.full_name
        )
        db.add(ci)
        db.flush()
        return {"reference": ci.external_id, "message": f"Jira ticket {ci.external_id} created successfully in project {project} and assigned to {p.full_name}."}
    if act.tool == "post_teams_message":
        msg_id = _next_id("TEAMS", db, ConnectorItem)
        ci = ConnectorItem(
            id=msg_id, company_id=p.company_id, connector_id="conn_teams", provider="teams",
            item_type="teams_message", external_id=f"msg_{random.randint(500, 999)}",
            title=f"Message to {a['channel']}", content=f"{p.full_name}: {a['message']}",
            metadata_json={"channel": a["channel"], "author": p.full_name},
            classification="INTERNAL", url=f"https://teams.microsoft.com/l/message/{a['channel']}",
            author=p.full_name
        )
        db.add(ci)
        db.flush()
        return {"reference": a["channel"], "message": f"Message successfully posted to Teams channel {a['channel']}."}
    raise ValueError("Unsupported action")
