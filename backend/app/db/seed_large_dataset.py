"""Large synthetic enterprise dataset for NovaTech Solutions.

Generates thousands of internally consistent, relational, permission-aware records:

    Business units → Departments → Directors/Managers → Employees
    Projects (manager, members, milestones, risks, tech) → Tasks → Meetings
    Project charters + status reports + knowledge articles (documents → chunks → embeddings)
    HR (leave balances/requests, performance reviews, compensation), IT (software catalogue, assets, tickets),
    Finance (cost centres, budgets, expenses), Sales (products, customers, opportunities, contracts),
    Procurement (vendors, purchase orders), Workflow (service requests)

Every business record carries a classification (PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED) and department
scope, enforced by core.rbac before anything reaches a tool result or the LLM.

ALL DATA IS FICTIONAL. Names are random first/last-name combinations; no real personal information is used.

Usage
-----
Called automatically on first start (from db.seed.seed). To rebuild the demo database from scratch:

    cd backend
    python -m app.db.seed_large_dataset --reset            # drop + reseed everything
    SEED_SCALE=0.25 python -m app.db.seed_large_dataset --reset   # smaller dataset for quick experiments
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import insert, select

from .models import (Budget, BusinessUnit, Compensation, CostCenter, Contract, Customer, Document, Expense, ITAsset,
                     ITTicket, LeaveBalance, LeaveRequest, Location, Meeting, MeetingAttendee, Opportunity,
                     PerformanceReview, Product, Project, ProjectMember, PurchaseOrder, Role, ServiceRequest,
                     SoftwareItem, Task, User, Vendor, new_id)
from . import seed_banks as B

log = logging.getLogger("novatech.seed.large")
NT = "cmp_novatech"
EXEC = "Executive"
UNUSABLE_PASSWORD = "!synthetic-employee-no-login"  # verify_password() always fails for this value


def _scale() -> float:
    try:
        return max(0.05, min(3.0, float(os.environ.get("SEED_SCALE", "1.0"))))
    except ValueError:
        return 1.0


def _n(base: int, scale: float) -> int:
    return max(1, int(round(base * scale)))


def _weighted(rng: random.Random, items: list[tuple]):
    total = sum(w for *_, w in items)
    r = rng.uniform(0, total)
    acc = 0.0
    for it in items:
        acc += it[-1]
        if r <= acc:
            return it
    return items[-1]


def _slug(s: str) -> str:
    return re.sub(r"\W+", "-", s.lower()).strip("-")


def _money(v: float) -> str:
    if v >= 1e7:
        return f"₹{v / 1e7:.2f} crore"
    if v >= 1e5:
        return f"₹{v / 1e5:.1f} lakh"
    return f"₹{v:,.0f}"


class Gen:
    def __init__(self, db, core_users: dict, deps: dict, rng: random.Random, now: datetime):
        self.db, self.rng, self.now = db, rng, now
        self.today = now.date()
        self.core = core_users          # employee_code -> User (demo personas & core staff)
        self.deps = deps                # dept name -> Department
        self.scale = _scale()
        self.roles = {r.code: r for r in db.scalars(select(Role).where(Role.company_id == NT)).all()}
        self.people: list[dict] = []    # all NovaTech employees (core + generated) as light dicts
        self.by_dept: dict[str, list[dict]] = {}
        self.managers_by_dept: dict[str, list[dict]] = {}
        self.counts: dict[str, int] = {}
        self._emails: set[str] = {u.email for u in core_users.values()}

    # ------------------------------------------------------------------ helpers
    def bulk(self, model, rows: list[dict]):
        for i in range(0, len(rows), 1000):
            self.db.execute(insert(model), rows[i:i + 1000])
        self.counts[model.__tablename__] = self.counts.get(model.__tablename__, 0) + len(rows)

    def name(self) -> tuple[str, str]:
        while True:
            f, l = self.rng.choice(B.FIRST_NAMES), self.rng.choice(B.LAST_NAMES)
            base = f"{f.lower()}.{l.lower()}"
            email = f"{base}@novatech.demo"
            k = 2
            while email in self._emails:
                email = f"{base}{k}@novatech.demo"
                k += 1
            self._emails.add(email)
            return f"{f} {l}", email

    def date_between(self, a: date, b: date) -> date:
        if b <= a:
            return a
        return a + timedelta(days=self.rng.randint(0, (b - a).days))

    # ------------------------------------------------------------------ organisation
    def organisation(self):
        self.bulk(Location, [dict(id=i, company_id=NT, name=n, city=c, country=co, kind=k, address=a, timezone=tz)
                             for i, n, c, co, k, a, tz in B.LOCATIONS])
        heads = {"Engineering": "NT-0417", "Human Resources": "NT-0233", "Finance": "NT-0420", "Sales": "NT-0588",
                 "Marketing": "NT-0640", "Information Technology": "NT-0310", "Legal": "NT-0512",
                 "Operations": "NT-0701", "Product": "NT-0480", "Executive": "NT-0001"}
        bu_heads = {"BU-TECH": "NT-0007", "BU-GTM": "NT-0588", "BU-CORP": "NT-0233", "BU-OPS": "NT-0701",
                    "BU-EXEC": "NT-0001"}
        self.bulk(BusinessUnit, [dict(id=i, company_id=NT, name=n, description=d, head_id=self.core[bu_heads[i]].id)
                                 for i, n, d, _ in B.BUSINESS_UNITS])
        self.bu_of = {dep: n for _, n, _, deps in B.BUSINESS_UNITS for dep in deps}
        for name, dep in self.deps.items():
            dep.description = B.DEPT_DESCRIPTIONS.get(name, "")
            dep.business_unit = self.bu_of.get(name, "")
            dep.head_id = self.core[heads[name]].id if name in heads else None
            dep.location = "Chennai" if name == "Customer Success" else "Hyderabad"
        for u in self.core.values():
            u.skills = self.rng.sample(B.DEPT_PROFILES.get(u.department.name if u.department else "Engineering",
                                                           B.DEPT_PROFILES["Engineering"])["skills"], 3) \
                if u.department else []
        self.db.flush()

    # ------------------------------------------------------------------ people
    def employees(self, total: int):
        rng = self.rng
        code = 10001
        pw = UNUSABLE_PASSWORD
        rows: list[dict] = []
        for u in self.core.values():
            d = {"id": u.id, "name": u.full_name, "dept": u.department.name, "title": u.job_title,
                 "manager_id": u.manager_id, "is_manager": u.role.code in ("engineering_manager", "hr_manager",
                 "finance_manager", "sales_director", "marketing_manager", "legal_counsel", "operations_manager",
                 "security_admin", "senior_executive"), "code": u.employee_code, "location": u.location,
                 "clearance": u.clearance}
            self.people.append(d)
        head_of = {"Engineering": self.core["NT-0417"], "Human Resources": self.core["NT-0233"],
                   "Finance": self.core["NT-0420"], "Sales": self.core["NT-0588"], "Marketing": self.core["NT-0640"],
                   "Information Technology": self.core["NT-0310"], "Legal": self.core["NT-0512"],
                   "Operations": self.core["NT-0701"], "Product": self.core["NT-0480"],
                   "Executive": self.core["NT-0001"]}
        coo = self.core["NT-0007"]

        def person(dept, role_code, title, clearance, manager_id, is_mgr, joined_lo=2012):
            nonlocal code
            full, email = self.name()
            prof = B.DEPT_PROFILES[dept]
            loc = _weighted(rng, prof["loc"])[0]
            joined = self.date_between(date(joined_lo, 1, 1), self.today - timedelta(days=20))
            status = _weighted(rng, [("Active", 93), ("On Leave", 3), ("Notice Period", 2), ("Probation", 2)])[0]
            if (self.today - joined).days < 180:
                status = "Probation"
            uid = new_id("usr_")
            rows.append(dict(id=uid, company_id=NT, employee_code=f"NT-{code}", email=email, full_name=full,
                             password_hash=pw, department_id=self.deps[dept].id, role_id=self.roles[role_code].id,
                             job_title=title, clearance=clearance, manager_id=manager_id, location=loc, phone="",
                             pan_number="", bank_account="", joined_on=joined, is_active=True, is_demo_persona=False,
                             is_guest=False, employment_status=status,
                             skills=rng.sample(prof["skills"], min(len(prof["skills"]), rng.randint(3, 5)))))
            d = {"id": uid, "name": full, "dept": dept, "title": title, "manager_id": manager_id, "is_manager": is_mgr,
                 "code": f"NT-{code}", "location": loc, "clearance": clearance}
            code += 1
            self.people.append(d)
            return d

        # Customer Success needs a head (generated) reporting to the COO.
        cs_head = person("Customer Success", "cs_lead", "Head of Customer Success", "CONFIDENTIAL", coo.id, True, 2014)
        self.deps["Customer Success"].head_id = cs_head["id"]
        heads = {**{k: v.id for k, v in head_of.items()}, "Customer Success": cs_head["id"]}

        for dept, prof in B.DEPT_PROFILES.items():
            n = max(3, int(total * prof["share"]))
            n_mgr = max(1, n // 8)
            directors = []
            if prof["director"] and n >= 60:
                for _ in range(max(2, n // 150)):
                    directors.append(person(dept, prof["mgr"][0], prof["director"], "CONFIDENTIAL",
                                            coo.id if dept == "Engineering" else heads[dept], True, 2013))
            managers = []
            for _ in range(n_mgr):
                boss = rng.choice(directors)["id"] if directors else heads[dept]
                managers.append(person(dept, prof["mgr"][0], prof["mgr"][1], "CONFIDENTIAL", boss, True, 2014))
            self.managers_by_dept[dept] = directors + managers
            for _ in range(n - n_mgr - len(directors)):
                role_code, title, _w = _weighted(rng, prof["ic"])
                person(dept, role_code, title, "INTERNAL", rng.choice(managers)["id"], False)
        # Priya's core team grows with a few generated engineers so "my team" is realistic.
        priya = self.core["NT-0417"]
        eng_ics = [p for p in self.people if p["dept"] == "Engineering" and not p["is_manager"] and p["code"] >= "NT-1"
                   and p["id"] not in {u.id for u in self.core.values()}]
        for p in eng_ics[:6]:
            p["manager_id"] = priya.id
            for r in rows:
                if r["id"] == p["id"]:
                    r["manager_id"] = priya.id
        self.bulk(User, rows)
        for p in self.people:
            self.by_dept.setdefault(p["dept"], []).append(p)
        for dept, core_mgr in head_of.items():
            self.managers_by_dept.setdefault(dept, []).append(
                next(p for p in self.people if p["id"] == core_mgr.id))
        self.pid = {p["id"]: p for p in self.people}

    # ------------------------------------------------------------------ projects, tasks, meetings
    def projects(self, total: int):
        rng, today = self.rng, self.today
        shares = {"Engineering": 35, "Product": 8, "Information Technology": 10, "Operations": 10, "Sales": 7,
                  "Marketing": 8, "Customer Success": 7, "Finance": 5, "Human Resources": 5, "Legal": 3,
                  "Executive": 2}
        used: set[str] = set()
        projects: list[dict] = []
        members: list[dict] = []
        pnum = 2001

        def unique(name):
            base, k = name, 2
            while name in used:
                name = f"{base} — Phase {k}"
                k += 1
            used.add(name)
            return name

        def build(dept, name, cls, allowed, objective, theme):
            nonlocal pnum
            pid = f"PRJ-{pnum}"
            pnum += 1
            status = _weighted(rng, [("Planning", 12), ("In Progress", 50), ("On Hold", 6), ("Completed", 27),
                                     ("Cancelled", 5)])[0]
            if status == "Completed":
                start = self.date_between(date(2024, 4, 1), today - timedelta(days=200))
                deadline = self.date_between(start + timedelta(days=90), today - timedelta(days=5))
                progress = 100
            elif status == "Planning":
                start = self.date_between(today - timedelta(days=20), today + timedelta(days=60))
                deadline = start + timedelta(days=rng.randint(120, 400))
                progress = rng.randint(0, 10)
            elif status == "Cancelled":
                start = self.date_between(date(2024, 6, 1), today - timedelta(days=120))
                deadline = start + timedelta(days=rng.randint(120, 360))
                progress = rng.randint(10, 60)
            else:  # In Progress / On Hold
                start = self.date_between(today - timedelta(days=420), today - timedelta(days=30))
                deadline = self.date_between(today - timedelta(days=75), today + timedelta(days=330))
                elapsed = max(0.05, min(1.0, (today - start).days / max(1, (deadline - start).days)))
                progress = int(max(8, min(95, elapsed * 100 + rng.randint(-25, 12))))
            if status == "Completed":
                health = "Green"
            elif status in ("Cancelled", "On Hold"):
                health = "Amber" if status == "On Hold" else "Grey"
            elif deadline < today:
                health = "Red"
            elif (deadline - today).days < 45 and progress < 70:
                health = "Amber"
            else:
                health = _weighted(rng, [("Green", 70), ("Amber", 22), ("Red", 8)])[0]
            mgrs = self.managers_by_dept.get(dept) or self.by_dept[dept]
            mgr = rng.choice(mgrs)
            n_ms = rng.randint(3, 5)
            names = sorted(rng.sample(B.MILESTONE_BANK, n_ms), key=B.MILESTONE_BANK.index)
            span = max(30, (deadline - start).days)
            milestones = []
            for i, mname in enumerate(names):
                due = start + timedelta(days=int(span * (i + 1) / n_ms))
                frac = (i + 1) / n_ms
                if status == "Completed" or progress / 100 >= frac:
                    state = "done"
                elif due < today:
                    state = "missed" if status == "In Progress" else "slipped"
                elif (due - today).days < 30 and health != "Green":
                    state = "at risk"
                elif status == "In Progress" and (due - today).days < 60:
                    state = "on track"
                else:
                    state = "planned"
                milestones.append({"name": mname, "due": due.isoformat(), "state": state})
            risks = []
            for text, mit in rng.sample(B.RISK_BANK.get(dept, B.RISK_BANK["Engineering"]),
                                        min(len(B.RISK_BANK.get(dept, [])) or 1, rng.randint(1, 3))):
                sev = "High" if health == "Red" else _weighted(rng, [("High", 20), ("Medium", 55), ("Low", 25)])[0]
                risks.append({"risk": text, "severity": sev, "mitigation": mit, "owner": mgr["name"]})
            tech = rng.sample(B.TECH_STACK[dept], min(len(B.TECH_STACK[dept]), rng.randint(2, 5)))
            budget = round(rng.choice([5, 8, 12, 18, 25, 40, 60, 90, 150, 250, 400]) * 1e5 * rng.uniform(0.8, 1.2), -3)
            summary = (f"{name} is a {dept} initiative to {objective}. Status: {status.lower()}, "
                       f"{progress}% complete, health {health}.")
            if health == "Red" and status == "In Progress":
                summary += f" The project is behind schedule — the deadline of {deadline.strftime('%d %b %Y')} " \
                           f"{'has passed' if deadline < today else 'is at risk'}; top risk: {risks[0]['risk'].lower()}."
            elif health == "Amber":
                summary += f" Watch item: {risks[0]['risk'].lower()}."
            prio = _weighted(rng, [("Critical", 8), ("High", 27), ("Medium", 45), ("Low", 20)])[0]
            p = dict(id=pid, company_id=NT, name=name, department=dept, classification=cls,
                     allowed_departments=allowed, allowed_roles=["*"], status=status, health=health,
                     progress=progress, owner_name=mgr["name"], summary=summary, milestones=milestones,
                     updated_on=today - timedelta(days=rng.randint(0, 20)) if status in ("In Progress", "Planning")
                     else deadline, manager_id=mgr["id"], priority=prio, start_date=start, deadline=deadline,
                     budget_category=rng.choice(["Capex", "Opex", "Strategic", "Run-the-business", "Compliance"]),
                     budget_amount=budget, risks=risks, technologies=tech, business_unit=self.bu_of.get(dept, ""))
            p["_theme"] = theme
            projects.append(p)
            pool = [x for x in self.by_dept[dept] if x["id"] != mgr["id"]]
            team = rng.sample(pool, min(len(pool), rng.randint(3, 8)))
            other = [x for d, lst in self.by_dept.items() if d not in (dept, "Executive") for x in lst]
            team += rng.sample(other, rng.randint(0, 2))
            members.append(dict(project_id=pid, user_id=mgr["id"], company_id=NT, project_role="Project Manager",
                                allocation_pct=rng.choice([30, 40, 50])))
            roles = {"Engineering": ["Tech Lead", "Developer", "Developer", "QA", "SRE"],
                     "Product": ["Product Owner", "Designer", "Analyst"]}.get(dept, ["Analyst", "Contributor",
                                                                                      "Specialist"])
            seen = {mgr["id"]}
            for m in team:
                if m["id"] in seen:
                    continue
                seen.add(m["id"])
                members.append(dict(project_id=pid, user_id=m["id"], company_id=NT,
                                    project_role="Stakeholder" if m["dept"] != dept else rng.choice(roles),
                                    allocation_pct=rng.choice([20, 25, 50, 50, 75, 100])))
            p["_members"] = [mgr["id"]] + [m for m in seen if m != mgr["id"]]
            return p

        # public initiatives
        for name, dept, objective in B.PUBLIC_PROJECTS:
            build(dept, unique(name), "PUBLIC", ["*"], objective[0].lower() + objective[1:].rstrip("."), name)
        remaining = max(0, total - len(B.PUBLIC_PROJECTS))
        tot_share = sum(shares.values())
        for dept, sh in shares.items():
            themes, suffixes = B.PROJECT_THEMES[dept]
            for _ in range(int(remaining * sh / tot_share)):
                theme = rng.choice(themes)
                if rng.random() < 0.3:
                    name = f"Project {rng.choice(B.CODENAMES)} — {theme} {rng.choice(suffixes)}"
                else:
                    name = f"{theme} {rng.choice(suffixes)}"
                name = unique(name)
                if dept == "Executive":
                    cls = "RESTRICTED"
                elif dept in ("Legal", "Finance", "Human Resources") and rng.random() < 0.35:
                    cls = "CONFIDENTIAL"
                elif dept in ("Legal", "Finance"):
                    cls = _weighted(rng, [("INTERNAL", 70), ("CONFIDENTIAL", 22), ("RESTRICTED", 8)])[0]
                else:
                    cls = _weighted(rng, [("INTERNAL", 86), ("CONFIDENTIAL", 14)])[0]
                if cls == "INTERNAL":
                    allowed = ["*"] if rng.random() < 0.7 else sorted({dept, EXEC, rng.choice(list(shares))})
                elif cls == "CONFIDENTIAL":
                    allowed = sorted({dept, EXEC})
                else:
                    allowed = [EXEC] if dept == "Executive" else sorted({dept, EXEC})
                build(dept, name, cls, allowed, rng.choice(B.OBJECTIVES[dept]), theme)

        # Existing flagship projects: enrich + make the demo personas members.
        core_projects = {p.id: p for p in self.db.scalars(select(Project).where(Project.company_id == NT)).all()}
        rahul, priya, amit = self.core["NT-1042"], self.core["NT-0417"], self.core["NT-0766"]
        flagship = {"PRJ-PHX": (priya, date(2026, 1, 12), date(2026, 11, 30), "Critical",
                                [rahul, self.core["NT-1088"], self.core["NT-0932"], amit]),
                    "PRJ-ORN": (amit, date(2026, 2, 2), date(2026, 10, 15), "High",
                                [rahul, self.core["NT-0955"], self.core["NT-0480"]]),
                    "PRJ-NAI": (priya, date(2025, 9, 1), date(2026, 8, 12), "High",
                                [rahul, self.core["NT-1088"], self.core["NT-0480"]]),
                    "PRJ-HEL": (self.core["NT-0420"], date(2026, 5, 1), date(2027, 1, 31), "Medium",
                                [self.core["NT-0451"], self.core["NT-0701"]]),
                    "PRJ-ATL": (self.core["NT-0007"], date(2026, 7, 1), date(2026, 12, 15), "Critical",
                                [self.core["NT-0512"], self.core["NT-0001"]])}
        risk_text = {"PRJ-PHX": [{"risk": "Production database cut-over slipped two weeks due to a storage driver issue",
                                  "severity": "High", "mitigation": "Rehearse cut-over in staging; keep rollback plan",
                                  "owner": "Priya Reddy"},
                                 {"risk": "Dual-running cost is 6% over the cloud budget", "severity": "Medium",
                                  "mitigation": "Decommission legacy VMs within 30 days of cut-over",
                                  "owner": "Tanvi Shah"}],
                     "PRJ-ORN": [{"risk": "Push-notification SDK upgrade needed before public beta", "severity": "Medium",
                                  "mitigation": "Rahul Sharma to complete SDK update this sprint", "owner": "Amit Patel"}],
                     "PRJ-NAI": [{"risk": "UK data-residency requirements for 2027 launch", "severity": "Low",
                                  "mitigation": "Legal review of hosting options", "owner": "Priya Reddy"}],
                     "PRJ-HEL": [{"risk": "Reserved-instance commitment needs CFO sign-off", "severity": "Medium",
                                  "mitigation": "Present business case in October", "owner": "Kavya Iyer"}],
                     "PRJ-ATL": [{"risk": "Valuation expectations may diverge", "severity": "High",
                                  "mitigation": "Independent valuation advisor engaged", "owner": "Vikram Mehta"}]}
        for pid, (mgr, start, deadline, prio, team) in flagship.items():
            p = core_projects.get(pid)
            if not p:
                continue
            p.manager_id, p.start_date, p.deadline, p.priority = mgr.id, start, deadline, prio
            p.status = {"PRJ-NAI": "Completed"}.get(pid, "In Progress")
            p.owner_name = mgr.full_name
            p.risks = risk_text[pid]
            p.technologies = {"PRJ-PHX": ["Kubernetes", "PostgreSQL", "Terraform", "AWS"],
                              "PRJ-ORN": ["React Native", "Kotlin", "Swift", "Firebase"],
                              "PRJ-NAI": ["Python", "FastAPI", "pgvector", "OpenAI"],
                              "PRJ-HEL": ["AWS Cost Explorer", "Power BI"],
                              "PRJ-ATL": ["Virtual data room"]}[pid]
            p.budget_category = "Strategic"
            p.budget_amount = {"PRJ-PHX": 3.2e7, "PRJ-ORN": 1.4e7, "PRJ-NAI": 5.5e7, "PRJ-HEL": 6e6,
                               "PRJ-ATL": 2.5e7}[pid]
            p.business_unit = self.bu_of.get(p.department, "")
            members.append(dict(project_id=pid, user_id=mgr.id, company_id=NT, project_role="Project Manager",
                                allocation_pct=40))
            for t in team:
                members.append(dict(project_id=pid, user_id=t.id, company_id=NT, project_role="Developer"
                                    if t.department.name == "Engineering" else "Stakeholder", allocation_pct=50))
        # Rahul: also on two generated engineering projects, one of them behind schedule.
        eng_active = [p for p in projects if p["department"] == "Engineering" and p["status"] == "In Progress"
                      and p["classification"] == "INTERNAL"]
        delayed = next((p for p in eng_active if p["health"] == "Red"), None)
        if delayed is None and eng_active:
            delayed = eng_active[0]
        if delayed:
            delayed["deadline"] = today - timedelta(days=9)
            delayed["health"], delayed["progress"] = "Red", 64
            delayed["risks"][0]["severity"] = "High"
            delayed["summary"] = (f"{delayed['name']} is an Engineering initiative that is behind schedule: the "
                                  f"deadline of {delayed['deadline'].strftime('%d %b %Y')} has passed with 64% complete. "
                                  f"Top risk: {delayed['risks'][0]['risk'].lower()}.")
        on_track = next((p for p in eng_active if p is not delayed and p["health"] == "Green"), None)
        for p in [x for x in (delayed, on_track) if x]:
            members.append(dict(project_id=p["id"], user_id=rahul.id, company_id=NT, project_role="Developer",
                                allocation_pct=25))
            p["_members"].append(rahul.id)
        self.rahul_projects = [p["id"] for p in (delayed, on_track) if p]

        # dedupe membership rows
        seen, uniq = set(), []
        for m in members:
            k = (m["project_id"], m["user_id"])
            if k not in seen:
                seen.add(k)
                uniq.append(m)
        self.bulk(Project, [{k: v for k, v in p.items() if not k.startswith("_")} for p in projects])
        self.bulk(ProjectMember, uniq)
        self.projects_list = projects
        self.flagship = core_projects
        self.db.flush()

    def tasks_and_meetings(self):
        rng, today = self.rng, self.today
        tasks, meetings, attendees = [], [], []
        tn, mn = 1000, 1
        for p in self.projects_list:
            if p["status"] == "Cancelled":
                continue
            bank = B.TASK_BANK[p["department"]]
            for _ in range(rng.randint(4, 8)):
                ms = rng.choice(p["milestones"])
                title = rng.choice(bank).format(theme=p["_theme"], milestone=ms["name"].lower())
                assignee = rng.choice(p["_members"])
                due = self.date_between(p["start_date"], p["deadline"])
                if p["status"] == "Completed":
                    st = "done"
                elif p["status"] == "Planning":
                    st = "todo"
                elif due < today:
                    st = _weighted(rng, [("done", 65), ("in_progress", 20), ("blocked", 5), ("todo", 10)])[0]
                else:
                    st = _weighted(rng, [("todo", 45), ("in_progress", 35), ("blocked", 5), ("done", 15)])[0]
                pri = _weighted(rng, [("High", 25), ("Medium", 50), ("Low", 25)])[0]
                tasks.append(dict(id=f"TSK-{tn}", company_id=NT, assignee_id=assignee, title=title,
                                  project=p["name"], project_id=p["id"], priority=pri, status=st, due_date=due,
                                  description=f"Part of {p['name']} ({p['id']}), milestone '{ms['name']}'.",
                                  created_at=self.now - timedelta(days=rng.randint(1, 120))))
                tn += 1
            if p["status"] in ("In Progress", "Planning"):
                for _ in range(rng.randint(1, 3)):
                    day = today + timedelta(days=rng.randint(-7, 14))
                    if day.weekday() >= 5:
                        day += timedelta(days=2)
                    hour = rng.choice([10, 11, 12, 14, 15, 16, 17])
                    start = datetime(day.year, day.month, day.day, hour - 5, 30, tzinfo=timezone.utc)  # IST → UTC
                    kind = rng.choice(["Weekly sync", "Sprint planning", "Risk review", "Stakeholder demo",
                                       "Design review", "Status review"])
                    mid = f"MTG-{mn}"
                    mn += 1
                    meetings.append(dict(id=mid, company_id=NT, title=f"{p['name']} — {kind}",
                                         organizer_id=p["manager_id"], project_id=p["id"], starts_at=start,
                                         ends_at=start + timedelta(minutes=rng.choice([30, 45, 60])),
                                         location=rng.choice(["Teams", "Teams", "Hyderabad — Room Godavari",
                                                              "Bengaluru — Room Kaveri", "Pune — Room Tapti"]),
                                         agenda=f"{kind} for {p['name']}: progress ({p['progress']}%), "
                                                f"milestones, top risks and decisions needed."))
                    picks = rng.sample(p["_members"], min(len(p["_members"]), rng.randint(2, 6)))
                    for uid in set(picks) | {p["manager_id"]}:
                        attendees.append(dict(meeting_id=mid, user_id=uid))
        # Personal tasks & meetings for the demo personas (tied to their real projects).
        rahul = self.core["NT-1042"]
        for i, pid in enumerate(self.rahul_projects):
            p = next(x for x in self.projects_list if x["id"] == pid)
            for title, due, st, pri in ([("Close out overdue integration fixes", -4, "in_progress", "High"),
                                         ("Update risk log and mitigation plan", 1, "todo", "High")] if i == 0 else
                                        [("Implement pagination for the export API", 5, "todo", "Medium")]):
                tasks.append(dict(id=f"TSK-{tn}", company_id=NT, assignee_id=rahul.id,
                                  title=f"{title} — {p['_theme']}", project=p["name"], project_id=pid, priority=pri,
                                  status=st, due_date=today + timedelta(days=due), description=f"Assigned in {pid}.",
                                  created_at=self.now - timedelta(days=10)))
                tn += 1
        persona_meetings = [
            ("NT-1042", "Project Phoenix — Daily stand-up", 0, 10, "PRJ-PHX", ["NT-0417", "NT-1088", "NT-0932"]),
            ("NT-1042", "PR #482 review: Kubernetes readiness probes", 0, 15, "PRJ-PHX", ["NT-0766"]),
            ("NT-1042", "Project Orion — Public beta go/no-go", 1, 12, "PRJ-ORN", ["NT-0766", "NT-0480"]),
            ("NT-0417", "Engineering leadership sync", 0, 11, None, ["NT-0007", "NT-0766"]),
            ("NT-0417", "1:1 with Rahul Sharma", 0, 16, None, ["NT-1042"]),
            ("NT-0233", "Mid-year review calibration prep", 0, 14, None, ["NT-0268"]),
            ("NT-0007", "Portfolio review — delayed projects", 0, 15, None, ["NT-0417", "NT-0420", "NT-0701"]),
            ("NT-0310", "Quarterly access review kick-off", 0, 12, None, ["NT-0355"]),
        ]
        for owner, title, day, hour, pid, others in persona_meetings:
            d = today + timedelta(days=day)
            start = datetime(d.year, d.month, d.day, hour - 5, 30, tzinfo=timezone.utc)
            mid = f"MTG-{mn}"
            mn += 1
            meetings.append(dict(id=mid, company_id=NT, title=title, organizer_id=self.core[owner].id, project_id=pid,
                                 starts_at=start, ends_at=start + timedelta(minutes=30), location="Teams",
                                 agenda=f"{title}."))
            for c in {owner, *others}:
                attendees.append(dict(meeting_id=mid, user_id=self.core[c].id))
        self.bulk(Task, tasks)
        self.bulk(Meeting, meetings)
        self.bulk(MeetingAttendee, attendees)

    # ------------------------------------------------------------------ HR
    def hr(self):
        rng, today = self.rng, self.today
        core_ids = {u.id for u in self.core.values()}
        balances, requests, reviews, comp = [], [], [], []
        ln = 50001
        band_of = lambda t: ("L7" if re.search(r"Chief|Head|Director", t) else "L6" if "Manager" in t or "Lead" in t
                             or "Counsel" in t else "L5" if re.search(r"Staff|Senior|Principal", t) else "L3"
                             if re.search(r"Intern|Representative|Coordinator|Assistant", t) else "L4")
        salary = {"L3": (6e5, 1.2e6), "L4": (1.4e6, 2.4e6), "L5": (2.4e6, 3.8e6), "L6": (3.8e6, 6e6),
                  "L7": (6e6, 1.1e7)}
        ratings = [("Exceeds Expectations", 18), ("Meets Expectations", 66), ("Partially Meets", 12),
                   ("Below Expectations", 4)]
        for p in self.people:
            if p["id"] not in core_ids:
                balances.append(dict(id=new_id("lb_"), company_id=NT, user_id=p["id"], year=today.year,
                                     casual_total=12, casual_used=rng.randint(0, 9), sick_total=10,
                                     sick_used=rng.randint(0, 5), earned_total=18, earned_used=rng.randint(0, 12)))
            for _ in range(rng.choice([0, 0, 1, 1, 2])):
                start = today + timedelta(days=rng.randint(-150, 45))
                if start.weekday() >= 5:
                    start += timedelta(days=2)
                days = rng.choice([1, 1, 1, 2, 3, 5])
                lt = _weighted(rng, [("casual", 55), ("sick", 25), ("earned", 20)])[0]
                st = ("approved" if start < today else _weighted(rng, [("pending_manager_approval", 55),
                                                                       ("approved", 40), ("rejected", 5)])[0])
                if p["id"] == self.core["NT-1042"].id:
                    continue  # Rahul's leave history stays clean for the confirmation demo
                requests.append(dict(id=f"LR-{ln}", company_id=NT, user_id=p["id"], leave_type=lt, start_date=start,
                                     end_date=start + timedelta(days=days - 1), days=float(days),
                                     reason=rng.choice(["Family function", "Personal work", "Medical appointment",
                                                        "Vacation", "Festival travel", "Child's school event"]),
                                     status=st, created_at=self.now - timedelta(days=rng.randint(1, 60))))
                ln += 1
            band = band_of(p["title"])
            lo, hi = salary[band]
            comp.append(dict(id=new_id("comp_"), company_id=NT, user_id=p["id"], band=band,
                             base_salary=round(rng.uniform(lo, hi), -4), currency="INR",
                             effective_date=date(today.year, 4, 1), classification="CONFIDENTIAL",
                             allowed_departments=["Human Resources"]))
            for cycle in ("2025-Annual", "2026-Annual"):
                r = _weighted(rng, ratings)[0]
                mgr = self.pid.get(p["manager_id"]) if p["manager_id"] else None
                reviews.append(dict(id=new_id("rev_"), company_id=NT, user_id=p["id"], reviewer_id=p["manager_id"],
                                    cycle=cycle, rating=r, classification="CONFIDENTIAL",
                                    allowed_departments=["Human Resources"],
                                    summary=f"{cycle} review by {mgr['name'] if mgr else 'the Board'}: {r.lower()}; "
                                            f"strengths in {', '.join(rng.sample(['delivery', 'collaboration', 'customer focus', 'technical depth', 'ownership', 'communication'], 2))}."))
        self.bulk(LeaveBalance, balances)
        self.bulk(LeaveRequest, requests)
        self.bulk(Compensation, comp)
        self.bulk(PerformanceReview, reviews)

    # ------------------------------------------------------------------ IT
    def it(self):
        rng, today = self.rng, self.today
        self.bulk(SoftwareItem, [dict(id=f"SW-{i + 101}", company_id=NT, name=n, category=c, vendor=v, license_type=l,
                                      approval_required=a, platforms=pl, description=d, classification="INTERNAL",
                                      allowed_departments=["*"])
                                 for i, (n, c, v, l, a, pl, d) in enumerate(B.SOFTWARE)])
        models = [("Laptop", "Dell Latitude 7440", 40), ("Laptop", "Lenovo ThinkPad T14 Gen 4", 35),
                  ("Laptop", "Apple MacBook Pro 14 (M3)", 25)]
        assets, tickets = [], []
        an, tn = 30001, 70001
        issues = [(sw[0], iss) for sw in B.SOFTWARE[:30] for iss in B.IT_ISSUES]
        for p in self.people:
            typ, model, _ = _weighted(rng, models)
            bought = self.date_between(date(2022, 1, 1), today - timedelta(days=30))
            assets.append(dict(id=f"NT-LT-{an}", company_id=NT, asset_type=typ, model=model, assigned_to=p["id"],
                               purchased_on=bought, warranty_until=bought + timedelta(days=3 * 365),
                               status="In use"))
            an += 1
            if rng.random() < 0.4:
                assets.append(dict(id=f"NT-MN-{an}", company_id=NT, asset_type="Monitor",
                                   model=rng.choice(["Dell P2723DE 27\"", "LG 27UP850 27\""]), assigned_to=p["id"],
                                   purchased_on=bought, warranty_until=bought + timedelta(days=3 * 365),
                                   status="In use"))
                an += 1
            for _ in range(rng.choice([0, 0, 1, 1, 2])):
                if rng.random() < 0.35:
                    title, cat, steps = rng.choice(B.DEVICE_TOPICS)
                    pri = "P2" if "Lost" in title or "Keyboard" in title else "P3"
                else:
                    sw, (issue, cat, pri, _steps) = rng.choice(issues)
                    title = f"{sw} {issue}"
                created = self.now - timedelta(days=rng.randint(0, 330), hours=rng.randint(0, 20))
                st = "resolved" if (self.now - created).days > 10 else _weighted(
                    rng, [("open", 35), ("in_progress", 35), ("resolved", 30)])[0]
                tickets.append(dict(id=f"INC-{tn}", company_id=NT, user_id=p["id"], title=title[:200],
                                    description=f"Reported by {p['name']}: {title}.", priority=pri, category=cat,
                                    status=st, created_at=created))
                tn += 1
        self.bulk(ITAsset, assets)
        self.bulk(ITTicket, tickets)

    # ------------------------------------------------------------------ Finance
    def finance(self, n_expenses: int):
        rng, today = self.rng, self.today
        ccs, budgets, expenses = [], [], []
        cats = {"Engineering": ["Personnel", "Cloud & Infrastructure", "Software Licences", "Travel", "Training"],
                "Product": ["Personnel", "Research", "Software Licences", "Travel"],
                "Information Technology": ["Personnel", "Hardware", "Software Licences", "Security Services"],
                "Human Resources": ["Personnel", "Recruitment", "Learning & Development", "Wellness"],
                "Finance": ["Personnel", "Audit & Advisory", "Software Licences"],
                "Sales": ["Personnel", "Travel", "Client Entertainment", "Partner Incentives"],
                "Marketing": ["Personnel", "Campaigns", "Events", "Agencies"],
                "Legal": ["Personnel", "External Counsel", "Compliance Tools"],
                "Operations": ["Personnel", "Facilities", "Utilities", "Travel Desk"],
                "Customer Success": ["Personnel", "Support Tools", "Training", "Travel"],
                "Executive": ["Personnel", "Board & Governance", "Strategic Advisory"]}
        for dept, dep in self.deps.items():
            code = dep.code
            n_cc = 1 + (2 if dept in ("Engineering", "Sales", "Operations", "Customer Success") else 0)
            for i in range(n_cc):
                ccs.append(dict(id=f"CC-{code}-{i + 1:02d}", company_id=NT,
                                name=f"{dept} — {['Core', 'Platform', 'Regional', 'Delivery'][i % 4]}", department=dept,
                                owner_id=dep.head_id, classification="INTERNAL", allowed_departments=["*"]))
            for fy, quarters in (("FY26", [date(2025, 4, 1), date(2025, 7, 1), date(2025, 10, 1), date(2026, 1, 1)]),
                                 ("FY27", [date(2026, 4, 1), date(2026, 7, 1), date(2026, 10, 1), date(2027, 1, 1)])):
                for qi, qstart in enumerate(quarters):
                    for cat in cats.get(dept, ["Personnel"]):
                        size = {"Personnel": 8e7, "Cloud & Infrastructure": 3e7}.get(cat, 6e6)
                        size *= {"Engineering": 2.5, "Sales": 1.2, "Customer Success": 1.0}.get(dept, 0.5)
                        alloc = round(size * rng.uniform(0.7, 1.3), -4)
                        qend = qstart + timedelta(days=90)
                        if qend <= today:
                            spent = alloc * rng.uniform(0.82, 1.12)
                        elif qstart <= today:
                            spent = alloc * ((today - qstart).days / 91) * rng.uniform(0.85, 1.15)
                        else:
                            spent = 0.0
                        budgets.append(dict(id=f"BGT-{code}-{fy}-Q{qi + 1}-{cat[:4].upper()}", company_id=NT,
                                            department=dept, cost_center=f"CC-{code}-01", fiscal_year=fy,
                                            quarter=f"Q{qi + 1}", category=cat, allocated=alloc,
                                            spent=round(spent, -3), classification="CONFIDENTIAL",
                                            allowed_departments=sorted({dept, "Finance", EXEC})))
        en = 90001
        for _ in range(n_expenses):
            p = rng.choice(self.people)
            cat, lo, hi = rng.choice([("Travel", 3000, 60000), ("Meals", 300, 4000), ("Client Entertainment", 2000, 25000),
                                      ("Training", 2000, 45000), ("Internet", 1000, 1000), ("Equipment", 1500, 20000)])
            spent_on = today - timedelta(days=rng.randint(0, 300))
            st = "Paid" if (today - spent_on).days > 20 else _weighted(
                rng, [("Submitted", 40), ("Approved", 35), ("Paid", 20), ("Rejected", 5)])[0]
            expenses.append(dict(id=f"EXP-{en}", company_id=NT, user_id=p["id"], department=p["dept"], category=cat,
                                 amount=float(rng.randint(lo, hi)), spent_on=spent_on, status=st,
                                 description=f"{cat} — {rng.choice(['customer visit', 'team offsite', 'conference', 'monthly claim', 'workshop', 'project travel'])}",
                                 classification="CONFIDENTIAL", allowed_departments=["Finance", EXEC]))
            en += 1
        self.bulk(CostCenter, ccs)
        self.bulk(Budget, budgets)
        self.bulk(Expense, expenses)

    # ------------------------------------------------------------------ Sales
    def sales(self, n_customers: int, n_opps: int, n_contracts: int):
        rng, today = self.rng, self.today
        self.bulk(Product, [dict(id=i, company_id=NT, name=n, category=c, description=d, list_price=float(pr),
                                 classification="PUBLIC", allowed_departments=["*"])
                            for i, n, c, d, pr in B.PRODUCTS])
        sales_people = [p for p in self.by_dept["Sales"]]
        customers, used = [], set()
        for i in range(n_customers):
            while True:
                name = f"{rng.choice(B.CUSTOMER_PREFIX)} {rng.choice(B.CUSTOMER_SUFFIX)}"
                if name not in used:
                    used.add(name)
                    break
            ref = rng.random() < 0.07
            customers.append(dict(id=f"CUST-{5001 + i}", company_id=NT, name=name,
                                  industry=rng.choice(B.SALES_INDUSTRIES), region=rng.choice(B.REGIONS),
                                  tier=_weighted(rng, [("Strategic", 10), ("Enterprise", 30), ("Mid-market", 60)])[0],
                                  account_owner_id=rng.choice(sales_people)["id"],
                                  customer_since=self.date_between(date(2015, 1, 1), today - timedelta(days=30)),
                                  is_reference=ref, classification="PUBLIC" if ref else "INTERNAL",
                                  allowed_departments=["*"] if ref else ["Sales", "Marketing", "Customer Success",
                                                                         "Finance", "Legal", EXEC]))
        opps = []
        stages = [("Prospecting", 10, 18), ("Qualification", 20, 20), ("Solution Design", 40, 18),
                  ("Proposal", 60, 15), ("Negotiation", 80, 10), ("Closed Won", 100, 12), ("Closed Lost", 0, 7)]
        for i in range(n_opps):
            c = rng.choice(customers)
            prod = rng.choice(B.PRODUCTS)
            stage, prob, _ = _weighted(rng, stages)
            close = today + timedelta(days=rng.randint(-200, -1)) if stage.startswith("Closed") else \
                today + timedelta(days=rng.randint(5, 270))
            opps.append(dict(id=f"OPP-{8001 + i}", company_id=NT, customer_id=c["id"], product_id=prod[0],
                             name=f"{c['name']} — {prod[1]} {rng.choice(['expansion', 'new logo', 'renewal', 'pilot', 'upgrade'])}",
                             stage=stage, amount=round(prod[4] * rng.uniform(0.5, 6), -3), probability=prob,
                             close_date=close, owner_id=c["account_owner_id"], region=c["region"],
                             classification="CONFIDENTIAL", allowed_departments=["Sales", "Finance", EXEC]))
        contracts = []
        for i in range(n_contracts):
            c = rng.choice(customers)
            start = self.date_between(date(2023, 1, 1), today - timedelta(days=10))
            end = start + timedelta(days=365 * rng.choice([1, 2, 3]))
            st = "Active" if end > today else rng.choice(["Expired", "Renewed"])
            if st == "Active" and (end - today).days < 90:
                st = "Renewal Due"
            contracts.append(dict(id=f"CTR-{3001 + i}", company_id=NT, customer_id=c["id"],
                                  title=f"{c['name']} — {rng.choice(['Master Subscription Agreement', 'Order Form', 'Services SOW', 'Support Renewal'])}",
                                  value=round(rng.uniform(8e5, 3e7), -3), start_date=start, end_date=end, status=st,
                                  classification="CONFIDENTIAL", allowed_departments=["Sales", "Legal", "Finance", EXEC]))
        self.bulk(Customer, customers)
        self.bulk(Opportunity, opps)
        self.bulk(Contract, contracts)
        self.customers = customers

    # ------------------------------------------------------------------ Procurement
    def procurement(self, n_vendors: int, n_pos: int):
        rng, today = self.rng, self.today
        vendors, used = [], set()
        for i in range(n_vendors):
            while True:
                name = f"{rng.choice(B.VENDOR_WORDS)} {rng.choice(B.VENDOR_TAILS)}"
                if name not in used:
                    used.add(name)
                    break
            vendors.append(dict(id=f"VEN-{4001 + i}", company_id=NT, name=name,
                                category=rng.choice(B.VENDOR_CATEGORIES),
                                country=_weighted(rng, [("India", 75), ("Singapore", 10), ("United Kingdom", 8),
                                                        ("United States", 7)])[0],
                                rating=round(rng.uniform(2.8, 4.9), 1),
                                status=_weighted(rng, [("Approved", 80), ("Preferred", 12), ("Under review", 5),
                                                       ("Blocked", 3)])[0],
                                onboarded_on=self.date_between(date(2016, 1, 1), today - timedelta(days=15)),
                                classification="INTERNAL", allowed_departments=["*"]))
        pos = []
        for i in range(n_pos):
            v = rng.choice(vendors)
            p = rng.choice(self.people)
            amt = round(rng.choice([0.3, 0.6, 1, 2, 4, 8, 15, 30, 60]) * 1e5 * rng.uniform(0.7, 1.3), -2)
            created = today - timedelta(days=rng.randint(0, 360))
            st = _weighted(rng, [("Draft", 5), ("Pending Approval", 15), ("Approved", 20), ("Ordered", 20),
                                 ("Received", 25), ("Closed", 12), ("Rejected", 3)])[0]
            pos.append(dict(id=f"PO-{60001 + i}", company_id=NT, vendor_id=v["id"], requester_id=p["id"],
                            department=p["dept"], category=v["category"],
                            description=f"{v['category']} — {rng.choice(['annual renewal', 'new purchase', 'additional licences', 'quarterly services', 'replacement stock', 'project engagement'])}",
                            amount=amt, status=st, created_on=created, classification="CONFIDENTIAL",
                            allowed_departments=sorted({p["dept"], "Operations", "Finance", EXEC})))
        self.bulk(Vendor, vendors)
        self.bulk(PurchaseOrder, pos)
        self.vendors = vendors

    # ------------------------------------------------------------------ service requests
    def service_requests(self, n: int):
        rng = self.rng
        rows = []
        kinds = [("access", "Access to {x}", ["Salesforce Sales Cloud", "AWS staging account", "Power BI finance workspace", "Jira project NOVA", "VPN — standard"]),
                 ("software", "Software request: {x}", [s[0] for s in B.SOFTWARE if s[4]]),
                 ("document", "Document request: {x}", ["Employment verification letter", "Salary certificate", "Address proof letter", "Experience letter"]),
                 ("procurement", "Purchase request: {x}", ["2 external monitors", "Conference room camera", "Team offsite venue", "Training vouchers"])]
        for i in range(n):
            p = rng.choice(self.people)
            k, tpl, xs = rng.choice(kinds)
            created = self.now - timedelta(days=rng.randint(0, 120))
            st = "completed" if (self.now - created).days > 14 else _weighted(
                rng, [("submitted", 30), ("in_review", 30), ("approved", 25), ("completed", 10), ("rejected", 5)])[0]
            rows.append(dict(id=f"REQ-{20001 + i}", company_id=NT, requester_id=p["id"], request_type=k,
                             title=tpl.format(x=rng.choice(xs)), details={"justification": "Needed for current work"},
                             status=st, approver_id=p["manager_id"], created_at=created, updated_at=created))
        rahul, priya = self.core["NT-1042"], self.core["NT-0417"]
        rows.append(dict(id="REQ-19991", company_id=NT, requester_id=rahul.id, request_type="access",
                         title="Access to AWS staging account", details={"justification": "Phoenix cut-over rehearsal"},
                         status="in_review", approver_id=priya.id, created_at=self.now - timedelta(days=2),
                         updated_at=self.now - timedelta(days=1)))
        rows.append(dict(id="REQ-19992", company_id=NT, requester_id=rahul.id, request_type="software",
                         title="Software request: JetBrains PyCharm", details={"justification": "Python services"},
                         status="approved", approver_id=priya.id, created_at=self.now - timedelta(days=6),
                         updated_at=self.now - timedelta(days=4)))
        self.bulk(ServiceRequest, rows)

    # ------------------------------------------------------------------ Knowledge base documents
    def documents(self, kb_scale: float):
        rng, today = self.rng, self.today
        docs: list[dict] = []
        n = [5000]
        dept_heads = {name: dep.head_id for name, dep in self.deps.items()}

        def add(title, doc_type, dept, cls, allowed, content, eff: date, family=None, version="1.0", tags=(),
                project_id=None, owner_id=None):
            n[0] += 1
            did = f"DOC-{n[0]}"
            ts = datetime(eff.year, eff.month, eff.day, 4, 0, tzinfo=timezone.utc)
            upd = ts + timedelta(days=rng.randint(0, 40)) if eff < today - timedelta(days=45) else ts
            docs.append(dict(id=did, company_id=NT, title=title[:300],
                             filename=re.sub(r"[^\w .()-]", "", title)[:90] + ".pdf", doc_type=doc_type,
                             department=dept, classification=cls, allowed_departments=list(allowed),
                             allowed_roles=["*"], owner_id=owner_id or dept_heads.get(dept),
                             family_key=family or f"kb-{did.lower()}", version=version, effective_date=eff,
                             status="published", content=content.strip(), summary=content.strip().split("\n")[0][:240],
                             source="synthetic", tags=list(tags), project_id=project_id, created_at=ts,
                             updated_at=min(upd, self.now), security_flags=[]))
            return did

        # 1) project charters + status reports
        for p in self.projects_list:
            mgr = self.pid.get(p["manager_id"], {"name": p["owner_name"]})
            members = [self.pid[m]["name"] for m in p["_members"][1:6] if m in self.pid]
            ms = "\n".join(f"- {m['name']} — due {m['due']} ({m['state']})" for m in p["milestones"])
            rk = "\n".join(f"- {r['risk']} (severity {r['severity']}). Mitigation: {r['mitigation']}."
                           for r in p["risks"])
            content = f"""
{p['name']} ({p['id']}) — Project Charter.
Sponsor department: {p['department']} ({p['business_unit']}). Project manager: {mgr['name']}. Priority: {p['priority']}.
Objective: {p['summary'].split('. Status')[0].split(' initiative to ')[-1] if ' initiative to ' in p['summary'] else p['summary']}.
Timeline: starts {p['start_date'].strftime('%d %b %Y')}, target completion {p['deadline'].strftime('%d %b %Y')}. Current status: {p['status']} ({p['progress']}% complete, health {p['health']}).

Milestones:
{ms}

Technologies and tools: {', '.join(p['technologies'])}.

Key risks:
{rk}

Team: {len(p['_members'])} members including {', '.join(members) if members else mgr['name']}.
Budget category: {p['budget_category']}. Detailed budget figures are held by Finance.
Success measures: milestones delivered on time, adoption by target users, and no High security findings at go-live.
"""
            add(f"{p['name']} — Project Charter", "Project Charter", p["department"], p["classification"],
                p["allowed_departments"], content, p["start_date"], family=f"charter-{p['id'].lower()}",
                tags=[p["department"], "project", p["status"]], project_id=p["id"], owner_id=p["manager_id"])
            if p["status"] in ("In Progress", "On Hold"):
                rep_date = today - timedelta(days=rng.randint(1, 14))
                next_ms = next((m for m in p["milestones"] if m["state"] not in ("done",)), p["milestones"][-1])
                reason = {"Green": "Work is on plan.", "Amber": f"Watch item: {p['risks'][0]['risk']}.",
                          "Red": f"Behind schedule. {p['risks'][0]['risk']}.", "Grey": "Paused."}[p["health"]]
                add(f"{p['name']} — Status Report {rep_date.strftime('%B %Y')}", "Status Report", p["department"],
                    p["classification"], p["allowed_departments"], f"""
Status report for {p['name']} ({p['id']}) as of {rep_date.strftime('%d %b %Y')}.
Overall health: {p['health']}. Progress: {p['progress']}%. Status: {p['status']}. Deadline: {p['deadline'].strftime('%d %b %Y')}.
Summary: {reason}
Next milestone: {next_ms['name']} due {next_ms['due']} ({next_ms['state']}).
Top risks: {'; '.join(r['risk'] + ' — ' + r['severity'] for r in p['risks'])}.
Decisions needed: {'Approve schedule re-baseline and additional capacity.' if p['health'] == 'Red' else 'None this period.'}
Prepared by {mgr['name']}.
""", rep_date, family=f"status-{p['id'].lower()}", tags=[p["department"], "status report"], project_id=p["id"],
                    owner_id=p["manager_id"])

        # 2) IT knowledge base
        it_owner = self.core["NT-0355"].id
        for sw in B.SOFTWARE:
            for issue, cat, pri, steps in rng.sample(B.IT_ISSUES, k=max(1, int(round(4 * kb_scale)))):
                body = "\n".join(f"{i + 1}. {s.format(sw=sw[0])}" for i, s in enumerate(steps))
                add(f"{sw[0]}: {issue} — troubleshooting", "Knowledge Article", "Information Technology", "INTERNAL",
                    ["*"], f"""
Applies to: {sw[0]} ({sw[1]}) on {', '.join(sw[5])}.
Symptom: {sw[0]} {issue}.
Resolution steps:
{body}
If the steps do not help, raise an IT ticket in the {cat} category with priority {pri}. The IT Service Desk (Information Technology department) owns this article.
""", self.date_between(date(2025, 6, 1), today), tags=["IT", sw[1], cat], owner_id=it_owner)
        for title, cat, steps in B.DEVICE_TOPICS:
            for loc in rng.sample(["Hyderabad", "Bengaluru", "Pune", "Chennai", "Singapore", "London"],
                                  k=max(1, int(3 * kb_scale))):
                body = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
                add(f"{title} ({loc} office)", "Knowledge Article", "Information Technology", "INTERNAL", ["*"], f"""
{title} — guidance for employees in the {loc} office.
Steps:
{body}
Local IT desk: {loc} office, ground floor, 09:00–18:00. Raise a {cat} ticket if the issue continues.
""", self.date_between(date(2025, 3, 1), today), tags=["IT", cat, loc], owner_id=it_owner)

        # 3) HR, Finance, Procurement, Legal, Security knowledge
        variants = ["All employees", "India employees", "Singapore addendum", "UK addendum", "Managers' guide"]
        topic_sets = [("Human Resources", B.HR_TOPICS, "HR"), ("Finance", B.FINANCE_TOPICS, "Finance"),
                      ("Operations", B.PROCUREMENT_TOPICS, "Procurement"), ("Legal", B.LEGAL_TOPICS, "Legal"),
                      ("Information Technology", B.SECURITY_TOPICS, "Security")]
        for dept, topics, label in topic_sets:
            for topic, text in topics:
                for v in rng.sample(variants, k=max(1, int(round(3 * kb_scale)))):
                    extra = {"Managers' guide": "Managers: review requests within 2 working days and consult your HR "
                                                "business partner for exceptions.",
                             "Singapore addendum": "For Singapore employees local statutory rules apply where they are "
                                                   "more favourable; contact the Singapore People team.",
                             "UK addendum": "For UK employees local statutory rules apply where they are more "
                                            "favourable; contact the London People team.",
                             "India employees": "Applies to employees on Indian payroll.",
                             "All employees": "Applies to all NovaTech employees."}[v]
                    doc_type = "FAQ" if label in ("HR", "Security") else "Guideline"
                    title = (f"{label} FAQ: {topic} ({v})" if doc_type == "FAQ" else f"{topic} — {label} guideline ({v})")
                    add(title, doc_type, dept, "INTERNAL", ["*"], f"""
{topic} — {label} guidance ({v}).
{text}
{extra}
Owner: {dept} department. Questions can be raised through the NovaTech Solutions assistant.
""", self.date_between(date(2025, 1, 15), today), family=f"{label.lower()}-{_slug(topic)}-{_slug(v)}",
                        tags=[label, topic])

        # 4) Department processes (INTERNAL, scoped to department + Executive for some)
        for dept, procs in B.DEPT_PROCESSES.items():
            for proc in procs:
                for team in rng.sample(["core team", "India", "APAC", "platform team", "shared services"],
                                       k=max(1, int(round(2 * kb_scale)))):
                    scoped = rng.random() < 0.4
                    add(f"{dept}: {proc} ({team})", "Process", dept, "INTERNAL",
                        sorted({dept, EXEC}) if scoped else ["*"], f"""
{proc} for the {dept} {team}.
1. Raise or pick up the request in the team queue and confirm the owner.
2. Follow the {proc.lower()} checklist and record decisions in the workspace.
3. Get the required approval from the {dept} manager before completion.
4. Communicate the outcome to stakeholders and update the knowledge base.
Process owner: {dept} department. Review cycle: every 6 months.
""", self.date_between(date(2025, 2, 1), today), tags=[dept, "process"])

        # 5) Sales: playbooks, battlecards (confidential), case studies (public)
        for prod in B.PRODUCTS:
            for ind in rng.sample(B.SALES_INDUSTRIES, k=max(1, int(round(5 * kb_scale)))):
                add(f"{prod[1]} sales playbook — {ind}", "Playbook", "Sales", "INTERNAL",
                    ["Sales", "Marketing", "Customer Success", EXEC], f"""
Selling {prod[1]} to {ind} customers.
Customer pains: manual processes, compliance pressure and slow service in {ind.lower()}.
Value: {prod[3]}
Discovery questions: How many approvals do you process monthly? Which systems must integrate? Who owns compliance?
Proof points: reference customers in {ind.lower()} and a 30-day pilot plan.
""", self.date_between(date(2025, 4, 1), today), tags=["Sales", ind, prod[1]])
            add(f"{prod[1]} competitive battlecard", "Battlecard", "Sales", "CONFIDENTIAL", ["Sales", EXEC], f"""
{prod[1]} battlecard (Confidential — Sales only).
Where we win: permission-aware AI, faster implementation and local support.
Pricing guidance: list price {_money(prod[4])} per year; discounts above 15% need deal-desk approval.
Landmines to set: ask competitors about data residency and audit logs.
""", self.date_between(date(2026, 1, 1), today), family=f"battlecard-{prod[0].lower()}", tags=["Sales", "battlecard"])
        for c in [x for x in self.customers if x["is_reference"]]:
            prod = rng.choice(B.PRODUCTS[:5])
            add(f"Customer story: {c['name']} and {prod[1]}", "Case Study", "Marketing", "PUBLIC", ["*"], f"""
{c['name']}, a {c['industry'].lower()} company in {c['region']}, uses {prod[1]} to modernise its operations.
Challenge: slow manual approvals and fragmented service channels.
Result: {rng.randint(20, 45)}% faster turnaround and {rng.randint(10, 30)}% lower operating cost within six months.
""", self.date_between(date(2025, 1, 1), today), tags=["case study", c["industry"]])

        # 6) Announcements
        months = [(today - timedelta(days=30 * i)) for i in range(0, 18)]
        for i in range(max(10, int(150 * kb_scale))):
            title_t, cls, dept, body_t = rng.choice(B.ANNOUNCEMENT_TEMPLATES)
            m = rng.choice(months)
            vals = dict(month=m.strftime("%B %Y"), ver=f"{rng.randint(6, 9)}.{rng.randint(0, 9)}",
                        city=rng.choice(["Hyderabad", "Bengaluru", "Pune", "Chennai"]), year=m.year,
                        n=rng.choice([40, 60, 85, 120, 150, 200, 250]),
                        topic=rng.choice([t for t, _ in B.SECURITY_TOPICS]))
            add(title_t.format(**vals), "Announcement", dept, cls, ["*"], body_t.format(**vals),
                m.replace(day=min(m.day, 28)), tags=["announcement"])

        # 7) Training programme pages
        for name in ["Secure Coding Academy", "Leading at NovaTech", "Cloud Practitioner track", "Data & AI Foundations",
                     "Customer Excellence", "Negotiation Skills", "Presentation Skills", "Kubernetes Fundamentals",
                     "Advanced SQL", "Product Discovery", "Finance for Non-Finance Managers", "Privacy Essentials"]:
            for batch in rng.sample(["Q1", "Q2", "Q3", "Q4"], k=max(1, int(round(3 * kb_scale)))):
                add(f"Training: {name} — {batch} {today.year} cohort", "Training", "Human Resources", "INTERNAL", ["*"],
                    f"""
{name} ({batch} {today.year} cohort). Format: 4 live sessions plus self-paced modules.
Who should attend: employees who want to build skills in {name.lower()}.
How to enrol: through the Learning portal with manager approval; the cost is covered by the central L&D budget.
Completion certificate and 8 learning credits on completion.
""", self.date_between(date(today.year, 1, 1), today), tags=["training", name])

        self.bulk(Document, docs)
        self.doc_count = len(docs)

    # ------------------------------------------------------------------ run
    def run(self):
        s = self.scale
        log.info("Generating large NovaTech dataset (scale %.2f)…", s)
        self.organisation()
        self.employees(_n(2400, s))
        self.projects(_n(1200, s))
        self.tasks_and_meetings()
        self.hr()
        self.it()
        self.finance(_n(2500, s))
        self.sales(_n(450, s), _n(1600, s), _n(380, s))
        self.procurement(_n(260, s), _n(1400, s))
        self.service_requests(_n(400, s))
        self.documents(kb_scale=min(1.0, s) if s < 1 else 1.0)
        self.db.flush()
        total = sum(self.counts.values())
        log.info("Large dataset ready: %s records — %s", f"{total:,}",
                 ", ".join(f"{k}={v:,}" for k, v in sorted(self.counts.items())))
        return self.counts


def generate(db, core_users: dict, deps: dict, rng: random.Random | None = None, now: datetime | None = None) -> dict:
    return Gen(db, core_users, deps, rng or random.Random(2026), now or datetime.now(timezone.utc)).run()


def main() -> None:  # pragma: no cover - CLI helper
    ap = argparse.ArgumentParser(description="(Re)generate the NovaTech Solutions demo database.")
    ap.add_argument("--reset", action="store_true", help="drop all tables and reseed from scratch")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from . import session as dbsession
    from .seed import seed
    dbsession.init_db(reset=args.reset)
    with dbsession.SessionLocal() as db:
        seed(db)
    print("Done.")


if __name__ == "__main__":  # pragma: no cover
    main()
