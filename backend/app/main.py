"""FastAPI application entrypoint for AI Development Studio."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agents,
    chat,
    edit,
    llm_config,
    projects,
    providers,
    pull_requests,
    rag,
    scan,
    tasks,
)
from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables on startup. Replace with Alembic migrations
    # before the schema is considered stable.
    init_db()
    yield


app = FastAPI(title="AI Development Studio", version="0.1.0", lifespan=lifespan)

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
):
    app.include_router(router.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "service": "ads-backend", "version": "0.1.0"}
