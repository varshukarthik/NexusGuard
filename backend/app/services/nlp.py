"""Deterministic language helpers: date parsing and rule-based intent detection (offline engine / fallback)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import get_settings

settings = get_settings()
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                          "nov", "dec"])}


def today() -> date:
    return datetime.now(ZoneInfo(settings.company_timezone)).date()


def parse_date(text: str, base: date | None = None) -> date | None:
    base = base or today()
    t = text.lower()
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    if "day after tomorrow" in t:
        return base + timedelta(days=2)
    if "tomorrow" in t:
        return base + timedelta(days=1)
    if re.search(r"\btoday\b", t):
        return base
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", t) or \
        re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b", t)
    if m:
        a, b = m.group(1), m.group(2)
        day, mon = (int(a), MONTHS[b[:3]]) if a.isdigit() else (int(b), MONTHS[a[:3]])
        try:
            d = date(base.year, mon, day)
            return d if d >= base else date(base.year + 1, mon, day)
        except ValueError:
            return None
    for i, wd in enumerate(WEEKDAYS):
        if re.search(rf"\b(next\s+)?{wd}\b", t):
            delta = (i - base.weekday()) % 7 or 7
            return base + timedelta(days=delta)
    return None


def fmt_date(d: date) -> str:
    return d.strftime("%A, %d %B %Y")


INTENTS = ["information_retrieval", "summarization", "document_search", "workflow_execution", "communication",
           "data_analysis", "restricted_data_request", "general"]

SENSITIVE_TERMS = re.compile(r"\b(executive (compensation|salar|pay)|ceo (salary|pay|compensation)|board (strategy|"
                             r"minutes|deck|meeting)|acquisition|m&a|project atlas|salary of|everyone'?s salar|"
                             r"all salaries|compensation of)\b", re.I)


def detect_flags(text: str) -> dict:
    t = text.lower()
    return {
        "leave_balance": bool(re.search(r"\b(leave|leaves|pto|vacation)\b.*\b(balance|remaining|left|how many)\b|"
                                        r"\b(balance|remaining|how many)\b.*\b(leave|leaves)\b", t)),
        "leave_submit": bool(re.search(r"\b(submit|apply|create|file|request|book|take)\b.*\b(leave|day off|pto|vacation)\b|"
                                       r"\bleave request\b", t)),
        "email": bool(re.search(r"\b(email|e-mail|mail|message|write to|send)\b", t) and
                      re.search(r"\b(email|e-mail|mail)\b|\bdraft\b", t)),
        "ticket": bool(re.search(r"\b(ticket|helpdesk|help desk|it support|incident)\b", t) or
                       re.search(r"\b(laptop|vpn|wifi|wi-fi|printer|monitor|password reset)\b.*\b(broken|not working|issue|"
                                 r"problem|fix|reset)\b", t)),
        "tasks": bool(re.search(r"\b(my )?(pending )?tasks?\b|\bto-?dos?\b|\bassigned to me\b", t)),
        "project": bool(re.search(r"\bproject\b|\bstatus of\b|\bproject status\b", t)),
        "summarize": bool(re.search(r"\b(summari[sz]e|summary|overview|tl;?dr|key points|brief me)\b", t)),
        "find_docs": bool(re.search(r"\b(find|list|search|look up|locate)\b.*\b(documents?|docs|files|policies)\b|"
                                    r"\bdocuments? (related|about|on)\b", t)),
        "delete": bool(re.search(r"\b(delete|remove|purge|erase)\b.*\b(document|file|record|data)\b", t)),
        "employee_info": bool(re.search(r"\b(my (profile|details|pan|bank|employee (id|info|information))|who is my manager|"
                                        r"my manager'?s? (name|email)|employee (info|information|details))\b", t)),
        "analysis": bool(re.search(r"\b(compare|trend|analy[sz]e|breakdown|versus|vs\.?)\b", t)),
        "sensitive": bool(SENSITIVE_TERMS.search(t)),
    }


def classify_intent(text: str) -> tuple[str, dict]:
    f = detect_flags(text)
    if f["delete"] or f["leave_submit"] or f["ticket"]:
        intent = "workflow_execution"
    elif f["email"]:
        intent = "communication"
    elif f["sensitive"]:
        intent = "restricted_data_request"
    elif f["analysis"]:
        intent = "data_analysis"
    elif f["summarize"]:
        intent = "summarization"
    elif f["find_docs"]:
        intent = "document_search"
    elif f["tasks"] or f["leave_balance"] or f["project"] or f["employee_info"]:
        intent = "information_retrieval"
    else:
        intent = "information_retrieval"
    return intent, f


def title_from(text: str, n: int = 6) -> str:
    words = re.sub(r"[^\w\s'-]", "", text).split()
    t = " ".join(words[:n])
    return (t[:1].upper() + t[1:]) if t else "New conversation"
