"""Agentic planning, risk, governance and observability helpers for NovaTech Solutions.

This module deliberately separates *planning* from hidden model reasoning. It returns a
safe, user-visible execution plan: actions, dependencies, required tools, risk and
approval gates. It never exposes chain-of-thought.
"""
from __future__ import annotations
import re
from datetime import date, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..core.rbac import LEVELS
from ..db.models import AuditLog, AIAction, Document, DocumentPermission, SecurityAlert, ToolExecution, User, WorkflowExecution

RISK_ORDER={"LOW":0,"MEDIUM":1,"HIGH":2,"CRITICAL":3}

def risk_for_goal(text:str, flags:dict|None=None)->str:
    t=text.lower()
    if re.search(r"\b(password|private key|api key|secret|bank|salary|compensation|executive|restricted)\b",t): return "CRITICAL"
    if re.search(r"\b(send|email|delete|archive|submit|approve|grant|revoke|external)\b",t): return "HIGH"
    if re.search(r"\b(leave|ticket|create|update|change)\b",t): return "MEDIUM"
    return "LOW"

def build_plan(text:str, flags:dict|None=None)->dict:
    t=text.lower(); flags=flags or {}
    steps=[]
    def add(k,label,kind="read",risk="LOW",approval=False,tool=None,depends=None):
        steps.append({"id":k,"label":label,"kind":kind,"risk":risk,"approval_required":approval,"tool":tool,"depends_on":depends or []})
    add("identity","Verify authenticated identity and tenant boundary")
    add("policy","Evaluate permissions, purpose and applicable policy","policy",risk_for_goal(text))
    if re.search(r"\b(meeting|calendar|tomorrow|today|weekly|report|briefing)\b",t):
        add("calendar","Collect authorized calendar context","read","LOW",False,"calendar.read",["policy"])
    if re.search(r"\b(project|phoenix|client|meeting|briefing|report)\b",t):
        add("knowledge","Retrieve authorized project/document evidence","read","LOW",False,"search_documents",["policy"])
    if re.search(r"\b(task|pending|work|weekly report)\b",t):
        add("tasks","Collect authorized task and project status","read","LOW",False,"search_tasks",["policy"])
    if re.search(r"\b(leave|day off|vacation|off)\b",t):
        add("leave_balance","Check leave balance and current leave policy","read","LOW",False,"get_leave_balance",["policy"])
        add("leave_request","Prepare leave request","write","MEDIUM",True,"create_leave_request",["leave_balance"])
    if re.search(r"\b(email|notify|message|tell my manager|let .* know)\b",t):
        add("draft","Prepare internal message","write","MEDIUM",True,"draft_email",[x for x in ("knowledge","policy") if any(z["id"]==x for z in steps)])
    if re.search(r"\b(ticket|it issue|service desk|laptop|vpn|network)\b",t):
        add("ticket","Prepare IT service request","write","MEDIUM",True,"create_it_ticket",["policy"])
    if re.search(r"\b(delete|archive|remove document)\b",t):
        add("delete","Prepare document archive/delete","write","HIGH",True,"delete_document",["policy","knowledge"])
    if not any(s["id"] in {"knowledge","tasks","leave_balance","leave_request","draft","ticket","delete","calendar"} for s in steps):
        add("understand","Interpret the goal and identify authorized data sources","analysis","LOW",False,None,["policy"])
        add("answer","Produce a grounded response with source/evidence metadata","output","LOW",False,None,["understand"])
    if any(s["approval_required"] for s in steps):
        add("approval","Pause at human approval gates","approval","MEDIUM",True,None,[s["id"] for s in steps if s["approval_required"]])
    add("verify","Verify every completed side effect before continuing","verify","LOW",False,None,[steps[-1]["id"]])
    add("audit","Persist audit, decision and data-lineage events","audit","LOW",False,None,["verify"])
    overall=max((RISK_ORDER[s["risk"]] for s in steps),default=0)
    return {"goal":text,"overall_risk":next(k for k,v in RISK_ORDER.items() if v==overall),"steps":steps,
            "principles":["least privilege","tenant isolation","data minimization","human control","post-action verification","complete auditability"]}

def metrics(db:Session, company_id:str)->dict:
    total=db.scalar(select(func.count(ToolExecution.id)).where(ToolExecution.company_id==company_id)) or 0
    failed=db.scalar(select(func.count(ToolExecution.id)).where(ToolExecution.company_id==company_id, ToolExecution.status.in_(["error","failed"]))) or 0
    actions=db.scalar(select(func.count(AIAction.id)).where(AIAction.company_id==company_id)) or 0
    pending=db.scalar(select(func.count(AIAction.id)).where(AIAction.company_id==company_id, AIAction.status=="pending_confirmation")) or 0
    workflows=db.scalar(select(func.count(WorkflowExecution.id)).where(WorkflowExecution.company_id==company_id)) or 0
    avg=db.scalar(select(func.avg(WorkflowExecution.duration_ms)).where(WorkflowExecution.company_id==company_id)) or 0
    alerts=db.scalar(select(func.count(SecurityAlert.id)).where(SecurityAlert.company_id==company_id, SecurityAlert.status!="resolved")) or 0
    return {"tool_executions":total,"tool_failures":failed,"action_proposals":actions,"pending_approvals":pending,
            "workflow_runs":workflows,"avg_workflow_ms":round(float(avg),1),"active_alerts":alerts,
            "estimated_cost_usd":round(total*0.0008,4),"note":"Estimated demo cost; not provider billing."}

def connectors()->list[dict]:
    return [
      {"id":"outlook","name":"Outlook / Teams","category":"Communication","mode":"DEMO CONNECTOR","scopes":["mail.read","mail.draft","calendar.read"]},
      {"id":"jira","name":"Jira","category":"Work","mode":"DEMO CONNECTOR","scopes":["issue.read","issue.create","issue.comment"]},
      {"id":"servicenow","name":"ServiceNow","category":"ITSM","mode":"DEMO CONNECTOR","scopes":["ticket.read","ticket.create"]},
      {"id":"sharepoint","name":"SharePoint / OneDrive","category":"Documents","mode":"DEMO CONNECTOR","scopes":["files.read"]},
      {"id":"entra","name":"Microsoft Entra ID","category":"Identity","mode":"DEMO SSO","scopes":["identity.read","groups.read"]},
    ]

def access_review(db:Session, company_id:str)->dict:
    users=db.scalars(select(User).where(User.company_id==company_id,User.is_active.is_(True))).all()
    grants=db.scalars(select(DocumentPermission).where(DocumentPermission.company_id==company_id)).all()
    expired=sum(1 for g in grants if g.expires_at and g.expires_at.date()<date.today())
    high=sum(1 for u in users if u.clearance in ("CONFIDENTIAL","RESTRICTED"))
    return {"employees":len(users),"reviews_required":max(1,round(len(users)*0.15)) if users else 0,
            "high_privilege_accounts":high,"temporary_grants":len(grants),"expired_grants":expired,
            "stale_permissions":expired,"campaign":"Quarterly Access Review"}

def replay(db:Session, company_id:str, workflow_id:str)->dict:
    wf=db.get(WorkflowExecution,workflow_id)
    if not wf or wf.company_id!=company_id: return {"found":False}
    events=db.scalars(select(AuditLog).where(AuditLog.company_id==company_id).order_by(AuditLog.ts.asc())).all()
    # Keep replay scoped to the workflow's user/time window; workflow id is also surfaced in details when present.
    scoped=[e for e in events if e.user_id==wf.user_id and (not wf.created_at or abs((e.ts-wf.created_at).total_seconds())<3600)]
    return {"found":True,"workflow":{"id":wf.id,"intent":wf.intent,"status":wf.status,"duration_ms":wf.duration_ms,"steps":wf.steps},
            "events":[{"ts":e.ts.isoformat(),"event":e.action,"result":e.result,"risk":e.risk,"permission":e.permission_result,
                       "tool":e.tool,"resource":e.resource,"reason":e.reason} for e in scoped[-100:]]}

def firewall_status()->list[dict]:
    return [
      {"layer":"Input","controls":["prompt injection","jailbreak patterns","external exfiltration"],"status":"ENFORCED","mode":"IMPLEMENTED"},
      {"layer":"Retrieval","controls":["tenant isolation","document authorization","quarantine","version checks"],"status":"ENFORCED","mode":"IMPLEMENTED"},
      {"layer":"Tool Gateway","controls":["scope validation","risk gate","approval gate","argument validation"],"status":"ENFORCED","mode":"IMPLEMENTED"},
      {"layer":"Output","controls":["DLP","secret masking","policy checks"],"status":"ENFORCED","mode":"IMPLEMENTED"},
      {"layer":"Infrastructure","controls":["DDoS","managed WAF","VPC/private subnets"],"status":"DESIGN ONLY","mode":"PROTOTYPE SIMULATION"},
    ]
