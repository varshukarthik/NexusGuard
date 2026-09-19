"""In-process hybrid search index: BM25 keyword scoring + dense-vector similarity over document chunks.

The index holds chunk *tokens* and *vectors* only (never handed to the LLM). Every search call receives the set of
document ids the caller is AUTHORIZED to read — computed beforehand by core.rbac — and scores only chunks belonging
to those documents. Unauthorized chunks are never scored for the answer path, and chunk text is loaded from the
database only for the few authorized chunks that are finally selected.

The index is rebuilt lazily when documents are (re)indexed in this process (invalidate()) or when the chunk count in
the database changes (another worker indexed something).
"""
from __future__ import annotations

import logging
import math
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import func, select

from .embeddings import SYNONYMS, _stem, tokenize

log = logging.getLogger("novatech.search")
K1, B = 1.4, 0.72

_GEN: dict[str, int] = {}
_CACHE: dict[str, "HybridIndex"] = {}
_LOCK = threading.Lock()


def invalidate(company_id: str) -> None:
    _GEN[company_id] = _GEN.get(company_id, 0) + 1


# Generic enterprise words carry little topical signal ("internal onboarding process" is about onboarding).
GENERIC = {_stem(w) for w in """internal company novatech employee employees staff official current latest new process
procedure policy policies guide document documents information detail details please explain show tell give
available team
organisation organization""".split()}


def term_weight(t: str) -> float:
    return 0.3 if t in GENERIC else 1.0


def query_terms(query: str, with_synonyms: bool = False):
    """Base query tokens (weight 1.0, generic words 0.3) plus synonym expansions (weight 0.5).

    With with_synonyms=True also returns {synonym_token: base_token} so a document that uses a synonym ("sold",
    "products") still counts as covering the user's word ("sell")."""
    base = list(dict.fromkeys(tokenize(query, expand=False)))
    weights: dict[str, float] = {t: term_weight(t) for t in base}
    syn_of: dict[str, str] = {}
    raw = [t for t in query.lower().replace("-", " ").split()]
    for w in raw:
        w = "".join(ch for ch in w if ch.isalnum() or ch == "&")
        b = _stem(w)
        for syn in SYNONYMS.get(w, []):
            s = _stem(syn)
            weights.setdefault(s, 0.5)
            if s not in base and b in base:
                syn_of.setdefault(s, b)
    return (base, weights, syn_of) if with_synonyms else (base, weights)


@dataclass
class DocHit:
    doc_id: str
    vec: float = 0.0
    bm25: float = 0.0
    matched: set = field(default_factory=set)
    chunks: list = field(default_factory=list)  # (chunk_id, chunk_score)


class HybridIndex:
    def __init__(self, chunk_ids: list[str], doc_ids: list[str], texts: list[str], vectors: list, dim: int):
        self.n = len(chunk_ids)
        self.chunk_ids = chunk_ids
        self.doc_list = list(dict.fromkeys(doc_ids))
        self.doc_pos = {d: i for i, d in enumerate(self.doc_list)}
        self.chunk_doc = np.array([self.doc_pos[d] for d in doc_ids], dtype=np.int32)
        mat = np.zeros((self.n, dim), dtype=np.float32)
        for i, v in enumerate(vectors):
            if v is not None and len(v) == dim:
                mat[i] = np.asarray(v, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1)
        norms[norms == 0] = 1.0
        self.emb = mat / norms[:, None]
        post: dict[str, list[tuple[int, int]]] = defaultdict(list)
        lengths = np.zeros(self.n, dtype=np.float32)
        for i, t in enumerate(texts):
            toks = tokenize(t, expand=False)
            lengths[i] = max(1, len(toks))
            for tok, tf in Counter(toks).items():
                post[tok].append((i, tf))
        self.dl = lengths
        self.avgdl = float(lengths.mean()) if self.n else 1.0
        self.post = {t: (np.array([i for i, _ in lst], dtype=np.int32), np.array([f for _, f in lst], dtype=np.float32))
                     for t, lst in post.items()}
        self.idf = {t: math.log(1 + (self.n - len(v[0]) + 0.5) / (len(v[0]) + 0.5)) for t, v in self.post.items()}

    def mask_for(self, doc_ids: set[str]) -> np.ndarray:
        pos = [self.doc_pos[d] for d in doc_ids if d in self.doc_pos]
        if not pos:
            return np.zeros(self.n, dtype=bool)
        return np.isin(self.chunk_doc, np.array(pos, dtype=np.int32))

    def search(self, qvec: list[float] | None, query: str, doc_ids: set[str], *, per_doc_chunks: int = 3) -> dict[str, DocHit]:
        if not self.n or not doc_ids:
            return {}
        mask = self.mask_for(doc_ids)
        if not mask.any():
            return {}
        # --- dense similarity (authorized chunks only)
        vec = np.zeros(self.n, dtype=np.float32)
        if qvec is not None:
            q = np.asarray(qvec, dtype=np.float32)
            nq = np.linalg.norm(q) or 1.0
            idx = np.nonzero(mask)[0]
            vec[idx] = self.emb[idx] @ (q / nq)
        # --- BM25 (authorized chunks only)
        base, weights, syn_of = query_terms(query, with_synonyms=True)
        base = set(base)
        bm = np.zeros(self.n, dtype=np.float32)
        matched_by_chunk: dict[int, set] = defaultdict(set)
        for tok, w in weights.items():
            p = self.post.get(tok)
            if p is None:
                continue
            ids, tf = p
            keep = mask[ids]
            if not keep.any():
                continue
            ids, tf = ids[keep], tf[keep]
            s = self.idf[tok] * tf * (K1 + 1) / (tf + K1 * (1 - B + B * self.dl[ids] / self.avgdl))
            np.add.at(bm, ids, w * s)
            credit = tok if tok in base else syn_of.get(tok)
            if credit:
                for i in ids.tolist():
                    matched_by_chunk[i].add(credit)
        bm_max = float(bm.max()) or 1.0
        combined = 0.5 * np.clip(vec, 0, None) + 0.5 * (bm / bm_max)
        cand = np.nonzero(mask & ((bm > 0) | (vec > 0.25)))[0]
        if len(cand) > 400:
            cand = cand[np.argsort(-combined[cand])[:400]]
        hits: dict[str, DocHit] = {}
        for i in cand.tolist():
            did = self.doc_list[self.chunk_doc[i]]
            h = hits.get(did)
            if h is None:
                h = hits[did] = DocHit(did)
            h.vec = max(h.vec, float(vec[i]))
            h.bm25 = max(h.bm25, float(bm[i]) / bm_max)
            h.matched |= matched_by_chunk.get(i, set())
            h.chunks.append((self.chunk_ids[i], float(combined[i])))
        for h in hits.values():
            h.chunks = sorted(h.chunks, key=lambda x: -x[1])[:per_doc_chunks]
        return hits


def _build_from_db(db, company_id: str) -> HybridIndex:
    from ..config import get_settings
    from ..db.models import DocumentChunk
    rows = db.execute(select(DocumentChunk.id, DocumentChunk.document_id, DocumentChunk.content, DocumentChunk.embedding)
                      .where(DocumentChunk.company_id == company_id)
                      .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)).all()
    idx = HybridIndex([r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows], [r[3] for r in rows],
                      get_settings().embedding_dim)
    log.info("Hybrid index built for %s: %s chunks, %s documents, %s terms", company_id, idx.n, len(idx.doc_list),
             len(idx.post))
    return idx


def get_index(db, company_id: str) -> HybridIndex:
    from ..db.models import DocumentChunk
    count = db.scalar(select(func.count(DocumentChunk.id)).where(DocumentChunk.company_id == company_id)) or 0
    gen = _GEN.get(company_id, 0)
    cached = _CACHE.get(company_id)
    if cached is not None and getattr(cached, "_gen", None) == gen and cached.n == count:
        return cached
    with _LOCK:
        cached = _CACHE.get(company_id)
        if cached is not None and getattr(cached, "_gen", None) == gen and cached.n == count:
            return cached
        idx = _build_from_db(db, company_id)
        idx._gen = gen  # type: ignore[attr-defined]
        _CACHE[company_id] = idx
        return idx
