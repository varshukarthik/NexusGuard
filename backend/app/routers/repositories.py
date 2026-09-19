"""API endpoints for repository ingestion, GitHub connection, security audits, and synchronization."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DBSession

from ..core.errors import AppError
from ..core.rbac import LEVELS, is_guest, norm_level
from ..core.security import Principal, get_principal, require
from ..db.models import (Repository, RepositoryChunk, RepositoryConnection,
                         RepositoryFile, new_id)
from ..db.session import get_db
from ..services import audit
from ..services.repo_ingestion import (ingest_repository_files,
                                       load_repository_content,
                                       sync_repository, validate_github_url)
from ..services.repo_retrieval import check_repo_access

log = logging.getLogger("novatech.repositories")
router = APIRouter(prefix="/repositories", tags=["repositories"])


class RepoValidateRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL or owner/repo")
    branch: Optional[str] = "main"


class RepoImportRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL or local reference")
    name: Optional[str] = None
    default_branch: Optional[str] = "main"
    classification: Optional[str] = "INTERNAL"
    allowed_departments: Optional[list[str]] = Field(default_factory=lambda: ["*"])
    sync_interval: Optional[str] = "manual"
    description: Optional[str] = None


class RepoConnectOAuthRequest(BaseModel):
    code: Optional[str] = None
    demo_mode: Optional[bool] = True


def repo_to_dict(repo: Repository, allowed: bool = True, access_rule: str = "rbac") -> dict:
    scan_report = repo.security_scan.get("findings", []) if isinstance(repo.security_scan, dict) else (repo.security_scan or [])
    return {
        "id": repo.id,
        "company_id": repo.company_id,
        "name": repo.name,
        "repo_name": repo.full_name,
        "owner_login": repo.full_name.split("/")[0] if "/" in repo.full_name else "novatech",
        "clone_url": repo.github_url,
        "default_branch": repo.default_branch,
        "classification": repo.classification,
        "allowed_departments": repo.allowed_departments or ["*"],
        "allowed_roles": repo.allowed_roles or ["*"],
        "status": (repo.status or "ready").upper(),
        "total_files": repo.file_count,
        "total_lines": 0,
        "total_chunks": repo.chunk_count,
        "sync_interval": "manual",
        "last_synced_at": repo.last_synced_at.isoformat() if repo.last_synced_at else None,
        "created_at": repo.created_at.isoformat() if repo.created_at else None,
        "tree_structure": repo.tree_structure or [],
        "security_scan_report": scan_report,
        "secrets_count": len(scan_report),
        "description": repo.description,
        "access": "granted" if allowed else "denied",
        "access_rule": access_rule,
    }


@router.get("")
def list_repositories(
    p: Principal = Depends(get_principal),
    db: DBSession = Depends(get_db),
):
    """Lists repositories visible within the principal's company and clearance scope."""
    repos = list(db.scalars(
        select(Repository).where(Repository.company_id == p.company_id).order_by(Repository.created_at.desc())
    ).all())

    results = []
    for r in repos:
        allowed, rule = check_repo_access(p, r)
        # Guests only see public repositories
        if is_guest(p) and not allowed:
            continue
        results.append(repo_to_dict(r, allowed=allowed, access_rule=rule))

    return {"repositories": results, "total": len(results)}


@router.post("/validate")
def validate_repo(
    body: RepoValidateRequest,
    p: Principal = Depends(get_principal),
):
    """Validates GitHub repository URL format and connectivity."""
    try:
        owner, repo = validate_github_url(body.repo_url)
        return {
            "valid": True,
            "owner": owner,
            "repo": repo,
            "normalized_url": f"https://github.com/{owner}/{repo}",
            "branch": body.branch or "main",
            "message": f"Successfully verified repository {owner}/{repo}",
        }
    except AppError as exc:
        return {"valid": False, "error": exc.code, "message": exc.message}


@router.post("/connect")
def connect_github(
    body: RepoConnectOAuthRequest,
    p: Principal = Depends(require("repositories:import")),
    db: DBSession = Depends(get_db),
):
    """Connects or verifies GitHub OAuth / demo connection."""
    if is_guest(p):
        raise AppError(403, "forbidden", "Guest accounts cannot connect repositories.")

    conn = db.scalar(
        select(RepositoryConnection).where(
            RepositoryConnection.company_id == p.company_id,
            RepositoryConnection.user_id == p.user_id,
            RepositoryConnection.provider == "github",
        )
    )
    if not conn:
        conn = RepositoryConnection(
            id=new_id("ghconn_"),
            company_id=p.company_id,
            user_id=p.user_id,
            provider="github",
            github_user=p.email.split("@")[0] or "novatech-dev",
            scopes=["repo", "read:org"],
        )
        db.add(conn)
        db.commit()

    return {
        "status": "connected",
        "provider": "github",
        "account_login": conn.github_user,
        "scopes": conn.scopes,
        "created_at": conn.created_at.isoformat() if conn.created_at else None,
    }


@router.post("/import")
def import_repository(
    body: RepoImportRequest,
    p: Principal = Depends(require("repositories:import")),
    db: DBSession = Depends(get_db),
):
    """Triggers the full repository import and indexing pipeline."""
    if is_guest(p):
        raise AppError(403, "forbidden", "Guest accounts cannot import repositories into the enterprise knowledge base.")

    # Validate URL
    owner, repo_name = validate_github_url(body.repo_url)
    display_name = body.name or repo_name

    # Validate classification clearance
    req_cls = norm_level(body.classification or "INTERNAL")
    if LEVELS.get(norm_level(p.clearance), 0) < LEVELS.get(req_cls, 99):
        raise AppError(403, "insufficient_clearance", "You cannot import a repository at a classification higher than your clearance.")

    # Check if duplicate repository in company
    existing = db.scalar(
        select(Repository).where(
            Repository.company_id == p.company_id,
            Repository.full_name == f"{owner}/{repo_name}".lower(),
        )
    )
    if existing:
        repo = existing
        repo.status = "scanning"
        repo.classification = req_cls
        repo.default_branch = body.default_branch or "main"
        if body.allowed_departments:
            repo.allowed_departments = body.allowed_departments
        db.commit()
    else:
        repo = Repository(
            id=new_id("repo_"),
            company_id=p.company_id,
            name=display_name,
            full_name=f"{owner}/{repo_name}".lower(),
            github_url=f"https://github.com/{owner}/{repo_name}",
            default_branch=body.default_branch or "main",
            classification=req_cls,
            allowed_departments=body.allowed_departments or ["*"],
            allowed_roles=["*"],
            status="scanning",
            description=body.description or f"Imported GitHub repository {owner}/{repo_name}",
        )
        db.add(repo)
        db.commit()

    # Load and ingest files
    try:
        files = load_repository_content(body.repo_url, branch=body.default_branch or "main")
        ingestion_res = ingest_repository_files(db, repo, files, user_id=p.user_id)
        
        audit.record(
            db,
            principal=p,
            action="repository.import",
            resource=repo.full_name,
            resource_id=repo.id,
            classification=repo.classification,
            permission_result="ALLOWED",
            result="SUCCESS",
            reason=f"Repository {repo.full_name} imported successfully ({ingestion_res['total_files']} files, {ingestion_res['total_chunks']} chunks)",
            risk="LOW",
            commit=True,
        )

        return {
            "message": f"Repository '{repo.full_name}' imported and indexed successfully.",
            "repository": repo_to_dict(repo, allowed=True),
            "stats": ingestion_res,
        }
    except Exception as exc:
        repo.status = "failed"
        db.commit()
        log.exception("Repository import failed for %s", body.repo_url)
        raise AppError(500, "import_failed", f"Failed to ingest repository: {str(exc)}")


@router.get("/{repo_id}")
def get_repository(
    repo_id: str,
    p: Principal = Depends(get_principal),
    db: DBSession = Depends(get_db),
):
    """Retrieves full repository metadata, file tree, and security scan report."""
    repo = db.get(Repository, repo_id)
    if not repo or repo.company_id != p.company_id:
        raise AppError(404, "not_found", "Repository not found.")

    allowed, rule = check_repo_access(p, repo)
    if not allowed:
        raise AppError(403, "forbidden", f"Access denied to this repository ({rule}).")

    return repo_to_dict(repo, allowed=allowed, access_rule=rule)


@router.get("/{repo_id}/status")
def get_repository_status(
    repo_id: str,
    p: Principal = Depends(get_principal),
    db: DBSession = Depends(get_db),
):
    """Checks the real-time ingestion / sync status of a repository."""
    repo = db.get(Repository, repo_id)
    if not repo or repo.company_id != p.company_id:
        raise AppError(404, "not_found", "Repository not found.")

    return {
        "id": repo.id,
        "repo_name": repo.full_name,
        "status": repo.status,
        "total_files": repo.file_count,
        "total_chunks": repo.chunk_count,
        "last_synced_at": repo.last_synced_at.isoformat() if repo.last_synced_at else None,
        "secrets_redacted": len(repo.security_scan.get("findings", []) if isinstance(repo.security_scan, dict) else (repo.security_scan or [])),
    }


@router.post("/{repo_id}/sync")
def trigger_sync(
    repo_id: str,
    p: Principal = Depends(require("repositories:manage")),
    db: DBSession = Depends(get_db),
):
    """Triggers an incremental hash-based synchronization for an existing repository."""
    if is_guest(p):
        raise AppError(403, "forbidden", "Guest accounts cannot sync repositories.")

    repo = db.get(Repository, repo_id)
    if not repo or repo.company_id != p.company_id:
        raise AppError(404, "not_found", "Repository not found.")

    allowed, rule = check_repo_access(p, repo)
    if not allowed:
        raise AppError(403, "forbidden", f"You do not have clearance to sync this repository ({rule}).")

    sync_res = sync_repository(db, repo_id, user_id=p.user_id)

    audit.record(
        db,
        principal=p,
        action="repository.sync",
        resource=repo.full_name,
        resource_id=repo.id,
        classification=repo.classification,
        permission_result="ALLOWED",
        result="SUCCESS",
        reason=f"Repository {repo.full_name} synchronized incrementally ({sync_res['total_files']} files, {sync_res['total_chunks']} chunks)",
        risk="LOW",
        commit=True,
    )

    return {"message": "Repository synchronized successfully.", "stats": sync_res}


@router.delete("/{repo_id}")
def delete_repository(
    repo_id: str,
    p: Principal = Depends(require("repositories:manage")),
    db: DBSession = Depends(get_db),
):
    """Disconnects and removes a repository and all indexed chunks."""
    if is_guest(p):
        raise AppError(403, "forbidden", "Guest accounts cannot delete repositories.")

    repo = db.get(Repository, repo_id)
    if not repo or repo.company_id != p.company_id:
        raise AppError(404, "not_found", "Repository not found.")

    # Remove all chunks and files
    db.execute(delete(RepositoryChunk).where(RepositoryChunk.repository_id == repo.id))
    db.execute(delete(RepositoryFile).where(RepositoryFile.repository_id == repo.id))
    db.delete(repo)
    db.commit()

    audit.record(
        db,
        principal=p,
        action="repository.delete",
        resource=repo.full_name,
        resource_id=repo.id,
        classification=repo.classification,
        permission_result="ALLOWED",
        result="SUCCESS",
        reason=f"Repository {repo.full_name} disconnected and purged from index",
        risk="MEDIUM",
        commit=True,
    )

    return {"message": f"Repository '{repo.full_name}' disconnected successfully."}
