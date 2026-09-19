"""Enterprise Reusable Agent Skills Router.

Endpoints for managing the Skills Library, inspecting skill metadata, and executing single/composed skills.
"""
from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import Principal, get_principal
from ..db.models import AgentSkillModel
from ..db.session import get_db
from ..services.skills.skill_executor import SkillExecutor
from ..services.skills.skills_registry import SkillsRegistry

log = logging.getLogger("novatech.skills")
router = APIRouter(prefix="/skills", tags=["skills"])


class ExecuteSkillPayload(BaseModel):
    skill_id: str = Field(..., description="ID of the skill to execute or 'composed_workflow'")
    params: dict[str, Any] = Field(default_factory=dict, description="Execution parameters for the skill")
    workflow: str | None = Field(default=None, description="Workflow pipeline name for composite runs")
    target: str | None = Field(default=None, description="Target component or service for assessment")


class UpdateSkillPayload(BaseModel):
    status: str | None = None
    instructions: str | None = None
    security_restrictions: str | None = None


@router.get("")
def list_skills(
    category: str | None = Query(default=None),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """List all registered enterprise agent skills."""
    stmt = select(AgentSkillModel)
    if category:
        stmt = stmt.where(AgentSkillModel.category == category)
    skills = db.scalars(stmt).all()

    # Fallback to in-memory registry declarations if DB empty
    if not skills:
        return {"skills": SkillsRegistry.list_skills()}

    result = []
    for s in skills:
        result.append({
            "id": s.id,
            "name": s.name,
            "category": s.category,
            "description": s.description,
            "version": s.version,
            "status": s.status,
            "required_connectors": s.required_connectors or [],
            "required_permissions": s.required_permissions or [],
            "tools": s.tools or [],
            "input_schema": s.input_schema or {},
            "output_schema": s.output_schema or {},
            "instructions": s.instructions or "",
            "security_restrictions": s.security_restrictions or "",
            "agents_using": s.agents_using or [],
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })
    return {"skills": result}


@router.get("/{skill_id}")
def get_skill(
    skill_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """Get detailed specification for an agent skill."""
    skill = db.get(AgentSkillModel, skill_id)
    if not skill:
        # Check static registry
        static_s = SkillsRegistry.get_skill(skill_id)
        if static_s:
            return static_s
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    return {
        "id": skill.id,
        "name": skill.name,
        "category": skill.category,
        "description": skill.description,
        "version": skill.version,
        "status": skill.status,
        "required_connectors": skill.required_connectors or [],
        "required_permissions": skill.required_permissions or [],
        "tools": skill.tools or [],
        "input_schema": skill.input_schema or {},
        "output_schema": skill.output_schema or {},
        "instructions": skill.instructions or "",
        "security_restrictions": skill.security_restrictions or "",
        "agents_using": skill.agents_using or [],
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
        "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
    }


@router.post("/execute")
def execute_skill(
    payload: ExecuteSkillPayload,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """Execute a single agent skill or run the composed cross-connector enterprise workflow."""
    try:
        if payload.skill_id in ("composed_workflow", "enterprise_assessment", "demo_pipeline") or payload.workflow:
            target = payload.target or payload.params.get("target") or "authentication service"
            result = SkillExecutor.execute_composed_workflow(db, principal, target_service=target)
            return {"execution_type": "composed_workflow", **result}

        result = SkillExecutor.execute_skill(db, principal, payload.skill_id, payload.params)
        return {"execution_type": "single_skill", **result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("Skill execution failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Skill execution failed: {str(e)}")


@router.patch("/{skill_id}")
def update_skill(
    skill_id: str,
    payload: UpdateSkillPayload,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """Update skill status or instructions (Admin only)."""
    if not principal.has("system:configure") and principal.role_code != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Only administrators can modify agent skills.")

    skill = db.get(AgentSkillModel, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    if payload.status is not None:
        skill.status = payload.status
    if payload.instructions is not None:
        skill.instructions = payload.instructions
    if payload.security_restrictions is not None:
        skill.security_restrictions = payload.security_restrictions

    db.commit()
    db.refresh(skill)

    return {
        "id": skill.id,
        "name": skill.name,
        "status": skill.status,
        "instructions": skill.instructions,
        "security_restrictions": skill.security_restrictions,
    }
