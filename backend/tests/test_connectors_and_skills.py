"""Tests for Enterprise Connectors, Least-Privilege Engine, Reusable Skills, and Composed Workflows."""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test_connectors.db"
os.environ["OPENAI_API_KEY"] = ""
os.environ["CHAT_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_PER_MINUTE"] = "5000"
os.environ["LOGIN_RATE_LIMIT_PER_MINUTE"] = "1000"

from app.main import app
from app.services.connectors.permission_engine import check_connector_access
from app.services.skills.skill_executor import SkillExecutor


RAHUL, PRIYA, ANANYA, VIKRAM, ARJUN = (f"{n}@novatech.demo" for n in
                                       ["rahul.sharma", "priya.reddy", "ananya.rao", "vikram.mehta", "arjun.nair"])


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(c, email=PRIYA):
    r = c.post("/api/auth/sso/demo", json={"email": email})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def guest(c):
    r = c.post("/api/auth/guest")
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_list_enterprise_connectors(client):
    auth_hdr = login(client, PRIYA)  # Engineering Lead
    r = client.get("/api/connectors", headers=auth_hdr)
    assert r.status_code == 200
    connectors = r.json().get("connectors", [])
    assert len(connectors) >= 5
    providers = [c["provider"] for c in connectors]
    assert "github" in providers
    assert "jira" in providers
    assert "outlook" in providers
    assert "teams" in providers
    assert "entra" in providers


def test_connector_lifecycle(client):
    auth_hdr = login(client, PRIYA)
    r = client.get("/api/connectors", headers=auth_hdr)
    jira_conn = next(c for c in r.json()["connectors"] if c["provider"] == "jira")
    conn_id = jira_conn["id"]

    # Connect
    r_conn = client.post(
        f"/api/connectors/{conn_id}/connect",
        json={"mode": "DEMO CONNECTOR", "account_name": "Nova Jira Admin"},
        headers=auth_hdr,
    )
    assert r_conn.status_code == 200
    assert r_conn.json()["status"] == "connected"

    # Sync
    r_sync = client.post(f"/api/connectors/{conn_id}/sync", headers=auth_hdr)
    assert r_sync.status_code == 200
    assert r_sync.json()["status"] == "synchronized"
    assert "items_indexed" in r_sync.json()

    # Update Permissions
    r_perm = client.patch(
        f"/api/connectors/{conn_id}/permissions",
        json={"agent_access": {"Engineering Agent": "read_write", "Guest Agent": "none"}},
        headers=auth_hdr,
    )
    assert r_perm.status_code == 200
    assert r_perm.json()["agent_access"]["Engineering Agent"] == "read_write"


def test_admin_connector_overview(client):
    auth_hdr = login(client, PRIYA)
    r = client.get("/api/connectors/admin/overview", headers=auth_hdr)
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert data["summary"]["total_connectors"] >= 5
    assert "health" in data
    assert "usage" in data


def test_skills_library_listing(client):
    auth_hdr = login(client, PRIYA)
    r = client.get("/api/skills", headers=auth_hdr)
    assert r.status_code == 200
    skills = r.json().get("skills", [])
    assert len(skills) >= 6
    skill_ids = [s["id"] for s in skills]
    assert "skill_code_analysis" in skill_ids
    assert "skill_security_analysis" in skill_ids
    assert "skill_repo_analysis" in skill_ids
    assert "skill_report_gen" in skill_ids
    assert "skill_jira_mgmt" in skill_ids
    assert "skill_doc_gen" in skill_ids


def test_single_skill_execution(client):
    auth_hdr = login(client, PRIYA)

    # Execute Security Analysis Skill
    r_sec = client.post(
        "/api/skills/execute",
        json={"skill_id": "skill_security_analysis", "params": {"target": "auth"}},
        headers=auth_hdr,
    )
    assert r_sec.status_code == 200
    data = r_sec.json()
    assert data["status"] == "completed"
    assert "findings" in data["result"]
    assert len(data["result"]["findings"]) > 0

    # Execute Jira Management Skill (Search)
    r_jira = client.post(
        "/api/skills/execute",
        json={"skill_id": "skill_jira_mgmt", "params": {"action": "search", "query": "token"}},
        headers=auth_hdr,
    )
    assert r_jira.status_code == 200
    assert len(r_jira.json()["result"]["issues"]) > 0


def test_composed_cross_connector_workflow(client):
    auth_hdr = login(client, PRIYA)

    r_wf = client.post(
        "/api/skills/execute",
        json={"skill_id": "composed_workflow", "target": "authentication service"},
        headers=auth_hdr,
    )
    assert r_wf.status_code == 200
    data = r_wf.json()
    assert data["execution_type"] == "composed_workflow"
    assert data["status"] == "awaiting_confirmation"
    assert len(data["pipeline"]) == 8
    assert len(data["timeline"]) >= 7

    # Validate action proposal exists for human-in-the-loop gate
    assert "action_proposal" in data
    assert data["action_proposal"]["title"].startswith("Create Jira Issue")
    assert "fields" in data["action_proposal"]


def test_guest_rbac_enforcement(client):
    # Guest user login
    auth_hdr = guest(client)

    # Guests cannot execute internal security workflows
    r = client.post(
        "/api/skills/execute",
        json={"skill_id": "skill_security_analysis", "params": {}},
        headers=auth_hdr,
    )
    assert r.status_code == 403

    # Guests cannot run composed workflows
    r_wf = client.post(
        "/api/skills/execute",
        json={"skill_id": "composed_workflow"},
        headers=auth_hdr,
    )
    assert r_wf.status_code == 403
