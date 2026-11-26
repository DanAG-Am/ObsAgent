"""Ollama-backed agents for deterministic ObsAgent portfolio analysis."""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import chromadb

from ChromaDB.precomputed_queries import (
    DEFAULT_METRICS,
    DIMENSIONS,
    anomaly_candidates,
    cohort_curve,
    kpis_by_dimension,
    portfolio_kpis,
    segment_ranking,
    vintage_comparison,
)

from .agentlib import chat, normalizar_argumentos


MAX_ITERATIONS = 8
MAX_TOOL_RESULT_CHARS = 12_000
MAX_TOTAL_TOOL_RESULT_CHARS = 12_000
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHROMA_PATH = PROJECT_ROOT / "ChromaDB" / "chroma_data"


class AgentRole(Enum):
    TRANSLATOR = "translator"
    RESEARCHER = "researcher"
    BUILDER = "builder"


@dataclass
class AgentTool:
    """A model-callable function and its JSON schema."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    execute: Callable[..., Any] | None = None

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class AgentContext:
    """Data handed between the translator, researcher, and builder."""

    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    query_context: dict[str, Any] = field(default_factory=dict)
    retrieved_data: Any = None
    translation_state: str = ""
    working_memory: list[str] = field(default_factory=list)
    original_query: str = ""
    translated_query: str = ""
    research_findings: dict[str, Any] = field(default_factory=dict)
    final_answer: str = ""


class Agent(ABC):
    def __init__(self, name: str, role: AgentRole):
        self.name = name
        self.role = role
        self.tools: list[AgentTool] = []

    @abstractmethod
    async def execute(self, request: str) -> Any:
        """Run this agent's task."""


class TranslatorAgent(Agent):
    """Translates the user's request to English without changing its intent."""

    def __init__(self, name: str = "Translator"):
        super().__init__(name, AgentRole.TRANSLATOR)

    async def execute(self, request: str) -> str:
        response = await asyncio.to_thread(
            chat,
            [
                {
                    "role": "system",
                    "content": (
                        "Translate the user's analytics request into English. "
                        "Preserve metric names, years, filters, and identifiers. "
                        "If it is already English, return it unchanged. Return "
                        "only the translated request."
                    ),
                },
                {"role": "user", "content": request},
            ],
        )
        return response.get("content", "").strip()


class ResearcherAgent(Agent):
    """Selects validated analytical tools and returns their deterministic data."""

    def __init__(
        self,
        name: str = "Researcher",
        aggregates: Any = None,
        max_iterations: int = MAX_ITERATIONS,
    ):
        super().__init__(name, AgentRole.RESEARCHER)
        if aggregates is None:
            client = chromadb.PersistentClient(path=str(DEFAULT_CHROMA_PATH))
            aggregates = client.get_collection("base_cards_sintetica_aggregates")
        self.aggregates = aggregates
        self.max_iterations = max_iterations
        self.tools = self._build_tools()

    def _build_tools(self) -> list[AgentTool]:
        filters_schema = {"type": "object", "additionalProperties": True}
        dimensions = list(DIMENSIONS)
        metrics = list(DEFAULT_METRICS)
        return [
            AgentTool(
                "portfolio_kpis",
                "Calculate portfolio measures and KPIs, optionally filtered by validated dimensions.",
                {
                    "type": "object",
                    "properties": {"filters": filters_schema},
                },
                lambda filters=None: portfolio_kpis(self.aggregates, filters),
            ),
            AgentTool(
                "cohort_curve",
                "Return deterministic KPI results by vintage and month-on-book. Use filters to narrow the cohort.",
                {
                    "type": "object",
                    "properties": {"filters": filters_schema},
                    "required": ["filters"],
                },
                lambda filters: cohort_curve(self.aggregates, filters),
            ),
            AgentTool(
                "kpis_by_dimension",
                "Calculate KPIs grouped by one supported portfolio dimension.",
                {
                    "type": "object",
                    "properties": {
                        "group_by": {"type": "string", "enum": dimensions},
                        "filters": filters_schema,
                    },
                    "required": ["group_by"],
                },
                lambda group_by, filters=None: kpis_by_dimension(
                    self.aggregates, group_by, filters
                ),
            ),
            AgentTool(
                "vintage_comparison",
                "Compare two vintages at the same month-on-book.",
                {
                    "type": "object",
                    "properties": {
                        "baseline_vintage": {"type": "integer"},
                        "comparison_vintage": {"type": "integer"},
                        "mob": {"type": "integer"},
                        "filters": filters_schema,
                    },
                    "required": ["baseline_vintage", "comparison_vintage", "mob"],
                },
                lambda baseline_vintage, comparison_vintage, mob, filters=None:
                    vintage_comparison(
                        self.aggregates,
                        baseline_vintage,
                        comparison_vintage,
                        mob,
                        filters,
                    ),
            ),
            AgentTool(
                "segment_ranking",
                "Rank portfolio groups by a supported KPI.",
                {
                    "type": "object",
                    "properties": {
                        "group_by": {"type": "string", "enum": dimensions},
                        "metric": {"type": "string", "enum": metrics},
                        "filters": filters_schema,
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                        "descending": {"type": "boolean"},
                        "minimum_accounts": {"type": "integer", "minimum": 0},
                    },
                    "required": ["group_by", "metric"],
                },
                lambda group_by, metric, filters=None, limit=10, descending=True,
                minimum_accounts=0: segment_ranking(
                    self.aggregates,
                    group_by,
                    metric,
                    filters,
                    limit,
                    descending,
                    minimum_accounts,
                ),
            ),
            AgentTool(
                "anomaly_candidates",
                "Find IQR outliers for a supported KPI across a portfolio dimension.",
                {
                    "type": "object",
                    "properties": {
                        "group_by": {"type": "string", "enum": dimensions},
                        "metric": {"type": "string", "enum": metrics},
                        "filters": filters_schema,
                        "minimum_accounts": {"type": "integer", "minimum": 0},
                    },
                    "required": ["group_by", "metric"],
                },
                lambda group_by, metric, filters=None, minimum_accounts=0:
                    anomaly_candidates(
                        self.aggregates,
                        group_by,
                        metric,
                        filters,
                        minimum_accounts,
                    ),
            ),
        ]

    async def execute(self, request: str) -> dict[str, Any]:
        tool_map = {
            tool.name: tool.execute
            for tool in self.tools
            if tool.execute is not None
        }
        schemas = [tool.schema() for tool in self.tools]
        messages = [
            {
                "role": "system",
                "content": (
                    "You are ObsAgent's portfolio researcher. Use the available "
                    "tools to retrieve evidence before answering. All numeric "
                    "results must come from tool output; do not calculate or "
                    "invent values. Use only supported dimensions and metrics. "
                    "For comparisons, compare the same MOB. Summarize the "
                    "evidence and name the tools used."
                ),
            },
            {"role": "user", "content": request},
        ]
        tool_results: list[dict[str, Any]] = []
        seen_calls: set[tuple[str, str]] = set()
        total_result_chars = 0

        for _ in range(self.max_iterations):
            response = await asyncio.to_thread(chat, messages, schemas)
            messages.append(response)
            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                return {
                    "role": self.role.value,
                    "query": request,
                    "response": response.get("content", "").strip(),
                    "tool_results": tool_results,
                }

            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                name = function.get("name")
                arguments = normalizar_argumentos(tool_call)
                result: Any
                signature = (
                    name or "",
                    json.dumps(arguments, sort_keys=True, ensure_ascii=False),
                )

                if not isinstance(arguments, dict) or "__error__" in arguments:
                    result = {"error": arguments.get("__error__", "invalid arguments")
                              if isinstance(arguments, dict) else "arguments must be an object"}
                elif name not in tool_map:
                    result = {
                        "error": f"Unknown tool: {name}",
                        "available_tools": list(tool_map),
                    }
                elif signature in seen_calls:
                    result = {
                        "error": "This exact tool call was already made; use its result.",
                    }
                else:
                    seen_calls.add(signature)
                    try:
                        result = tool_map[name](**arguments)
                    except (TypeError, ValueError, KeyError) as error:
                        result = {"error": str(error)}

                serialized = json.dumps(result, ensure_ascii=False, default=str)
                if (
                    len(serialized) > MAX_TOOL_RESULT_CHARS
                    or total_result_chars + len(serialized) > MAX_TOTAL_TOOL_RESULT_CHARS
                ):
                    result = {
                        "error": (
                            "Result exceeds the researcher context limit. Narrow "
                            "the filters or use segment_ranking with a smaller limit."
                        )
                    }
                    serialized = json.dumps(result, ensure_ascii=False)
                total_result_chars += len(serialized)
                tool_results.append({"tool": name, "result": result})
                messages.append({"role": "tool", "content": serialized})

        raise RuntimeError(
            f"{self.name} exceeded the {self.max_iterations}-iteration tool-call limit."
        )


class BuilderAgent(Agent):
    """Turns the researcher's evidence into a concise response for the user."""

    def __init__(self, name: str = "Builder"):
        super().__init__(name, AgentRole.BUILDER)

    async def execute(self, request: str) -> str:
        response = await asyncio.to_thread(
            chat,
            [
                {
                    "role": "system",
                    "content": (
                        "Write a concise answer to the user's original request. "
                        "Use only the supplied researcher response and tool "
                        "results; do not add facts, estimates, or unsupported "
                        "recommendations. Respond in the language of the original "
                        "request. State clearly when the evidence is empty or "
                        "incomplete."
                    ),
                },
                {"role": "user", "content": request},
            ],
        )
        return response.get("content", "").strip()


class MultiAgentSystem:
    """Runs the translator -> researcher -> builder pipeline."""

    def __init__(
        self,
        chroma_path: str | Path | None = None,
        max_iterations: int = MAX_ITERATIONS,
    ):
        path = Path(chroma_path) if chroma_path else DEFAULT_CHROMA_PATH
        client = chromadb.PersistentClient(path=str(path))
        self.source = client.get_collection("base_cards_sintetica")
        self.aggregates = client.get_collection("base_cards_sintetica_aggregates")
        if self.aggregates.count() == 0:
            raise RuntimeError(
                "ObsAgent's aggregate collection is empty. Ingest the source CSV "
                "and run build_aggregate_collection before starting the agents."
            )
        self._agents: dict[AgentRole, Agent] = {}
        self.register_agent(AgentRole.TRANSLATOR, TranslatorAgent())
        self.register_agent(
            AgentRole.RESEARCHER,
            ResearcherAgent(
                aggregates=self.aggregates,
                max_iterations=max_iterations,
            ),
        )
        self.register_agent(AgentRole.BUILDER, BuilderAgent())

    def register_agent(
        self,
        role: AgentRole,
        agent: Agent | None = None,
        name: str | None = None,
    ) -> None:
        if agent is None:
            if role == AgentRole.TRANSLATOR:
                agent = TranslatorAgent(name or "Translator")
            elif role == AgentRole.RESEARCHER:
                agent = ResearcherAgent(
                    name or "Researcher", aggregates=self.aggregates
                )
            elif role == AgentRole.BUILDER:
                agent = BuilderAgent(name or "Builder")
            else:
                raise ValueError(f"Unknown agent role: {role}")
        if agent.role != role:
            raise ValueError(f"Agent role {agent.role} does not match {role}.")
        self._agents[role] = agent

    async def execute(self, query: str) -> dict[str, Any]:
        context = AgentContext(original_query=query)
        context.translated_query = await self._agents[AgentRole.TRANSLATOR].execute(query)
        context.research_findings = await self._agents[AgentRole.RESEARCHER].execute(
            context.translated_query
        )
        builder_request = json.dumps(
            {
                "original_query": context.original_query,
                "research_response": context.research_findings["response"],
                "tool_results": context.research_findings["tool_results"],
            },
            ensure_ascii=False,
            default=str,
        )
        context.final_answer = await self._agents[AgentRole.BUILDER].execute(
            builder_request
        )
        return {
            "original_query": context.original_query,
            "translated_query": context.translated_query,
            "research_findings": context.research_findings,
            "builder_output": context.final_answer,
            "final_answer": context.final_answer,
        }


def setup_multi_agent_system(
    chroma_path: str | Path | None = None,
    max_iterations: int = MAX_ITERATIONS,
) -> MultiAgentSystem:
    return MultiAgentSystem(chroma_path, max_iterations)


async def run_multi_agent_workflow(
    query: str,
    source_language: str = "es",
    chroma_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the workflow; `source_language` remains for API compatibility."""
    return await setup_multi_agent_system(chroma_path).execute(query)
