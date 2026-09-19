"""Embedding provider.

- OpenAI `text-embedding-3-small` (truncated to EMBEDDING_DIM via the `dimensions` param) when a key is set.
- Otherwise a deterministic local feature-hashing embedder (unigrams + bigrams + synonym expansion), so
  semantic-ish search works offline. Both produce L2-normalised vectors of the same dimension.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re

from ..config import get_settings
from . import llm

log = logging.getLogger("novatech.embed")
settings = get_settings()

STOP = set("""a an the and or of to in on for with is are was were be been by at as it this that from
what whats how many much do does did i me my we our you your can could please tell show give find
about any all there their them than then into also latest current will would should which who when
where let know need get summarize summarise summary overview key points show find give tell related
docs list search look up locate brief tldr kindly want see""".split())

# Light domain synonym map so the offline embedder behaves "semantically" for enterprise vocabulary.
SYNONYMS = {
    "wfh": ["work", "home", "remote"], "remote": ["wfh", "home"], "remotely": ["remote", "wfh"],
    "pto": ["leave"], "vacation": ["leave"], "holiday": ["leave", "holidays"], "leaves": ["leave"],
    "salary": ["compensation", "pay"], "salaries": ["compensation", "pay"], "pay": ["compensation"],
    "comp": ["compensation"], "ceo": ["executive"], "cxo": ["executive"], "executives": ["executive"],
    "revenue": ["financial", "finance"], "earnings": ["financial", "revenue"], "finance": ["financial"],
    "onboard": ["onboarding"], "joiner": ["onboarding"], "laptop": ["it", "device"], "vpn": ["it", "network"],
    "password": ["security", "credential"], "board": ["strategy", "directors"], "q3": ["quarter", "third"],
    "q4": ["quarter", "fourth"], "forecast": ["projection", "projected"], "projected": ["forecast"],
    "handbook": ["policy", "employee"], "status": ["progress", "report"], "acquisition": ["m&a", "merger"],
    "wifi": ["wi", "fi", "network", "guest"], "cafeteria": ["canteen", "lunch", "food"], "canteen": ["cafeteria"],
    # --- broader enterprise paraphrase coverage (offline engine) ---
    "absence": ["leave"], "timeoff": ["leave"], "off": ["leave"], "sick": ["leave"], "annual": ["leave", "earned"],
    "reimburse": ["reimbursement", "expense", "claim"], "reimbursed": ["reimbursement", "expense"],
    "refund": ["reimbursement", "expense"], "claim": ["expense", "reimbursement"], "claims": ["expense", "reimbursement"],
    "expenses": ["expense", "reimbursement"], "computer": ["laptop", "device"], "pc": ["laptop", "device"],
    "notebook": ["laptop"], "macbook": ["laptop"], "replace": ["replacement"], "swap": ["replacement"],
    "broken": ["fault", "replacement", "hardware"], "damaged": ["fault", "replacement"],
    "hybrid": ["remote", "wfh", "home"], "perks": ["benefits"], "perk": ["benefits"], "insurance": ["benefits", "health"],
    "medical": ["health", "insurance"], "joining": ["onboarding"], "joined": ["onboarding"], "induction": ["onboarding"],
    "newcomer": ["onboarding"], "hire": ["recruitment", "hiring"], "buy": ["purchase", "procurement"],
    "buying": ["purchase", "procurement"], "procure": ["procurement", "purchase"], "requisition": ["purchase", "request"],
    "supplier": ["vendor"], "suppliers": ["vendor"], "escalate": ["escalation"], "escalating": ["escalation"],
    "issue": ["ticket", "incident"], "problem": ["ticket", "troubleshooting"], "fix": ["troubleshooting"],
    "login": ["sign", "authentication", "password"], "signin": ["authentication"], "credentials": ["password"],
    "payroll": ["salary", "pay"], "appraisal": ["performance", "review"], "rating": ["performance"],
    "course": ["training", "learning"], "courses": ["training", "learning"], "learning": ["training"],
    "recruitment": ["hiring", "recruiting"], "interview": ["recruitment", "hiring"], "gdpr": ["data", "protection", "privacy"],
    "privacy": ["data", "protection"], "scam": ["phishing"], "app": ["software", "application"],
    "apps": ["software", "application"], "tool": ["software"], "tools": ["software"], "install": ["software", "installation"],
    "timings": ["hours", "time"], "hours": ["working", "attendance"], "boss": ["manager"], "supervisor": ["manager"],
    "due": ["deadline"], "late": ["delayed", "overdue"], "behind": ["delayed", "schedule"], "overdue": ["delayed"],
    "slipping": ["delayed"], "org": ["organization", "structure"], "hierarchy": ["organization", "structure"],
    "owns": ["owner", "ownership"], "responsible": ["owner", "ownership"], "whom": ["contact"],
    "offices": ["locations", "office"], "headquarters": ["office", "locations"],
    "sell": ["products", "sold", "services"], "sells": ["products", "sold"], "offer": ["products", "services"],
    "offerings": ["products", "services"], "portfolio": ["products"], "located": ["locations", "office"],
    "where": ["locations"],
}


def _stem(t: str) -> str:
    for suf in ("ing", "ies", "es", "ed", "s"):
        if len(t) > 4 and t.endswith(suf):
            return t[: -len(suf)] + ("y" if suf == "ies" else "")
    return t


def tokenize(text: str, expand: bool = True) -> list[str]:
    toks = [t for t in re.findall(r"[a-z0-9&]+", text.lower()) if t not in STOP and len(t) > 1]
    out: list[str] = []
    for t in toks:
        out.append(_stem(t))
        if expand:
            out.extend(_stem(s) for s in SYNONYMS.get(t, []))
    return out


def _h(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "little")


def local_embed(text: str, dim: int | None = None) -> list[float]:
    dim = dim or settings.embedding_dim
    vec = [0.0] * dim
    toks = tokenize(text)
    counts: dict[str, int] = {}
    for t in toks:
        counts[t] = counts.get(t, 0) + 1
    for i in range(len(toks) - 1):
        bg = toks[i] + "_" + toks[i + 1]
        counts[bg] = counts.get(bg, 0) + 1
    for feat, c in counts.items():
        h = _h(feat)
        w = (1 + math.log(c)) * (0.6 if "_" in feat else 1.0)
        vec[h % dim] += w if (h >> 32) & 1 else -w
    n = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / n for v in vec]


class Embedder:
    def __init__(self):
        self.provider = "local"
        if settings.openai_enabled and settings.use_openai_embeddings:
            self.provider = "openai"

    @property
    def model_id(self) -> str:
        if self.provider == "openai":
            return f"openai:{settings.openai_embedding_model}:{settings.embedding_dim}"
        return f"local-hash:{settings.embedding_dim}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "openai":
            try:
                client = llm.client()
                out: list[list[float]] = []
                for i in range(0, len(texts), 64):
                    resp = client.embeddings.create(model=settings.openai_embedding_model,
                                                    input=[t[:8000] for t in texts[i:i + 64]],
                                                    dimensions=settings.embedding_dim)
                    out.extend(d.embedding for d in resp.data)
                return out
            except Exception as exc:
                log.warning("OpenAI embeddings failed (%s) — switching to local embedder", type(exc).__name__)
                self.provider = "local"
        return [local_embed(t) for t in texts]


embedder = Embedder()


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
