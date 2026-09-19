"""Microsoft Entra ID Enterprise Connector Provider.

Handles enterprise identity, security groups, directory roles, and conditional access policies.
Strengthens identity-aware agent access:
User Identity -> Roles/Groups -> Connector Permissions -> Data Access -> Agent Permissions.
"""
from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....db.models import ConnectorItem, User

log = logging.getLogger("novatech.connectors.entra")


class EntraProvider:
    @staticmethod
    def get_directory_groups(company_id: str) -> list[dict[str, Any]]:
        return [
            {
                "id": "grp-sec-01",
                "displayName": "Security Engineering",
                "description": "Information Security engineers, SOC analysts, and security auditors.",
                "mail": "sec-eng@novatech.demo",
                "securityEnabled": True,
                "members_count": 8,
                "assigned_roles": ["Security Administrator", "Security Reader"],
            },
            {
                "id": "grp-eng-02",
                "displayName": "Core Backend Team",
                "description": "Engineers with access to core API gateways and production microservices.",
                "mail": "backend-core@novatech.demo",
                "securityEnabled": True,
                "members_count": 14,
                "assigned_roles": ["Contributor", "Service Desk Agent"],
            },
            {
                "id": "grp-ops-03",
                "displayName": "Cloud Platform Admin",
                "description": "DevOps and cloud infrastructure administrators.",
                "mail": "cloud-admin@novatech.demo",
                "securityEnabled": True,
                "members_count": 6,
                "assigned_roles": ["Global Administrator", "Privileged Role Administrator"],
            },
            {
                "id": "grp-all-04",
                "displayName": "All Employees (NovaTech)",
                "description": "Standard corporate directory group for all full-time personnel.",
                "mail": "all-staff@novatech.demo",
                "securityEnabled": True,
                "members_count": 120,
                "assigned_roles": ["User"],
            },
        ]

    @staticmethod
    def lookup_identity(db: Session, company_id: str, email_or_code: str) -> dict[str, Any] | None:
        u = db.scalar(
            select(User).where(
                User.company_id == company_id,
                (User.email == email_or_code) | (User.employee_code == email_or_code),
            )
        )
        if not u:
            return None

        # derive Entra ID directory context
        is_eng = u.department_id in ("dep_eng", "dep_engineering") or "engineer" in u.job_title.lower()
        is_sec = "security" in u.job_title.lower() or u.clearance == "RESTRICTED"

        groups = ["All Employees (NovaTech)"]
        if is_eng:
            groups.append("Core Backend Team")
        if is_sec:
            groups.append("Security Engineering")

        return {
            "id": f"entra_{u.employee_code.lower()}",
            "userPrincipalName": u.email,
            "displayName": u.full_name,
            "jobTitle": u.job_title,
            "clearance": u.clearance,
            "accountEnabled": u.is_active,
            "memberOf": groups,
            "assignedRoles": [u.job_title],
            "mfaStatus": "Enforced (Microsoft Authenticator)",
            "conditionalAccess": "Compliant (Managed Device)",
        }
