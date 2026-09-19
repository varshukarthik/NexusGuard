"""Edge-style protections implemented in-app for the prototype.

• Rate limiting — REAL (sliding window per client+route group). In production, also enforce at the WAF / API gateway.
• WAF-lite     — REAL but minimal signature rules on URL/query only. Production: AWS WAF / Cloudflare managed rules.
• Security headers + request ids — REAL.
"""
from __future__ import annotations

import re
import threading
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_settings

settings = get_settings()

COUNTERS = {"requests": 0, "rate_limited": 0, "waf_blocked": 0, "started": time.time()}
_WAF = re.compile(r"(<script|javascript:|union\s+select|;\s*drop\s+table|\.\./\.\./|/etc/passwd|\bor\s+1=1\b)", re.I)


class RateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float = 60.0) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                return False, int(window - (now - q[0])) + 1
            q.append(now)
            return True, 0


limiter = RateLimiter()


def _group(path: str) -> tuple[str, int]:
    if path.endswith("/chat") or path.endswith("/chat/stream") or path.endswith("/regenerate") \
            or "/policy-lab/evaluate" in path:
        return "chat", settings.chat_rate_limit_per_minute
    if "/auth/guest" in path:
        return "guest", settings.guest_rate_limit_per_minute
    if "/auth/" in path:
        return "auth", settings.login_rate_limit_per_minute
    return "api", settings.rate_limit_per_minute


class EdgeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = uuid.uuid4().hex[:16]
        request.state.request_id = rid
        path = request.url.path
        COUNTERS["requests"] += 1
        if path.startswith("/api"):
            raw = f"{path}?{request.url.query}"
            if _WAF.search(raw):
                COUNTERS["waf_blocked"] += 1
                return self._secure(JSONResponse({"error": "request_blocked", "message":
                                                  "Request blocked by the web application firewall."}, 403), rid)
            if request.method != "OPTIONS" and not path.endswith("/health"):
                grp, lim = _group(path)
                auth = request.headers.get("authorization", "")
                ident = auth[-16:] if auth else (request.client.host if request.client else "anon")
                if grp == "auth" and request.method == "GET":
                    grp, lim = "api", settings.rate_limit_per_minute
                ok, retry = limiter.allow(f"{grp}:{ident}", lim)
                if not ok:
                    COUNTERS["rate_limited"] += 1
                    resp = JSONResponse({"error": "rate_limited", "message": f"Too many requests. Please wait "
                                         f"{retry}s and try again.", "retry_after": retry}, 429)
                    resp.headers["Retry-After"] = str(retry)
                    return self._secure(resp, rid)
        response = await call_next(request)
        return self._secure(response, rid)

    @staticmethod
    def _secure(resp, rid):
        resp.headers["X-Request-ID"] = rid
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        resp.headers["Cache-Control"] = resp.headers.get("Cache-Control", "no-store")
        return resp
