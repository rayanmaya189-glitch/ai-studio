"""LLM provider interface.

Every provider implements the same small surface so the rest of the app never
branches on which backend is in use. Real implementations call out over HTTP.
Providers are registered dynamically from the DB-backed config.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMProvider(ABC):
    """Abstract base for chat + embedding backends."""

    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """True if this provider has the credentials/endpoint it needs."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """Known/curated model identifiers for this provider."""

    @abstractmethod
    def chat(self, messages: list[ChatMessage], model: str) -> str:
        """Return the assistant's reply text for the given messages."""

    @abstractmethod
    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Return one embedding vector per input text."""
