"""FastAPI application entrypoint for AI Development Studio."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agents,
    chat,
    edit,
    fs,
    llm_config,
    memory,
    projects,
    providers,
    pull_requests,
    rag,
    scan,
    system,
    tasks,
)
from app.config import settings
from app.db import init_db
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Zero-config/dev/test path: create tables on startup. Postgres deployments
    # should run `alembic upgrade head` instead (create_all is a no-op once the
    # schema already exists).
    init_db()
    yield


app = FastAPI(title="AI Development Studio", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    projects,
    scan,
    chat,
    agents,
    tasks,
    providers,
    rag,
    llm_config,
    edit,
    pull_requests,
    system,
    memory,
    fs,
):
    app.include_router(router.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "service": "ads-backend", "version": "0.1.0"}
