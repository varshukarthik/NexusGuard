"""Tests for Repository Import, Secret Scanning, RBAC Authorization, and Code Search."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test_repo.db"
os.environ["OPENAI_API_KEY"] = ""
os.environ["CHAT_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_PER_MINUTE"] = "5000"
os.environ["LOGIN_RATE_LIMIT_PER_MINUTE"] = "1000"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.repo_ingestion import (
    compute_file_hash,
    detect_language,
    scan_and_redact_secrets,
    should_skip_file,
    validate_github_url,
)
from app.services.repo_retrieval import check_repo_access, retrieve_repository_chunks


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(c, email):
    r = c.post("/api/auth/sso/demo", json={"email": email})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_validate_github_url():
    owner, repo = validate_github_url("https://github.com/novatech/enterprise-agent")
    assert owner == "novatech"
    assert repo == "enterprise-agent"

    owner2, repo2 = validate_github_url("varshukarthik/NexusGuard")
    assert owner2 == "varshukarthik"
    assert repo2 == "NexusGuard"

    with pytest.raises(Exception):
        validate_github_url("https://gitlab.com/novatech/project")

    with pytest.raises(Exception):
        validate_github_url("not a url")


def test_secret_scanning_and_redaction():
    code_with_secrets = """
    OPENAI_API_KEY = "sk-proj-abc1234567890abcdef1234567890abcdef1234"
    GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
    print("Connecting to DB...")
    """
    redacted, findings = scan_and_redact_secrets(code_with_secrets, "config.py")
    assert len(findings) >= 3
    assert "sk-proj-abc1234567890abcdef1234567890abcdef1234" not in redacted
    assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED_" in redacted


def test_file_exclusion_rules():
    assert should_skip_file(".git/config") is True
    assert should_skip_file("node_modules/react/index.js") is True
    assert should_skip_file("dist/bundle.js") is True
    assert should_skip_file("assets/image.png") is True
    assert should_skip_file(".env") is True
    assert should_skip_file("backend/app/main.py") is False
    assert should_skip_file("frontend/src/App.tsx") is False


def test_guest_blocked_from_import(client):
    # Attempt to import as Guest
    login_resp = client.post("/api/auth/guest")
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]

    import_resp = client.post(
        "/api/repositories/import",
        json={"repo_url": "https://github.com/novatech/demo-repo"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Guest must be forbidden (403)
    assert import_resp.status_code == 403


def test_engineer_can_list_and_validate(client):
    # Login as Priya (Engineering Lead)
    h = login(client, "priya.reddy@novatech.demo")

    # Validate endpoint
    val_resp = client.post(
        "/api/repositories/validate",
        json={"repo_url": "https://github.com/novatech/enterprise-agent"},
        headers=h,
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["valid"] is True

    # List endpoint
    list_resp = client.get("/api/repositories", headers=h)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "repositories" in data
    assert data["total"] >= 1
    repo = data["repositories"][0]
    assert repo["status"] == "READY"
    assert repo["total_files"] > 0


def test_repository_search_and_citation(client):
    from app.services.repo_retrieval import retrieve_repository_chunks
    from app.core.security import Principal
    from app.db.models import User
    from app.db.session import SessionLocal
    from sqlalchemy import select

    h = login(client, "priya.reddy@novatech.demo")

    # Call AI agent with a technical code question
    chat_resp = client.post(
        "/api/chat",
        json={"message": "Where is the RBAC check_access function implemented in our codebase?"},
        headers=h,
    )
    assert chat_resp.status_code == 200
    res_data = chat_resp.json()
    assert "assistant_message" in res_data
    assert len(res_data["assistant_message"]["content"]) > 0

    # Test direct repository chunk retrieval & citation generation
    with SessionLocal() as db:
        priya = db.scalar(select(User).where(User.email == "priya.reddy@novatech.demo"))
        p = Principal(
            user_id=priya.id,
            company_id=priya.company_id,
            company_name="NovaTech Solutions",
            employee_code=priya.employee_code,
            full_name=priya.full_name,
            email=priya.email,
            department=priya.department.name,
            role_code=priya.role.code,
            role_name=priya.role.name,
            job_title=priya.job_title,
            manager_id=priya.manager_id,
            clearance=priya.clearance,
            permissions=set(priya.role.permissions or []),
            session_id="test_sess",
            auth_method="demo",
        )
        retrieval = retrieve_repository_chunks(db, p, "check_access rbac", limit=5)
        assert retrieval.authorized_repos >= 1
        assert len(retrieval.hits) >= 1
        hit = retrieval.hits[0]
        assert hit.file_path != ""
        assert "http" in hit.github_url
        assert hit.start_line >= 1
        citation = hit.to_citation()
        assert citation["type"] == "repository_file"
        assert ":" in citation["citation"]


def test_multi_tenant_isolation(client):
    # Orbit tenant user cannot see NovaTech repos
    h = login(client, "maya.collins@orbitlabs.demo")
    orbit_repos = client.get("/api/repositories", headers=h).json()
    for r in orbit_repos.get("repositories", []):
        assert r["company_id"] == "cmp_orbit"
        assert r["company_id"] != "cmp_novatech"
