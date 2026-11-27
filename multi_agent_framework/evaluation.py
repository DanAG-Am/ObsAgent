"""Opt-in evaluation against a small isolated synthetic portfolio."""

from __future__ import annotations

import re
import uuid
from typing import Any, TypedDict

import chromadb
import requests
from chromadb.config import Settings

from .agent_manager import AgentRole, BuilderAgent, MultiAgentSystem, ResearcherAgent
from .variable_dictionary import SOURCE_FIELDS


class EvaluationCase(TypedDict):
    nombre: str
    pregunta: str
    herramienta: str
    porcentajes: tuple[float, ...]


CASES: tuple[EvaluationCase, ...] = (
    {
        "nombre": "Indicador de una cosecha",
        "pregunta": "Para la cosecha 202401 en MOB 6 calcula la tasa de morosidad por monto en porcentaje.",
        "herramienta": "portfolio_kpis",
        "porcentajes": (10.0,),
    },
    {
        "nombre": "Comparación de cosechas",
        "pregunta": (
            "Compara la tasa de morosidad por monto de las cosechas 202401 y 202402 "
            "en MOB 6. Indica ambas tasas en porcentaje y la diferencia en puntos porcentuales."
        ),
        "herramienta": "vintage_comparison",
        "porcentajes": (10.0, 25.0, 15.0),
    },
)


def assess_result(case: EvaluationCase, result: dict[str, Any]) -> dict[str, Any]:
    calls = result["research_findings"]["tool_results"]
    matching = [
        call for call in calls
        if call["tool"] == case["herramienta"]
        and isinstance(call.get("result"), dict)
        and "error" not in call["result"]
    ]
    evidence_ok = False
    for call in matching:
        args, data = call["arguments"], call["result"]
        if case["herramienta"] == "portfolio_kpis":
            filters = args.get("filters", {})
            evidence_ok = (
                set(filters) == {"vintage", "mob"}
                and str(filters.get("vintage")) == "202401" and str(filters.get("mob")) == "6"
                and data.get("metrics", {}).get("delinquency_rate_amount") == 0.1
            )
        else:
            delta = data.get("metric_delta", {}).get("delinquency_rate_amount")
            evidence_ok = (
                str(args.get("baseline_vintage")) == "202401"
                and str(args.get("comparison_vintage")) == "202402"
                and str(args.get("mob")) == "6"
                and not args.get("filters")
                and data.get("baseline", {}).get("metrics", {}).get("delinquency_rate_amount") == 0.1
                and data.get("comparison", {}).get("metrics", {}).get("delinquency_rate_amount") == 0.25
                and isinstance(delta, (int, float))
                and abs(delta - 0.15) < 1e-9
            )
        if evidence_ok:
            break
    found = {
        float(match.replace(",", "."))
        for match in re.findall(r"(?<![\d.,])[-+]?\d+(?:[.,]\d+)?(?![\d.,])", result["final_answer"])
    }
    return {
        "caso": case["nombre"],
        "herramienta_correcta": bool(matching),
        "evidencia_correcta": evidence_ok,
        "cifras_presentes": all(value in found for value in case["porcentajes"]),
        "errores_herramientas": sum(
            isinstance(call.get("result"), dict) and "error" in call["result"] for call in calls
        ),
        "respuesta": result["final_answer"],
        "tiempos_ms": result.get("timings_ms", {}),
    }


async def run_synthetic_evaluation() -> list[dict[str, Any]]:
    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    name = "evaluacion_" + uuid.uuid4().hex
    collection = client.create_collection(name)
    try:
        collection.add(
            ids=["cohorte_a", "cohorte_b"],
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
            metadatas=[
                {"vintage": 202401, "mob": 6, "accounts": 100, "enrolled_amount": 200, "over30_amount": 20},
                {"vintage": 202402, "mob": 6, "accounts": 100, "enrolled_amount": 200, "over30_amount": 50},
            ],
        )
        definitions = {name: "Definición sintética para evaluación." for name in SOURCE_FIELDS.values()}
        researcher = ResearcherAgent(aggregates=collection, dictionary_definitions=definitions)
        researcher.tools = [tool for tool in researcher.tools if tool.name in {"portfolio_kpis", "vintage_comparison"}]
        system = MultiAgentSystem.__new__(MultiAgentSystem)
        system._agents = {AgentRole.RESEARCHER: researcher, AgentRole.BUILDER: BuilderAgent()}
        reports = []
        for case in CASES:
            try:
                result = await system.execute(case["pregunta"])
                reports.append(assess_result(case, result))
            except (RuntimeError, ValueError, KeyError, requests.exceptions.RequestException) as error:
                reports.append({"caso": case["nombre"], "error": str(error)})
        return reports
    finally:
        client.delete_collection(name)
