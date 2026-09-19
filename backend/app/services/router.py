"""Query understanding for the multi-agent orchestrator.

Detects the question type, extracts entities (projects, employees, departments, documents, dates) and selects the
specialised agents that should handle the request. Used by the offline engine as its planner and by the OpenAI
engine for routing hints and the activity timeline. It never grants access — authorization is enforced by tools.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

from sqlalchemy import select

from .nlp import detect_flags, parse_date
from .retrieval import DEPT_WORDS

AGENTS = ["Knowledge Agent", "HR Agent", "IT Agent", "Project Agent", "Document Agent", "Analytics Agent",
          "Workflow Agent", "Productivity Agent"]

QUESTION_TYPES = {
    "knowledge": "Knowledge question", "employee": "Employee question", "analytics": "Analytics question",
    "document": "Document question", "workflow": "Workflow request", "multi_step": "Multi-step request",
    "restricted": "Restricted-data request", "general": "General", "productivity": "Productivity request",
    "project": "Project question",
}

_R = lambda p: re.compile(p, re.I)
RX = {
    "greeting": _R(r"^\s*(hi|hello|hey|good (morning|afternoon|evening)|namaste|thanks|thank you|ok(ay)?|cool)\b[\s!.?]*$"),
    "capabilities": _R(r"\b(what can you do|how can you help|who are you|what are you|help me get started|your capabilities|what do you know)\b"),
    "create": _R(r"\b(create|raise|open|log|file|submit|apply|book|request|need|get me|order|prepare|make)\b"),
    "ticket": _R(r"\b(ticket|incident|helpdesk|help desk|service desk request|it support request|support request)\b"),
    "device_problem": _R(r"\b(laptop|vpn|wifi|wi-fi|printer|monitor|keyboard|mouse|outlook|teams|email|password|screen|battery|computer)\b.{0,40}\b(broken|not working|isn'?t working|stopped|won'?t|keeps? (disconnecting|crashing|freezing)|crash\w*|fail\w*|dead|slow|locked|issue|problem)\b"),
    "access_req": _R(r"\b(request|need|get|want|apply for)\b.{0,25}\baccess\b|\baccess request\b"),
    "software_req": _R(r"\b(install|need|request|get|want)\b.{0,20}\b(licen[cs]e|software|app)\b|\bsoftware request\b"),
    "document_req": _R(r"\b(employment verification|experience|salary|address proof|relieving)\s+(letter|certificate)\b|\bdocument request\b"),
    "procurement_req": _R(r"\b(purchase request|purchase requisition|procurement request|raise a pr\b|buy|procure|order)\b.{0,60}"),
    "my_requests": _R(r"\b(status of my (requests?|tickets?|leave)|my (open )?(requests|tickets)|track my|where is my (request|ticket))\b"),
    "productivity": _R(r"\b(what should i (work on|focus on|do)( today)?|(my|work) priorities|prioriti[sz]e my|tasks? (that )?(need|require)s? my attention|what needs my attention|my (day|agenda|schedule)|today'?s (agenda|plan|meetings)|daily (summary|brief|briefing|plan)|action items|pending tasks|my (open |pending )?tasks|to-?dos?|meeting prep|prepare (me )?for (my )?(next |upcoming )?meeting|work summary)\b"),
    "my_projects": _R(r"\b(my projects?|projects? (i am|i'm) (on|assigned|working)|assigned projects?|projects? assigned to me|(am i|i am) assigned|my project manager|my assigned)\b"),
    "project_word": _R(r"\bprojects?\b"),
    "project_aspect": _R(r"\b(status|delayed|behind|late|overdue|deadlines?|members?|team|assigned|manages?|manager|risks?|milestones?|progress|health|budget|working on|current(ly)?)\b"),
    "analytics": _R(r"\b(how many|number of|count of|percentage|percent|%|share of|ratio|which (department|team|region|stage)s? (has|have)|highest|lowest|most|least|average|avg|total|sum of|breakdown|distribution|statistics|stats|by department|per department|by region|by stage|by status|by category|by location|headcount|utili[sz]ation)\b"),
    "hr": _R(r"\b(leave|leaves|vacation|pto|time off|holiday|benefits?|insurance|onboarding|joining|payroll|payslip|salary|attendance|working hours|performance review|appraisal|promotion|training|learning|recruit\w*|hiring|interview|referral|notice period|parental|maternity|paternity|employee information|my (profile|details)|hr\b|probation|resignation|exit)\b"),
    "it": _R(r"\b(vpn|laptop|password|software|install\w*|wi-?fi|printer|mfa|2fa|multi-factor|access management|it support|service desk|helpdesk|help desk|device|monitor|outlook|teams|zoom|slack|jira|escalat\w+|troubleshoot\w*|computer|phishing|security awareness|cloud|aws|azure|it (issue|policy|team))\b"),
    "document": _R(r"\b(summari[sz]e|summary of|tl;?dr|compare|comparison|differences? between|what changed|extract|classification of|this (document|doc|policy|file)|documents? (related|about|on|for)|find (all )?(documents|docs|files|policies)|list (the )?(documents|policies)|policy updates|latest (policy|policies|updates|announcements)|recent (policy|policies|updates)|which department owns|who owns (this|the) process|owns this)\b"),
    "directory": _R(r"\b(who is|who's|who are|contact (for|person)|email (address )?of|reports? to|my manager|my team|team members|direct reports|employee (id|nt-\d+)|nt-\d{3,6}|salary of|performance (rating|review) of|rating of|my (pan|bank|profile|details|phone( number)?|employee (id|record|information|info))|what'?s my (salary|pan|band|rating)|my (salary|compensation|band|performance rating))\b"),
    "department": _R(r"\b(department|dept|team)\b.{0,30}\b(head|lead|leads|who runs|what does|about|headcount|size|overview)\b|\b(head of|who leads|who runs) (the )?\w+"),
    "restricted": _R(r"\b(executive (compensation|salar\w*|pay)|ceo (salary|pay|compensation)|board (strategy|minutes|deck|meeting|paper)|acquisition|m&a|merger|project atlas|strategic plan|salaries of (all|everyone)|everyone'?s salar\w*|all salaries|security (configuration|baseline))\b"),
    "summary_of_projects": _R(r"\b(summary|summari[sz]e|overview)\b.{0,30}\bprojects?\b"),
    "steps": _R(r"\b(how (do|can|should) i|how to|steps?|process|procedure|what do i (need to )?do|what should i do|explain what i need)\b"),
}

DATASET_WORDS = [
    ("projects", r"\bprojects?\b"), ("employees", r"\b(employees?|people|staff|headcount|workforce)\b"),
    ("tickets", r"\b(it )?tickets?\b|\bincidents?\b"), ("opportunities", r"\b(opportunit\w+|pipeline|deals?)\b"),
    ("contracts", r"\bcontracts?\b"), ("customers", r"\bcustomers?|clients?\b"),
    ("purchase_orders", r"\b(purchase orders?|pos?)\b"), ("vendors", r"\b(vendors?|suppliers?)\b"),
    ("budgets", r"\bbudgets?\b"), ("expenses", r"\b(expenses?|claims?|reimbursements?)\b"),
    ("tasks", r"\btasks?\b"), ("leave_requests", r"\bleave requests?\b"),
]


@dataclass
class Understanding:
    text: str
    qtype: str = "knowledge"
    agents: list[str] = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    projects: list[tuple[str, str]] = field(default_factory=list)   # (id, name)
    employees: list[str] = field(default_factory=list)               # names / codes as written
    departments: list[str] = field(default_factory=list)
    doc_ids: list[str] = field(default_factory=list)
    dates: list = field(default_factory=list)
    self_ref: bool = False
    hits: dict = field(default_factory=dict)

    def has(self, key: str) -> bool:
        return bool(self.hits.get(key))

    def public(self) -> dict:
        return {"question_type": QUESTION_TYPES.get(self.qtype, self.qtype), "agents": self.agents,
                "entities": {"projects": [n for _, n in self.projects], "employees": self.employees,
                             "departments": self.departments, "documents": self.doc_ids}}


_PROJECT_CACHE: dict[str, list[tuple[str, str, str]]] = {}
_NAME_CACHE: dict[str, set[str]] = {}
_LOCK = threading.Lock()


def _project_names(db, company_id: str) -> list[tuple[str, str, str]]:
    if company_id not in _PROJECT_CACHE:
        from ..db.models import Project
        with _LOCK:
            rows = db.execute(select(Project.id, Project.name).where(Project.company_id == company_id)).all()
            _PROJECT_CACHE[company_id] = sorted(((pid, name, name.lower()) for pid, name in rows),
                                                key=lambda x: -len(x[2]))
    return _PROJECT_CACHE[company_id]


def _people_names(db, company_id: str) -> set[str]:
    if company_id not in _NAME_CACHE:
        from ..db.models import User
        with _LOCK:
            _NAME_CACHE[company_id] = {n.lower() for n in db.scalars(select(User.full_name).where(
                User.company_id == company_id, User.is_guest.is_(False))).all()}
    return _NAME_CACHE[company_id]


def find_projects(db, company_id: str, text: str) -> list[tuple[str, str]]:
    t = text.lower()
    out: list[tuple[str, str]] = []
    for m in re.finditer(r"\bprj-[a-z0-9]+\b", t):
        pid = m.group(0).upper()
        name = next((n for i, n, _ in _project_names(db, company_id) if i == pid), pid)
        out.append((pid, name))
    if out:
        return out
    names = _project_names(db, company_id)
    for pid, name, low in names:
        if len(low) >= 8 and low in t:
            out.append((pid, name))
            t = t.replace(low, " ")
    if not out:  # "project phoenix" / "phoenix project" → match a single project whose name has that word
        m = re.search(r"\bproject\s+([a-z][a-z0-9-]{2,})\b|\b([a-z][a-z0-9-]{2,})\s+project\b", t)
        word = (m.group(1) or m.group(2)) if m else None
        stop = {"the", "my", "this", "that", "each", "every", "any", "which", "what", "all", "our", "a", "current",
                "previous", "new", "management", "engineering", "active", "delayed", "assigned", "your", "his", "her",
                "their", "of", "for", "policy", "manager", "status", "one"}
        if word and word not in stop:
            cands = [(pid, name) for pid, name, low in names if re.search(rf"\b{re.escape(word)}\b", low)]
            exact = [c for c in cands if c[1].lower() in (f"project {word}",)]
            if exact or len(cands) == 1:
                out.append((exact or cands)[0])
            elif cands:
                out.append(sorted(cands, key=lambda c: len(c[1]))[0])
    return out


def find_people(db, company_id: str, text: str) -> list[str]:
    out = re.findall(r"\bNT-\d{3,6}\b", text, re.I)
    names = _people_names(db, company_id)
    for m in re.finditer(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", text):
        cand = f"{m.group(1)} {m.group(2)}"
        if cand.lower() in names:
            out.append(cand)
    return out


def understand(db, principal, text: str) -> Understanding:
    u = Understanding(text=text)
    t = text.strip()
    u.flags = detect_flags(t)
    u.hits = {k: bool(rx.search(t)) for k, rx in RX.items()}
    u.projects = find_projects(db, principal.company_id, t)
    u.employees = find_people(db, principal.company_id, t)
    low = t.lower()
    u.departments = sorted({d for w, d in DEPT_WORDS.items() if re.search(rf"\b{re.escape(w)}\b", low)
                            and not (w == "it" and not re.search(r"\bIT\b|\bit (department|team|support|policy)\b", t))
                            and not (w in ("product",) and "product manager" in low)})
    u.doc_ids = [d.upper() for d in re.findall(r"\b(?:DOC|ORB)-\d+\b", t, re.I)]
    d = parse_date(t)
    u.dates = [d] if d else []
    u.self_ref = bool(re.search(r"\b(my|me|mine|i am|i'm|am i|for me|i)\b", low))
    h, f = u.hits, u.flags
    agents: list[str] = []

    def add(a):
        if a not in agents:
            agents.append(a)

    if h["greeting"] or (h["capabilities"] and len(t) < 80):
        u.qtype = "general"
        u.agents = []
        return u

    # --- Workflow (state-changing) requests ---------------------------------------------------
    question = bool(re.search(r"^\s*(how|what|when|where|why|who|which|can i|do i|should i|is|are|explain|tell me)\b",
                              low))
    wants_action = h["create"] and not question
    wf = (f["delete"] or f["email"] or (f["leave_submit"] and not question) or (h["ticket"] and h["create"]) or
          (h["device_problem"] and not re.search(r"^\s*(how|what|why)\b", low)) or
          (wants_action and (h["access_req"] or h["software_req"] or h["document_req"] or h["procurement_req"])))
    if f["leave_balance"] or (f["leave_submit"] and re.search(r"\b(balance|check|remaining|left)\b", low)):
        add("HR Agent")
    if wf:
        if h["device_problem"] or h["it"]:
            add("IT Agent")
        add("Workflow Agent")
    if h["my_requests"]:
        add("Workflow Agent")

    # --- Productivity -------------------------------------------------------------------------
    if h["productivity"] or (f["tasks"] and not wf):
        add("Productivity Agent")

    # --- Projects ---------------------------------------------------------------------------
    if u.projects or h["my_projects"] or (h["project_word"] and (h["project_aspect"] or h["summary_of_projects"])):
        add("Project Agent")

    # --- Analytics --------------------------------------------------------------------------
    data_view = bool(re.search(r"\b(budgets?|pipeline|expenses|purchase orders|opportunities|headcount|contracts)\b", low)
                     and (u_depts_hint(low) or re.search(r"\b(show|give|what is|what's|list)\b", low))
                     and not re.search(r"\b(polic(y|ies)|procedure|process|guideline|how (do|can|to))\b", low))
    if (h["analytics"] or data_view) and any(re.search(p, low) for _, p in DATASET_WORDS) and not h["my_projects"]:
        if "Project Agent" in agents and not re.search(r"\b(how many|number of|percentage|percent|%|which department|"
                                                        r"average|total|breakdown|distribution|most|highest)\b", low):
            pass
        else:
            add("Analytics Agent")
            if "Project Agent" in agents and not u.projects:
                agents.remove("Project Agent")

    # --- Documents ----------------------------------------------------------------------------
    if h["document"] or u.doc_ids:
        doc_noun = bool(u.doc_ids or re.search(r"\b(document|doc|docs|policy|policies|guide|file|report|article|procedure|"
                                               r"handbook|notice|checklist|announcements?|updates)\b", low))
        # "…and summarize the main risks" after a project request is part of the project task, not a document task
        if doc_noun or not agents:
            add("Document Agent")

    # --- HR / IT knowledge ------------------------------------------------------------------
    if not wf and not agents:
        if h["directory"] or (u.employees and not h["hr"]):
            add("HR Agent")
        elif h["hr"] and not h["it"]:
            add("HR Agent")
        elif h["it"]:
            add("IT Agent")
        elif h["hr"]:
            add("HR Agent")
    if not agents and h["department"] and u.departments:
        add("Knowledge Agent")
    if not agents:
        add("Knowledge Agent")
    u.agents = agents

    if h["restricted"] or f.get("sensitive"):
        u.qtype = "restricted"
    elif len(agents) > 1 or re.search(r"\band (then |also )?(summari[sz]e|explain|tell|list|create|submit|draft)\b", low):
        u.qtype = "multi_step"
    elif "Workflow Agent" in agents:
        u.qtype = "workflow"
    elif "Analytics Agent" in agents:
        u.qtype = "analytics"
    elif "Document Agent" in agents:
        u.qtype = "document"
    elif "Productivity Agent" in agents:
        u.qtype = "productivity"
    elif "Project Agent" in agents:
        u.qtype = "project"
    elif "HR Agent" in agents and (h["directory"] or u.employees):
        u.qtype = "employee"
    else:
        u.qtype = "knowledge"
    return u


def u_depts_hint(low: str) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", low) for w in DEPT_WORDS if w != "it")


def parse_analytics(u: Understanding) -> dict:
    """Map a natural-language analytics question onto the analytics_query tool parameters."""
    low = u.text.lower()
    dataset = next((ds for ds, p in DATASET_WORDS if re.search(p, low)), "projects")
    if dataset == "projects" and re.search(r"\b(pipeline|opportunit)", low):
        dataset = "opportunities"
    group = ""
    m = re.search(r"\b(?:by|per|each|across|which)\s+(department|region|stage|status|category|location|priority|health|"
                  r"quarter|industry|tier|vendor|country|business unit|fiscal year)s?\b", low)
    if m:
        group = {"vendor": "category", "business unit": "business_unit", "fiscal year": "fiscal_year"}.get(m.group(1), m.group(1))
    elif re.search(r"\bwhich (department|team)s?\b|\bdepartment (with|has)\b", low):
        group = "department"
    status = ""
    if re.search(r"\b(delayed|behind schedule|behind|late|overdue|slipping)\b", low):
        status = "overdue" if dataset == "tasks" else "delayed"
    elif re.search(r"\b(approaching|upcoming|due soon|near(ing)?) (their |the )?deadlines?\b|\bdeadlines? (approaching|coming up)\b", low):
        status = "approaching_deadline"
    elif re.search(r"\b(complete|completed|finished|done)\b", low):
        status = "Completed"
    elif re.search(r"\b(active|in progress|ongoing|current(ly)?|working on|open)\b", low):
        status = {"tickets": "open", "tasks": "open", "opportunities": "open"}.get(dataset, "active")
    elif re.search(r"\bon hold\b", low):
        status = "On Hold"
    elif m2 := re.search(r"\bfy ?(\d{2})\b", low):
        status = f"fy{m2.group(1)}"
    metric = "count"
    if re.search(r"\b(percentage|percent|%|share of|proportion)\b", low):
        metric = "percentage"
    elif dataset == "budgets" or re.search(r"\b(utili[sz]ation|spent|spend)\b", low):
        metric = "utilization" if dataset == "budgets" else "sum"
    elif re.search(r"\b(total|sum|value|worth|amount)\b", low) and dataset in ("opportunities", "contracts",
                                                                                "purchase_orders", "expenses"):
        metric = "sum"
    elif re.search(r"\baverage progress|avg progress|average completion\b", low):
        metric = "avg_progress"
    elif not group and re.search(r"^\s*(which|list|show|what)\b", low) and dataset == "projects" and \
            not re.search(r"\b(how many|number of|count)\b", low):
        metric = "list"
    department = u.departments[0] if u.departments and group != "department" else ""
    return {"dataset": dataset, "metric": metric, "group_by": group, "status": status, "department": department}
