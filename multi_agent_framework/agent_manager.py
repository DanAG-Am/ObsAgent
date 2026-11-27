"""Agentes respaldados por Ollama para el análisis determinista de cartera ObsAgent."""

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
    TRANSLATOR = "traductor"
    RESEARCHER = "investigador"
    BUILDER = "redactor"


@dataclass
class AgentTool:
    """Función invocable por el modelo y su esquema JSON."""

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
    """Datos compartidos entre el traductor, el investigador y el redactor."""

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
        """Ejecuta la tarea de este agente."""


class TranslatorAgent(Agent):
    """Normaliza la solicitud del usuario al español sin cambiar su intención."""

    def __init__(self, name: str = "Traductor"):
        super().__init__(name, AgentRole.TRANSLATOR)

    async def execute(self, request: str) -> str:
        response = await asyncio.to_thread(
            chat,
            [
                {
                    "role": "system",
                    "content": (
                        "Eres un normalizador de consultas en español. "
                        "Si la consulta del usuario ya está en español, devuélvela "
                        "exactamente igual. Si contiene palabras en otro idioma, "
                        "tradúcelas al español conservando sin cambios los nombres "
                        "propios, años, valores de filtros e identificadores. "
                        "Responde únicamente en español y solo con la consulta "
                        "resultante, sin explicaciones ni notas."
                    ),
                },
                {"role": "user", "content": request},
            ],
        )
        return response.get("content", "").strip()


class ResearcherAgent(Agent):
    """Selecciona herramientas analíticas validadas y devuelve sus datos deterministas."""

    def __init__(
        self,
        name: str = "Investigador",
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
                "Calcula medidas e indicadores de cartera, opcionalmente filtrados por dimensiones validadas.",
                {
                    "type": "object",
                    "properties": {"filters": filters_schema},
                },
                lambda filters=None: portfolio_kpis(self.aggregates, filters),
            ),
            AgentTool(
                "cohort_curve",
                "Devuelve resultados deterministas por cosecha y mes en libros. Usa filtros para acotar la cohorte.",
                {
                    "type": "object",
                    "properties": {"filters": filters_schema},
                    "required": ["filters"],
                },
                lambda filters: cohort_curve(self.aggregates, filters),
            ),
            AgentTool(
                "kpis_by_dimension",
                "Calcula indicadores agrupados por una dimensión de cartera compatible.",
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
                "Compara dos cosechas en el mismo mes en libros.",
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
                "Ordena los grupos de cartera según un indicador compatible.",
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
                "Encuentra valores atípicos por rango intercuartílico para un indicador compatible y una dimensión de cartera.",
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
                    "Eres el agente de investigación de cartera de ObsAgent. "
                    "Responde exclusivamente en español. "
                    "Si el usuario hace un saludo general o pregunta qué puedes hacer, "
                    "no ejecutes herramientas y explica brevemente en español qué análisis "
                    "de cartera puedes realizar (indicadores de morosidad, castigos, "
                    "margen operativo, comparación entre cosechas y detección de anomalías). "
                    "Para cualquier pregunta analítica, usa las herramientas disponibles "
                    "para obtener evidencia antes de responder. Todos los resultados numéricos "
                    "deben provenir de las herramientas; no calcules ni inventes valores. "
                    "En las comparaciones, compara el mismo mes en libros. Resume la "
                    "evidencia en español e indica qué herramientas utilizaste."
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
                    result = {
                        "error": (
                            arguments.get("__error__", "argumentos no válidos")
                            if isinstance(arguments, dict)
                            else "los argumentos deben ser un objeto"
                        )
                    }
                elif name not in tool_map:
                    result = {
                        "error": f"Herramienta desconocida: {name}",
                        "herramientas_disponibles": list(tool_map),
                    }
                elif signature in seen_calls:
                    result = {
                        "error": "Esta llamada exacta ya se realizó; usa su resultado.",
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
                            "El resultado supera el límite de contexto. Acota los "
                            "filtros o usa segment_ranking con un límite menor."
                        )
                    }
                    serialized = json.dumps(result, ensure_ascii=False)
                total_result_chars += len(serialized)
                tool_results.append({"tool": name, "result": result})
                messages.append({"role": "tool", "content": serialized})

        raise RuntimeError(
            f"{self.name} superó el límite de {self.max_iterations} iteraciones de herramientas."
        )


class BuilderAgent(Agent):
    """Convierte la evidencia de investigación en una respuesta concisa."""

    def __init__(self, name: str = "Redactor"):
        super().__init__(name, AgentRole.BUILDER)

    async def execute(self, request: str) -> str:
        response = await asyncio.to_thread(
            chat,
            [
                {
                    "role": "system",
                    "content": (
                        "Redacta una respuesta clara y concisa a la consulta original "
                        "del usuario, siempre y exclusivamente en español. "
                        "Si la consulta es un saludo o pregunta sobre tus capacidades y no "
                        "requirió herramientas, responde de forma cordial y útil en español "
                        "con base en la respuesta de investigación. "
                        "Si se consultaron herramientas, usa únicamente los resultados "
                        "proporcionados; no agregues hechos, estimaciones ni recomendaciones "
                        "sin sustento. Indica claramente si la evidencia está vacía o incompleta."
                    ),
                },
                {"role": "user", "content": request},
            ],
        )
        return response.get("content", "").strip()


class MultiAgentSystem:
    """Ejecuta el flujo traductor -> investigador -> redactor."""

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
                "La colección de agregados de ObsAgent está vacía. Carga el archivo CSV "
                "de origen y ejecuta build_aggregate_collection antes de iniciar los agentes."
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
                agent = TranslatorAgent(name or "Traductor")
            elif role == AgentRole.RESEARCHER:
                agent = ResearcherAgent(
                    name or "Investigador", aggregates=self.aggregates
                )
            elif role == AgentRole.BUILDER:
                agent = BuilderAgent(name or "Redactor")
            else:
                raise ValueError(f"Rol de agente desconocido: {role}")
        if agent.role != role:
            raise ValueError(f"El rol del agente {agent.role} no coincide con {role}.")
        self._agents[role] = agent

    async def execute(self, query: str) -> dict[str, Any]:
        context = AgentContext(original_query=query)
        context.translated_query = await self._agents[AgentRole.TRANSLATOR].execute(query)
        context.research_findings = await self._agents[AgentRole.RESEARCHER].execute(
            context.translated_query
        )
        builder_request = json.dumps(
            {
                "consulta_original": context.original_query,
                "respuesta_de_investigacion": context.research_findings["response"],
                "resultados_de_herramientas": context.research_findings["tool_results"],
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
    """Ejecuta el flujo multiagente; `source_language` se conserva por compatibilidad."""
    return await setup_multi_agent_system(chroma_path).execute(query)