"""SQLAlchemy ORM models for NovaTech Solutions. Mirrors db/schema.sql (PostgreSQL + pgvector).

Every tenant-owned table carries company_id; every repository query filters on it.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from ..config import get_settings

try:  # pgvector is optional (SQLite fallback stores JSON arrays)
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover
    Vector = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class Embedding(TypeDecorator):
    """pgvector `vector(n)` on PostgreSQL, JSON array everywhere else."""

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 384):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and Vector is not None:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return [float(x) for x in value]


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list: JSON}


DIM = get_settings().embedding_dim


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dep_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text, default="")
    business_unit: Mapped[str] = mapped_column(String(120), default="")
    head_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    location: Mapped[str] = mapped_column(String(120), default="Hyderabad")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)  # guest pseudo-department is hidden
    __table_args__ = (UniqueConstraint("company_id", "name"),)


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("perm_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(300))
    __table_args__ = (UniqueConstraint("company_id", "code"),)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("role_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(300), default="")
    permissions: Mapped[list["Permission"]] = relationship(secondary="role_permissions", lazy="selectin")
    __table_args__ = (UniqueConstraint("company_id", "code"),)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("usr_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_code: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(300))
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"))
    job_title: Mapped[str] = mapped_column(String(160))
    clearance: Mapped[str] = mapped_column(String(20), default="INTERNAL")
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    location: Mapped[str] = mapped_column(String(120), default="Hyderabad")
    phone: Mapped[str] = mapped_column(String(40), default="")
    pan_number: Mapped[str] = mapped_column(String(20), default="")      # fictional; DLP-masked on output
    bank_account: Mapped[str] = mapped_column(String(30), default="")    # fictional; DLP-masked on output
    joined_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo_persona: Mapped[bool] = mapped_column(Boolean, default=False)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    employment_status: Mapped[str] = mapped_column(String(30), default="Active")
    skills: Mapped[list] = mapped_column(JSON, default=list)

    department: Mapped[Department] = relationship(lazy="joined")
    role: Mapped[Role] = relationship(lazy="joined")
    __table_args__ = (UniqueConstraint("company_id", "employee_code"),)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ses_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    auth_method: Mapped[str] = mapped_column(String(40), default="demo-saml")
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. DOC-1005
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    filename: Mapped[str] = mapped_column(String(300))
    doc_type: Mapped[str] = mapped_column(String(40), default="Policy")
    department: Mapped[str] = mapped_column(String(120))  # owning department
    classification: Mapped[str] = mapped_column(String(20), index=True)
    allowed_departments: Mapped[list] = mapped_column(JSON, default=list)
    allowed_roles: Mapped[list] = mapped_column(JSON, default=list)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    family_key: Mapped[str] = mapped_column(String(200), index=True)  # groups versions of the same document
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    effective_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="published", index=True)
    # published | superseded | pending_approval | quarantined | rejected
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    ai_classification: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_classification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_flags: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(20), default="seed")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    project_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    owner: Mapped[User | None] = relationship(lazy="joined")


class DocumentPermission(Base):
    """Explicit, time-bound grants (e.g. an approved access request)."""
    __tablename__ = "document_permissions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("grant_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    granted_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(500), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("chk_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Embedding(DIM), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(80), default="")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("conv_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("msg_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # timeline, sources, withheld, actions, security
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIAction(Base):
    """A tool invocation proposed by the agent. High-risk ones wait here for human confirmation."""
    __tablename__ = "ai_actions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("act_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tool: Mapped[str] = mapped_column(String(60))
    args: Mapped[dict] = mapped_column(JSON, default=dict)
    preview: Mapped[dict] = mapped_column(JSON, default=dict)
    risk: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(30), default="pending_confirmation")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ToolExecution(Base):
    __tablename__ = "tool_executions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tex_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tool: Mapped[str] = mapped_column(String(60), index=True)
    args: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30))
    result_summary: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class WorkflowExecution(Base):
    """One agent run (a chat turn): intent, steps, engine, outcome."""
    __tablename__ = "workflow_executions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wf_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    intent: Mapped[str] = mapped_column(String(40))
    engine: Mapped[str] = mapped_column(String(40))
    agents: Mapped[list] = mapped_column(JSON, default=list)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("apr_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))  # leave | document_access | classification | general
    title: Mapped[str] = mapped_column(String(300))
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    approver_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    approver_permission: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    risk: Mapped[str] = mapped_column(String(20), default="LOW")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requester: Mapped[User] = relationship(foreign_keys=[requester_id], lazy="joined")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aud_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    user_name: Mapped[str] = mapped_column(String(200), default="")
    session_id: Mapped[str] = mapped_column(String(60), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(80), index=True)
    query: Mapped[str] = mapped_column(Text, default="")
    resource: Mapped[str] = mapped_column(String(300), default="")
    resource_id: Mapped[str] = mapped_column(String(60), default="")
    classification: Mapped[str] = mapped_column(String(20), default="")
    permission_result: Mapped[str] = mapped_column(String(20), default="N/A", index=True)
    tool: Mapped[str] = mapped_column(String(60), default="")
    result: Mapped[str] = mapped_column(String(40), default="SUCCESS")
    reason: Mapped[str] = mapped_column(String(500), default="")
    risk: Mapped[str] = mapped_column(String(20), default="LOW", index=True)
    request_id: Mapped[str] = mapped_column(String(60), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class SecurityAlert(Base):
    __tablename__ = "security_alerts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("alr_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_name: Mapped[str] = mapped_column(String(200), default="")
    alert_type: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(200))
    pattern: Mapped[str] = mapped_column(String(400))
    risk: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | investigating | resolved
    event_count: Mapped[int] = mapped_column(Integer, default=1)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


# ---- Enterprise systems the agent's tools operate on ------------------------------------------

class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lb_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    casual_total: Mapped[float] = mapped_column(Float)
    casual_used: Mapped[float] = mapped_column(Float)
    sick_total: Mapped[float] = mapped_column(Float)
    sick_used: Mapped[float] = mapped_column(Float)
    earned_total: Mapped[float] = mapped_column(Float)
    earned_used: Mapped[float] = mapped_column(Float)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="pending_manager_approval")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ITTicket(Base):
    __tablename__ = "it_tickets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(40), default="General")
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("eml_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_email: Mapped[str] = mapped_column(String(200))
    recipient_name: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="sent_simulated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    assignee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    project: Mapped[str] = mapped_column(String(120), default="")
    priority: Mapped[str] = mapped_column(String(10), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="todo", index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(120))
    classification: Mapped[str] = mapped_column(String(20))
    allowed_departments: Mapped[list] = mapped_column(JSON, default=list)
    allowed_roles: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30))
    health: Mapped[str] = mapped_column(String(20))
    progress: Mapped[int] = mapped_column(Integer)
    owner_name: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    milestones: Mapped[list] = mapped_column(JSON, default=list)
    updated_on: Mapped[date] = mapped_column(Date)
    manager_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    budget_category: Mapped[str] = mapped_column(String(40), default="Opex")
    budget_amount: Mapped[float] = mapped_column(Float, default=0.0)  # CONFIDENTIAL field — shown by policy only
    risks: Mapped[list] = mapped_column(JSON, default=list)
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    business_unit: Mapped[str] = mapped_column(String(120), default="")


# ---- Large synthetic enterprise dataset (see db/seed_large_dataset.py) ------------------------
#
# Every business record carries an access classification (PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED) and
# the departments it is scoped to. core.rbac.check_record() evaluates them BEFORE a record reaches a tool result,
# the analytics engine or the LLM.

class ClassifiedMixin:
    classification: Mapped[str] = mapped_column(String(20), default="INTERNAL", index=True)
    allowed_departments: Mapped[list] = mapped_column(JSON, default=lambda: ["*"])


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(40), default="Office")
    address: Mapped[str] = mapped_column(String(300), default="")
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Kolkata")


class BusinessUnit(Base):
    __tablename__ = "business_units"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    head_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ProjectMember(Base):
    __tablename__ = "project_members"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    project_role: Mapped[str] = mapped_column(String(80), default="Contributor")
    allocation_pct: Mapped[int] = mapped_column(Integer, default=50)


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    organizer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(String(120), default="Teams")
    agenda: Mapped[str] = mapped_column(Text, default="")


class MeetingAttendee(Base):
    __tablename__ = "meeting_attendees"
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)


class PerformanceReview(ClassifiedMixin, Base):
    __tablename__ = "performance_reviews"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cycle: Mapped[str] = mapped_column(String(20))
    rating: Mapped[str] = mapped_column(String(30))
    summary: Mapped[str] = mapped_column(Text, default="")


class Compensation(ClassifiedMixin, Base):
    __tablename__ = "compensation"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    band: Mapped[str] = mapped_column(String(20))
    base_salary: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    effective_date: Mapped[date] = mapped_column(Date)


class CostCenter(ClassifiedMixin, Base):
    __tablename__ = "cost_centers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. CC-ENG-01
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    department: Mapped[str] = mapped_column(String(120), index=True)
    owner_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Budget(ClassifiedMixin, Base):
    __tablename__ = "budgets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    department: Mapped[str] = mapped_column(String(120), index=True)
    cost_center: Mapped[str] = mapped_column(String(40))
    fiscal_year: Mapped[str] = mapped_column(String(10), index=True)
    quarter: Mapped[str] = mapped_column(String(4))
    category: Mapped[str] = mapped_column(String(60))
    allocated: Mapped[float] = mapped_column(Float)
    spent: Mapped[float] = mapped_column(Float)


class Expense(ClassifiedMixin, Base):
    __tablename__ = "expenses"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    department: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(60))
    amount: Mapped[float] = mapped_column(Float)
    spent_on: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    description: Mapped[str] = mapped_column(String(300), default="")


class Product(ClassifiedMixin, Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    list_price: Mapped[float] = mapped_column(Float, default=0.0)  # INTERNAL field


class Customer(ClassifiedMixin, Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    industry: Mapped[str] = mapped_column(String(80))
    region: Mapped[str] = mapped_column(String(60), index=True)
    tier: Mapped[str] = mapped_column(String(20))
    account_owner_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    customer_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False)


class Opportunity(ClassifiedMixin, Base):
    __tablename__ = "opportunities"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    stage: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[float] = mapped_column(Float)
    probability: Mapped[int] = mapped_column(Integer)
    close_date: Mapped[date] = mapped_column(Date, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    region: Mapped[str] = mapped_column(String(60), index=True)


class Contract(ClassifiedMixin, Base):
    __tablename__ = "contracts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    value: Mapped[float] = mapped_column(Float)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)


class Vendor(ClassifiedMixin, Base):
    __tablename__ = "vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    country: Mapped[str] = mapped_column(String(60))
    rating: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30))
    onboarded_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class PurchaseOrder(ClassifiedMixin, Base):
    __tablename__ = "purchase_orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    department: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(300))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), index=True)
    created_on: Mapped[date] = mapped_column(Date, index=True)


class SoftwareItem(ClassifiedMixin, Base):
    __tablename__ = "software_catalog"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(80))
    vendor: Mapped[str] = mapped_column(String(120))
    license_type: Mapped[str] = mapped_column(String(60))
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    platforms: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(String(400), default="")


class ITAsset(Base):
    __tablename__ = "it_assets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # asset tag
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    asset_type: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    purchased_on: Mapped[date] = mapped_column(Date)
    warranty_until: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="In use")


class ServiceRequest(Base):
    """Access / document / procurement / software / general requests created by the Workflow Agent."""
    __tablename__ = "service_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    request_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(200))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)
    approver_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MessageFeedback(Base):
    __tablename__ = "message_feedback"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fb_"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)  # +1 / -1
    comment: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("user_id", "message_id"),)


Index("ix_audit_company_ts", AuditLog.company_id, AuditLog.ts)
Index("ix_users_company_dept", User.company_id, User.department_id)
Index("ix_users_manager", User.manager_id)
Index("ix_projects_company_status", Project.company_id, Project.status)
Index("ix_tasks_assignee_status", Task.assignee_id, Task.status)
Index("ix_docs_company_type", Document.company_id, Document.doc_type)
Index("ix_chunks_company_doc", DocumentChunk.company_id, DocumentChunk.document_id)
Index("ix_leave_user_status", LeaveRequest.user_id, LeaveRequest.status)
Index("ix_tickets_user_status", ITTicket.user_id, ITTicket.status)
Index("ix_wf_company_created", WorkflowExecution.company_id, WorkflowExecution.created_at)
Index("ix_docs_company_status", Document.company_id, Document.status)
