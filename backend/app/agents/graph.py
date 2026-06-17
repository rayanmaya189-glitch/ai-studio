"""Multi-agent orchestration (F5/F11).

Two entry points:

- ``run_chat`` — single-agent passthrough used by the workspace chat (F10). The
  user's message goes straight to the resolved LLM provider.
- ``run_agent_pipeline`` — the real LangGraph state machine (F11) chaining
  Planner -> Architect -> Coding -> Review -> Testing. **Each role runs on its
  own assigned model** (model-per-agent is a core PRD requirement), and each
  stage's output is threaded into the next stage's prompt alongside the
  project's RAG context.

``registry.resolve`` raises a descriptive ``ValueError`` when no provider is
configured, and a per-node ``provider.chat`` failure degrades to a recorded
error string rather than aborting the whole run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

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
    """Single-agent passthrough chat (used by the workspace chat endpoint)."""
    registry = get_registry()
    provider, model = registry.resolve(model_ref)

    messages = [ChatMessage(role="system", content=_SYSTEM_PROMPT)]
    if context:
        messages.append(ChatMessage(role="system", content=f"Project context:\n{context}"))
    messages.append(ChatMessage(role="user", content=message))

    reply = provider.chat(messages, model)
    return ChatResult(reply=reply, provider=provider.name, model=model)


# --- Project chatbot (grounded single agent) --------------------------------

# Preamble that constrains a project chatbot to the supplied grounding so it
# doesn't invent files, services, or APIs that aren't in the codebase.
_GROUNDING_PREAMBLE = (
    "You are a project-specific assistant for this exact codebase. Answer ONLY "
    "from the grounding provided below (environment facts, retrieved code, and "
    "memory). If the grounding does not contain the answer, say so plainly and "
    "ask for the file or detail you need — do NOT guess or invent file names, "
    "services, endpoints, or APIs. Prefer citing concrete paths from the "
    "retrieved code."
)


@dataclass
class GroundedChatResult:
    reply: str
    provider: str
    model: str
    used_context: bool
    used_private_memory: bool
    used_shared_memory: bool


def run_grounded_chat(
    message: str,
    model_ref: str | None,
    system_prompt: str | None = None,
    env_facts: str | None = None,
    context: str | None = None,
    private_memory: str | None = None,
    shared_memory: str | None = None,
    history: list[ChatMessage] | None = None,
) -> GroundedChatResult:
    """Single project chatbot turn, grounded in the project's real environment.

    The prompt is assembled from (in order): the anti-hallucination preamble,
    the agent's own ``system_prompt`` (persona), the project's environment facts
    (scan metadata), retrieved code (RAG ``context``), the agent's ``private``
    memory, and the ``shared`` project memory both agents and chatbots write to.
    """
    registry = get_registry()
    provider, model = registry.resolve(model_ref)

    messages = [ChatMessage(role="system", content=_GROUNDING_PREAMBLE)]
    if system_prompt and system_prompt.strip():
        messages.append(ChatMessage(role="system", content=system_prompt.strip()))
    if env_facts:
        messages.append(
            ChatMessage(role="system", content=f"Project environment (from scan):\n{env_facts}")
        )
    if context:
        messages.append(
            ChatMessage(role="system", content=f"Retrieved code (grounding):\n{context}")
        )
    if private_memory:
        messages.append(
            ChatMessage(role="system", content=f"Your private memory (notes):\n{private_memory}")
        )
    if shared_memory:
        messages.append(
            ChatMessage(
                role="system",
                content=(
                    "Shared project memory (what other agents have done/decided):\n"
                    f"{shared_memory}"
                ),
            )
        )
    for turn in history or []:
        messages.append(turn)
    messages.append(ChatMessage(role="user", content=message))

    reply = provider.chat(messages, model)
    return GroundedChatResult(
        reply=reply,
        provider=provider.name,
        model=model,
        used_context=bool(context),
        used_private_memory=bool(private_memory),
        used_shared_memory=bool(shared_memory),
    )


# --- Multi-agent pipeline (F11) ---------------------------------------------

# The ordered stages and the system prompt that frames each role. The pipeline
# always runs in this order; each stage sees the goal, the RAG context, and the
# concatenated output of every prior stage.
PIPELINE_ROLES: tuple[str, ...] = ("planner", "architect", "coding", "review", "testing")

_ROLE_PROMPTS: dict[str, str] = {
    "planner": (
        "You are the Planner. Break the developer's goal into a short, ordered "
        "list of concrete implementation steps. Do not write code."
    ),
    "architect": (
        "You are the Architect. Given the plan, decide where each change lives "
        "in the codebase and outline the interfaces/contracts involved. Do not "
        "write full implementations."
    ),
    "coding": (
        "You are the Coding agent. Implement the architect's design as concrete "
        "code changes. Show the code and the files it belongs in."
    ),
    "review": (
        "You are the Review agent. Critically review the proposed code for bugs, "
        "missing edge cases, and deviations from the plan. List actionable issues."
    ),
    "testing": (
        "You are the Testing agent. Propose tests that verify the implementation "
        "and the review's concerns are addressed. Describe each test's intent."
    ),
}


@dataclass
class StageResult:
    role: str
    provider: str
    model: str
    output: str
    error: str | None = None


@dataclass
class PipelineResult:
    goal: str
    stages: list[StageResult] = field(default_factory=list)

    @property
    def final_output(self) -> str:
        """The last stage's output — the pipeline's overall result."""
        return self.stages[-1].output if self.stages else ""


class _PipelineState(TypedDict):
    goal: str
    context: str
    project_memory: str
    agent_memory_map: dict[str, str]
    model_map: dict[str, str]
    stages: list[StageResult]


def _run_stage(role: str, state: _PipelineState) -> StageResult:
    """Resolve the role's model and run one stage against prior-stage outputs."""
    registry = get_registry()
    provider, model = registry.resolve(state["model_map"].get(role))

    messages = [ChatMessage(role="system", content=_ROLE_PROMPTS[role])]
    if state["context"]:
        messages.append(ChatMessage(role="system", content=f"Project context:\n{state['context']}"))
    if state.get("project_memory"):
        messages.append(
            ChatMessage(
                role="system",
                content=f"Project memory (long-term notes):\n{state['project_memory']}",
            )
        )
    agent_mem = state.get("agent_memory_map", {}).get(role)
    if agent_mem:
        messages.append(
            ChatMessage(role="system", content=f"{role.title()} memory (notes):\n{agent_mem}")
        )
    # Thread every prior stage's output in so each role builds on the last.
    for prior in state["stages"]:
        messages.append(
            ChatMessage(
                role="assistant",
                content=f"[{prior.role}]\n{prior.output}",
            )
        )
    messages.append(ChatMessage(role="user", content=f"Goal: {state['goal']}"))

    try:
        output = provider.chat(messages, model)
        error = None
    except Exception as exc:  # noqa: BLE001 - a dead provider degrades, never aborts
        output = ""
        error = f"{type(exc).__name__}: {exc}"

    return StageResult(role=role, provider=provider.name, model=model, output=output, error=error)


def _make_node(role: str):
    def node(state: _PipelineState) -> dict:
        result = _run_stage(role, state)
        # Returning the appended list updates the channel; LangGraph runs nodes
        # sequentially here so this read-modify-write is safe.
        return {"stages": [*state["stages"], result]}

    return node


def _build_graph():
    builder = StateGraph(_PipelineState)
    for role in PIPELINE_ROLES:
        builder.add_node(role, _make_node(role))

    builder.add_edge(START, PIPELINE_ROLES[0])
    for src, dst in zip(PIPELINE_ROLES, PIPELINE_ROLES[1:], strict=False):
        builder.add_edge(src, dst)
    builder.add_edge(PIPELINE_ROLES[-1], END)
    return builder.compile()


# Compiled once at import; the graph is stateless across invocations (state is
# passed in per call), so a single compiled instance is safe to reuse.
_GRAPH = _build_graph()


def run_agent_pipeline(
    goal: str,
    model_map: dict[str, str] | None = None,
    context: str | None = None,
    project_memory: str | None = None,
    agent_memory_map: dict[str, str] | None = None,
) -> PipelineResult:
    """Run the Planner->Architect->Coding->Review->Testing chain for one goal.

    ``model_map`` maps a role name to its ``"<provider>:<model>"`` ref (from the
    Agent table). Missing roles fall back to the configured default model.
    """
    final = _GRAPH.invoke(
        {
            "goal": goal,
            "context": context or "",
            "project_memory": project_memory or "",
            "agent_memory_map": agent_memory_map or {},
            "model_map": model_map or {},
            "stages": [],
        }
    )
    return PipelineResult(goal=goal, stages=final["stages"])
