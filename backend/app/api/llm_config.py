"""DB-backed LLM provider configuration (persistent across restarts).

One ``LLMProviderConfig`` row per provider holds its enabled flag, credentials,
and (for Ollama) the localhost/cloud endpoint pair. Saving config refreshes the
provider registry so changes take effect live, without a server restart.

API keys are write-only: ``GET`` returns ``has_api_key`` instead of the key, and
``PUT`` leaves the stored key untouched when the incoming ``api_key`` is null.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LLMProviderConfig
from app.providers import reset_registry
from app.schemas import (
    LLMConfigIn,
    LLMConfigOut,
    LLMProviderConfigOut,
    ProviderName,
)

router = APIRouter(prefix="/llm-config", tags=["llm-config"])


def _to_out(row: LLMProviderConfig) -> LLMProviderConfigOut:
    return LLMProviderConfigOut(
        provider_name=row.provider_name,
        enabled=bool(row.enabled),
        has_api_key=bool(row.api_key),
        base_url=row.base_url,
        ollama_mode=row.ollama_mode or "localhost",
        ollama_local_base_url=row.ollama_local_base_url,
        ollama_cloud_base_url=row.ollama_cloud_base_url,
    )


def _default_out(name: ProviderName) -> LLMProviderConfigOut:
    return LLMProviderConfigOut(
        provider_name=name,
        enabled=False,
        has_api_key=False,
        base_url=None,
        ollama_mode="localhost",
        ollama_local_base_url=None,
        ollama_cloud_base_url=None,
    )


def _apply_config(db: Session, payload: LLMConfigIn) -> LLMConfigOut:
    existing = {c.provider_name: c for c in db.scalars(select(LLMProviderConfig)).all()}

    for p in payload.providers:
        name = str(p.provider_name.value)

        row = existing.get(name)
        if row is None:
            row = LLMProviderConfig(provider_name=name)
            db.add(row)
            existing[name] = row

        row.enabled = p.enabled

        # api_key: None -> keep stored value; "" -> clear; otherwise replace.
        if p.api_key is not None:
            row.api_key = p.api_key or None

        row.base_url = p.base_url

        # Ollama mode + endpoints.
        row.ollama_mode = p.ollama_mode
        if p.ollama_local_base_url is not None:
            row.ollama_local_base_url = p.ollama_local_base_url
        if p.ollama_cloud_base_url is not None:
            row.ollama_cloud_base_url = p.ollama_cloud_base_url

    db.commit()

    # Providers are built from these rows at registry-build time; drop the cache
    # so the new config takes effect on the next resolve without a restart.
    reset_registry()

    return _read_all(db)


def _read_all(db: Session) -> LLMConfigOut:
    rows = db.scalars(select(LLMProviderConfig)).all()
    row_map = {r.provider_name: r for r in rows}

    providers: list[LLMProviderConfigOut] = []
    for name in ProviderName:
        key = str(name.value)
        if key in row_map:
            providers.append(_to_out(row_map[key]))
        else:
            providers.append(_default_out(name))

    return LLMConfigOut(providers=providers)


@router.get("", response_model=LLMConfigOut)
def get_llm_config(db: Session = Depends(get_db)) -> LLMConfigOut:
    return _read_all(db)


@router.put("", response_model=LLMConfigOut)
def put_llm_config(payload: LLMConfigIn, db: Session = Depends(get_db)) -> LLMConfigOut:
    names = [p.provider_name for p in payload.providers]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=400, detail="Duplicate provider configs provided")
    return _apply_config(db, payload)
