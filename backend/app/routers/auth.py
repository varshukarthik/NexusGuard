"""Authentication — password sign-in, Demo SAML SSO and Guest Mode.

The prototype simulates the SP-initiated SAML flow (AuthnRequest → IdP → signed Assertion → ACS → session).
It is clearly labelled as a demo IdP. In production this module is replaced by a real SAML 2.0 / OIDC integration
(Okta, Entra ID, Google Workspace) — see README §Authentication.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from ..config import get_settings
from ..core.errors import AppError
from ..core.security import (Principal, client_ip, create_session, get_principal, principal_from_user,
                             verify_password)
from ..db.models import Company, Conversation, Department, Role, Session, User
from ..db.session import get_db
from ..services import audit

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

PERSONA_NOTES = {
    "NT-1042": "Employee · Public + Internal + own data",
    "NT-0417": "Manager · + Engineering Confidential + team",
    "NT-0233": "HR · + HR Confidential",
    "NT-0310": "Administrator · dashboard, audit & security",
    "NT-0007": "Executive · + Confidential + Restricted",
    "OL-0101": "Other tenant · isolation test",
}
DEFAULT_TENANT = "cmp_novatech"


class LoginIn(BaseModel):
    # corporate email OR employee id (e.g. NT-1042)
    email: str = Field(pattern=r"^([^@\s]+@[^@\s]+\.[^@\s]+|[A-Za-z]{2,5}-\d{3,6})$", max_length=200)
    password: str = Field(min_length=1, max_length=200)


class DemoSSOIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)


def _assertion(user: User, company: Company) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    attrs = {"NameID": user.email, "employeeId": user.employee_code, "displayName": user.full_name,
             "department": user.department.name, "title": user.job_title, "role": user.role.code,
             "clearance": user.clearance, "tenant": company.domain}
    body = json.dumps({"issuer": "https://idp.demo-saml.local/novatech", "audience": "urn:novatech:workspace",
                       "issued_at": now, "attributes": attrs}, sort_keys=True)
    sig = hmac.new(settings.session_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return {"issuer": "Demo SAML IdP (prototype — not a production identity provider)", "issued_at": now,
            "attributes": attrs, "signature_alg": "HMAC-SHA256 (demo)", "signature": sig[:32] + "…",
            "saml_response_b64": base64.b64encode(body.encode()).decode()[:96] + "…"}


def _login_response(db: DBSession, user: User, request: Request, method: str) -> dict:
    company = db.get(Company, user.company_id)
    token, ses = create_session(db, user, client_ip(request), request.headers.get("user-agent", ""), method)
    p = principal_from_user(user, company.name, ses, client_ip(request))
    audit.record(db, principal=p, action="auth.login", resource="NovaTech Solutions sign-in", result="SUCCESS",
                 reason=f"Signed in via {method}", request_id=request.state.request_id)
    return {"token": token, "user": p.to_public(), "assertion": _assertion(user, company)}


@router.get("/sso/config")
def sso_config(db: DBSession = Depends(get_db)):
    personas = []
    if settings.demo_mode:
        for u in db.scalars(select(User).where(User.is_demo_persona.is_(True))).all():
            company = db.get(Company, u.company_id)
            personas.append({"email": u.email, "full_name": u.full_name, "job_title": u.job_title,
                             "department": u.department.name, "clearance": u.clearance, "role": u.role.name,
                             "employee_code": u.employee_code, "company": company.name,
                             "note": PERSONA_NOTES.get(u.employee_code, "")})
        order = list(PERSONA_NOTES)
        personas.sort(key=lambda x: order.index(x["employee_code"]) if x["employee_code"] in order else 99)
    return {"idp_name": "NovaTech Solutions SSO (demo)", "is_simulation": True, "entity_id": "urn:novatech:workspace",
            "acs_url": "/api/auth/sso/acs", "demo_mode": settings.demo_mode, "personas": personas,
            "guest_mode": settings.guest_mode_enabled,
            "demo_password_hint": "NovaTech@Demo1" if settings.demo_mode else None}


@router.post("/login")
def login(body: LoginIn, request: Request, db: DBSession = Depends(get_db)):
    ident = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == ident)) if "@" in ident else \
        db.scalar(select(User).where(func.lower(User.employee_code) == ident))
    if user is not None and user.is_guest:
        user = None
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        if user:
            audit.record(db, company_id=user.company_id, user_id=user.id, user_name=user.full_name,
                         ip=client_ip(request), action="auth.login", resource="Demo SAML SSO", result="FAILURE",
                         risk="MEDIUM", reason="Invalid credentials", request_id=request.state.request_id)
        raise AppError(401, "invalid_credentials", "Sign-in failed. Check your corporate email / employee ID and password.")
    return _login_response(db, user, request, "saml-password")


@router.post("/sso/demo")
def demo_sso(body: DemoSSOIn, request: Request, db: DBSession = Depends(get_db)):
    """Demo-only: the mock IdP authenticates a pre-provisioned demo persona (judges' identity switcher)."""
    if not settings.demo_mode:
        raise AppError(404, "not_found", "Not available.")
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.is_demo_persona.is_(True)))
    if not user:
        raise AppError(404, "unknown_persona", "Unknown demo identity.")
    return _login_response(db, user, request, "demo-saml")


def _retire_guest(db: DBSession, user: User) -> None:
    """Guest conversations are temporary: they disappear with the guest session."""
    user.is_active = False
    for c in db.scalars(select(Conversation).where(Conversation.user_id == user.id)).all():
        c.is_deleted = True


@router.post("/guest")
def guest_login(request: Request, db: DBSession = Depends(get_db)):
    """Guest Mode — a real, server-side authorization role limited to PUBLIC information.

    Each guest gets an isolated, short-lived identity so their temporary conversations can never be seen by anyone
    else (including other guests)."""
    if not settings.guest_mode_enabled:
        raise AppError(404, "not_found", "Guest Mode is not available.")
    company = db.get(Company, DEFAULT_TENANT)
    dep = db.scalar(select(Department).where(Department.company_id == DEFAULT_TENANT, Department.code == "GST"))
    role = db.scalar(select(Role).where(Role.company_id == DEFAULT_TENANT, Role.code == "guest"))
    if not company or not dep or not role:
        raise AppError(503, "guest_unavailable", "Guest Mode is temporarily unavailable.")
    # retire expired guest identities (housekeeping)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.guest_session_ttl_minutes)
    stale = db.scalars(select(User).join(Session, Session.user_id == User.id).where(
        User.is_guest.is_(True), User.is_active.is_(True), Session.created_at < cutoff).limit(200)).all()
    for u in stale:
        _retire_guest(db, u)
    tag = secrets.token_hex(4).upper()
    user = User(company_id=DEFAULT_TENANT, employee_code=f"GUEST-{tag}", email=f"guest-{tag.lower()}@guest.novatech.demo",
                full_name="Guest Visitor", password_hash="!guest-no-password", department_id=dep.id, role_id=role.id,
                job_title="Guest (public access)", clearance="PUBLIC", location="—", is_guest=True,
                employment_status="Guest")
    db.add(user)
    db.flush()
    db.refresh(user)
    token, ses = create_session(db, user, client_ip(request), request.headers.get("user-agent", ""), "guest",
                                ttl_minutes=settings.guest_session_ttl_minutes)
    p = principal_from_user(user, company.name, ses, client_ip(request))
    audit.record(db, principal=p, action="auth.guest_session", resource="Guest Mode", result="SUCCESS",
                 reason="Guest session started — PUBLIC data only", request_id=request.state.request_id)
    return {"token": token, "user": p.to_public()}


@router.post("/logout")
def logout(request: Request, p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    ses = db.get(Session, p.session_id)
    if ses:
        ses.revoked = True
    if p.is_guest:
        u = db.get(User, p.user_id)
        if u:
            _retire_guest(db, u)
    audit.record(db, principal=p, action="auth.logout", resource="Session", request_id=request.state.request_id)
    return {"ok": True}
