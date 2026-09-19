"""Authentication primitives: password hashing, session tokens, and the request Principal.

The Principal is ALWAYS built server-side from the session token. Nothing the frontend sends about
identity, role or clearance is trusted.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from ..config import get_settings
from ..db.models import Session, User
from ..db.session import get_db
from .errors import AppError

settings = get_settings()
PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, digest = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), digest)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hmac.new(settings.session_secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def client_ip(request: Request) -> str:
    # Behind a trusted load balancer this would read X-Forwarded-For set by the LB only.
    return request.client.host if request.client else "unknown"


@dataclass
class Principal:
    user_id: str
    company_id: str
    company_name: str
    employee_code: str
    full_name: str
    email: str
    department: str
    role_code: str
    role_name: str
    job_title: str
    clearance: str
    manager_id: str | None
    permissions: set[str] = field(default_factory=set)
    session_id: str = ""
    ip: str = ""
    auth_method: str = ""
    session_started: datetime | None = None
    session_expires: datetime | None = None

    is_guest: bool = False

    def has(self, perm: str) -> bool:
        return perm in self.permissions

    def to_public(self) -> dict:
        return {
            "user_id": self.user_id, "company_id": self.company_id, "company_name": self.company_name,
            "employee_code": self.employee_code, "full_name": self.full_name, "email": self.email,
            "department": self.department, "role_code": self.role_code, "role_name": self.role_name,
            "job_title": self.job_title, "clearance": self.clearance,
            "permissions": sorted(self.permissions), "session_id": self.session_id, "ip": self.ip,
            "auth_method": self.auth_method, "is_guest": self.is_guest,
            "session_started": self.session_started.isoformat() if self.session_started else None,
            "session_expires": self.session_expires.isoformat() if self.session_expires else None,
        }


def principal_from_user(user: User, company_name: str, ses: Session | None = None, ip: str = "") -> Principal:
    return Principal(
        user_id=user.id, company_id=user.company_id, company_name=company_name,
        employee_code=user.employee_code, full_name=user.full_name, email=user.email,
        department=user.department.name, role_code=user.role.code, role_name=user.role.name,
        job_title=user.job_title, clearance=user.clearance, manager_id=user.manager_id,
        permissions={p.code for p in user.role.permissions},
        session_id=ses.id if ses else "", ip=ip, auth_method=ses.auth_method if ses else "",
        session_started=ses.created_at if ses else None, session_expires=ses.expires_at if ses else None,
        is_guest=bool(user.is_guest),
    )


def create_session(db: DBSession, user: User, ip: str, user_agent: str, method: str,
                   ttl_minutes: int | None = None) -> tuple[str, Session]:
    token = secrets.token_urlsafe(32)
    ses = Session(company_id=user.company_id, user_id=user.id, token_hash=token_hash(token), auth_method=method,
                  ip=ip, user_agent=user_agent[:300],
                  expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes or settings.session_ttl_minutes))
    db.add(ses)
    db.commit()
    return token, ses


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_principal(request: Request, db: DBSession = Depends(get_db)) -> Principal:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise AppError(401, "unauthenticated", "Please sign in to NovaTech Solutions to continue.")
    token = auth[7:].strip()
    ses = db.scalar(select(Session).where(Session.token_hash == token_hash(token)))
    if not ses or ses.revoked or _aware(ses.expires_at) < datetime.now(timezone.utc):
        raise AppError(401, "session_expired", "Your session has expired. Please sign in again.")
    user = db.get(User, ses.user_id)
    if not user or not user.is_active or user.company_id != ses.company_id:
        raise AppError(401, "unauthenticated", "Account is not active.")
    from ..db.models import Company
    company = db.get(Company, user.company_id)
    p = principal_from_user(user, company.name if company else "", ses, client_ip(request))
    request.state.principal = p
    return p


def require(perm: str):
    def _dep(p: Principal = Depends(get_principal)) -> Principal:
        if not p.has(perm):
            raise AppError(403, "forbidden", f"Your role does not include the '{perm}' permission.")
        return p
    return _dep
