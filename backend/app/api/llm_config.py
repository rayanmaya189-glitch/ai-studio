from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LLMProviderConfig
from app.schemas import LLMConfigIn, LLMConfigOut, LLMProviderConfigIn, ProviderName

router = APIRouter(prefix="/llm-config", tags=["llm-config"])


def _apply_config(db: Session, payload: LLMConfigIn) -> LLMConfigOut:
    existing = {c.provider_name: c for c in db.scalars(select(LLMProviderConfig)).all()}

    out: dict[str, dict] = {}

    for p in payload.providers:
        name = p.provider_name

        row = existing.get(name)
        if row is None:
            row = LLMProviderConfig(provider_name=name)
            db.add(row)

        row.enabled = p.enabled
        row.api_key = p.api_key
        row.base_url = p.base_url

        # Ollama mode
        row.ollama_mode = p.ollama_mode

        # Ollama URLs: allow separate endpoints for localhost/cloud.
        if p.ollama_local_base_url is not None:
            row.ollama_local_base_url = p.ollama_local_base_url
        if p.ollama_cloud_base_url is not None:
            row.ollama_cloud_base_url = p.ollama_cloud_base_url

        row.updated_at = row.updated_at  # keep mypy/linters quiet; onupdate handles it.

        db.flush()
        out[name] = {
            "provider_name": row.provider_name,
            "enabled": row.enabled,
            "api_key": row.api_key,
            "base_url": row.base_url,
            "ollama_mode": row.ollama_mode,
            "ollama_local_base_url": row.ollama_local_base_url,
            "ollama_cloud_base_url": row.ollama_cloud_base_url,
        }

    db.commit()

    # Re-load for accurate timestamps/defaulted fields.
    saved = db.scalars(select(LLMProviderConfig)).all()
    saved_map = {c.provider_name: c for c in saved}

    return LLMConfigOut(
        providers=[LLMProviderConfigIn.model_validate(saved_map[k]) for k in saved_map.keys()]
    )


@router.get("", response_model=LLMConfigOut)
def get_llm_config(db: Session = Depends(get_db)) -> LLMConfigOut:
    rows = db.scalars(select(LLMProviderConfig)).all()
    row_map = {r.provider_name: r for r in rows}
    providers: list[LLMProviderConfigIn] = []

    for name in ProviderName:
        key = str(name.value)
        if key in row_map:
            providers.append(LLMProviderConfigIn.model_validate(row_map[key]))
        else:
            # Default config: disabled (so /providers doesn't show it).
            providers.append(
                LLMProviderConfigIn(
                    provider_name=name,
                    enabled=False,
                    api_key=None,
                    base_url=None,
                    ollama_mode="localhost",
                    ollama_local_base_url=None,
                    ollama_cloud_base_url=None,
                )
            )

    return LLMConfigOut(providers=providers)


@router.put("", response_model=LLMConfigOut)
def put_llm_config(payload: LLMConfigIn, db: Session = Depends(get_db)) -> LLMConfigOut:
    # Ensure no duplicates
    names = [p.provider_name for p in payload.providers]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=400, detail="Duplicate provider configs provided")
    return _apply_config(db, payload)
