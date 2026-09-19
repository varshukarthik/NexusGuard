"""Deterministic language helpers: date parsing and rule-based intent detection (offline engine / fallback)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import get_settings

settings = get_settings()
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                          "nov", "dec"])}
WORD_NUMS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


@dataclass
class LeaveRequestDetails:
    is_leave: bool
    start_date: date | None = None
    end_date: date | None = None
    duration_days: float | None = None
    leave_type: str = "casual"
    reason: str = "Personal work"
    is_ambiguous: bool = False
    clarification_prompt: str | None = None


def parse_num(s: str) -> int | None:
    s = s.lower().strip()
    if s.isdigit():
        return int(s)
    return WORD_NUMS.get(s)


def today() -> date:
    return datetime.now(ZoneInfo(settings.company_timezone)).date()


def parse_date(text: str, base: date | None = None) -> date | None:
    base = base or today()
    t = text.lower().strip()
    if not t:
        return None
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
        m_wd = re.search(rf"\b(?:(this|next)\s+)?{wd}\b", t)
        if m_wd:
            delta = (i - base.weekday()) % 7 or 7
            return base + timedelta(days=delta)
    return None


def extract_leave_reason(text: str) -> str:
    t = text.strip()
    m = re.search(r"\bbecause\s+of\s+([^.?!,]+)", t, re.I)
    if not m:
        m = re.search(r"\bbecause\s+([^.?!,]+)", t, re.I)
    if not m:
        m = re.search(r"\b(?:due\s+to|on\s+account\s+of)\s+([^.?!,]+)", t, re.I)
    if not m:
        m = re.search(r"\bas\s+i\s+(?:have|need|am)\s+([^.?!,]+)", t, re.I)
    if not m:
        m = re.search(r"\breason[:\s]+([^.?!,]+)", t, re.I)
    if not m:
        m = re.search(r"\bfor\s+(?!(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a few|some)\s+days?\b|(?:tomorrow|today|next|this|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b)([^.?!,]+)", t, re.I)
    if m:
        raw = m.group(1).strip()
        cleaned = re.sub(r"^(?:i\s+have\s+(?:to\s+attend\s+)?(?:a\s+|an\s+)?|i\s+need\s+to\s+(?:attend\s+)?|i\s+am\s+(?:having\s+)?(?:a\s+|an\s+)?|to\s+attend\s+(?:a\s+|an\s+)?|having\s+(?:a\s+|an\s+)?|a\s+|an\s+|my\s+)", "", raw, flags=re.I).strip()
        if cleaned:
            return cleaned[:1].upper() + cleaned[1:]
    return "Personal work"


def parse_leave_request(text: str, base: date | None = None) -> LeaveRequestDetails:
    base = base or today()
    t = text.strip()
    low = t.lower()

    is_leave = bool(re.search(
        r"\b(submit|apply|create|file|request|book|take|taking|need|want|give me|asking for|can i take|plan to take)\b.{0,40}\b(leave|days? off|pto|vacation|time off)\b"
        r"|\b(leave|pto|day off)\s+(tomorrow|today|next|this|on|from|for)\b"
        r"|\bleave request\b|\bneed\s+(some\s+)?leave\b",
        low
    ))
    if not is_leave:
        return LeaveRequestDetails(is_leave=False)

    lt = "sick" if re.search(r"\b(sick|unwell|fever|doctor|medical|hospital)\b", low) else \
         "earned" if re.search(r"\b(earned|privilege|annual|vacation|holiday)\b", low) else "casual"

    reason = extract_leave_reason(t)

    # Ambiguity 1: Vague request with no date at all
    if re.search(r"\b(some leave|leave for a few days|a few days off|take some time off)\b", low) and not re.search(r"\b(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}-\d{2}-\d{2})\b", low):
        return LeaveRequestDetails(
            is_leave=True, leave_type=lt, reason=reason, is_ambiguous=True,
            clarification_prompt="Sure! What date should the leave start, and how many days do you need?"
        )

    # Ambiguity 2: Vague 'next week' without specific dates
    if re.search(r"\b(next week|sometime next week)\b", low) and not re.search(r"\b(\d+|one|two|three|four|five)\s+days?\b", low) and not re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", low):
        return LeaveRequestDetails(
            is_leave=True, leave_type=lt, reason=reason, is_ambiguous=True,
            clarification_prompt="I can help you prepare a leave request. Which specific dates next week would you like to take off, and for how many days?"
        )

    # Ambiguity 3: 'from <Date>' but missing duration and return date
    m_from_only = re.search(r"\b(?:from|starting|beginning)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today|\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+|[a-z]+\s+\d{1,2})\b", low)
    if m_from_only and not re.search(r"\b(to|until|till|through)\b", low) and not re.search(r"\b(?:for\s+)?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+days?\b", low):
        day_name = m_from_only.group(1).title()
        return LeaveRequestDetails(
            is_leave=True, leave_type=lt, reason=reason, is_ambiguous=True,
            clarification_prompt=f"Sure! How many days of leave do you need starting {day_name}, or what is your return date?"
        )

    # Range Pattern: 'from <Date1> to/until/through/till <Date2>'
    m_range = re.search(r"\bfrom\s+([^,]+?)\s+(?:to|until|till|through)\s+([^,.?!]+)", low)
    if not m_range:
        m_range = re.search(r"\b([^,]+?)\s+(?:to|until|till|through)\s+([^,.?!]+)", low)
        if m_range:
            d1_try = parse_date(m_range.group(1), base)
            d2_try = parse_date(m_range.group(2), base)
            if not (d1_try and d2_try):
                m_range = None

    if m_range:
        d1 = parse_date(m_range.group(1), base)
        d2 = parse_date(m_range.group(2), base)
        if d1 and d2:
            if d2 < d1:
                return LeaveRequestDetails(
                    is_leave=True, leave_type=lt, reason=reason, is_ambiguous=True,
                    clarification_prompt="The requested end date cannot be earlier than the start date. Please verify the dates."
                )
            dur = float((d2 - d1).days + 1)
            # Edge case: conflicting duration mentioned
            m_dur_check = re.search(r"\b(?:for\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+days?\b", low)
            if m_dur_check:
                n_stated = parse_num(m_dur_check.group(1))
                if n_stated and n_stated != int(dur):
                    return LeaveRequestDetails(
                        is_leave=True, leave_type=lt, reason=reason, is_ambiguous=True,
                        clarification_prompt=f"You mentioned {n_stated} days, but the dates from {fmt_date(d1)} to {fmt_date(d2)} span {int(dur)} calendar days. Could you please clarify the exact dates or duration?"
                    )
            return LeaveRequestDetails(
                is_leave=True, start_date=d1, end_date=d2, duration_days=dur,
                leave_type=lt, reason=reason, is_ambiguous=False
            )

    # Duration Pattern: '<N> days from/starting <Date>' or 'for <N> days'
    m_dur = re.search(r"\b(?:for\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+days?(?:\s+off)?(?:\s+(?:from|starting|beginning|on))?\s*([^,;.?!]*)", low)
    if m_dur:
        n = parse_num(m_dur.group(1))
        date_str = m_dur.group(2).strip()
        d_start = parse_date(date_str, base) or parse_date(low, base)
        if d_start and n:
            d_end = d_start + timedelta(days=n - 1)
            return LeaveRequestDetails(
                is_leave=True, start_date=d_start, end_date=d_end, duration_days=float(n),
                leave_type=lt, reason=reason, is_ambiguous=False
            )

    # 'tomorrow and the day after'
    if "tomorrow and the day after" in low:
        d1 = base + timedelta(days=1)
        d2 = base + timedelta(days=2)
        return LeaveRequestDetails(
            is_leave=True, start_date=d1, end_date=d2, duration_days=2.0,
            leave_type=lt, reason=reason, is_ambiguous=False
        )

    # Single date pattern: 'tomorrow', 'today', 'on Friday', etc.
    d_single = parse_date(low, base)
    if d_single:
        return LeaveRequestDetails(
            is_leave=True, start_date=d_single, end_date=d_single, duration_days=1.0,
            leave_type=lt, reason=reason, is_ambiguous=False
        )

    return LeaveRequestDetails(
        is_leave=True, leave_type=lt, reason=reason, is_ambiguous=True,
        clarification_prompt="Sure! What date should the leave start, and how many days do you need?"
    )


def fmt_date(d: date) -> str:
    return d.strftime("%A, %d %B %Y")


INTENTS = ["information_retrieval", "summarization", "document_search", "workflow_execution", "communication",
           "data_analysis", "restricted_data_request", "general"]

SENSITIVE_TERMS = re.compile(r"\b(executive (compensation|salar|pay)|ceo (salary|pay|compensation)|board (strategy|"
                             r"minutes|deck|meeting)|acquisition|m&a|project atlas|salary of|everyone'?s salar|"
                             r"all salaries|compensation of)\b", re.I)


def detect_flags(text: str) -> dict:
    t = text.lower()
    has_leave_balance = bool(re.search(r"\b(leave|leaves|pto|vacation)\b.*\b(balance|remaining|left|how many)\b|"
                                       r"\b(balance|remaining|how many)\b.*\b(leave|leaves)\b", t))
    has_leave_submit = bool(re.search(
        r"\b(submit|apply|create|file|request|book|take|taking|need|want|give me|asking for|can i take|plan to take)\b.{0,40}\b(leave|days? off|pto|vacation|time off)\b"
        r"|\b(leave|pto|day off)\s+(tomorrow|today|next|this|on|from|for)\b"
        r"|\bleave request\b|\bneed\s+(some\s+)?leave\b",
        t
    ))
    return {
        "leave_balance": has_leave_balance,
        "leave_submit": has_leave_submit and not (has_leave_balance and not re.search(r"\b(apply|submit|book|take|request)\b", t)),
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
