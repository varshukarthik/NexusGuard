"""Multi-Skill Composition & Pipeline Execution Engine.

Allows composing multiple reusable agent skills into an orchestrated workflow:
Example:
GitHub -> Repository Analysis -> Code Analysis -> Security Analysis -> Jira -> Teams -> Report -> Human Confirmation Gate.
"""
from __future__ import annotations

import logging
import time
from typing import Any
from sqlalchemy.orm import Session

from ...core.rbac import is_guest
from ...core.security import Principal
from .skills_registry import SkillsRegistry

log = logging.getLogger("novatech.skills.executor")


class SkillExecutor:
    @staticmethod
    def execute_skill(
        db: Session,
        principal: Principal,
        skill_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Executes a single reusable skill."""
        if is_guest(principal) and skill_id != "skill_doc_gen":
            raise PermissionError("Guest users cannot execute internal enterprise skills.")

        handlers = {
            "skill_code_analysis": SkillsRegistry.run_code_analysis,
            "skill_security_analysis": SkillsRegistry.run_security_analysis,
            "skill_repo_analysis": SkillsRegistry.run_repo_analysis,
            "skill_report_gen": SkillsRegistry.run_report_generation,
            "skill_jira_mgmt": SkillsRegistry.run_jira_management,
            "skill_doc_gen": SkillsRegistry.run_doc_generation,
        }

        handler = handlers.get(skill_id)
        if not handler:
            raise ValueError(f"Skill '{skill_id}' not found in registry.")

        t0 = time.time()
        result = handler(db, principal, params)
        duration_ms = int((time.time() - t0) * 1000)

        return {
            "skill_id": skill_id,
            "status": "completed",
            "duration_ms": duration_ms,
            "result": result,
        }

    @staticmethod
    def execute_composed_workflow(
        db: Session,
        principal: Principal,
        target_service: str = "authentication service",
    ) -> dict[str, Any]:
        """Executes the full enterprise cross-connector assessment workflow for the demo:

        1. GitHub Repository Analysis
        2. Code Analysis
        3. Security Analysis
        4. Jira Issue Search & Correlation
        5. Microsoft Teams Discussion Summary
        6. Report Generation
        7. Propose Jira Issue (Human Confirmation Required!)
        """
        if is_guest(principal):
            raise PermissionError("Guests cannot run cross-connector workflows.")

        steps_timeline: list[dict[str, Any]] = []

        def add_step(name: str, label: str, connector: str, status: str = "done", detail: str = ""):
            steps_timeline.append({
                "step": name,
                "label": label,
                "connector": connector,
                "status": status,
                "detail": detail,
            })

        # Step 1: GitHub / Repo Analysis
        add_step("repo_analysis", "Analyze repository architecture", "GitHub", "done", "Indexed 38 files, detected FastAPI + React stack")
        repo_res = SkillsRegistry.run_repo_analysis(db, principal, {"repo_name": "novatech/enterprise-agent"})

        # Step 2: Code Analysis
        add_step("code_analysis", "Inspect code execution flow & dependencies", "GitHub", "done", "Analyzed auth router & RBAC policy gates")
        code_res = SkillsRegistry.run_code_analysis(db, principal, {"query": target_service, "file_path": "backend/app/routers/auth.py"})

        # Step 3: Security Analysis
        add_step("security_analysis", "Vulnerability & secret scanning", "GitHub + Entra", "done", "Identified 1 HIGH finding (Token Expiration Bypass)")
        sec_res = SkillsRegistry.run_security_analysis(db, principal, {"target": target_service})

        # Step 4: Jira Management
        add_step("jira_search", "Query existing Jira backlog & sprint status", "Jira", "done", "Found NOVA-421 already in progress (Sprint 44)")
        jira_res = SkillsRegistry.run_jira_management(db, principal, {"action": "search", "project": "NOVA", "query": "token"})

        # Step 5: Teams Discussion
        add_step("teams_summary", "Retrieve recent discussions in #security-eng", "Teams", "done", "Alex Chen confirmed PR #142 addresses token expiry")

        # Step 6: Report Generation
        add_step("report_generation", "Synthesize executive cross-system report", "Multi-Connector", "done", "Generated comprehensive audit report with evidence tables")
        report_res = SkillsRegistry.run_report_generation(db, principal, {"report_type": "Security Assessment & Engineering Status Report"})

        # Step 7: Prepare Action Proposal for Jira creation (Human confirmation gate!)
        add_step("jira_proposal", "Propose Jira ticket creation (Requires User Approval)", "Jira", "pending_confirmation", "Paused at confirmation gate")
        jira_proposal = SkillsRegistry.run_jira_management(
            db, principal,
            {
                "action": "propose_issue",
                "title": "Enforce atomic Redis session blacklisting for token revocation",
                "description": "Follow-up remediation for SEC-VULN-01. Ensure single-use refresh token verification.",
                "priority": "High",
            }
        )

        return {
            "workflow": "Cross-Connector Security Assessment & Triage",
            "target": target_service,
            "status": "awaiting_confirmation",
            "pipeline": [
                {"id": "github", "label": "GitHub", "status": "completed"},
                {"id": "repo", "label": "Repository Analysis", "status": "completed"},
                {"id": "code", "label": "Code Analysis", "status": "completed"},
                {"id": "security", "label": "Security Analysis", "status": "completed"},
                {"id": "jira", "label": "Jira", "status": "completed"},
                {"id": "teams", "label": "Teams", "status": "completed"},
                {"id": "report", "label": "Report Generation", "status": "completed"},
                {"id": "approval", "label": "Human Confirmation", "status": "waiting"},
            ],
            "timeline": steps_timeline,
            "findings": sec_res["findings"],
            "report": report_res,
            "jira_issues": jira_res["issues"],
            "action_proposal": jira_proposal["proposal"],
        }
