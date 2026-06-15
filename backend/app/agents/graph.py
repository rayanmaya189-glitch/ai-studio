"""Multi-agent orchestration (F5/F11).

STUB-level: a single passthrough "agent" that sends the user's message straight
to the resolved LLM provider. The real version builds a LangGraph state machine
chaining Planner -> Architect -> Coding -> Review -> Testing, each with its own
assigned model, and threads project RAG context + memory into the prompts.

The ``run_chat`` signature is what the chat API depends on, so the LangGraph
implementation can replace the body without touching callers.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.providers import get_registry
from app.providers.base import ChatMessage

_SYSTEM_PROMPT = (
    "You are an agent inside AI Development Studio, helping a developer reason "
    "about their codebase. Be concise and concrete."
)


@dataclass
class ChatResult:
    reply: str
    provider: str
    model: str


def run_chat(message: str, model_ref: str | None, context: str | None = None) -> ChatResult:
    """Single-agent passthrough chat (stub for the full agent graph)."""
    registry = get_registry()
    provider, model = registry.resolve(model_ref)

    messages = [ChatMessage(role="system", content=_SYSTEM_PROMPT)]
    if context:
        messages.append(ChatMessage(role="system", content=f"Project context:\n{context}"))
    messages.append(ChatMessage(role="user", content=message))

    reply = provider.chat(messages, model)
    return ChatResult(reply=reply, provider=provider.name, model=model)
