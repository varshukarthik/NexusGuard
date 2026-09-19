"""AI security layer: prompt-injection detection, DLP redaction, upload sanitization.

Heuristic, deterministic and fast — it runs on (1) user input, (2) every retrieved chunk before it can reach
the model, (3) every uploaded document at ingestion, and (4) every model output before it reaches the user.
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field

# ---- Prompt injection ------------------------------------------------------------------------

INJECTION_RULES: list[tuple[str, str, int]] = [
    (r"\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|your|system)\b.{0,30}"
     r"\b(instruction|instructions|rules|prompt|guidelines|polic(y|ies))", "instruction_override", 9),
    (r"\b(reveal|print|show|output|repeat|leak)\b.{0,30}\b(system|hidden|developer)\s+(prompt|message|instructions)",
     "system_prompt_extraction", 9),
    (r"\b(override|bypass|disable|skip|circumvent)\b.{0,30}\b(access control|rbac|authori[sz]ation|permission|"
     r"security|guardrail|filter)", "access_control_bypass", 9),
    (r"\b(reveal|expose|dump|list|share)\b.{0,40}\b(confidential|restricted|secret|classified)\b.{0,30}"
     r"\b(information|data|documents?|files?)", "confidential_exfiltration", 7),
    (r"\b(send|email|forward|post|upload|exfiltrate)\b.{0,60}\b(to|at)\b.{0,20}"
     r"[\w.+-]+@(?!novatech\.demo)[\w-]+\.[\w.]+", "external_exfiltration", 8),
    (r"\byou are now\b|\bact as (an? )?(admin|administrator|root|developer mode|dan)\b|\bjailbreak\b",
     "role_hijack", 7),
    (r"\b(new|updated) (system )?instructions?\s*:", "instruction_injection", 6),
    (r"<\s*/?\s*(system|assistant|im_start|im_end)\s*>|\[\[\s*system\s*\]\]", "delimiter_spoofing", 7),
    (r"\bdo not (tell|inform|mention)\b.{0,30}\b(user|employee|anyone)\b", "concealment", 5),
    (r"\bwhat (is|are|were) your (system |initial |hidden )?(prompt|instructions|rules)\b|\brepeat (the|your) "
     r"(text|words|instructions) above\b|\b(print|show|reveal|dump) (your|the) (config|configuration|system prompt)",
     "system_prompt_extraction", 8),
    (r"\b(pretend|assume|act as if|imagine|suppose)\b.{0,30}\b(i am|i'm|i have|you are)\b.{0,30}\b(an? )?(admin|"
     r"administrator|hr( manager)?|ceo|cfo|executive|root|superuser|security admin|elevated|full access)",
     "privilege_escalation", 7),
    (r"\b(dump|export|list|show|give me)\b.{0,25}\b(all|entire|whole|every|complete)\b.{0,25}\b(database|db|tables?|"
     r"employee records|salar(y|ies)|personal data|confidential (docs|documents|files))", "bulk_data_extraction", 7),
    (r"('|\")\s*(or|and)\s+('|\")?\d+('|\")?\s*=\s*('|\")?\d|;\s*(drop|delete|truncate|alter|insert|update)\s+"
     r"(table|from|into)?|\bunion\s+(all\s+)?select\b|--\s*$", "sql_injection", 7),
    (r"\bdeveloper mode\b|\bdan mode\b|\bno (restrictions|limits|rules)\b.{0,20}\b(mode|now)\b", "role_hijack", 7),
]
_COMPILED = [(re.compile(p, re.I | re.S), cat, sev) for p, cat, sev in INJECTION_RULES]
ZERO_WIDTH = re.compile(r"[​‌‍⁠﻿­]")


@dataclass
class InjectionReport:
    detected: bool
    score: int = 0
    findings: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return ", ".join(sorted({f["category"] for f in self.findings}))


def scan_injection(text: str) -> InjectionReport:
    findings: list[dict] = []
    t = unicodedata.normalize("NFKC", ZERO_WIDTH.sub("", text or ""))
    for rx, cat, sev in _COMPILED:
        m = rx.search(t)
        if m:
            findings.append({"category": cat, "severity": sev, "evidence": m.group(0)[:160]})
    if ZERO_WIDTH.search(text or ""):
        findings.append({"category": "hidden_characters", "severity": 4, "evidence": "zero-width characters present"})
    score = max((f["severity"] for f in findings), default=0)
    return InjectionReport(detected=score >= 6, score=score, findings=findings)


# ---- Data loss prevention --------------------------------------------------------------------

def _luhn(num: str) -> bool:
    digits = [int(d) for d in num][::-1]
    total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digits))
    return total % 10 == 0


def _mask_tail(value: str, keep: int = 4, group: int = 4) -> str:
    digits = re.sub(r"\D", "", value)
    if not digits:
        return "X" * max(len(value) - keep, 4) + value[-keep:]
    masked = "X" * (len(digits) - keep) + digits[-keep:]
    return "-".join(masked[i:i + group] for i in range(0, len(masked), group))


DLP_RULES = [
    ("API key", re.compile(r"\b(sk-(?:proj-)?[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|"
                           r"xox[bap]-[A-Za-z0-9-]{10,})\b"), lambda m: m.group(0)[:4] + "••••[REDACTED]"),
    ("Password", re.compile(r"(?i)\b(password|passwd|pwd|passcode)(\s*(?:is|:|=)\s*)([^\s,;]{4,})"),
     lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]"),
    ("Credit card", re.compile(r"\b(?:\d[ -]?){13,16}\b"), None),  # validated with Luhn below
    ("Aadhaar", re.compile(r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b"), lambda m: _mask_tail(m.group(0))),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), lambda m: "XXXXX" + m.group(0)[5:9] + "X"),
    ("Bank account", re.compile(r"(?i)\b(a/c|account(?:\s+(?:no\.?|number))?|acct)(\s*(?:is|:|#|no\.?)?\s*)(\d{9,18})\b"),
     lambda m: f"{m.group(1)}{m.group(2)}{_mask_tail(m.group(3))}"),
    ("Personal phone", re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"),
     lambda m: "+91 XXXXX-X" + re.sub(r"\D", "", m.group(0))[-4:]),
    ("Passport", re.compile(r"\b[A-Z]\d{7}\b"), lambda m: "[PASSPORT-REDACTED]"),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), lambda m: "[JWT-REDACTED]"),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.S), lambda m: "[PRIVATE-KEY-REDACTED]"),
    ("Cloud credential", re.compile(r"\b(?:aws_secret_access_key|client_secret|secret_access_key)\s*[=:]\s*[^\s,;]{8,}", re.I), lambda m: m.group(0).split("=")[0].strip()+"=[REDACTED]"),
    ("Employee ID", re.compile(r"\b(?:EMP|EID)[-_]?\d{4,10}\b", re.I), lambda m: "[EMPLOYEE-ID-REDACTED]"),
]


@dataclass
class DLPResult:
    text: str
    redactions: list[dict] = field(default_factory=list)

    @property
    def redacted(self) -> bool:
        return bool(self.redactions)


def redact(text: str) -> DLPResult:
    if not text:
        return DLPResult(text or "")
    found: list[dict] = []
    out = text
    for label, rx, fn in DLP_RULES:
        def _sub(m, label=label, fn=fn):
            raw = m.group(0)
            if label == "Credit card":
                digits = re.sub(r"\D", "", raw)
                if not (13 <= len(digits) <= 16 and _luhn(digits)):
                    return raw
                rep = _mask_tail(digits)
            else:
                rep = fn(m)
            if rep != raw:
                found.append({"type": label})
            return rep
        out = rx.sub(_sub, out)
    counts: dict[str, int] = {}
    for f in found:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    return DLPResult(out, [{"type": k, "count": v} for k, v in counts.items()])


# ---- Upload sanitization ---------------------------------------------------------------------

ALLOWED_EXT = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".docx", ".pdf"}


def sanitize_text(raw: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    text = raw
    if ZERO_WIDTH.search(text):
        notes.append("Removed zero-width / hidden characters")
        text = ZERO_WIDTH.sub("", text)
    if re.search(r"<\s*(script|iframe|object|embed|style)\b", text, re.I):
        notes.append("Stripped active HTML content (script/iframe/style)")
        text = re.sub(r"<\s*(script|iframe|object|embed|style)\b.*?<\s*/\s*\1\s*>", " ", text, flags=re.I | re.S)
    if re.search(r"<[a-zA-Z/][^>]*>", text):
        notes.append("Stripped HTML markup")
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)  # HTML comments are a classic hiding place
        text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, notes
