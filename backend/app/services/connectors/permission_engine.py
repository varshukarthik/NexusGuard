"""Centralized Permission & Least-Privilege Authorization Engine for Enterprise Connectors.

Enforces:
User Identity -> Roles/Clearance -> Connector Permissions -> Resource Permissions -> Agent Access -> Data Retrieval.

The LLM is NEVER the authorization layer. Every access to connected data is checked server-side
and audited.
"""
from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.rbac import LEVELS, is_guest
from ...core.security import Principal
from ...db.models import Connector, ConnectorItem

log = logging.getLogger("novatech.connectors.permissions")


class ConnectorPermissionDecision:
    def __init__(self, allowed: bool, reason: str, connector: Connector | None = None, classification: str = "INTERNAL"):
        self.allowed = allowed
        self.reason = reason
        self.connector = connector
        self.classification = classification

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "classification": self.classification,
            "connector_id": self.connector.id if self.connector else None,
        }


def check_connector_access(
    db: Session,
    principal: Principal,
    connector_id: str,
    action: str = "READ",
    resource: str | None = None,
    agent_name: str | None = None,
) -> ConnectorPermissionDecision:
    """Verifies that the principal and requesting agent have least-privilege permission

    to perform `action` on `connector_id` and optional `resource`.
    """
    # 1. Tenant Boundary
    connector = db.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.company_id == principal.company_id,
        )
    )
    if not connector:
        return ConnectorPermissionDecision(
            allowed=False,
            reason=f"Connector '{connector_id}' not found or belongs to another tenant.",
        )

    # 2. Guest Boundary: Guests can NEVER access private enterprise connectors
    if is_guest(principal):
        return ConnectorPermissionDecision(
            allowed=False,
            reason="Guest users cannot access enterprise connectors or internal system data.",
            connector=connector,
        )

    # 3. Connector Connection State
    if connector.status != "connected":
        return ConnectorPermissionDecision(
            allowed=False,
            reason=f"Connector '{connector.name}' is currently {connector.status.replace('_', ' ')}.",
            connector=connector,
        )

    # 4. Action / Operation Type Verification (Read vs Write/Execute)
    action_upper = action.upper()
    read_write = connector.agent_access.get("read_write", {})
    if action_upper in ("CREATE", "UPDATE", "DELETE"):
        if not read_write.get(action_upper.lower(), False):
            return ConnectorPermissionDecision(
                allowed=False,
                reason=f"Action '{action_upper}' is not permitted by connector policy for '{connector.name}'.",
                connector=connector,
            )

    # 5. Agent-Level Access Control
    if agent_name:
        allowed_agents = connector.agent_access.get("allowed_agents", [])
        if allowed_agents and "*" not in allowed_agents and agent_name not in allowed_agents:
            return ConnectorPermissionDecision(
                allowed=False,
                reason=f"Agent '{agent_name}' is not authorized to access '{connector.name}'.",
                connector=connector,
            )

    # 6. Resource-Level Permission Check
    if resource and connector.resources:
        allowed_res = connector.agent_access.get("allowed_resources", ["*"])
        if "*" not in allowed_res:
            res_match = any(r.lower() in resource.lower() for r in allowed_res)
            if not res_match:
                return ConnectorPermissionDecision(
                    allowed=False,
                    reason=f"Resource '{resource}' is outside the authorized scope for connector '{connector.name}'.",
                    connector=connector,
                )

    # 7. Clearance Enforcement
    user_clearance = getattr(principal, "clearance", "INTERNAL")
    user_level = LEVELS.get(user_clearance, 1)

    # By default internal connector data requires at least INTERNAL clearance
    if user_level < LEVELS.get("INTERNAL", 1):
        return ConnectorPermissionDecision(
            allowed=False,
            reason=f"Clearance '{user_clearance}' is insufficient for enterprise connector data.",
            connector=connector,
        )

    return ConnectorPermissionDecision(
        allowed=True,
        reason="Authorized under least-privilege connector policy.",
        connector=connector,
        classification="INTERNAL",
    )


def filter_connector_items(
    items: list[ConnectorItem],
    principal: Principal,
) -> list[ConnectorItem]:
    """Filters a list of retrieved connector items according to tenant boundary

    and clearance levels.
    """
    if is_guest(principal):
        return []

    user_clearance = getattr(principal, "clearance", "INTERNAL")
    user_level = LEVELS.get(user_clearance, 1)

    accessible: list[ConnectorItem] = []
    for item in items:
        if item.company_id != principal.company_id:
            continue
        item_level = LEVELS.get(item.classification, 1)
        if user_level >= item_level:
            accessible.append(item)

    return accessible
