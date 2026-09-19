"""Specialised agents used by the offline engine (and as the fallback when the LLM provider fails).

Each agent plans a small sequence of tool calls, then composes a grounded answer ONLY from what those tools returned —
i.e. from data that already passed server-side authorization. No canned answers: every sentence is built from
retrieved documents or database rows at query time.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..core.rbac import check_tool, is_guest
from . import composer
from .nlp import fmt_date, parse_date, today
from .router import Understanding, parse_analytics
from .tools import PRIORITY_WORD, ToolContext, ToolOutcome, resolve_employee, run_tool

NOT_FOUND = "I couldn't find that information in the NovaTech Solutions knowledge base."
CONTACTS = [
    (r"leave|benefit|payroll|salary|onboard|hr|promotion|performance|training|hiring|recruit|attendance", "HR (hr.ops@novatech.demo)"),
    (r"laptop|vpn|password|software|device|wifi|it|access|email|mfa|printer", "the IT Service Desk (extension 4357)"),
    (r"expense|reimburse|invoice|budget|finance|payment|cost", "Finance (ap@novatech.demo)"),
    (r"purchase|procure|vendor|facilit|travel", "Operations / Procurement"),
    (r"contract|legal|privacy|compliance|retention|data protection", "Legal (privacy@novatech.demo)"),
    (r"security|phish|incident|breach", "Security Operations (security@novatech.demo)"),
]


@dataclass
class AgentReply:
    agent: str
    text: str
    handled: bool = True
    extra: dict = field(default_factory=dict)


def not_found_message(query: str, guest: bool = False) -> str:
    if guest:
        return (f"{NOT_FOUND} In Guest Mode I can only search **public** company information — internal policies, "
                "employee data and project details require an employee sign-in.")
    who = next((c for rx, c in CONTACTS if re.search(rf"\b({rx})", query, re.I)), None)
    tips = ["rephrase the question or name the policy / project / document", "browse the Documents page for what your "
            "role can access"]
    if who:
        tips.append(f"contact {who}")
    return f"{NOT_FOUND}\n\nYou could:\n" + "\n".join(f"- {t[0].upper() + t[1:]}" for t in tips)


class Runner:
    """Small helper that runs tools and records them on the timeline."""

    def __init__(self, ctx: ToolContext, step_cb):
        self.ctx, self.step_cb = ctx, step_cb

    def __call__(self, name: str, **args) -> ToolOutcome:
        out = run_tool(self.ctx, name, args)
        self.step_cb(out)
        return out

    def can(self, tool: str) -> bool:
        return check_tool(self.ctx.principal.permissions, tool).allowed


# ---- composition helpers ----------------------------------------------------------------------

def _latest_ev(ctx: ToolContext):
    for r in reversed(ctx.retrievals):
        ev = [e for e in r.evidence if e.is_latest] or r.evidence
        if ev:
            return r, ev
    return None, []


def answer_from_retrieval(ctx: ToolContext, query: str, u: Understanding, *, force_mode: str | None = None) -> str:
    res, ev = _latest_ev(ctx)
    if res is None:
        last = ctx.retrievals[-1] if ctx.retrievals else None
        if last is not None and last.only_restricted_answer():
            return composer.compose(query, last)
        msg = not_found_message(query, is_guest(ctx.principal))
        if last is not None and last.quarantined:
            msg += ("\n\n🛡️ **Potential prompt injection detected.** Matching excerpt(s) from "
                    f"'{last.quarantined[0]['title']}' contained instructions trying to override security policy, "
                    "so they were quarantined and never sent to the AI.")
        return msg
    if res.only_restricted_answer():
        return composer.compose(query, res)
    mode = force_mode or ("steps" if u.has("steps") else composer.choose_mode(query, u.flags))
    if mode == "answer" and not force_mode and ev[0].signals.get("title", 0) >= 0.5 and not re.search(
            r"\b(how many|how much|how long|when|who|what time|timings?|limit|deadline|which day|can i|do i|am i)\b",
            query, re.I):
        mode = "summary"  # broad question about a specific document → summarize it
    if mode == "summary":
        top = ev[0]
        from .tools import _full_text
        text = _full_text(ctx, top.doc.id) or "\n".join(top.chunks)
        lines = [f"**{top.doc.title}** (v{top.doc.version}, effective {top.doc.effective_date.strftime('%d %b %Y')}, "
                 f"owned by {top.doc.department}) [{top.doc.id}] — key points:"]
        lines += [f"- {b}" for b in composer.summarize_text(text, query, n=6)]
        related = [e for e in ev[1:3] if e.doc.family_key != top.doc.family_key]
        if related:
            lines += ["", "**Related:** " + " · ".join(f"{e.doc.title} [{e.doc.id}]" for e in related)]
        notes = composer.notes_for(res)
        if notes:
            lines += [""] + notes
        return "\n".join(lines)
    if mode == "steps":
        top = ev[0]
        from .tools import _full_text
        text = _full_text(ctx, top.doc.id) or "\n".join(top.chunks)
        steps = composer.extract_steps(text)
        if len(steps) >= 2:
            intro = composer.best_sentences(query, [top], n=1)
            lines = [f"Here's what to do, per **{top.doc.title}** (v{top.doc.version}, owned by "
                     f"{top.doc.department}) [{top.doc.id}]:", ""]
            lines += [f"{i + 1}. {s}" for i, s in enumerate(steps[:8])]
            extra = [s for s, e in composer.best_sentences(query, [top], n=3)
                     if not any(s[:40] in x for x in steps) and not s.rstrip().endswith(("?", ":"))
                     and not re.match(r"^(how|what|who|when|where|which)\b", s, re.I)]
            if extra:
                lines += ["", f"**Also note:** {extra[0]}"]
            notes = composer.notes_for(res)
            if notes:
                lines += [""] + notes
            return "\n".join(lines)
        mode = "answer"
    return composer.compose(query, res, mode)


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y")
    except ValueError:
        return iso


def _health(h: str) -> str:
    return {"Red": "🔴 Red", "Amber": "🟠 Amber", "Green": "🟢 Green"}.get(h, h)


def project_table(rows: list[dict], cols=("name", "status", "health", "progress", "deadline", "manager")) -> str:
    heads = {"name": "Project", "status": "Status", "health": "Health", "progress": "Progress", "deadline": "Deadline",
             "manager": "Manager", "my_role": "My role", "department": "Department"}
    out = ["| " + " | ".join(heads[c] for c in cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        vals = []
        for c in cols:
            v = r.get(c)
            if c == "name":
                v = f"{v} ({r['id']})"
            elif c == "health":
                v = _health(v)
            elif c == "progress":
                v = f"{v}%"
            elif c == "deadline":
                v = _fmt_date(v)
            vals.append(str(v if v is not None else "—"))
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


# ---- agents -------------------------------------------------------------------------------------

def knowledge_agent(run: Runner, u: Understanding) -> AgentReply:
    ctx = run.ctx
    q = u.text
    if u.departments and u.has("department") and run.can("get_department"):
        out = run("get_department", department=u.departments[0])
        if out.status == "ok":
            d = out.data
            lines = [f"**{d['department']}** — {d['description']}", ""]
            for k, label in (("business_unit", "Business unit"), ("head", "Department head"),
                             ("headcount", "Headcount"), ("location", "Primary location"),
                             ("active_projects", "Active projects you can see")):
                if d.get(k) not in (None, ""):
                    lines.append(f"- **{label}:** {d[k]:,}" if isinstance(d[k], int) else f"- **{label}:** {d[k]}")
            return AgentReply("Knowledge Agent", "\n".join(lines))
    dept = u.departments[0] if len(u.departments) == 1 else ""
    run("search_knowledge", query=q, department=dept)
    return AgentReply("Knowledge Agent", answer_from_retrieval(ctx, q, u))


def hr_agent(run: Runner, u: Understanding) -> AgentReply:
    ctx, q, low = run.ctx, u.text, u.text.lower()
    parts: list[str] = []
    # People / directory questions
    sens = re.search(r"\b(salary|salaries|compensation|pay|ctc|band)\b", low)
    perf = re.search(r"\b(performance (rating|review)s?|rating|appraisal result)\b", low)
    target = None
    howq = u.has("steps") or re.match(r"^\s*(how|what is the process|what are the steps)\b", low)
    if howq and not u.employees:
        pass
    elif u.employees:
        target = u.employees[0]
    elif re.search(r"\bmy manager|who is my (manager|boss|lead)|reports? to\b", low) and not re.search(
            r"reports? to me\b", low):
        target = "manager"
    elif re.search(r"\b(my team|team members|direct reports|who reports to me|reports to me)\b", low):
        target = "me"
    elif re.search(r"\bmy (profile|details|pan|bank|employee (id|info|information|record))|my (salary|compensation|"
                   r"performance|rating)\b", low):
        target = "me"
    if target and u.flags.get("leave_balance") and target != "me" and run.can("get_leave_balance"):
        out = run("get_leave_balance", employee=target)
        if out.status == "ok":
            b = out.data
            return AgentReply("HR Agent", f"**{b['employee']}** has **{b['casual']['remaining']:g} casual**, "
                              f"{b['sick']['remaining']:g} sick and {b['earned']['remaining']:g} earned leave(s) "
                              f"remaining for {b['year']}.")
        return AgentReply("HR Agent", f"🔒 **Access denied.** {out.summary} The request was logged."
                          if out.status == "denied" else out.summary)
    if target and not run.can("get_employee"):
        run("get_employee", employee=str(target), include="profile")  # audited denial
        return AgentReply("HR Agent", "🔒 The employee directory and personal records are not available in Guest Mode. "
                                      "Please sign in with your NovaTech Solutions employee account.")
    if target and run.can("get_employee"):
        include = "compensation" if sens else "performance" if perf else "team" if re.search(
            r"\b(my team|team members|direct reports|reports to me)\b", low) else "profile"
        out = run("get_employee", employee=target, include=include)
        if out.status == "ok":
            d = out.data
            if include == "compensation":
                parts.append(f"**{d['name']}** — band **{d['band']}**, base salary **{d['base_salary']}** "
                             f"(effective {d['effective']}). This is Confidential compensation data.")
            elif include == "performance":
                parts.append(f"Performance history for **{d['name']}** (Confidential):\n" +
                             "\n".join(f"- {r}" for r in d["reviews"]))
            elif include == "team":
                reps = d.get("direct_reports") or []
                parts.append(f"**{d['name']}** has **{len(reps)} direct report(s)**:\n" + "\n".join(f"- {r}" for r in reps[:40]))
            else:
                rows = [f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in d.items() if v and k != "name"]
                parts.append(f"Here's the directory profile for **{d['name']}**:\n" + "\n".join(rows))
        elif out.status == "denied":
            parts.append(f"🔒 **Access denied.** {out.summary} The request was logged.")
        else:
            parts.append(f"I couldn't find an employee matching “{u.employees[0] if u.employees else target}” in the "
                         "NovaTech Solutions directory.")
        if not (u.flags.get("leave_balance") or u.has("hr") and not target):
            return AgentReply("HR Agent", "\n\n".join(parts))
    # Leave balance
    if u.flags.get("leave_balance") and run.can("get_leave_balance"):
        run("get_leave_policy")
        res = ctx.retrievals[-1] if ctx.retrievals else None
        bal = run("get_leave_balance", employee="me")
        if res and res.evidence:
            picks = composer.best_sentences("casual leave entitlement per year days", res.evidence, n=1)
            if picks:
                s, ev = picks[0]
                parts.append(f"Per the **{ev.doc.title}** (v{ev.doc.version}) [{ev.doc.id}]: {s}")
            for c in res.conflicts:
                parts.append(f"⚠️ {c['note']}")
        if bal.status == "ok":
            c = bal.data["casual"]
            parts.append(f"You have **{c['remaining']:g} casual leave(s) remaining** for {bal.data['year']} "
                         f"({c['used']:g} of {c['total']:g} used). Sick: {bal.data['sick']['remaining']:g} · "
                         f"Earned: {bal.data['earned']['remaining']:g}"
                         + (f" · {bal.data['pending_requests_days']:g} day(s) pending approval" if bal.data['pending_requests_days'] else "") + ".")
        return AgentReply("HR Agent", "\n\n".join(parts))
    if parts:
        return AgentReply("HR Agent", "\n\n".join(parts))
    # HR knowledge
    if re.search(r"\bleave polic|leave entitlement|how many (casual|sick|earned) leaves?\b", low):
        run("get_leave_policy")
    else:
        run("search_policies", query=q, department="Human Resources")
    return AgentReply("HR Agent", answer_from_retrieval(ctx, q, u))


def it_agent(run: Runner, u: Understanding, *, with_workflow: bool = False) -> AgentReply:
    ctx, q, low = run.ctx, u.text, u.text.lower()
    if re.search(r"\b(software|apps?|tools?|applications?)\b.{0,40}\b(available|approved|allowed|can i (use|install)|"
                 r"catalog\w*|list)\b|\bcan i install\b|\bis .{2,30} (approved|allowed)\b", low) and run.can("search_software"):
        out = run("search_software", query=q)
        items = out.data.get("items", [])
        run("search_policies", query="standard software catalog request software approval",
            department="Information Technology")
        res, ev = _latest_ev(ctx)
        cite = f" [{ev[0].doc.id}]" if ev else ""
        if out.data.get("matched") and len(items) <= 6:
            lines = ["Here's what the software catalogue says" + cite + ":"]
            for d in items:
                lines.append(f"- **{d['name']}** ({d['category']}, {', '.join(d['platforms'])}) — "
                             + ("**needs approval** (manager for paid licences / Security for sensitive tools)"
                                if d["approval_required"] else "**self-service** from the Company Portal")
                             + f". {d['description']}")
        else:
            free = [d["name"] for d in items if not d["approval_required"]]
            appr = [d["name"] for d in items if d["approval_required"]]
            lines = [f"The NovaTech software catalogue has **{len(items)} titles**{cite}.",
                     f"\n**Available to all employees (self-service):** {', '.join(free[:22])}.",
                     f"\n**Needs approval:** {', '.join(appr[:22])}."]
        lines.append("\nTo get something that needs approval, ask me to create a software request — nothing is "
                     "submitted until you confirm.")
        return AgentReply("IT Agent", "\n".join(lines))
    query = q
    if with_workflow and u.has("device_problem"):
        query = re.sub(r"^(please )?(create|raise|open|log|file)( an?)?( it)?( support)? ticket( for| saying| about)?",
                       "", q, flags=re.I).strip() or q
        query += " troubleshooting"
    run("search_policies", query=query, department="Information Technology")
    text = answer_from_retrieval(ctx, query, u, force_mode="steps" if (u.has("steps") or with_workflow) else None)
    if with_workflow and text.startswith(NOT_FOUND):
        return AgentReply("IT Agent", "", handled=False)
    return AgentReply("IT Agent", text)


def _ticket_parts(text: str) -> dict:
    t = text.lower()
    cat = ("Hardware" if re.search(r"laptop|monitor|keyboard|mouse|printer|hardware|battery|screen|computer", t) else
           "Network" if re.search(r"vpn|wifi|wi-fi|network|internet", t) else
           "Access" if re.search(r"access|password|login|account|locked|mfa", t) else
           "Software" if re.search(r"install|software|licen[cs]e|app|ide|update|outlook|teams|zoom|slack", t) else "Other")
    pri = ("P1" if re.search(r"\b(p1|critical|outage|everyone|whole team|production down)\b", t) else
           "P2" if re.search(r"urgent|asap|blocked|cannot work|can't work|p2", t) else "P3")
    m = re.search(r"\b(?:saying|that says|stating|for|about|because|regarding|re:)\s+(?:that\s+)?(?:my\s+)?(.{4,110}?)(?:[.?!]|$)",
                  text, re.I)
    subject = m.group(1).strip() if m else ""
    if not subject:
        m = re.search(r"\b(my\s+)?((laptop|vpn|wi-?fi|printer|monitor|keyboard|outlook|teams|password|screen|battery|"
                      r"computer)[^.?!,]{0,60})", text, re.I)
        subject = m.group(2).strip() if m else {"Hardware": "Hardware issue", "Network": "Network connectivity issue",
                                                "Access": "Access / account issue", "Software": "Software issue",
                                                "Other": "General IT support request"}[cat]
    subject = re.sub(r"^(an?|the)\s+", "", subject)
    return {"title": subject[:1].upper() + subject[1:], "priority": pri, "category": cat,
            "description": f"Raised via the NovaTech Solutions AI assistant: \"{text.strip()}\""}


def _reason_from(text: str, default: str) -> str:
    m = re.search(r"\b(?:for|because|due to|reason[:\s]+)\s+(.{3,80}?)(?:[.?!]|$)", text, re.I)
    if m and not re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today|next|"
                           r"\d+ days?)\b", m.group(1), re.I):
        return m.group(1).strip().capitalize()
    return default


def _email_parts(ctx: ToolContext, text: str) -> tuple[str, str, str]:
    t = text.strip()
    recipient = "manager" if re.search(r"\bmanager\b|\bboss\b|\blead\b", t, re.I) else None
    if not recipient:
        m = re.search(r"\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?|[\w.+-]+@[\w.-]+)", t)
        recipient = m.group(1) if m else "manager"
    target = resolve_employee(ctx.db, ctx.principal, recipient) if "@" not in recipient else None
    first = target.full_name.split()[0] if target else "there"
    m = re.search(r"\b(?:saying|that says|to say|telling (?:them|him|her)|letting (?:them|him|her) know|"
                  r"informing (?:them|him|her)|that|about)\s+(.+)$", t, re.I)
    clause = (m.group(1) if m else "I wanted to give you a quick update").strip().rstrip(".!")
    clause = re.sub(r"\bI'll\b", "I will", clause, flags=re.I)
    clause = re.sub(r"\bI'm\b", "I am", clause, flags=re.I)
    d = parse_date(clause)
    wfh = re.search(r"\b(remote|remotely|from home|wfh)\b", clause, re.I)
    if d:
        clause = re.sub(r"\b(tomorrow|today|on \w+day|next \w+day|\w+day)\b", f"on {fmt_date(d)}", clause, count=1,
                        flags=re.I)
    sentence = clause[0].upper() + clause[1:]
    me = ctx.principal.full_name.split()[0]
    if wfh:
        subject = f"Working from home — {d.strftime('%a, %d %b') if d else 'update'}"
        body = (f"Hi {first},\n\n{sentence}. I will be available on Teams and email during core hours "
                f"(11:00–16:00 IST), in line with the Work From Home Policy.\n\nThanks,\n{me}")
    else:
        subject = f"Quick update from {me}"
        body = f"Hi {first},\n\n{sentence}.\n\nThanks,\n{me}"
    return recipient, subject, body


def workflow_agent(run: Runner, u: Understanding) -> AgentReply:
    ctx, text, low = run.ctx, u.text, u.text.lower()
    f, h = u.flags, u.hits
    parts: list[str] = []
    if h.get("my_requests") and run.can("get_my_requests"):
        out = run("get_my_requests")
        items = out.data.get("items", [])
        if not items:
            parts.append("You have no leave requests, tickets or service requests on record.")
        else:
            open_ = [i for i in items if i["status"] not in ("resolved", "completed", "approved", "rejected", "closed")]
            parts.append(f"You have **{len(items)} request(s)** on record — **{len(open_)} still open**:\n\n"
                         "| Request | Type | Status | Raised |\n|---|---|---|---|\n" +
                         "\n".join(f"| {i['title']} ({i['id']}) | {i['kind']} | {i['status'].replace('_', ' ')} | "
                                   f"{_fmt_date(i['date'])} |" for i in items[:12]))
    if f.get("delete"):
        m = re.search(r"\bDOC-\d+\b", text, re.I)
        if not run.can("delete_document"):
            out = run("delete_document", document_id=m.group(0).upper() if m else "")
            parts.append("❌ **Not permitted.** Deleting documents requires elevated authorization and explicit "
                         "confirmation. This attempt was logged.")
        elif not m:
            parts.append("Which document should be archived? Please give its ID (e.g. DOC-1012).")
        else:
            out = run("delete_document", document_id=m.group(0).upper())
            parts.append("I've prepared the deletion. **It will only happen after you approve** the action card below."
                         if out.status == "pending_confirmation" else f"❌ {out.summary}.")
    if f.get("leave_submit") and run.can("create_leave_request"):
        d = parse_date(text)
        if not d:
            parts.append("Which date would you like to take off? For example: *“apply casual leave for next Monday”*.")
        else:
            lt = "sick" if re.search(r"\b(sick|unwell|fever|doctor|medical)\b", text, re.I) else \
                "earned" if re.search(r"\b(earned|privilege|vacation|annual)\b", text, re.I) else "casual"
            end = d
            m = re.search(r"\bfor (\d+) days\b", text, re.I)
            if m:
                n = int(m.group(1))
                while n > 1:
                    end += timedelta(days=1)
                    if end.weekday() < 5:
                        n -= 1
            out = run("create_leave_request", start_date=d.isoformat(), end_date=end.isoformat(), leave_type=lt,
                      reason=_reason_from(text, "Personal work"))
            if out.status == "pending_confirmation":
                parts.append(f"I've prepared a **{lt} leave request for {fmt_date(d)}**"
                             + (f" to {fmt_date(end)}" if end != d else "") + ". Review the details below and click "
                             "**Confirm & submit** to submit it to your manager — nothing is submitted until you do.")
            else:
                parts.append(f"❌ I couldn't prepare the request: {out.summary}.")
    if f.get("email") and run.can("draft_email"):
        recipient, subject, body = _email_parts(ctx, text)
        out = run("draft_email", recipient=recipient, subject=subject, body=body)
        if out.status == "pending_confirmation":
            parts.append(f"Here's a draft to **{out.data.get('recipient_name', recipient)}**. Nothing is sent until you "
                         "review it and click **Confirm & submit** — you can edit the subject and body first.")
        elif out.status == "blocked":
            parts.append("🛡️ **Blocked.** Company policy only allows the AI assistant to email internal "
                         "@novatech.demo recipients. This attempt was logged.")
        else:
            parts.append(f"I couldn't draft that email: {out.summary}.")
    is_ticket = (h.get("ticket") and h.get("create")) or h.get("device_problem") or f.get("ticket")
    wants = is_ticket or f.get("leave_submit") or f.get("email") or h.get("access_req") or h.get("software_req") \
        or h.get("document_req") or h.get("procurement_req")
    if wants and not (run.can("create_it_ticket") or run.can("create_request")):
        run("create_it_ticket" if is_ticket else "create_request", title="(not permitted)", description="-")
        return AgentReply("Workflow Agent", "🔒 **This action isn't available in Guest Mode.** Creating tickets, leave "
                                            "requests or other workflows requires an employee sign-in. The attempt was "
                                            "logged.")
    if is_ticket and not f.get("email") and run.can("create_it_ticket"):
        tp = _ticket_parts(text)
        out = run("create_it_ticket", **tp)
        if out.status == "pending_confirmation":
            parts.append(f"I can create an IT ticket with:\n\n- **Issue:** {tp['title']}\n- **Category:** "
                         f"{tp['category']}\n- **Priority:** {PRIORITY_WORD[tp['priority']]} ({tp['priority']})\n\n"
                         "Would you like me to submit it? Review the card below and click **Confirm & submit**.")
        else:
            parts.append(f"❌ {out.summary}.")
    elif not is_ticket and run.can("create_request") and not f.get("leave_submit") and not f.get("email"):
        req = None
        if h.get("access_req"):
            m = re.search(r"\baccess (?:to|for)\s+(?:the\s+)?(.{3,80}?)(?:[.?!]|$| because| for )", text, re.I)
            what = m.group(1).strip() if m else ("VPN — standard" if "vpn" in low else "the requested system")
            req = ("access", f"Access to {what}")
        elif h.get("software_req"):
            from ..db.models import SoftwareItem
            from sqlalchemy import select
            names = ctx.db.scalars(select(SoftwareItem.name).where(SoftwareItem.company_id == ctx.principal.company_id)).all()
            sw = next((n for n in sorted(names, key=len, reverse=True) if n.lower() in low or
                       n.lower().split()[0] in low.split()), None)
            req = ("software", f"Software request: {sw or 'licence (see justification)'}")
        elif h.get("document_req"):
            m = re.search(r"\b(employment verification|experience|salary|address proof|relieving)\s+(letter|certificate)\b", low)
            req = ("document", f"Document request: {m.group(0).title() if m else 'HR letter'}")
        elif h.get("procurement_req"):
            m = re.search(r"\b(?:for|buy|procure|order|purchase request (?:for|of))\s+(.{3,80}?)(?:[.?!]|$| costing| worth| at )",
                          text, re.I)
            req = ("procurement", f"Purchase request: {m.group(1).strip() if m else 'item(s) described below'}")
        if req:
            cost = 0.0
            m = re.search(r"(?:₹|rs\.?|inr)\s?([\d,]+(?:\.\d+)?)\s*(lakh|l|k|crore)?", text, re.I)
            if m:
                cost = float(m.group(1).replace(",", "")) * {"lakh": 1e5, "l": 1e5, "k": 1e3, "crore": 1e7}.get(
                    (m.group(2) or "").lower(), 1)
            just = _reason_from(text, "Requested via the NovaTech Solutions AI assistant")
            out = run("create_request", request_type=req[0], title=req[1], justification=just, estimated_cost=cost)
            if out.status == "pending_confirmation":
                parts.append(f"I've prepared a **{req[0]} request**: *{req[1]}*. It will be routed for approval "
                             "only after you confirm it below.")
    if not parts:
        return AgentReply("Workflow Agent", "", handled=False)
    return AgentReply("Workflow Agent", "\n\n".join(parts))


def project_agent(run: Runner, u: Understanding) -> AgentReply:
    ctx, low = run.ctx, u.text.lower()
    parts: list[str] = []
    wants_risks = bool(re.search(r"\brisks?\b", low))
    wants_members = bool(re.search(r"\b(members?|team|assigned|who (works|is working)|employees|people|staff)\b", low))
    wants_manager = bool(re.search(r"\b(who manages|manager|who (leads|owns|runs))\b", low))
    if u.projects:
        for pid, name in u.projects[:3]:
            out = run("get_project", project=pid)
            if out.status == "denied":
                parts.append(f"I couldn't locate details for project “{name}” in your accessible directory. "
                             "This project may be inactive or managed under a separate departmental scope.")
                continue
            if out.status != "ok":
                parts.append(f"I couldn't find a project called “{name}”.")
                continue
            d = out.data
            if wants_members and not wants_risks:
                mem = d["members"]
                if not mem:
                    parts.append(f"Team membership for **{d['name']}** isn't available in Guest Mode.")
                else:
                    parts.append(f"**{d['name']}** ({d['id']}) has **{len(mem)} assigned member(s)**:\n\n| Name | Title | "
                                 "Project role |\n|---|---|---|\n" +
                                 "\n".join(f"| {m['name']} | {m['title']} | {m['role']} |" for m in mem))
                continue
            if wants_manager and not wants_risks:
                parts.append(f"**{d['name']}** ({d['id']}) is managed by **{d['manager']}** — {d['department']} "
                             f"department, status {d['status']}, health {_health(d['health'])}.")
                continue
            lines = [f"**{d['name']}** ({d['id']}) — {d['status']} · health {_health(d['health'])} · "
                     f"**{d['progress']}%** complete · priority {d['priority']}",
                     f"Manager **{d['manager']}** · {d['department']} · deadline **{_fmt_date(d['deadline'])}**"
                     + (" — ⚠️ **behind schedule**" if d["delayed"] else "")
                     + (f" · budget {d['budget']}" if d.get("budget") else ""), "", d["summary"]]
            if d["milestones"]:
                lines += ["", "**Milestones**"] + [f"- {m['name']} — {_fmt_date(m['due'])} · {m['state']}"
                                                   for m in d["milestones"]]
            if d["risks"]:
                lines += ["", "**Top risks**"] + [f"- {r['risk']} (*{r['severity']}*) — mitigation: {r['mitigation']}"
                                                  for r in d["risks"]]
            if d.get("members"):
                lines += ["", f"**Team:** {len(d['members'])} members · tasks {d['tasks_open']} open, "
                              f"{d['tasks_overdue']} overdue"]
            parts.append("\n".join(lines))
        return AgentReply("Project Agent", "\n\n".join(parts))

    if u.has("my_projects") or (u.self_ref and re.search(r"\bprojects?\b", low)):
        if not run.can("get_my_projects"):
            return AgentReply("Project Agent", "Project assignments are only available to signed-in employees. In "
                              "Guest Mode I can describe NovaTech's public initiatives instead.")
        flt = ("delayed" if re.search(r"\b(delayed|behind|late|overdue|slipping|at risk)\b", low) else
               "approaching_deadline" if re.search(r"\b(deadline|due soon|approaching)\b", low) else
               "active" if re.search(r"\b(active|current|ongoing)\b", low) else "all")
        out = run("get_my_projects", filter=flt)
        rows = out.data.get("projects", [])
        if not rows:
            return AgentReply("Project Agent", {"delayed": "Good news — none of your projects are behind schedule.",
                                                "approaching_deadline": "None of your projects has a deadline in the "
                                                                        "next 45 days."}.get(flt,
                                                                                             "You aren't assigned to any projects."))
        if re.search(r"\bproject manager\b|\bwho manages\b", low):
            parts.append("Your project managers:\n" + "\n".join(f"- **{r['name']}** ({r['id']}) — managed by "
                                                              f"**{r['manager']}** · you are {r['my_role']}"
                                                              for r in rows))
            return AgentReply("Project Agent", "\n\n".join(parts))
        label = {"delayed": "behind schedule", "approaching_deadline": "approaching their deadline", "active": "active",
                 "all": "assigned to you"}[flt]
        parts.append(f"You have **{len(rows)} project(s) {label}**:\n\n" +
                     project_table(rows, ("name", "my_role", "status", "health", "progress", "deadline")))
        risky = [r for r in rows if r["risks"] and (wants_risks or flt == "delayed" or r["delayed"])]
        if wants_risks or flt == "delayed":
            if risky:
                lines = ["**Main risks**"]
                for r in risky[:6]:
                    top = sorted(r["risks"], key=lambda x: {"High": 0, "Medium": 1, "Low": 2}.get(x["severity"], 3))
                    lines.append(f"- **{r['name']}** — " + "; ".join(f"{x['risk']} (*{x['severity']}*, mitigation: "
                                                                     f"{x['mitigation'].rstrip('.')})" for x in top[:2]))
                parts.append("\n".join(lines))
        elif risky:
            parts.append(f"⚠️ {sum(1 for r in rows if r['delayed'])} of these are behind schedule — ask me to "
                         "“summarize the risks in my delayed projects” for details.")
        return AgentReply("Project Agent", "\n\n".join(parts))

    # Org-wide project lists (department projects, approaching deadlines, delayed)
    params = parse_analytics(u)
    params["dataset"] = "projects"
    if params["metric"] not in ("count", "percentage", "avg_progress"):
        params["metric"] = "list"
    elif not re.search(r"\b(how many|number of|count|percentage|percent|%)\b", low):
        params["metric"] = "list"
    if not params["status"] and re.search(r"\b(working on|current|ongoing|now)\b", low):
        params["status"] = "active"
    out = run("analytics_query", **params)
    if out.status == "denied":
        return AgentReply("Project Agent", f"🔒 **Access denied.** {out.summary}")
    d = out.data
    rows = d.get("rows", [])
    scope = " · ".join(d.get("filters") or []) or "all projects you can access"
    if params["metric"] == "list":
        if not rows:
            return AgentReply("Project Agent", f"No projects match ({scope}).")
        head = f"**{d['total']:,} project(s)** match ({scope})" + (" — showing the 25 most urgent" if d["total"] > 25 else "") + ":"
        txt = head + "\n\n" + project_table(rows, ("name", "department", "status", "health", "progress", "deadline"))
        if d.get("hidden_by_policy"):
            txt += f"\n\n🔒 {d['hidden_by_policy']:,} other project record(s) are outside your access scope and were not included."
        return AgentReply("Project Agent", txt)
    return AgentReply("Project Agent", analytics_text(d))


def analytics_text(d: dict) -> str:
    label, total, rows = d["label"], d["total"], d.get("rows", [])
    scope = " · ".join(d.get("filters") or [])
    lines = []
    money = lambda v: f"₹{v / 1e7:,.2f} crore" if v >= 1e7 else f"₹{v / 1e5:,.1f} lakh" if v >= 1e5 else f"₹{v:,.0f}"
    if d["metric"] == "percentage":
        lines.append(f"**{d['percentage']}%** of {label} ({total:,} of {d.get('base_total', 0):,}) match"
                     + (f" *{scope}*" if scope else "") + ".")
    elif d["metric"] in ("sum", "utilization") and "sum" in d:
        lines.append(f"Total {'allocated budget' if d['dataset'] == 'budgets' else 'value'} across **{total:,} {label}**"
                     + (f" ({scope})" if scope else "") + f": **{money(d['sum'])}**"
                     + (f"; spent **{money(d['spent'])}** — utilisation **{d['utilization_pct']}%**." if "spent" in d else "."))
    elif d["metric"] == "avg_progress":
        lines.append(f"Average progress across **{total:,} {label}**" + (f" ({scope})" if scope else "")
                     + f" is **{d['avg_progress']}%**.")
    else:
        lines.append(f"There are **{total:,} {label}**" + (f" matching *{scope}*" if scope else "") + ".")
    if rows and d.get("group_by"):
        g = d["group_by"].replace("_", " ").title()
        if "spent" in rows[0]:
            lines += ["", f"| {g} | Allocated | Spent | Utilisation |", "|---|---|---|---|"]
            lines += [f"| {r['group']} | {money(r['value'])} | {money(r['spent'])} | {r['utilization_pct']}% |" for r in rows[:15]]
        elif d["metric"] in ("sum",):
            lines += ["", f"| {g} | Value |", "|---|---|"] + [f"| {r['group']} | {money(r['value'])} |" for r in rows[:15]]
        elif d["metric"] == "avg_progress":
            lines += ["", f"| {g} | Avg progress | Projects |", "|---|---|---|"] + [
                f"| {r['group']} | {r['value']}% | {r['count']} |" for r in rows[:15]]
        else:
            lines += ["", f"| {g} | Count | Share |", "|---|---|---|"] + [
                f"| {r['group']} | {r['value']:,} | {r['pct']}% |" for r in rows[:15]]
            if len(rows) > 1:
                lines += ["", f"**{rows[0]['group']}** has the most ({rows[0]['value']:,})."]
    lines.append("")
    lines.append(f"*Computed from the database over {total:,} record(s) you are authorized to view"
                 + (f"; {d['hidden_by_policy']:,} record(s) were excluded by access policy" if d.get("hidden_by_policy") else "")
                 + ".*")
    return "\n".join(lines)


def analytics_agent(run: Runner, u: Understanding) -> AgentReply:
    params = parse_analytics(u)
    out = run("analytics_query", **params)
    if out.status == "denied":
        return AgentReply("Analytics Agent", f"🔒 **Access denied.** {out.summary} The attempt was logged.")
    if out.status != "ok":
        return AgentReply("Analytics Agent", f"I couldn't run that analysis: {out.summary}.")
    d = out.data
    if params["metric"] == "list":
        rows = d.get("rows", [])
        txt = f"**{d['total']:,} {d['label']}** match ({' · '.join(d['filters']) or 'all accessible'}):\n\n"
        return AgentReply("Analytics Agent", txt + (project_table(rows, ("name", "department", "status", "health",
                                                                         "progress", "deadline"))
                                                    if d["dataset"] == "projects" else
                                                    "\n".join(f"- {r['name']} ({r['id']}) — {r['status']}" for r in rows)))
    return AgentReply("Analytics Agent", analytics_text(d))


def document_agent(run: Runner, u: Understanding) -> AgentReply:
    ctx, q, low = run.ctx, u.text, u.text.lower()
    # latest updates
    if re.search(r"\b(latest|recent|new)\b.{0,30}\b(polic(y|ies)|updates?|announcements?|changes)\b", low) and \
            not re.search(r"\b(summari[sz]e|compare)\b", low):
        dt = "Announcement" if "announcement" in low else "Policy"
        out = run("latest_updates", doc_type=dt, limit=8)
        items = out.data.get("items", [])
        if not items:
            return AgentReply("Document Agent", NOT_FOUND)
        lines = [f"The latest {dt.lower()} updates you're authorized to see:"]
        lines += [f"- **{i['title']}** [{i['doc_id']}] · {i['department']} · v{i['version']} · updated "
                  f"{_fmt_date(i['updated_at'])} · {i['classification'].title()}" for i in items]
        return AgentReply("Document Agent", "\n".join(lines))
    # compare
    if re.search(r"\b(compare|comparison|differences? between|what changed|vs\.?|versus)\b", low):
        ids = u.doc_ids
        topic = re.sub(r"\b(compare|comparison of|the|current|previous|old|new|latest|with|and|versus|vs\.?|"
                       r"what changed in|differences? between|policy with|version)\b", " ", low)
        topic = re.sub(r"\s+", " ", topic).strip(" ?.") or "policy"
        out = run("compare_documents", document_a=ids[0] if ids else topic,
                  document_b=ids[1] if len(ids) > 1 else "previous")
        if out.status != "ok":
            return AgentReply("Document Agent", out.summary)
        return AgentReply("Document Agent", composer.compare(out.data))
    # department ownership
    if re.search(r"\b(which department owns|who owns|owner of|department owns)\b", low):
        subject = re.sub(r"\b(which department owns|who owns|owner of|department owns|this|the|process)\b", " ", low).strip(" ?.")
        if not subject and ctx.recent_docs:
            from .tools import resolve_document
            meta, _ = resolve_document(ctx, "this")
            if meta:
                return AgentReply("Document Agent", f"**{meta.title}** [{meta.id}] is owned by the **{meta.department}** "
                                  f"department" + (f" (document owner: {meta.owner_name})" if meta.owner_name else "") + ".")
        run("search_policies", query=f"{subject} process ownership department")
        res, ev = _latest_ev(ctx)
        reg = next((e for e in ev if e.doc.family_key == "process-ownership"), None)
        if reg:
            from .tools import _full_text
            st = set(re.findall(r"[a-z]+", subject))
            lines = [l.strip("- ").strip() for l in _full_text(ctx, reg.doc.id).split("\n") if l.strip().startswith("-")]
            best = max(lines, key=lambda l: len(st & set(re.findall(r"[a-z]+", l.lower()))), default="")
            if best and st & set(re.findall(r"[a-z]+", best.lower())):
                return AgentReply("Document Agent", f"Per the **{reg.doc.title}** [{reg.doc.id}]: {best}")
        top = next((e for e in ev if e.signals.get("title", 0) >= 0.5), None)
        if not top:
            return AgentReply("Document Agent", not_found_message(q, is_guest(ctx.principal)))
        txt = (f"The **{top.doc.department}** department owns this — per **{top.doc.title}** [{top.doc.id}]"
               + (f" (document owner: {top.doc.owner_name})" if top.doc.owner_name else "") + ".")
        return AgentReply("Document Agent", txt)
    # find documents
    if re.search(r"\b(find|list|search|show|locate)\b.{0,20}\b(documents?|docs|files|policies|articles)\b|\bdocuments? "
                 r"(related|about|on|for)\b", low):
        topic = re.sub(r"\b(find|list|search|show|locate|me|all|the|documents?|docs|files|articles|related|to|about|on|"
                       r"for)\b", " ", low).strip(" ?.")
        out = run("search_knowledge", query=topic or q, department="")
        return AgentReply("Document Agent", answer_from_retrieval(ctx, topic or q, u, force_mode="search"))
    # classification question
    if re.search(r"\bclassification of\b|\bhow is .* classified\b", low) and u.doc_ids:
        from .tools import resolve_document
        meta, why = resolve_document(ctx, u.doc_ids[0])
        if not meta:
            return AgentReply("Document Agent", "🔒 That document is outside your access level." if why == "denied" else NOT_FOUND)
        return AgentReply("Document Agent", f"**{meta.title}** [{meta.id}] is classified **{meta.classification.title()}**, "
                          f"owned by {meta.department}, version {meta.version} (effective {_fmt_date(meta.effective_date.isoformat())}).")
    # summarize (default)
    ref = u.doc_ids[0] if u.doc_ids else re.sub(r"\b(please|can you|could you|summari[sz]e|summary of|give me|a|the|"
                                                r"tl;?dr|of|for|me|document|doc)\b", " ", low).strip(" ?.")
    if re.fullmatch(r"(this|that|it)?", ref or ""):
        ref = "this"
    dept = "Human Resources" if u.has("hr") and not u.has("it") else "Information Technology" if u.has("it") else ""
    out = run("summarize_document", document=ref, department=dept)
    if out.status != "ok":
        return AgentReply("Document Agent", out.summary if out.status != "denied" else
                          "🔒 **Access denied.** That document is above your access level, so it was not loaded.")
    meta = out.data["doc"]
    bullets = composer.summarize_text(out.data["text"], q, n=6)
    lines = [f"**{meta['title']}** [{meta['doc_id']}] — {meta['classification'].title()} · owned by "
             f"{meta['department']} · v{meta['version']} · updated {_fmt_date(meta['updated_at'])}", "", "**Summary**"]
    lines += [f"- {b}" for b in bullets]
    return AgentReply("Document Agent", "\n".join(lines))


def productivity_agent(run: Runner, u: Understanding) -> AgentReply:
    ctx, low = run.ctx, u.text.lower()
    if not run.can("get_pending_tasks"):
        return AgentReply("Productivity Agent", "Personal work summaries are available to signed-in employees only.")
    out = run("get_pending_tasks", scope="team" if re.search(r"\bmy team'?s?\b", low) else "me")
    d = out.data
    tasks, meetings = d["tasks"], d["meetings"]
    # meeting preparation
    if re.search(r"\bmeeting prep|prepare (me )?for (my )?(next |upcoming )?meeting\b", low):
        now = datetime.now(timezone.utc)
        upcoming = [m for m in meetings if datetime.fromisoformat(m["starts_at"]) >= now - timedelta(minutes=30)] or meetings
        if not upcoming:
            return AgentReply("Productivity Agent", "You have no meetings today or tomorrow.")
        m = upcoming[0]
        lines = [f"**Next meeting:** {m['title']} — {_local(m['starts_at'])} · {m['location']}", "", f"*Agenda:* {m['agenda']}"]
        if m.get("project_id"):
            po = run("get_project", project=m["project_id"])
            if po.status == "ok":
                p = po.data
                lines += ["", f"**Project context — {p['name']}:** {p['status']}, health {_health(p['health'])}, "
                              f"{p['progress']}% complete, deadline {_fmt_date(p['deadline'])}."]
                if p["risks"]:
                    lines += ["Risks to raise:"] + [f"- {r['risk']} (*{r['severity']}*)" for r in p["risks"][:3]]
            mine = [t for t in tasks if t.get("project_id") == m["project_id"]]
            if mine:
                lines += ["", "Your open items for this project:"] + [f"- {t['title']} — due {_fmt_date(t['due'])}"
                                                                      for t in mine[:5]]
        return AgentReply("Productivity Agent", "\n".join(lines))
    # priorities
    prio = {"High": 0, "Medium": 1, "Low": 2}
    ranked = sorted(tasks, key=lambda t: (not t["overdue"], t["status"] != "blocked", not t["due_soon"],
                                          prio.get(t["priority"], 3), t["due"] or "9999"))
    my_proj = run("get_my_projects", filter="delayed") if run.can("get_my_projects") else None
    delayed = my_proj.data.get("projects", []) if my_proj and my_proj.status == "ok" else []
    first = ctx.principal.full_name.split()[0]
    lines = [f"Here's your work summary for **{today().strftime('%A, %d %B')}**, {first}:", ""]
    overdue = [t for t in ranked if t["overdue"]]
    soon = [t for t in ranked if t["due_soon"] and not t["overdue"]]
    lines.append(f"**{len(tasks)} open task(s)** · {len(overdue)} overdue · {len(soon)} due in the next 2 days · "
                 f"{len(meetings)} meeting(s) today/tomorrow")
    if ranked:
        lines += ["", "**Priority list**"]
        for i, t in enumerate(ranked[:7], 1):
            tag = "🔴 overdue" if t["overdue"] else "⛔ blocked" if t["status"] == "blocked" else \
                "🟠 due soon" if t["due_soon"] else t["priority"].lower()
            lines.append(f"{i}. **{t['title']}** — {t['project']} · due {_fmt_date(t['due'])} · {tag}")
    if meetings:
        lines += ["", "**Meetings**"] + [f"- {_local(m['starts_at'])} — {m['title']} ({m['location']})" for m in meetings[:6]]
    if delayed:
        lines += ["", "**Projects needing attention**"] + [
            f"- {p['name']} ({p['id']}) — {_health(p['health'])}, deadline {_fmt_date(p['deadline'])}" for p in delayed[:4]]
    if d["approvals_waiting"]:
        lines += ["", f"📥 **{d['approvals_waiting']} approval(s)** are waiting for your decision in Approvals."]
    if d["pending_actions"]:
        lines += [f"🤖 **{d['pending_actions']} AI-prepared action(s)** are awaiting your confirmation."]
    if ranked:
        lines += ["", f"**Suggested focus:** start with *{ranked[0]['title']}*"
                      + (f", then *{ranked[1]['title']}*" if len(ranked) > 1 else "") + "."]
    return AgentReply("Productivity Agent", "\n".join(lines))


def _local(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    ist = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
    day = "today" if ist.date() == today() else "tomorrow" if ist.date() == today() + timedelta(days=1) else ist.strftime("%d %b")
    return f"{day} {ist.strftime('%H:%M')} IST"


def general_reply(ctx: ToolContext, u: Understanding) -> str:
    p = ctx.principal
    low = u.text.lower()
    if re.search(r"^\s*(thanks|thank you|ok(ay)?|cool)\b", low):
        return "You're welcome! Anything else I can help you with?"
    if is_guest(p):
        return ("Welcome to NovaTech Solutions. You are currently using **Guest Mode**. I can help you explore publicly "
                "available company information and demonstrate our enterprise AI capabilities — for example our "
                "products, office locations, public policies, announcements and public initiatives.\n\n"
                "Employee data, internal policies and workflows require an employee sign-in.")
    from .tools import TOOL_AGENT
    allowed = sorted({TOOL_AGENT[t] for t in TOOL_AGENT if check_tool(p.permissions, t).allowed})
    return (f"Hi {p.full_name.split()[0]} — I'm the NovaTech Solutions enterprise assistant. I answer from company "
            f"knowledge and records you're authorized to access, and I can get work done for you.\n\n"
            f"**Agents available to you:** {', '.join(allowed)}.\n\n"
            "Ask about policies and procedures, your projects and tasks, company analytics, or ask me to prepare "
            "tickets, leave and access requests — anything that changes data waits for your confirmation.")
