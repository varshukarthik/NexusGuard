from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..config import get_settings
from .models import Base

log = logging.getLogger("novatech.db")
settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

PGVECTOR = False


def init_db(reset: bool = False) -> None:
    global PGVECTOR
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                PGVECTOR = True
            except Exception as exc:  # pragma: no cover
                log.warning("pgvector unavailable (%s); falling back to in-app vector ranking", exc)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    if PGVECTOR:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw ON document_chunks "
                "USING hnsw (embedding vector_cosine_ops)"))
    log.info("Database ready (%s, pgvector=%s)", engine.dialect.name, PGVECTOR)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
