"""NovaTech Solutions — Enterprise Intelligence Platform (FastAPI)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .core.errors import AppError
from .core.middleware import EdgeMiddleware
from .db import session as dbsession
from .db.seed import ensure_index, seed
from .routers import agentic, auth, documents, governance, policy_lab, workspace
from .services import llm
from .services.embeddings import embedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("novatech")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    dbsession.init_db(reset=settings.reset_db_on_start)
    with dbsession.SessionLocal() as db:
        seed(db)
        ensure_index(db)
    log.info("AI engine: %s · embeddings: %s", "openai:" + settings.openai_model if llm.enabled() else "offline",
             embedder.model_id)
    try:  # warm the hybrid search index so the first question is fast
        from .services.search_index import get_index
        with dbsession.SessionLocal() as db:
            get_index(db, "cmp_novatech")
    except Exception:  # pragma: no cover
        log.exception("search index warm-up failed")
    yield


app = FastAPI(title="NovaTech Solutions — Enterprise Intelligence Platform", version="2.0.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
app.add_middleware(EdgeMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                   allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])


@app.exception_handler(AppError)
async def app_error(request: Request, exc: AppError):
    return JSONResponse({"error": exc.code, "message": exc.message, **exc.extra}, status_code=exc.status)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    fields = [".".join(str(x) for x in e.get("loc", [])[1:]) for e in exc.errors()]
    return JSONResponse({"error": "invalid_request", "message": "Some fields are invalid: " + ", ".join(fields[:5]),
                         "fields": fields[:10]}, status_code=422)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    msg = exc.detail if exc.status_code < 500 else "Something went wrong."
    if exc.status_code == 404 and msg == "Not Found":
        msg = "The requested resource was not found."
    return JSONResponse({"error": "http_error", "message": msg}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error (request %s)", getattr(request.state, "request_id", "?"))
    return JSONResponse({"error": "internal_error", "message": "Something went wrong on our side. The incident was "
                         "logged — please try again.", "request_id": getattr(request.state, "request_id", "")},
                        status_code=500)


for r in (auth.router, workspace.router, documents.router, governance.router, policy_lab.router, agentic.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health")
def health():
    try:
        with dbsession.engine.connect() as c:
            c.exec_driver_sql("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "service": "NovaTech Solutions",
            "database": dbsession.engine.dialect.name, "db_ok": db_ok,
            "pgvector": dbsession.PGVECTOR, "ai_engine": "openai" if llm.enabled() else "offline",
            "model": settings.openai_model if llm.enabled() else None, "embeddings": embedder.model_id}


# Serve the built React app (frontend/dist) when present — single-process demo deployment.
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        if path and f.is_file() and DIST in f.resolve().parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
