"""Enterprise Connectors Router.

Endpoints for managing GitHub, Jira, Microsoft Outlook, Microsoft Teams, and Microsoft Entra ID.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import Principal, get_principal
from ..db.session import get_db
from ..services.connectors.connector_service import ConnectorService

router = APIRouter(prefix="/connectors", tags=["connectors"])


class ConnectPayload(BaseModel):
    mode: str = "DEMO CONNECTOR"
    account_name: str | None = None
    account_email: str | None = None
    scopes: list[str] | None = None


class PermissionsPayload(BaseModel):
    agent_access: dict[str, Any] | None = None
    resources: list[str] | None = None


@router.get("")
def list_connectors(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """List all enterprise connectors available for the current tenant."""
    return {"connectors": ConnectorService.list_connectors(db, principal)}


@router.get("/admin/overview")
def get_admin_overview(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """Admin dashboard providing connector health, sync health, usage, and security status."""
    return ConnectorService.get_admin_overview(db, principal)


@router.get("/{connector_id}")
def get_connector(
    connector_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    conn = ConnectorService.get_connector(db, principal, connector_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")
    return conn


@router.post("/{connector_id}/connect")
def connect_connector(
    connector_id: str,
    payload: ConnectPayload,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    try:
        return ConnectorService.connect_connector(db, principal, connector_id, payload.model_dump(exclude_unset=True))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{connector_id}/sync")
def sync_connector(
    connector_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    try:
        return ConnectorService.sync_connector(db, principal, connector_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{connector_id}/disconnect")
def disconnect_connector(
    connector_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    try:
        return ConnectorService.disconnect_connector(db, principal, connector_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{connector_id}/permissions")
def update_permissions(
    connector_id: str,
    payload: PermissionsPayload,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    try:
        return ConnectorService.update_permissions(db, principal, connector_id, payload.model_dump(exclude_unset=True))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
