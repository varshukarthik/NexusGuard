"""Natural-Language Intent and Action Detection Service.

Provides structured intent classification and entity extraction using OpenAI JSON-mode completions,
with deterministic offline NLP fallback when OpenAI is offline or quota-limited.

Supported Intents:
- APPLY_LEAVE
- KNOWLEDGE_BASE_QUERY
- POLICY_QUERY
- CHECK_ACCESS
- GENERAL_QUERY
- CLARIFICATION_REQUIRED
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta

from . import llm
from .nlp import LeaveRequestDetails, fmt_date, parse_date, parse_leave_request, today

log = logging.getLogger("novatech.intent")

SUPPORTED_INTENTS = [
    "APPLY_LEAVE",
    "KNOWLEDGE_BASE_QUERY",
    "POLICY_QUERY",
    "CHECK_ACCESS",
    "GENERAL_QUERY",
    "CLARIFICATION_REQUIRED",
]

INTENT_SYSTEM_PROMPT = """You are the enterprise intent and action classifier for NovaTech Solutions.
Analyze the user's natural language request and determine what the user is trying to do.

Supported intents:
- APPLY_LEAVE: The user wants to apply, request, or book leave/PTO/vacation/time off.
- KNOWLEDGE_BASE_QUERY: The user is asking for company information, documents, projects, employees, or departmental data.
- POLICY_QUERY: The user is asking about company policies, rules, procedures, guidelines, or standards.
- CHECK_ACCESS: The user is asking if they can access a resource, who has access, or about access rights and permissions.
- GENERAL_QUERY: General greeting, conversational remark, or non-company question.
- CLARIFICATION_REQUIRED: The user's request is completely ambiguous, vague, or cannot be understood without more information.

Today's date is: {today_str}.

You MUST return a valid JSON object with the following schema:
{{
  "intent": "APPLY_LEAVE" | "KNOWLEDGE_BASE_QUERY" | "POLICY_QUERY" | "CHECK_ACCESS" | "GENERAL_QUERY" | "CLARIFICATION_REQUIRED",
  "status": "READY" | "CLARIFICATION_REQUIRED",
  "action": "create_leave_request" | "search_knowledge" | "search_policies" | "check_permissions" | "none",
  "start_date": string | null,
  "duration_days": number | null,
  "leave_type": "casual" | "sick" | "earned" | null,
  "reason": string | null,
  "query": string | null,
  "resource": string | null,
  "clarification_question": string | null
}}

Guidelines:
1. For APPLY_LEAVE:
   - If the user specifies when (e.g. tomorrow, next Monday, 22 Sep) and for how long (or end date), set status = "READY" and action = "create_leave_request".
   - If critical information is missing (e.g. "I want leave", "Need some leave", "Give me leave for a few days", "I need leave next week"), set status = "CLARIFICATION_REQUIRED" and set clarification_question to ask what is missing.
   - Extract reason if provided (e.g. "family function", "medical appointment", "personal work").
2. For CHECK_ACCESS:
   - User asks "Can I access ...", "Who can access ...", "do I have permission to ...". Set action = "check_permissions" or "search_knowledge", and set resource / query.
3. For POLICY_QUERY:
   - User asks about policy contents, leave policy rules, IT policy, remote work guidelines. Set action = "search_policies".
4. For KNOWLEDGE_BASE_QUERY:
   - User asks about documents, roadmap, revenue, team, projects. Set action = "search_knowledge" and extract an optimized search query.
5. Return ONLY valid JSON."""


def detect_intent_offline(text: str, base_date: date) -> dict:
    """Deterministic, rule-based intent and action extraction."""
    low = text.lower().strip()

    # 1. Check for Greeting / General
    if re.match(r"^\s*(hi|hello|hey|good (morning|afternoon|evening)|namaste|thanks|thank you|ok(ay)?|cool)\b[\s!.?]*$", low):
        return {
            "intent": "GENERAL_QUERY",
            "status": "READY",
            "action": "none",
            "query": text,
            "resource": None,
            "start_date": None,
            "duration_days": None,
            "leave_type": None,
            "reason": None,
            "clarification_question": None,
            "engine": "offline",
        }

    # 2. Check for Leave Request
    is_leave_phrase = bool(re.search(
        r"\b(apply|submit|request|book|take|taking|need|want|give me|asking for|can i take|plan to take|avail)\b.{0,40}\b(leave|days? off|pto|vacation|time off)\b"
        r"|\b(leave|pto|day off)\s+(tomorrow|today|next|this|on|from|for)\b"
        r"|\bleave request\b|\bneed\s+(some\s+)?leave\b|\bwant\s+(some\s+)?leave\b|\bwon'?t be available\b",
        low
    ))
    is_leave_balance_check = bool(re.search(r"\b(balance|remaining|how many)\b.*\b(leave|leaves)\b|\b(leave|leaves)\b.*\b(balance|remaining)\b", low))

    if is_leave_phrase and not is_leave_balance_check:
        details: LeaveRequestDetails = parse_leave_request(text, base=base_date)
        if details.is_ambiguous:
            return {
                "intent": "APPLY_LEAVE",
                "status": "CLARIFICATION_REQUIRED",
                "action": "create_leave_request",
                "start_date": details.start_date.isoformat() if details.start_date else None,
                "duration_days": int(details.duration_days) if details.duration_days else None,
                "leave_type": details.leave_type,
                "reason": details.reason,
                "query": None,
                "resource": None,
                "clarification_question": details.clarification_prompt or "Sure! What date should the leave start, and how many days do you need?",
                "engine": "offline",
            }
        else:
            return {
                "intent": "APPLY_LEAVE",
                "status": "READY",
                "action": "create_leave_request",
                "start_date": details.start_date.isoformat() if details.start_date else None,
                "duration_days": int(details.duration_days) if details.duration_days else 1,
                "leave_type": details.leave_type,
                "reason": details.reason,
                "query": None,
                "resource": None,
                "clarification_question": None,
                "engine": "offline",
            }

    # 3. Check for Access Rights / Permissions
    if re.search(r"\b(can i access|who can access|who has access|permission(s)? to|do i have access|access (rights|permissions)|authorized to (view|read|access))\b", low):
        # Extract resource being asked about
        m_res = re.search(r"\b(?:access|view|read)\s+(?:the\s+)?([a-z0-9_\-\s]+?)(?:\?|\.|$|\bfor\b)", low)
        resource = m_res.group(1).strip() if m_res else "corporate documents"
        return {
            "intent": "CHECK_ACCESS",
            "status": "READY",
            "action": "check_permissions",
            "query": f"{resource} access permissions",
            "resource": resource,
            "start_date": None,
            "duration_days": None,
            "leave_type": None,
            "reason": None,
            "clarification_question": None,
            "engine": "offline",
        }

    # 4. Check for Policy Query
    if re.search(r"\b(policy|policies|guideline|guidelines|procedure|procedures|rule|rules|standard|standards|code of conduct|handbook)\b", low):
        return {
            "intent": "POLICY_QUERY",
            "status": "READY",
            "action": "search_policies",
            "query": text,
            "resource": None,
            "start_date": None,
            "duration_days": None,
            "leave_type": None,
            "reason": None,
            "clarification_question": None,
            "engine": "offline",
        }

    # 5. Default to Knowledge Base Query
    return {
        "intent": "KNOWLEDGE_BASE_QUERY",
        "status": "READY",
        "action": "search_knowledge",
        "query": text,
        "resource": None,
        "start_date": None,
        "duration_days": None,
        "leave_type": None,
        "reason": None,
        "clarification_question": None,
        "engine": "offline",
    }


def detect_intent_and_action(text: str, base_date: date | None = None) -> dict:
    """Detect natural-language intent and action.

    First attempts OpenAI structured JSON extraction. If OpenAI is disabled or errors (e.g. quota/timeout),
    gracefully falls back to deterministic offline NLP detection.
    """
    if base_date is None:
        base_date = today()

    today_str = fmt_date(base_date)

    if llm.enabled():
        try:
            prompt = INTENT_SYSTEM_PROMPT.format(today_str=today_str)
            raw = llm.chat_json(prompt, text, max_tokens=250)
            if isinstance(raw, dict) and raw.get("intent") in SUPPORTED_INTENTS:
                raw["engine"] = "openai"
                # Post-process dates if relative dates were returned
                if raw.get("intent") == "APPLY_LEAVE":
                    # Re-verify and resolve relative dates against system backend date
                    offline_eval = detect_intent_offline(text, base_date)
                    if offline_eval.get("status") == "CLARIFICATION_REQUIRED":
                        raw["status"] = "CLARIFICATION_REQUIRED"
                        if not raw.get("clarification_question"):
                            raw["clarification_question"] = offline_eval.get("clarification_question")
                    elif offline_eval.get("start_date"):
                        raw["start_date"] = offline_eval["start_date"]
                        if offline_eval.get("duration_days"):
                            raw["duration_days"] = offline_eval["duration_days"]
                        if offline_eval.get("reason") and not raw.get("reason"):
                            raw["reason"] = offline_eval["reason"]
                        if offline_eval.get("leave_type") and not raw.get("leave_type"):
                            raw["leave_type"] = offline_eval["leave_type"]
                log.info("OpenAI detected intent: %s (action: %s)", raw.get("intent"), raw.get("action"))
                return raw
        except Exception as exc:
            log.warning("OpenAI intent detection failed (%s) — falling back to offline intent engine", type(exc).__name__)

    # Fallback to deterministic NLP engine
    result = detect_intent_offline(text, base_date)
    log.info("Offline NLP detected intent: %s (action: %s)", result.get("intent"), result.get("action"))
    return result
