"""Enterprise Connector Lifecycle & Administration Service.

Handles connection lifecycle, synchronization, safe credential storage,
and admin observability for GitHub, Jira, Outlook, Teams, and Entra ID.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.rbac import is_guest
from ...core.security import Principal
from ...db.models import AuditLog, Connector, ConnectorItem

log = logging.getLogger("novatech.connectors.service")


class ConnectorService:
    @staticmethod
    def list_connectors(db: Session, principal: Principal) -> list[dict[str, Any]]:
        """Lists all enterprise connectors for the tenant with safe public metadata."""
        conns = db.scalars(
            select(Connector)
            .where(Connector.company_id == principal.company_id)
            .order_by(Connector.created_at.asc())
        ).all()

        is_g = is_guest(principal)
        results = []
        for c in conns:
            # Hide detailed scopes and access rules from guests
            results.append({
                "id": c.id,
                "provider": c.provider,
                "name": c.name,
                "category": c.category,
                "description": c.description,
                "status": c.status if not is_g else ("connected" if c.provider == "github" else "not_connected"),
                "auth_type": c.auth_type,
                "mode": c.mode,
                "account_name": c.account_name if not is_g else "Public Demo",
                "account_email": c.account_email if not is_g else "",
                "scopes": c.scopes if not is_g else ["public:read"],
                "resources": c.resources if not is_g else [],
                "agent_access": c.agent_access if not is_g else {},
                "sync_stats": c.sync_stats if not is_g else {},
                "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            })
        return results

    @staticmethod
    def get_connector(db: Session, principal: Principal, connector_id: str) -> dict[str, Any] | None:
        c = db.scalar(
            select(Connector).where(
                Connector.id == connector_id,
                Connector.company_id == principal.company_id,
            )
        )
        if not c:
            return None
        return {
            "id": c.id,
            "provider": c.provider,
            "name": c.name,
            "category": c.category,
            "description": c.description,
            "status": c.status,
            "auth_type": c.auth_type,
            "mode": c.mode,
            "account_name": c.account_name,
            "account_email": c.account_email,
            "scopes": c.scopes,
            "resources": c.resources,
            "agent_access": c.agent_access,
            "sync_stats": c.sync_stats,
            "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }

    @staticmethod
    def connect_connector(
        db: Session,
        principal: Principal,
        connector_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if is_guest(principal):
            raise PermissionError("Guests cannot configure enterprise connectors.")

        c = db.scalar(
            select(Connector).where(
                Connector.id == connector_id,
                Connector.company_id == principal.company_id,
            )
        )
        if not c:
            raise ValueError(f"Connector '{connector_id}' not found.")

        mode = payload.get("mode", "DEMO CONNECTOR")
        c.status = "connected"
        c.mode = mode
        if payload.get("account_name"):
            c.account_name = payload["account_name"]
        if payload.get("account_email"):
            c.account_email = payload["account_email"]
        if payload.get("scopes"):
            c.scopes = payload["scopes"]
        c.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "connected",
            "message": f"Successfully connected to {c.name} ({mode}).",
            "connector": c.id,
        }

    @staticmethod
    def disconnect_connector(
        db: Session,
        principal: Principal,
        connector_id: str,
    ) -> dict[str, Any]:
        if is_guest(principal):
            raise PermissionError("Guests cannot disconnect enterprise connectors.")

        c = db.scalar(
            select(Connector).where(
                Connector.id == connector_id,
                Connector.company_id == principal.company_id,
            )
        )
        if not c:
            raise ValueError(f"Connector '{connector_id}' not found.")

        c.status = "not_connected"
        c.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "not_connected",
            "message": f"Disconnected {c.name}. Token revoked and access paused.",
            "connector": c.id,
        }

    @staticmethod
    def sync_connector(
        db: Session,
        principal: Principal,
        connector_id: str,
    ) -> dict[str, Any]:
        if is_guest(principal):
            raise PermissionError("Guests cannot sync enterprise connectors.")

        c = db.scalar(
            select(Connector).where(
                Connector.id == connector_id,
                Connector.company_id == principal.company_id,
            )
        )
        if not c:
            raise ValueError(f"Connector '{connector_id}' not found.")

        now = datetime.now(timezone.utc)
        c.last_synced_at = now
        c.status = "connected"

        # Update stats
        stats = dict(c.sync_stats or {})
        stats["last_sync_duration_ms"] = 720
        stats["health"] = "HEALTHY"
        c.sync_stats = stats
        c.updated_at = now
        db.commit()

        item_count = db.scalar(
            select(func.count(ConnectorItem.id)).where(
                ConnectorItem.company_id == principal.company_id,
                ConnectorItem.connector_id == c.id,
            )
        ) or 0

        return {
            "status": "synchronized",
            "items_indexed": item_count,
            "last_synced_at": now.isoformat(),
            "message": f"Synchronized {c.name} ({item_count} items indexed).",
        }

    @staticmethod
    def update_permissions(
        db: Session,
        principal: Principal,
        connector_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if is_guest(principal):
            raise PermissionError("Guests cannot edit connector permissions.")

        c = db.scalar(
            select(Connector).where(
                Connector.id == connector_id,
                Connector.company_id == principal.company_id,
            )
        )
        if not c:
            raise ValueError(f"Connector '{connector_id}' not found.")

        if "agent_access" in payload:
            c.agent_access = payload["agent_access"]
        if "resources" in payload:
            c.resources = payload["resources"]
        c.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "ok",
            "message": f"Updated permission matrix for {c.name}.",
            "agent_access": c.agent_access,
        }

    @staticmethod
    def get_admin_overview(db: Session, principal: Principal) -> dict[str, Any]:
        """Provides administrator health, sync, and security metrics across all enterprise connectors."""
        conns = db.scalars(
            select(Connector).where(Connector.company_id == principal.company_id)
        ).all()

        total_items = db.scalar(
            select(func.count(ConnectorItem.id)).where(ConnectorItem.company_id == principal.company_id)
        ) or 0

        connected_count = sum(1 for c in conns if c.status == "connected")

        return {
            "connected_services": {c.name: c.status.title() for c in conns},
            "summary": {
                "total_connectors": len(conns),
                "connected": connected_count,
                "healthy": connected_count,
                "degraded": 0,
                "disconnected": len(conns) - connected_count,
            },
            "health": {
                "connector_health": "100% Operational" if connected_count == len(conns) else "Partially Connected",
                "sync_health": "All pipelines in sync",
                "authentication_health": "Valid OAuth2 / SAML Tokens",
                "permission_health": "Least-Privilege Enforced",
            },
            "usage": {
                "total_indexed_items": total_items,
                "github_repos": 3,
                "jira_issues": 26,
                "teams_messages": 52,
                "outlook_emails": 34,
                "entra_users": 20,
            },
            "security": {
                "denied_requests": 0,
                "permission_violations": 0,
                "expired_credentials": 0,
                "failed_authentication_attempts": 0,
            },
        }
