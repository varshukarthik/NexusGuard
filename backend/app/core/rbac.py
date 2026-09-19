"""The permission engine.

Authorization is deterministic code — the LLM never participates. Every document read path
(RAG retrieval, document viewer, search, project status, policy lab) calls `check_document_access`
BEFORE any content is loaded into memory destined for the model or the user.

Rule (all must pass unless an explicit, unexpired grant exists):
  0. Guest boundary       — guest principals can only ever read PUBLIC resources (no grants, no exceptions)
  1. Tenant isolation     — subject.company_id == resource.company_id
  2. Lifecycle            — only published/superseded content is readable via retrieval
  3. Clearance            — rank(subject.clearance) >= rank(resource.classification)
  4. Department scope     — resource.allowed_departments contains subject.department (or "*")
  5. Role scope           — resource.allowed_roles contains subject.role (or "*")
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable, Protocol

LEVELS = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "RESTRICTED": 3}
GUEST_ROLE = "guest"
READABLE_STATUSES = {"published", "superseded"}


def norm_level(value: str) -> str:
    v = (value or "").strip().upper()
    if v not in LEVELS:
        raise ValueError(f"Unknown classification '{value}'")
    return v


class Subject(Protocol):
    user_id: str
    company_id: str
    department: str
    role_code: str
    role_name: str
    clearance: str


class Resource(Protocol):
    id: str
    company_id: str
    classification: str
    allowed_departments: list
    allowed_roles: list


@dataclass
class Decision:
    allowed: bool
    rule: str
    reason: str
    resource_id: str = ""
    classification: str = ""

    def dict(self) -> dict:
        return asdict(self)


def _matches(values: Iterable[str], *candidates: str) -> bool:
    vals = {str(v).strip().lower() for v in (values or [])}
    if not vals or "*" in vals:
        return True
    return any(c and c.strip().lower() in vals for c in candidates)


def is_guest(subject) -> bool:
    return getattr(subject, "role_code", "") == GUEST_ROLE


def allowed_levels(subject) -> list[str]:
    """Classification levels the subject's clearance can ever reach (used as a SQL pre-filter)."""
    if is_guest(subject):
        return ["PUBLIC"]
    return [lvl for lvl, rank in LEVELS.items() if rank <= LEVELS[norm_level(subject.clearance)]]


def check_access(subject: Subject, res: Resource, *, status: str | None = "published",
                 grant_ids: set[str] | None = None) -> Decision:
    cls = norm_level(res.classification)
    base = dict(resource_id=res.id, classification=cls)
    if is_guest(subject) and cls != "PUBLIC":
        return Decision(False, "guest_boundary", "Guest Mode can only access public NovaTech Solutions information.",
                        **base)
    if subject.company_id != res.company_id:
        return Decision(False, "tenant_isolation", "Resource belongs to a different organization.", **base)
    if status is not None and status not in READABLE_STATUSES:
        return Decision(False, "lifecycle", f"Document is '{status}' and not available for retrieval.", **base)
    if grant_ids and res.id in grant_ids:
        return Decision(True, "explicit_grant", "Access granted by an approved, time-bound access request.", **base)
    if LEVELS[norm_level(subject.clearance)] < LEVELS[cls]:
        return Decision(False, "clearance",
                        f"Your clearance ({subject.clearance.title()}) is below the document's classification "
                        f"({cls.title()}).", **base)
    if not _matches(res.allowed_departments, subject.department):
        return Decision(False, "department_scope",
                        f"Document is limited to {', '.join(res.allowed_departments)}; you are in "
                        f"{subject.department}.", **base)
    if not _matches(getattr(res, "allowed_roles", None) or ["*"], subject.role_code, subject.role_name):
        return Decision(False, "role_scope", "Your role is not in the document's allowed roles.", **base)
    return Decision(True, "rbac", f"Clearance {subject.clearance.title()} ≥ {cls.title()}, department and role "
                                  f"in scope.", **base)


@dataclass
class _Rec:
    id: str
    company_id: str
    classification: str
    allowed_departments: list


def check_record(subject: Subject, rec, *, owner_ids: Iterable[str | None] = ()) -> Decision:
    """Record-level authorization for structured business data (projects, budgets, opportunities, POs, reviews…).

    Same rules as documents, plus an ownership rule: the people a record is *about* or *created by* (requester,
    assignee, project member) can read it within the guest boundary. Evaluated before data reaches any tool result.
    """
    r = _Rec(id=str(getattr(rec, "id", "")), company_id=rec.company_id,
             classification=getattr(rec, "classification", "INTERNAL") or "INTERNAL",
             allowed_departments=list(getattr(rec, "allowed_departments", None) or ["*"]))
    if not is_guest(subject) and subject.company_id == r.company_id and subject.user_id in {o for o in owner_ids if o}:
        return Decision(True, "ownership", "You are the owner / subject of this record.", r.id, norm_level(r.classification))
    return check_access(subject, r, status=None)


def active_grant_ids(db, subject: Subject) -> set[str]:
    if is_guest(subject):
        return set()
    from sqlalchemy import select
    from ..db.models import DocumentPermission
    now = datetime.now(timezone.utc)
    rows = db.scalars(select(DocumentPermission).where(
        DocumentPermission.company_id == subject.company_id, DocumentPermission.user_id == subject.user_id)).all()
    out = set()
    for g in rows:
        exp = g.expires_at if g.expires_at.tzinfo else g.expires_at.replace(tzinfo=timezone.utc)
        if exp > now:
            out.add(g.document_id)
    return out


# ---- Tool-level least privilege --------------------------------------------------------------

TOOL_POLICIES: dict[str, dict] = {
    # read-only knowledge & document tools (available to guests — results are PUBLIC-only for them)
    "search_knowledge":    {"permission": "documents:read",   "risk": "LOW",    "confirm": False},
    "search_policies":     {"permission": "documents:read",   "risk": "LOW",    "confirm": False},
    "get_leave_policy":    {"permission": "documents:read",   "risk": "LOW",    "confirm": False},
    "summarize_document":  {"permission": "documents:read",   "risk": "LOW",    "confirm": False},
    "compare_documents":   {"permission": "documents:read",   "risk": "LOW",    "confirm": False},
    "latest_updates":      {"permission": "documents:read",   "risk": "LOW",    "confirm": False},
    "get_department":      {"permission": "documents:read",   "risk": "LOW",    "confirm": False},
    "analytics_query":     {"permission": "analytics:read",   "risk": "LOW",    "confirm": False},
    "get_project":         {"permission": "projects:read",    "risk": "LOW",    "confirm": False},
    "search_repositories": {"permission": "repositories:read", "risk": "LOW",    "confirm": False},
    # personal / employee tools
    "get_employee":        {"permission": "directory:read",   "risk": "LOW",    "confirm": False},
    "get_my_projects":     {"permission": "projects:read_self", "risk": "LOW",  "confirm": False},
    "get_pending_tasks":   {"permission": "tasks:read_self",  "risk": "LOW",    "confirm": False},
    "get_my_requests":     {"permission": "requests:read_self", "risk": "LOW",  "confirm": False},
    "search_software":     {"permission": "it:catalog",       "risk": "LOW",    "confirm": False},
    "create_request":      {"permission": "requests:create",  "risk": "MEDIUM", "confirm": True},
    "search_documents":    {"permission": "documents:read",   "risk": "LOW",    "confirm": False},
    "get_leave_balance":   {"permission": "leave:read_self",  "risk": "LOW",    "confirm": False},
    "create_leave_request": {"permission": "leave:create",    "risk": "MEDIUM", "confirm": True},
    "create_it_ticket":    {"permission": "tickets:create",   "risk": "MEDIUM", "confirm": True},
    "draft_email":         {"permission": "email:draft",      "risk": "LOW",    "confirm": False},
    "send_email":          {"permission": "email:send",       "risk": "HIGH",   "confirm": True},
    "request_approval":    {"permission": "approvals:create", "risk": "MEDIUM", "confirm": True},
    "delete_document":     {"permission": "documents:delete", "risk": "CRITICAL", "confirm": True},
    # enterprise connector & skill tools
    "search_jira_issues":   {"permission": "projects:read",     "risk": "LOW",    "confirm": False},
    "create_jira_issue":    {"permission": "requests:create",   "risk": "MEDIUM", "confirm": True},
    "search_emails":        {"permission": "workspace:use",     "risk": "LOW",    "confirm": False},
    "search_teams_messages":{"permission": "workspace:use",     "risk": "LOW",    "confirm": False},
    "post_teams_message":   {"permission": "workspace:use",     "risk": "MEDIUM", "confirm": True},
    "lookup_entra_identity":{"permission": "directory:read",   "risk": "LOW",    "confirm": False},
    "scan_vulnerabilities": {"permission": "repositories:read", "risk": "LOW",    "confirm": False},
    "get_repo_architecture":{"permission": "repositories:read", "risk": "LOW",    "confirm": False},
    "generate_enterprise_report": {"permission": "documents:read", "risk": "LOW", "confirm": False},
}
# Friendly aliases used in docs/prompts (same implementation + policy).
TOOL_ALIASES = {"create_ticket": "create_it_ticket", "get_employee_info": "get_employee", "search_tasks": "get_pending_tasks",
                "get_project_status": "get_project"}


def check_tool(subject_perms: set[str], tool: str) -> Decision:
    tool = TOOL_ALIASES.get(tool, tool)
    pol = TOOL_POLICIES.get(tool)
    if not pol:
        return Decision(False, "unknown_tool", f"Tool '{tool}' is not registered.")
    if pol["permission"] not in subject_perms:
        return Decision(False, "tool_permission", f"Your role lacks '{pol['permission']}' required by {tool}.")
    return Decision(True, "tool_permission", f"'{pol['permission']}' granted by role.")
