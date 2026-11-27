import asyncio
import csv
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from multi_agent_framework.agent_manager import (
    Agent,
    AgentRole,
    BuilderAgent,
    MultiAgentSystem,
    ResearcherAgent,
)
from multi_agent_framework.evaluation import CASES, assess_result, run_synthetic_evaluation
from multi_agent_framework.skill_guides import available_skill_guides, read_skill_guide
from multi_agent_framework.variable_dictionary import (
    SOURCE_FIELDS,
    describe_variable,
    dictionary_context,
    load_variable_dictionary,
)


class FakeResearcher(Agent):
    def __init__(self):
        super().__init__("FakeResearcher", AgentRole.RESEARCHER)

    async def execute(self, request: str) -> dict[str, object]:
        return {
            "response": f"Respuesta con evidencia para: {request}",
            "tool_results": [],
        }


class FakeBuilder(Agent):
    def __init__(self):
        super().__init__("FakeBuilder", AgentRole.BUILDER)

    async def execute(self, request: str) -> str:
        return f"Respuesta personalizada: {request}"


def test_default_pipeline_runs_researcher_and_builder():
    system = MultiAgentSystem.__new__(MultiAgentSystem)
    agents: dict[AgentRole, Agent] = {
        AgentRole.RESEARCHER: FakeResearcher(),
        AgentRole.BUILDER: BuilderAgent(),
    }
    system._agents = agents

    with patch.object(
        BuilderAgent, "execute", new_callable=AsyncMock, return_value="Respuesta redactada"
    ) as build:
        result = asyncio.run(system.execute("Compara la morosidad"))

    build.assert_awaited_once()
    assert "Respuesta con evidencia para: Compara la morosidad" in build.await_args_list[0].args[0]
    assert result["final_answer"] == "Respuesta redactada"
    assert set(result["timings_ms"]) == {"researcher", "builder", "total"}
    assert all(value >= 0 for value in result["timings_ms"].values())


def test_custom_builder_receives_research():
    system = MultiAgentSystem.__new__(MultiAgentSystem)
    agents: dict[AgentRole, Agent] = {
        AgentRole.RESEARCHER: FakeResearcher(),
        AgentRole.BUILDER: FakeBuilder(),
    }
    system._agents = agents

    result = asyncio.run(system.execute("Compare delinquency"))

    assert result["final_answer"].startswith("Respuesta personalizada:")
    assert "Respuesta con evidencia para: Compare delinquency" in result["final_answer"]


def test_empty_builder_response_fails_explicitly():
    system = MultiAgentSystem.__new__(MultiAgentSystem)
    system._agents = {
        AgentRole.RESEARCHER: FakeResearcher(),
        AgentRole.BUILDER: BuilderAgent(),
    }
    with patch.object(BuilderAgent, "execute", new_callable=AsyncMock, return_value=""):
        try:
            asyncio.run(system.execute("Consulta"))
        except RuntimeError as error:
            assert "redactor" in str(error)
        else:
            raise AssertionError("An empty builder response must raise an error")


def test_researcher_reports_actual_tool_arguments_and_failures():
    researcher = ResearcherAgent(aggregates=object())
    with patch(
        "multi_agent_framework.agent_manager.chat",
        side_effect=[
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "segment_ranking",
                            "arguments": {
                                "group_by": "invalid",
                                "metric": "delinquency_rate_amount",
                            },
                        }
                    }
                ],
            },
            {"role": "assistant", "content": "No hay resultados válidos."},
        ],
    ):
        result = asyncio.run(researcher.execute("Ranking"))

    call = result["tool_results"][0]
    assert call["arguments"]["group_by"] == "invalid"
    assert "error" in call["result"]


def test_researcher_accepts_string_vintage_without_retry():
    aggregates = Mock()
    aggregates.get.return_value = {"metadatas": []}
    researcher = ResearcherAgent(aggregates=aggregates)
    with patch("multi_agent_framework.agent_manager.chat", side_effect=[
        {"role": "assistant", "tool_calls": [{"function": {
            "name": "portfolio_kpis", "arguments": {"filters": {"vintage": "202401", "mob": 6}},
        }}]},
        {"role": "assistant", "content": "No hay datos."},
    ]):
        result = asyncio.run(researcher.execute("Consulta cosecha 202401 en MOB 6"))
    assert len(result["tool_results"]) == 1
    assert "error" not in result["tool_results"][0]["result"]
    assert result["tool_results"][0]["arguments"]["filters"]["vintage"] == "202401"
    assert aggregates.get.call_args.kwargs["where"] == {"$and": [{"vintage": 202401}, {"mob": 6}]}
    assert result["tool_results"][0]["duration_ms"] >= 0


def test_synthetic_evaluation_checks_actual_tool_results_and_answer_numbers():
    responses = [
        {"tool_calls": [{"function": {
            "name": "portfolio_kpis", "arguments": {"filters": {"vintage": 202401, "mob": 6}},
        }}]},
        {"content": "La tasa es 10%."},
        {"content": "La tasa es 10%."},
        {"tool_calls": [{"function": {
            "name": "vintage_comparison",
            "arguments": {"baseline_vintage": 202401, "comparison_vintage": 202402, "mob": 6},
        }}]},
        {"content": "Las tasas son 10% y 25%; la diferencia es 15 puntos porcentuales."},
        {"content": "Las tasas son 10% y 25%; la diferencia es 15 puntos porcentuales."},
    ]
    with patch("multi_agent_framework.agent_manager.chat", side_effect=responses):
        reports = asyncio.run(run_synthetic_evaluation())
    assert len(reports) == 2
    assert all(report["herramienta_correcta"] and report["evidencia_correcta"]
               and report["cifras_presentes"] for report in reports)
    assert all(report["errores_herramientas"] == 0 for report in reports)
    incomplete = {
        "final_answer": "La tasa es 10%.",
        "research_findings": {"tool_results": []},
    }
    checked = assess_result(CASES[0], incomplete)
    assert checked["cifras_presentes"] and not checked["evidencia_correcta"]


def test_skill_guides_are_allowlisted_and_read_by_section():
    guides = {guide["name"]: guide["status"] for guide in available_skill_guides()}
    assert guides["Compare_Periods"] == "guide_only"
    assert "Fetch_From_Storage" not in guides
    assert "Human_Review_Flag" not in guides
    researcher = ResearcherAgent(aggregates=object())
    guide_tool = next(tool for tool in researcher.tools if tool.name == "consultar_skill")
    assert "Fetch_From_Storage" not in guide_tool.parameters["properties"]["nombre"]["enum"]
    overview = read_skill_guide("Compare_Periods")
    overview_content = overview["content"]
    assert isinstance(overview_content, dict)
    assert "Required inputs" in overview_content
    section = read_skill_guide("Compare_Periods", "Calculation rules")
    section_content = section["content"]
    assert isinstance(section_content, dict)
    assert list(section_content) == ["Calculation rules"]
    assert "baseline" in section_content["Calculation rules"]
    for name, section_name in [
        ("../README", None),
        ("Human_Review_Flag", None),
        ("Fetch_From_Storage", None),
        ("Compare_Periods", "Missing section"),
    ]:
        try:
            read_skill_guide(name, section_name)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid guide request accepted: {name}, {section_name}")


def test_researcher_consults_guide_and_records_following_analytics():
    researcher = ResearcherAgent(aggregates=object())
    with (
        patch(
            "multi_agent_framework.agent_manager.portfolio_kpis",
            return_value={"metrics": {"net_chargeoff_rate": 0.1}},
        ),
        patch(
            "multi_agent_framework.agent_manager.chat",
            side_effect=[
                {"role": "assistant", "tool_calls": [{"function": {
                    "name": "consultar_skill",
                    "arguments": {"nombre": "Compare_Periods"},
                }}]},
                {"role": "assistant", "tool_calls": [{"function": {
                    "name": "portfolio_kpis", "arguments": {"filters": {"mob": 0}},
                }}]},
                {"role": "assistant", "content": "Resultado."},
            ],
        ) as chat_mock,
    ):
        result = asyncio.run(researcher.execute("Compara periodos"))

    calls = result["tool_results"]
    assert [call["tool"] for call in calls] == ["consultar_skill", "portfolio_kpis"]
    assert calls[0]["result"]["status"] == "guide_only"
    assert calls[1]["result"]["metrics"]["net_chargeoff_rate"] == 0.1
    assert "Compare_Periods" in chat_mock.call_args_list[1].args[0][3]["content"]


def test_dictionary_reads_multiline_definitions_and_rejects_missing_variables():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "dictionary.csv"
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Variable", "Descripción"])
            for name in SOURCE_FIELDS.values():
                writer.writerow([name, f"Definición {name}.\nDetalle para {name}."])
        definitions = load_variable_dictionary(path)
        assert "Definición MOB." in dictionary_context(definitions)
        assert "Detalle para MOB" not in dictionary_context(definitions)
        with patch("multi_agent_framework.variable_dictionary.DICTIONARY_PATH", path):
            assert describe_variable("mob")["descripcion"] == "Definición MOB.\nDetalle para MOB."
            assert describe_variable("MOB")["variable_fuente"] == "MOB"
        path.write_text("Variable,Descripción\nMOB,Mes\n", encoding="utf-8")
        try:
            load_variable_dictionary(path)
        except ValueError as error:
            assert "Faltan variables" in str(error)
        else:
            raise AssertionError("Incomplete dictionary must fail")


def test_researcher_includes_dictionary_and_reports_if_unavailable():
    researcher = ResearcherAgent(aggregates=object())
    definitions = {name: f"Definición de {name}." for name in SOURCE_FIELDS.values()}
    with (
        patch("multi_agent_framework.agent_manager.load_variable_dictionary", return_value=definitions),
        patch("multi_agent_framework.agent_manager.chat", return_value={"content": "Respuesta"}) as model,
    ):
        result = asyncio.run(researcher.execute("¿Qué es MOB?"))
    assert "Definición de MOB." in model.call_args.args[0][0]["content"]
    assert result["dictionary_warning"] is None
    instructions = model.call_args.args[0][0]["content"]
    assert "gráficas interactivas" in instructions
    assert "no necesita PDF ni Excel" in instructions
    with (
        patch("multi_agent_framework.agent_manager.load_variable_dictionary", side_effect=ValueError("No disponible")),
        patch("multi_agent_framework.agent_manager.chat", return_value={"content": "Respuesta"}),
    ):
        result = asyncio.run(researcher.execute("Hola"))
    assert result["dictionary_warning"] == "No disponible"


def test_researcher_can_request_a_full_dictionary_definition():
    researcher = ResearcherAgent(aggregates=object())
    definitions = {name: f"Definición de {name}." for name in SOURCE_FIELDS.values()}
    with (
        patch("multi_agent_framework.agent_manager.load_variable_dictionary", return_value=definitions),
        patch("multi_agent_framework.variable_dictionary.load_variable_dictionary", return_value=definitions),
        patch(
            "multi_agent_framework.agent_manager.chat",
            side_effect=[
                {"role": "assistant", "tool_calls": [{"function": {
                    "name": "consultar_diccionario", "arguments": {"variable": "revenue"},
                }}]},
                {"role": "assistant", "content": "Definición de ingresos."},
            ],
        ),
    ):
        result = asyncio.run(researcher.execute("Define ingresos"))
    assert result["tool_results"][0]["result"]["variable_fuente"] == "REVENUE"
    assert result["tool_results"][0]["result"]["descripcion"] == "Definición de REVENUE."


def test_researcher_validates_local_csv_without_accepting_arbitrary_paths():
    researcher = ResearcherAgent(aggregates=object())
    with (
        patch("multi_agent_framework.agent_manager.validate_local_csv", return_value={"status": "checks_completed"}) as validate,
        patch("multi_agent_framework.agent_manager.chat", side_effect=[
            {"role": "assistant", "tool_calls": [{"function": {
                "name": "validar_csv_local", "arguments": {},
            }}]},
            {"role": "assistant", "content": "Requiere revisión."},
        ]),
    ):
        result = asyncio.run(researcher.execute("Valida el archivo local"))
    validate.assert_called_once_with()
    assert result["tool_results"][0]["result"]["status"] == "checks_completed"
    tool = next(tool for tool in researcher.tools if tool.name == "validar_csv_local")
    try:
        assert tool.execute is not None
        tool.execute(path="/tmp/other.csv")
    except TypeError:
        pass
    else:
        raise AssertionError("El modelo no debe poder seleccionar archivos arbitrarios")


def test_synthetic_fraud_tool_is_registered_and_uses_no_external_input():
    researcher = ResearcherAgent(aggregates=object())
    with patch("multi_agent_framework.agent_manager.chat", side_effect=[
        {"role": "assistant", "tool_calls": [{"function": {
            "name": "analizar_fraude_simulado", "arguments": {},
        }}]},
        {"role": "assistant", "content": "Demostración sintética."},
    ]) as model:
        result = asyncio.run(researcher.execute("Analiza el fraude simulado"))
    tool = next(tool for tool in researcher.tools if tool.name == "analizar_fraude_simulado")
    assert tool.parameters["additionalProperties"] is False
    assert result["tool_results"][0]["result"]["tipo"] == "demostracion_sintetica"
    assert "Si se pide fraude real" in model.call_args_list[0].args[0][0]["content"]
    assert tool.execute is not None
    try:
        tool.execute(path="/tmp/other.csv")
    except TypeError:
        pass
    else:
        raise AssertionError("La demostración no debe aceptar fuentes arbitrarias")


if __name__ == "__main__":
    test_default_pipeline_runs_researcher_and_builder()
    test_custom_builder_receives_research()
    test_empty_builder_response_fails_explicitly()
    test_researcher_reports_actual_tool_arguments_and_failures()
    test_researcher_accepts_string_vintage_without_retry()
    test_synthetic_evaluation_checks_actual_tool_results_and_answer_numbers()
    test_skill_guides_are_allowlisted_and_read_by_section()
    test_researcher_consults_guide_and_records_following_analytics()
    test_dictionary_reads_multiline_definitions_and_rejects_missing_variables()
    test_researcher_includes_dictionary_and_reports_if_unavailable()
    test_researcher_can_request_a_full_dictionary_definition()
    test_researcher_validates_local_csv_without_accepting_arbitrary_paths()
    test_synthetic_fraud_tool_is_registered_and_uses_no_external_input()
    print("Agent workflow tests passed.")
