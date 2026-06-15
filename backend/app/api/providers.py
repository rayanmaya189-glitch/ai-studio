"""List configured LLM providers and their availability/models."""

from __future__ import annotations

from fastapi import APIRouter

from app.providers import get_registry
from app.schemas import ProviderInfo

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderInfo])
def list_providers() -> list[ProviderInfo]:
    registry = get_registry()
    infos: list[ProviderInfo] = []
    for provider in registry.all():
        available = provider.available()
        infos.append(
            ProviderInfo(
                name=provider.name,
                available=available,
                models=provider.list_models() if available else [],
            )
        )
    return infos
