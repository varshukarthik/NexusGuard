"""Deterministic, extractive answer composition used by the offline engine and the Policy Lab fallback.
It only ever reads Evidence objects — i.e. content that already passed authorization."""
from __future__ import annotations

import re
from datetime import timedelta

from .embeddings import tokenize
from .nlp import today
from .retrieval import Evidence, RetrievalResult

STALE_DAYS = 540


def split_sentences(text: str) -> list[str]:
    out = []
    for line in re.split(r"\n+", text):
        line = line.strip(" -•*\t")
        if not line or len(line) < 3:
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9₹])", line):
            s = s.strip()
            if len(s) > 2:
                out.append(s)
    return out


ANSWER_RX = re.compile(r"\b(how many|how much|how long|how do|how can|when|who|which|where|what time|timings?|"
                       r"password|limit|deadline|number|amount|forecast|budget|revenue|allowance|entitle\w*|days?|"
                       r"hours?|can i|do i|am i|is it|are we)\b", re.I)
BROAD_RX = re.compile(r"\b(polic(y|ies)|guidelines?|handbook|process|procedures?|report|status|plan|overview|"
                      r"strategy|show me|tell me about)\b", re.I)


def choose_mode(query: str, flags: dict) -> str:
    if flags.get("find_docs"):
        return "search"
    if flags.get("summarize") or flags.get("project"):
        return "summary"
    if BROAD_RX.search(query) and not ANSWER_RX.search(query):
        return "summary"
    return "answer"


def _score(sentence: str, q_tokens: set[str], numeric_q: bool, title_tokens: set[str] | None = None) -> float:
    st = set(tokenize(sentence))
    if not st or len(sentence) < 28 or sentence.rstrip().endswith("?"):
        return -1
    overlap = len(q_tokens & st)
    s = overlap / (len(q_tokens) ** 0.5 + 0.1)
    if numeric_q and re.search(r"\d", sentence):
        s += 0.35
    if sentence.endswith(":"):
        s -= 0.9  # headings are poor answers
    if title_tokens and len(sentence) < 110 and len(st & title_tokens) >= 0.6 * len(st):
        s -= 0.6  # title restatements ("Q3 2026 Engineering Report — status as of…")
    return s


def best_sentences(query: str, evidence: list[Evidence], n: int = 2, latest_only: bool = True) -> list[tuple[str, Evidence]]:
    q_tokens = set(tokenize(query))
    numeric_q = bool(re.search(r"\b(how many|how much|what is|number|amount|days|limit|revenue|forecast|budget)\b",
                               query.lower()))
    pool = []
    top_score = max((e.score for e in evidence), default=0) or 1
    for ev in evidence:
        if latest_only and not ev.is_latest:
            continue
        if ev.score < 0.85 * top_score and len(evidence) > 1:
            continue  # answer from the strongest document(s), not from weakly related ones
        for i, s in enumerate(split_sentences("\n".join(ev.chunks))):
            pool.append((_score(s, q_tokens, numeric_q, set(tokenize(ev.doc.title))) - i * 0.005, s, ev))
    pool.sort(key=lambda x: -x[0])
    seen, out = set(), []
    top = pool[0][0] if pool else 0
    for sc, s, ev in pool:
        if sc <= 0.15 or sc < 0.5 * top or s in seen:
            continue
        seen.add(s)
        out.append((s, ev))
        if len(out) >= n:
            break
    return out


def summarize(ev: Evidence, query: str, n: int = 5) -> list[str]:
    sents = split_sentences("\n".join(ev.chunks))
    q_tokens = set(tokenize(query)) or set(tokenize(ev.doc.title))
    tt = set(tokenize(ev.doc.title))
    scored = [(_score(s, q_tokens, False, tt) + (0.25 if re.search(r"\d", s) else 0) - i * 0.01, i, s)
              for i, s in enumerate(sents) if len(s) >= 30]
    top = sorted(scored, key=lambda x: -x[0])[:n]
    return [s for _, _, s in sorted(top, key=lambda x: x[1])]


def cite(ev: Evidence) -> str:
    return f"[{ev.doc.id}]"


def notes_for(res: RetrievalResult) -> list[str]:
    notes = []
    for c in res.conflicts:
        notes.append(f"⚠️ **Version conflict resolved:** {c['note']}")
    for ev in res.evidence:
        if ev.is_latest and ev.doc.effective_date < today() - timedelta(days=STALE_DAYS):
            notes.append(f"🕒 **Possibly outdated:** {ev.doc.title} was last effective "
                         f"{ev.doc.effective_date.isoformat()}; confirm with the document owner.")
    if res.withheld and res.evidence:
        notes.append(f"🔒 {len(res.withheld)} additional relevant document(s) are classified above your access "
                     "level and were **not** used for this answer.")
    if res.quarantined:
        notes.append(f"🛡️ {len(res.quarantined)} excerpt(s) were quarantined by the prompt-injection filter and "
                     "excluded from the answer.")
    return notes


def compose(query: str, res: RetrievalResult, mode: str = "answer") -> str:
    if res.only_restricted_answer():
        top = res.withheld[0]
        return (f"🔒 **Access denied.** Your current role does not have permission to access this "
                f"{top['classification'].lower()} resource. The information you asked about exists only in documents "
                "above your access level, so none of it was retrieved or shown to the AI.\n\n"
                "If you need it for your work, you can **request access** — the document owner will review it.")
    if not res.evidence:
        msg = ("I couldn't find that information in the NovaTech Solutions knowledge base you're authorized to "
               "access. Try rephrasing, or check the Documents page for what's available to your role.")
        if res.quarantined:
            msg += (f"\n\n🛡️ **Potential prompt injection detected.** {len(res.quarantined)} matching excerpt(s) from "
                    f"'{res.quarantined[0]['title']}' contained instructions trying to override security policy, so they "
                    "were quarantined and never sent to the AI. The security team has been alerted.")
        return msg
    latest = [e for e in res.evidence if e.is_latest] or res.evidence
    lines: list[str] = []
    if mode == "summary":
        ev = latest[0]
        lines.append(f"**{ev.doc.title}** (v{ev.doc.version}, effective {ev.doc.effective_date.strftime('%d %b %Y')}) "
                     f"{cite(ev)} — key points:")
        lines.extend(f"- {s}" for s in summarize(ev, query))
        related = [e for e in latest[1:3] if e.doc.family_key != ev.doc.family_key]
        if related:
            lines.append("")
            lines.append("**Related:** " + " · ".join(f"{e.doc.title} {cite(e)}" for e in related))
    elif mode == "search":
        lines.append(f"I found **{len(res.evidence)}** relevant document(s) you can access:")
        for ev in res.evidence:
            status = "current" if ev.is_latest else f"superseded by {ev.superseded_by}"
            first = next(iter(summarize(ev, query, 1)), "")
            lines.append(f"- **{ev.doc.title}** {cite(ev)} · {ev.doc.classification.title()} · "
                         f"{ev.doc.effective_date.strftime('%b %Y')} · {status} — {first[:140]}")
    else:
        picks = best_sentences(query, latest, n=3)
        if not picks:
            ev = latest[0]
            lines.append(f"The most relevant document I can access is **{ev.doc.title}** {cite(ev)}:")
            lines.extend(f"- {s}" for s in summarize(ev, query, 3))
        else:
            for s, ev in picks:
                lines.append(f"- {s} {cite(ev)}")
            lines.insert(0, f"Based on **{picks[0][1].doc.title}** (v{picks[0][1].doc.version}, effective "
                            f"{picks[0][1].doc.effective_date.strftime('%d %b %Y')}):")
    notes = notes_for(res)
    if notes:
        lines.append("")
        lines.extend(notes)
    return "\n".join(lines)


# ---- steps / summaries / comparisons (Document & IT agents) -----------------------------------

STEP_RX = re.compile(r"^\s*(?:\d+[.)]|step \d+[:.)]?|[-•*])\s+(.+)$", re.I)


def extract_steps(text: str) -> list[str]:
    """Numbered / bulleted procedure lines from an authorized document (first contiguous list wins)."""
    blocks: list[list[str]] = []
    cur: list[str] = []
    for line in text.split("\n"):
        m = STEP_RX.match(line)
        if m and len(m.group(1)) > 8:
            cur.append(m.group(1).strip())
        elif line.strip():
            if len(cur) >= 2:
                blocks.append(cur)
            cur = []
    if len(cur) >= 2:
        blocks.append(cur)
    numbered = [b for b in blocks if len(b) >= 3]
    return (numbered or blocks or [[]])[0]


def summarize_text(text: str, query: str = "", n: int = 6) -> list[str]:
    sents = []
    for s in split_sentences(text):
        s = s.strip()
        if len(s) < 30 or s.endswith((":", "?")):
            continue
        sents.append(s)
    if not sents:
        return [text.strip()[:300]]
    q = set(tokenize(query)) - {"summari", "summarize", "summary", "document", "policy"}
    scored = []
    for i, s in enumerate(sents):
        st = set(tokenize(s))
        sc = (0.6 if i == 0 else 0) + (0.25 if re.search(r"\d", s) else 0) + 0.3 * len(q & st) - i * 0.01
        sc += 0.15 if re.search(r"\b(must|required|mandatory|entitled|within|approval|never|only)\b", s, re.I) else 0
        scored.append((sc, i, s))
    top = sorted(scored, key=lambda x: -x[0])[:n]
    return [s for _, _, s in sorted(top, key=lambda x: x[1])]


def compare(data: dict) -> str:
    a, b, text_a, text_b = data["a"], data["b"], data["text_a"], data["text_b"]
    if (a["effective_date"], a["version"]) < (b["effective_date"], b["version"]):
        a, b, text_a, text_b = b, a, text_b, text_a  # orient: a = newer
    sa = [s for s in split_sentences(text_a) if len(s) > 25]
    sb = [s for s in split_sentences(text_b) if len(s) > 25]
    ta = {s: set(tokenize(s, expand=False)) for s in sa}
    tb = {s: set(tokenize(s, expand=False)) for s in sb}

    def best(s, pool):
        toks = ta.get(s) or tb.get(s) or set()
        cands = [(len(toks & t) / (len(toks | t) or 1), x) for x, t in pool.items()]
        return max(cands, default=(0, None))

    changed, added, same = [], [], []
    for s in sa:
        sim, other = best(s, tb)
        if sim >= 0.85:
            same.append(s)
        elif sim >= 0.35 and other:
            changed.append((other, s))
        else:
            added.append(s)
    removed = [s for s in sb if best(s, ta)[0] < 0.35]
    newer, older = a, b
    lines = [f"Comparing **{newer['title']}** v{newer['version']} ({newer['effective_date']}) [{newer['doc_id']}] "
             f"with **{older['title']}** v{older['version']} ({older['effective_date']}) [{older['doc_id']}].", ""]
    if changed:
        lines.append("**What changed**")
        for old, new in changed[:6]:
            lines.append(f"- **Now:** {new}\n  *Before:* {old}")
    if added:
        lines += ["", "**New in the current version**"] + [f"- {s}" for s in added[:5]]
    if removed:
        lines += ["", "**No longer in the current version**"] + [f"- {s}" for s in removed[:4]]
    if same:
        lines += ["", f"*{len(same)} provision(s) are unchanged.*"]
    if not (changed or added or removed):
        lines.append("The two documents are substantively the same.")
    lines += ["", f"The current version ({newer['doc_id']}) is authoritative."]
    return "\n".join(lines)
