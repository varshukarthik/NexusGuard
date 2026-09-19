"""Chat (JSON + streaming), conversations, feedback, AI actions (human-in-the-loop) and the employee's own work."""
from __future__ import annotations

import json
import logging
import queue
import re
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session as DBSession

from ..core.errors import AppError
from ..core.rbac import TOOL_POLICIES, active_grant_ids, check_access
from ..core.security import Principal, get_principal, require
from ..db.models import (AIAction, Conversation, Document, EmailOutbox, ITTicket, LeaveRequest, Message,
                         MessageFeedback, ServiceRequest, Task, User)
from ..db.session import SessionLocal, get_db
from ..services import audit
from ..services.agent import action_public, run_agent
from ..services.guard import redact
from ..services.nlp import title_from
from ..services.tools import ToolContext, execute_action, run_tool

router = APIRouter(tags=["workspace"])
log = logging.getLogger("novatech.chat")


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=40)


def _msg(m: Message) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "intent": m.intent, "meta": m.meta or {},
            "created_at": m.created_at.isoformat()}


def _conv(c: Conversation, preview: str = "") -> dict:
    return {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(), "preview": preview}


def _own_conversation(db, p: Principal, cid: str) -> Conversation:
    c = db.get(Conversation, cid)
    if not c or c.is_deleted or c.company_id != p.company_id or c.user_id != p.user_id:
        raise AppError(404, "not_found", "Conversation not found.")
    return c


def _context_refs(msgs: list[Message]) -> tuple[list[str], list[str]]:
    """Documents / projects referenced in recent assistant turns (for "this document", "that project")."""
    docs, projects = [], []
    for m in reversed(msgs[-6:]):
        if m.role != "assistant":
            continue
        meta = m.meta or {}
        docs += [s["doc_id"] for s in meta.get("sources") or [] if s.get("doc_id") not in docs]
        projects += [r["id"] for r in meta.get("records") or [] if r.get("type") == "project" and r["id"] not in projects]
    return docs[:6], projects[:6]


def _do_chat(db: DBSession, p: Principal, text: str, conversation_id: str | None, request_id: str,
             on_step=None, regenerate: bool = False) -> dict:
    text = text.strip()
    if not text:
        raise AppError(422, "empty", "Please type a message.")
    if conversation_id:
        conv = _own_conversation(db, p, conversation_id)
    else:
        conv = Conversation(company_id=p.company_id, user_id=p.user_id, title=title_from(text))
        db.add(conv)
        db.flush()
    msgs = db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)).all()
    history = [{"role": m.role, "content": m.content} for m in msgs]
    recent_docs, recent_projects = _context_refs(msgs)
    if regenerate:
        um = next((m for m in reversed(msgs) if m.role == "user"), None)
        if um is None:
            raise AppError(409, "nothing_to_regenerate", "There is no question to regenerate.")
        history = [{"role": m.role, "content": m.content} for m in msgs if m.created_at < um.created_at]
        for m in msgs:  # the regenerated answer replaces the previous one(s)
            if m.role == "assistant" and m.created_at >= um.created_at:
                db.delete(m)
    else:
        um = Message(company_id=p.company_id, conversation_id=conv.id, role="user", content=text)
        db.add(um)
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()  # persist the user turn before the agent runs (agent may roll back its own partial work)

    result = run_agent(db, p, um.content, conversation_id=conv.id, history=history, request_id=request_id,
                       on_step=on_step, recent_docs=recent_docs, recent_projects=recent_projects)
    am = Message(company_id=p.company_id, conversation_id=conv.id, role="assistant", content=result["answer"],
                 intent=result["meta"]["intent"], meta={**result["meta"], "regenerated": regenerate})
    db.add(am)
    db.flush()
    for a in result["actions"]:
        a.message_id = am.id
    db.commit()
    return {"conversation": _conv(conv), "user_message": _msg(um), "assistant_message": _msg(am)}


@router.post("/chat")
def chat(body: ChatIn, request: Request, p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    return _do_chat(db, p, body.message, body.conversation_id, request.state.request_id)


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _stream(p: Principal, request_id: str, *, text: str, conversation_id: str | None, regenerate: bool = False):
    q: queue.Queue = queue.Queue()

    def worker():
        with SessionLocal() as db:
            try:
                res = _do_chat(db, p, text, conversation_id, request_id,
                               on_step=lambda s: q.put(("step", s)), regenerate=regenerate)
                q.put(("done", res))
            except AppError as exc:
                q.put(("error", {"error": exc.code, "message": exc.message}))
            except Exception:
                log.exception("streamed chat failed (request %s)", request_id)
                db.rollback()
                q.put(("error", {"error": "internal_error", "message": "Something went wrong while generating the "
                                                                       "answer. Please retry."}))

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        yield _sse("start", {"request_id": request_id})
        while True:
            try:
                kind, payload = q.get(timeout=180)
            except queue.Empty:
                yield _sse("error", {"error": "timeout", "message": "The assistant took too long to respond."})
                return
            if kind == "step":
                yield _sse("step", payload)
                continue
            if kind == "error":
                yield _sse("error", payload)
                return
            content = payload["assistant_message"]["content"]
            yield _sse("conversation", payload["conversation"])
            for i in range(0, len(content), 48):  # progressive delivery of the final, already-checked answer
                yield _sse("delta", {"text": content[i:i + 48]})
                time.sleep(0.008)
            yield _sse("done", payload)
            return

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/chat/stream")
def chat_stream(body: ChatIn, request: Request, p: Principal = Depends(get_principal)):
    """Server-sent events: live agent-activity steps, then the answer text progressively, then the final message."""
    return _stream(p, request.state.request_id, text=body.message, conversation_id=body.conversation_id)


@router.post("/conversations/{cid}/regenerate")
def regenerate(cid: str, request: Request, stream: bool = False, p: Principal = Depends(get_principal),
               db: DBSession = Depends(get_db)):
    c = _own_conversation(db, p, cid)
    if stream:
        return _stream(p, request.state.request_id, text="(regenerate)", conversation_id=c.id, regenerate=True)
    return _do_chat(db, p, "(regenerate)", c.id, request.state.request_id, regenerate=True)


@router.get("/conversations")
def list_conversations(q: str = "", p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    stmt = select(Conversation).where(Conversation.company_id == p.company_id, Conversation.user_id == p.user_id,
                                      Conversation.is_deleted.is_(False))
    if q.strip():
        like = f"%{q.strip()[:100].lower()}%"
        sub = select(Message.conversation_id).where(func.lower(Message.content).like(like))
        stmt = stmt.where(or_(func.lower(Conversation.title).like(like), Conversation.id.in_(sub)))
    convs = db.scalars(stmt.order_by(Conversation.updated_at.desc()).limit(100)).all()
    return [_conv(c) for c in convs]


@router.get("/conversations/{cid}")
def get_conversation(cid: str, p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    c = _own_conversation(db, p, cid)
    msgs = db.scalars(select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at)).all()
    # refresh action statuses (they may have been confirmed since)
    out = []
    for m in msgs:
        d = _msg(m)
        acts = d["meta"].get("actions") or []
        if acts:
            fresh = {a.id: a for a in db.scalars(select(AIAction).where(AIAction.id.in_([x["id"] for x in acts])))}
            d["meta"] = {**d["meta"], "actions": [action_public(fresh[x["id"]]) if x["id"] in fresh else x for x in acts]}
        out.append(d)
    return {**_conv(c), "messages": out}


class RenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


@router.patch("/conversations/{cid}")
def rename(cid: str, body: RenameIn, p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    c = _own_conversation(db, p, cid)
    c.title = body.title.strip()
    db.commit()
    return _conv(c)


@router.delete("/conversations/{cid}")
def delete_conversation(cid: str, request: Request, p: Principal = Depends(get_principal),
                        db: DBSession = Depends(get_db)):
    c = _own_conversation(db, p, cid)
    c.is_deleted = True
    audit.record(db, principal=p, action="conversation.delete", resource=c.title, resource_id=c.id,
                 request_id=request.state.request_id)
    return {"ok": True}


@router.post("/conversations/{cid}/clear")
def clear_conversation(cid: str, request: Request, p: Principal = Depends(get_principal),
                       db: DBSession = Depends(get_db)):
    c = _own_conversation(db, p, cid)
    n = db.execute(delete(Message).where(Message.conversation_id == c.id)).rowcount
    c.updated_at = datetime.now(timezone.utc)
    audit.record(db, principal=p, action="conversation.clear", resource=c.title, resource_id=c.id,
                 reason=f"{n} message(s) removed", request_id=request.state.request_id)
    return {"ok": True, "removed": n}


@router.get("/conversations/{cid}/export")
def export_conversation(cid: str, request: Request, p: Principal = Depends(get_principal),
                        db: DBSession = Depends(get_db)):
    c = _own_conversation(db, p, cid)
    msgs = db.scalars(select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at)).all()
    lines = [f"# {c.title}", "", f"*NovaTech Solutions — exported {datetime.now(timezone.utc):%d %b %Y %H:%M} UTC by "
                                 f"{p.full_name}.*", ""]
    for m in msgs:
        who = p.full_name if m.role == "user" else "NovaTech Solutions Assistant"
        lines += [f"**{who}** · {m.created_at:%d %b %Y %H:%M}", "", redact(m.content).text, ""]
        srcs = (m.meta or {}).get("sources") or []
        if srcs:
            lines += ["Sources: " + "; ".join(f"{s['title']} [{s['doc_id']}] ({s['classification'].title()})"
                                              for s in srcs), ""]
    audit.record(db, principal=p, action="conversation.export", resource=c.title, resource_id=c.id,
                 request_id=request.state.request_id)
    fname = re.sub(r"[^\w-]+", "-", c.title.lower()).strip("-")[:60] or "conversation"
    return PlainTextResponse("\n".join(lines), media_type="text/markdown",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.md"'})


class FeedbackIn(BaseModel):
    rating: int = Field(ge=-1, le=1)
    comment: str = Field(default="", max_length=500)


@router.post("/messages/{mid}/feedback")
def feedback(mid: str, body: FeedbackIn, request: Request, p: Principal = Depends(get_principal),
             db: DBSession = Depends(get_db)):
    m = db.get(Message, mid)
    if not m or m.company_id != p.company_id or m.role != "assistant":
        raise AppError(404, "not_found", "Message not found.")
    _own_conversation(db, p, m.conversation_id)
    fb = db.scalar(select(MessageFeedback).where(MessageFeedback.user_id == p.user_id, MessageFeedback.message_id == mid))
    if body.rating == 0:
        if fb:
            db.delete(fb)
    elif fb:
        fb.rating, fb.comment = body.rating, body.comment
    else:
        db.add(MessageFeedback(company_id=p.company_id, user_id=p.user_id, message_id=mid, rating=body.rating,
                               comment=body.comment))
    m.meta = {**(m.meta or {}), "feedback": body.rating}
    audit.record(db, principal=p, action="ai.feedback", resource="AI response", resource_id=mid,
                 result="POSITIVE" if body.rating > 0 else "NEGATIVE" if body.rating < 0 else "CLEARED",
                 reason=body.comment[:200], request_id=request.state.request_id, evaluate=False)
    return {"ok": True, "rating": body.rating}


# ---- Human-in-the-loop actions ----------------------------------------------------------------

class ConfirmIn(BaseModel):
    overrides: dict | None = None


def _own_action(db, p: Principal, aid: str) -> AIAction:
    a = db.get(AIAction, aid)
    if not a or a.company_id != p.company_id or a.user_id != p.user_id:
        raise AppError(404, "not_found", "Action not found.")
    return a


@router.get("/actions")
def list_actions(p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    acts = db.scalars(select(AIAction).where(AIAction.company_id == p.company_id, AIAction.user_id == p.user_id)
                      .order_by(AIAction.created_at.desc()).limit(50)).all()
    return [action_public(a) for a in acts]


@router.post("/actions/{aid}/confirm")
def confirm_action(aid: str, body: ConfirmIn, request: Request, p: Principal = Depends(get_principal),
                   db: DBSession = Depends(get_db)):
    a = _own_action(db, p, aid)
    if a.status != "pending_confirmation":
        raise AppError(409, "already_decided", f"This action is already {a.status.replace('_', ' ')}.")
    try:
        result = execute_action(db, p, a, body.overrides)
    except PermissionError as exc:
        a.status = "failed"
        audit.record(db, principal=p, action="ai.action_executed", tool=a.tool, resource=a.preview.get("title", ""),
                     resource_id=a.id, permission_result="DENIED", result="DENIED", reason=str(exc), risk="HIGH",
                     request_id=request.state.request_id)
        raise AppError(403, "forbidden", str(exc))
    except Exception:
        db.rollback()
        a = db.get(AIAction, aid)
        a.status = "failed"
        a.result = {"message": "Execution failed. Nothing was changed."}
        db.commit()
        raise AppError(500, "tool_failed", "The action could not be executed. Nothing was changed.")
    a.status, a.result, a.decided_at = "executed", result, datetime.now(timezone.utc)
    audit.record(db, principal=p, action="ai.action_executed", tool=a.tool, resource=a.preview.get("title", ""),
                 resource_id=result.get("reference", a.id), permission_result="ALLOWED", result="EXECUTED",
                 risk=TOOL_POLICIES[a.tool]["risk"], reason="Confirmed by user (human-in-the-loop)",
                 details={"action_id": a.id, "args": a.args}, request_id=request.state.request_id)
    return action_public(a)


@router.post("/actions/{aid}/cancel")
def cancel_action(aid: str, request: Request, p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    a = _own_action(db, p, aid)
    if a.status != "pending_confirmation":
        raise AppError(409, "already_decided", f"This action is already {a.status.replace('_', ' ')}.")
    a.status, a.decided_at = "cancelled", datetime.now(timezone.utc)
    a.result = {"message": "Cancelled by user. Nothing was executed."}
    audit.record(db, principal=p, action="ai.action_cancelled", tool=a.tool, resource=a.preview.get("title", ""),
                 resource_id=a.id, result="CANCELLED", request_id=request.state.request_id)
    return action_public(a)


# ---- Direct tool endpoints (same permission + confirmation pipeline as the agent) ---------------

class LeaveIn(BaseModel):
    start_date: str = Field(max_length=40)
    end_date: str | None = Field(default=None, max_length=40)
    leave_type: str = Field(default="casual", pattern="^(casual|sick|earned)$")
    reason: str = Field(default="Personal work", max_length=300)


class TicketIn(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=3, max_length=2000)
    priority: str = Field(default="P3", pattern="^P[1-4]$")
    category: str = Field(default="Other", max_length=40)


class EmailIn(BaseModel):
    recipient: str = Field(min_length=2, max_length=200)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)


def _direct(db, p, request, tool, args):
    ctx = ToolContext(db=db, principal=p, request_id=request.state.request_id)
    out = run_tool(ctx, tool, args)
    db.commit()
    if out.status in ("denied", "blocked"):
        raise AppError(403, out.status, out.summary)
    if out.status == "error":
        raise AppError(422, "invalid", out.summary)
    return {"status": out.status, "summary": out.summary, "action": action_public(out.action) if out.action else None}


@router.post("/tools/leave")
def tool_leave(body: LeaveIn, request: Request, p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    return _direct(db, p, request, "create_leave_request", body.model_dump())


@router.post("/tools/ticket")
def tool_ticket(body: TicketIn, request: Request, p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    return _direct(db, p, request, "create_it_ticket", body.model_dump())


@router.post("/tools/email")
def tool_email(body: EmailIn, request: Request, p: Principal = Depends(get_principal), db: DBSession = Depends(get_db)):
    return _direct(db, p, request, "send_email", body.model_dump())


@router.get("/my/work")
def my_work(p: Principal = Depends(require("workspace:use")), db: DBSession = Depends(get_db)):
    tasks = db.scalars(select(Task).where(Task.company_id == p.company_id, Task.assignee_id == p.user_id)
                       .order_by(Task.due_date).limit(200)).all()
    leaves = db.scalars(select(LeaveRequest).where(LeaveRequest.user_id == p.user_id)
                        .order_by(LeaveRequest.created_at.desc()).limit(50)).all()
    tickets = db.scalars(select(ITTicket).where(ITTicket.user_id == p.user_id).order_by(ITTicket.created_at.desc())
                         .limit(50)).all()
    emails = db.scalars(select(EmailOutbox).where(EmailOutbox.sender_id == p.user_id)
                        .order_by(EmailOutbox.created_at.desc())).all()
    acts = db.scalars(select(AIAction).where(AIAction.user_id == p.user_id, AIAction.status == "pending_confirmation")
                      .order_by(AIAction.created_at.desc())).all()
    reqs = db.scalars(select(ServiceRequest).where(ServiceRequest.requester_id == p.user_id)
                      .order_by(ServiceRequest.created_at.desc()).limit(50)).all()
    return {
        "requests": [{"id": r.id, "type": r.request_type, "title": r.title, "status": r.status,
                      "created_at": r.created_at.isoformat()} for r in reqs],
        "tasks": [{"id": t.id, "title": t.title, "project": t.project, "priority": t.priority, "status": t.status,
                   "due": t.due_date.isoformat() if t.due_date else None} for t in tasks],
        "leave_requests": [{"id": l.id, "type": l.leave_type, "start": l.start_date.isoformat(),
                            "end": l.end_date.isoformat(), "days": l.days, "reason": l.reason, "status": l.status}
                           for l in leaves],
        "tickets": [{"id": t.id, "title": t.title, "priority": t.priority, "category": t.category, "status": t.status,
                     "created_at": t.created_at.isoformat()} for t in tickets],
        "emails": [{"id": e.id, "to": e.recipient_name, "subject": e.subject, "status": e.status,
                    "created_at": e.created_at.isoformat()} for e in emails],
        "pending_actions": [action_public(a) for a in acts],
    }
