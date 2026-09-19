"""Agentic Work Mode and governance APIs."""
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession
from ..core.security import Principal, get_principal, require
from ..db.session import get_db
from ..services.agentic import build_plan, metrics, connectors, access_review, replay, firewall_status
from ..services import audit

router=APIRouter(tags=["agentic"])

class PlanIn(BaseModel):
    goal:str=Field(min_length=3,max_length=4000)

@router.post("/agentic/plan")
def plan(body:PlanIn,p:Principal=Depends(require("workspace:use"))):
    return build_plan(body.goal)

@router.get("/agentic/overview")
def overview(p:Principal=Depends(require("workspace:use")),db:DBSession=Depends(get_db)):
    if not p.has("admin:dashboard"):  # employees see controls, not organisation-wide telemetry
        return {"metrics":None,"connectors":connectors(),"firewall":firewall_status(),"access_review":None}
    return {"metrics":metrics(db,p.company_id),"connectors":connectors(),"firewall":firewall_status(),
            "access_review":access_review(db,p.company_id)}

@router.get("/agentic/connectors")
def connector_list(p:Principal=Depends(require("workspace:use"))):
    return connectors()

@router.get("/agentic/metrics")
def metric_view(p:Principal=Depends(require("admin:dashboard")),db:DBSession=Depends(get_db)):
    return metrics(db,p.company_id)

@router.get("/agentic/access-review")
def review(p:Principal=Depends(require("admin:dashboard")),db:DBSession=Depends(get_db)):
    return access_review(db,p.company_id)

@router.get("/agentic/replay/{workflow_id}")
def replay_workflow(workflow_id:str,p:Principal=Depends(require("audit:read_all")),db:DBSession=Depends(get_db)):
    return replay(db,p.company_id,workflow_id)

@router.get("/agentic/firewall")
def firewall(p:Principal=Depends(require("security:read"))):
    return firewall_status()

@router.post("/agentic/pause")
def pause_stub(p:Principal=Depends(require("workspace:use"))):
    # The current synchronous API cannot suspend an in-flight request; this endpoint provides
    # a truthful control-plane acknowledgement for the prototype UI.
    return {"status":"accepted","mode":"prototype","message":"Pause requested for the next agent checkpoint. In-flight synchronous calls cannot be interrupted."}

class RedTeamIn(BaseModel):
    attack_type: str = Field(pattern="^(Prompt Injection|Data Exfiltration|Privilege Escalation|Malicious Document|Cross-Tenant Access|Tool Abuse|PII Leakage|Indirect Prompt Injection)$")

@router.post("/agentic/red-team")
def red_team(body:RedTeamIn,p:Principal=Depends(require("security:read")),db:DBSession=Depends(get_db)):
    # Safe simulation: no real exploit is attempted and no security boundary is bypassed.
    import uuid
    audit.record(db, principal=p, action="security.red_team_simulation", resource=body.attack_type,
                 permission_result="BLOCKED", result="SIMULATED_BLOCK", risk="HIGH",
                 reason="Controlled demonstration; no exploit was executed", details={"attack_type":body.attack_type},
                 commit=True)
    return {"attack_type":body.attack_type,"detected":True,"action":"QUARANTINED","llm_exposure":0,
            "data_leaked":0,"audit_event":"SEC-"+uuid.uuid4().hex[:8].upper(),
            "mode":"SAFE SIMULATION","message":"Controlled attack simulation blocked by NovaTech Solutions policy."}
