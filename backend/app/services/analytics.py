"""Analytics Agent back-end: aggregate queries over STRUCTURED records, computed with real database queries.

Rows are pre-filtered in SQL (tenant + classification levels reachable by the caller) and then authorized row by
row with core.rbac.check_record (department scope, ownership). Only authorized rows are aggregated; the number of
rows hidden by policy is reported (never their content). The LLM is never asked to estimate numbers.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import select

from ..core.rbac import allowed_levels, check_record, is_guest
from ..db.models import (Budget, Contract, Customer, Department, Expense, ITTicket, LeaveRequest, Opportunity, Project,
                         PurchaseOrder, Task, User, Vendor)
from . import audit
from .nlp import today

DATASET_META = {
    # dataset: (model, label, amount field, allowed group-bys, permission)
    "projects": (Project, "projects", None, ["department", "status", "health", "priority", "business_unit",
                                             "budget_category", "classification"], "projects:read"),
    "tasks": (Task, "tasks", None, ["status", "priority", "project"], "tasks:read_self"),
    "employees": (User, "employees", None, ["department", "location", "employment_status", "job_title"],
                  "directory:read"),
    "tickets": (ITTicket, "IT tickets", None, ["category", "priority", "status"], "tickets:create"),
    "opportunities": (Opportunity, "opportunities", "amount", ["stage", "region", "product_id"], "analytics:read"),
    "contracts": (Contract, "contracts", "value", ["status"], "analytics:read"),
    "customers": (Customer, "customers", None, ["industry", "region", "tier"], "analytics:read"),
    "purchase_orders": (PurchaseOrder, "purchase orders", "amount", ["status", "category", "department"],
                        "analytics:read"),
    "vendors": (Vendor, "vendors", None, ["category", "country", "status"], "analytics:read"),
    "budgets": (Budget, "budget lines", "allocated", ["department", "fiscal_year", "quarter", "category"],
                "analytics:read"),
    "expenses": (Expense, "expense claims", "amount", ["category", "status", "department"], "analytics:read"),
    "leave_requests": (LeaveRequest, "leave requests", "days", ["status", "leave_type"], "leave:read_self"),
}
ACTIVE = ("In Progress", "Planning", "On Hold")


def _is_delayed(r) -> bool:
    return r.status not in ("Completed", "Cancelled") and bool((r.deadline and r.deadline < today()) or
                                                              r.health == "Red")


def _load(ctx, dataset: str):
    """Returns (visible_rows, hidden_count). Authorization happens here, before any aggregation."""
    from .tools import my_project_ids
    p, db = ctx.principal, ctx.db
    model = DATASET_META[dataset][0]
    levels = allowed_levels(p)
    if dataset == "employees":
        if is_guest(p):
            return [], 0
        hidden_depts = select(Department.id).where(Department.is_public.is_(False))
        rows = db.execute(select(User, Department.name).join(Department, Department.id == User.department_id)
                          .where(User.company_id == p.company_id, User.is_active.is_(True), User.is_guest.is_(False),
                                 User.department_id.not_in(hidden_depts))).all()
        out = []
        for u, dname in rows:
            u._dept = dname
            out.append(u)
        return out, 0
    if dataset == "tasks":
        ids = [p.user_id]
        if p.has("leave:read_team"):
            ids += list(db.scalars(select(User.id).where(User.manager_id == p.user_id)).all())
        return db.scalars(select(Task).where(Task.company_id == p.company_id, Task.assignee_id.in_(ids))).all(), 0
    if dataset == "tickets":
        q = select(ITTicket).where(ITTicket.company_id == p.company_id)
        if not p.has("tickets:read_all"):
            q = q.where(ITTicket.user_id == p.user_id)
        return db.scalars(q).all(), 0
    if dataset == "leave_requests":
        q = select(LeaveRequest).where(LeaveRequest.company_id == p.company_id)
        if not p.has("leave:read_all"):
            ids = [p.user_id] + (list(db.scalars(select(User.id).where(User.manager_id == p.user_id)).all())
                                 if p.has("leave:read_team") else [])
            q = q.where(LeaveRequest.user_id.in_(ids))
        return db.scalars(q).all(), 0
    total = db.scalars(select(model).where(model.company_id == p.company_id)).all()
    mine = my_project_ids(db, p) if dataset == "projects" else set()
    visible = []
    for r in total:
        if r.classification not in levels and not (dataset == "projects" and r.id in mine):
            continue
        owners = []
        if dataset == "projects" and (r.id in mine or r.manager_id == p.user_id):
            owners = [p.user_id]
        elif dataset in ("purchase_orders",):
            owners = [r.requester_id]
        elif dataset == "expenses":
            owners = [r.user_id]
        elif dataset == "opportunities":
            owners = [r.owner_id]
        if check_record(p, r, owner_ids=owners).allowed:
            visible.append(r)
    return visible, (0 if is_guest(p) else len(total) - len(visible))


def _apply_status(dataset: str, rows: list, status: str) -> tuple[list, str]:
    s = (status or "").strip().lower()
    if not s:
        return rows, ""
    d0 = today()
    if dataset == "projects":
        if s in ("delayed", "behind", "behind schedule", "late", "overdue"):
            return [r for r in rows if _is_delayed(r)], "delayed"
        if s in ("approaching_deadline", "approaching deadline", "due soon", "upcoming"):
            return [r for r in rows if r.status in ACTIVE and r.deadline and 0 <= (r.deadline - d0).days <= 30], \
                "deadline within 30 days"
        if s in ("active", "in progress", "ongoing", "current", "in_progress"):
            return [r for r in rows if r.status == "In Progress"], "in progress"
        if s in ("red", "amber", "green"):
            return [r for r in rows if r.health.lower() == s], f"health {s.title()}"
    if dataset == "tickets" and s in ("open", "unresolved"):
        return [r for r in rows if r.status != "resolved"], "open"
    if dataset == "tasks" and s in ("open", "pending"):
        return [r for r in rows if r.status != "done"], "open"
    if dataset == "tasks" and s in ("overdue", "late"):
        return [r for r in rows if r.status != "done" and r.due_date and r.due_date < d0], "overdue"
    if dataset == "opportunities" and s in ("open", "pipeline"):
        return [r for r in rows if not r.stage.startswith("Closed")], "open pipeline"
    if dataset == "budgets" and re.fullmatch(r"fy\d{2}", s):
        return [r for r in rows if r.fiscal_year.lower() == s], s.upper()
    field = {"projects": "status", "tickets": "status", "tasks": "status", "opportunities": "stage",
             "contracts": "status", "purchase_orders": "status", "vendors": "status", "expenses": "status",
             "leave_requests": "status", "employees": "employment_status", "customers": "tier",
             "budgets": "category"}.get(dataset)
    if field:
        return [r for r in rows if str(getattr(r, field, "")).lower() == s], f"{field} = {status}"
    return rows, ""


def _group_value(dataset, r, g):
    if dataset == "employees" and g == "department":
        return r._dept
    return getattr(r, g, None) or "—"


def run_query(ctx, dataset: str, metric: str = "count", group_by: str = "", status: str = "", department: str = ""):
    from .tools import ToolOutcome, _denied
    p = ctx.principal
    dataset = (dataset or "").strip().lower().replace(" ", "_")
    if dataset not in DATASET_META:
        return ToolOutcome("analytics_query", "error", "Unknown dataset",
                           f"Unknown dataset. Available: {', '.join(DATASET_META)}.")
    model, label, amount_field, groups, perm = DATASET_META[dataset]
    if perm and not p.has(perm):
        return _denied(ctx, "analytics_query", f"Your role cannot run analytics over {label}.",
                       resource=f"analytics:{dataset}", classification="INTERNAL")
    rows, hidden = _load(ctx, dataset)
    if not rows:
        if hidden:
            return _denied(ctx, "analytics_query", f"The {label} records matching this question are outside your "
                           f"access scope ({hidden:,} record(s) withheld by policy).",
                           resource=f"analytics:{dataset}", classification="CONFIDENTIAL")
        if is_guest(p):
            return _denied(ctx, "analytics_query", f"{label.capitalize()} are not public information — Guest Mode can "
                           "only analyse PUBLIC NovaTech Solutions data.", resource=f"analytics:{dataset}",
                           classification="INTERNAL", risk="LOW")
    filters_applied = []
    if department and department.strip():
        from .retrieval import DEPT_WORDS
        dname = DEPT_WORDS.get(department.strip().lower(), department.strip())
        before = rows
        if dataset == "employees":
            rows = [r for r in rows if r._dept.lower() == dname.lower()]
        elif hasattr(model, "department"):
            rows = [r for r in rows if (r.department or "").lower() == dname.lower()]
        if len(rows) != len(before):
            filters_applied.append(f"department = {dname}")
        if not rows and hidden:
            return _denied(ctx, "analytics_query", f"{dname} {label} are outside your access scope.",
                           resource=f"analytics:{dataset}:{dname}", classification="CONFIDENTIAL")
    rows, st = _apply_status(dataset, rows, status)
    if st:
        filters_applied.append(st)
    if dataset == "budgets" and not any(f.startswith("FY") for f in filters_applied):
        d0 = today()
        fy = f"FY{(d0.year + (1 if d0.month >= 4 else 0)) % 100:02d}"  # Indian fiscal year (April–March)
        rows = [r for r in rows if r.fiscal_year == fy]
        filters_applied.append(f"{fy} (current fiscal year)")
        if not group_by:
            group_by = "category"
    g = (group_by or "").strip().lower().replace(" ", "_")
    if g and g not in groups:
        g = next((x for x in groups if g in x or x in g), "")
    metric = (metric or "count").lower()
    result: dict = {"dataset": dataset, "label": label, "metric": metric, "group_by": g, "filters": filters_applied,
                    "total": len(rows), "hidden_by_policy": hidden}
    table: list[dict] = []
    if metric == "list":
        order = {"Red": 0, "Amber": 1, "Green": 2}
        if dataset == "projects":
            rows = sorted(rows, key=lambda r: (order.get(r.health, 3), r.deadline or today() + timedelta(days=9999)))
            table = [{"id": r.id, "name": r.name, "department": r.department, "status": r.status, "health": r.health,
                      "progress": r.progress, "deadline": r.deadline.isoformat() if r.deadline else None,
                      "manager": r.owner_name, "classification": r.classification} for r in rows[:25]]
            for r in rows[:25]:
                ctx.cite("project", r.id, r.name, r.classification, r.updated_on, f"{r.status} · {r.health}")
        else:
            key = "name" if hasattr(model, "name") else "title"
            table = [{"id": getattr(r, "id", ""), "name": getattr(r, key, getattr(r, "full_name", "")),
                      "status": getattr(r, "status", getattr(r, "stage", ""))} for r in rows[:25]]
    elif metric in ("sum", "utilization") and amount_field:
        if g:
            agg = defaultdict(lambda: [0.0, 0.0])
            for r in rows:
                k = _group_value(dataset, r, g)
                agg[k][0] += getattr(r, amount_field) or 0
                agg[k][1] += getattr(r, "spent", 0) or 0
            table = [{"group": k, "value": round(v[0], 2), **({"spent": round(v[1], 2),
                      "utilization_pct": round(100 * v[1] / v[0], 1) if v[0] else 0} if dataset == "budgets" else {})}
                     for k, v in sorted(agg.items(), key=lambda kv: -kv[1][0])]
        result["sum"] = round(sum(getattr(r, amount_field) or 0 for r in rows), 2)
        if dataset == "budgets":
            spent = sum(r.spent for r in rows)
            result["spent"] = round(spent, 2)
            result["utilization_pct"] = round(100 * spent / result["sum"], 1) if result["sum"] else 0
    elif metric == "avg_progress" and dataset == "projects":
        if g:
            agg = defaultdict(list)
            for r in rows:
                agg[_group_value(dataset, r, g)].append(r.progress)
            table = [{"group": k, "value": round(sum(v) / len(v), 1), "count": len(v)}
                     for k, v in sorted(agg.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))]
        result["avg_progress"] = round(sum(r.progress for r in rows) / len(rows), 1) if rows else 0
    else:  # count / percentage
        if g:
            c = Counter(_group_value(dataset, r, g) for r in rows)
            table = [{"group": k, "value": v, "pct": round(100 * v / len(rows), 1) if rows else 0}
                     for k, v in c.most_common()]
        if metric == "percentage":
            base, _ = _load(ctx, dataset)
            if department and department.strip():
                base = [r for r in base if (getattr(r, "department", None) or getattr(r, "_dept", "")).lower()
                        == department.strip().lower()]
            result["base_total"] = len(base)
            result["percentage"] = round(100 * len(rows) / len(base), 1) if base else 0.0
    result["rows"] = table
    audit.record(ctx.db, principal=p, action="tool.analytics_query", tool="analytics_query",
                 resource=f"Analytics: {label}", resource_id=dataset, classification="INTERNAL",
                 permission_result="ALLOWED", reason=f"metric={metric} group_by={g or '-'} filters={filters_applied} "
                 f"rows={len(rows)} hidden={hidden}", commit=False, request_id=ctx.request_id)
    ctx.cite("dataset", f"DS-{dataset}", f"{label.capitalize()} ({len(rows):,} authorized records)", "INTERNAL",
             today(), ", ".join(filters_applied))
    view = (f"Analytics over {label} (authorized rows only): total={len(rows)}, hidden_by_policy={hidden}, "
            f"filters={filters_applied}, metric={metric}, group_by={g or 'none'}. "
            + ", ".join(f"{k}={v}" for k, v in result.items() if k in ("sum", "spent", "utilization_pct",
                                                                        "avg_progress", "percentage", "base_total"))
            + "\n" + "\n".join(str(r) for r in table[:30]))
    return ToolOutcome("analytics_query", "ok", f"{label}: {len(rows):,} authorized record(s)"
                       + (f" · {hidden:,} hidden by policy" if hidden else ""), view, result)
