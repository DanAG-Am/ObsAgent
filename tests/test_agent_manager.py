import asyncio
from unittest.mock import AsyncMock, patch

from multi_agent_framework.agent_manager import (
    Agent,
    AgentRole,
    BuilderAgent,
    MultiAgentSystem,
    ResearcherAgent,
    TranslatorAgent,
)
from multi_agent_framework.skill_guides import available_skill_guides, read_skill_guide


class FakeResearcher(Agent):
    def __init__(self):
        super().__init__("FakeResearcher", AgentRole.RESEARCHER)

    async def execute(self, request: str) -> dict[str, object]:
        return {
            "response": f"Respuesta con evidencia para: {request}",
            "tool_results": [],
        }


class FakeTranslator(Agent):
    def __init__(self):
        super().__init__("FakeTranslator", AgentRole.TRANSLATOR)

    async def execute(self, request: str) -> str:
        return f"normalizada: {request}"


class FakeBuilder(Agent):
    def __init__(self):
        super().__init__("FakeBuilder", AgentRole.BUILDER)

    async def execute(self, request: str) -> str:
        return f"Respuesta personalizada: {request}"


def test_default_pipeline_skips_redundant_translator_and_builder_calls():
    system = MultiAgentSystem.__new__(MultiAgentSystem)
    agents: dict[AgentRole, Agent] = {
        AgentRole.TRANSLATOR: TranslatorAgent(),
        AgentRole.RESEARCHER: FakeResearcher(),
        AgentRole.BUILDER: BuilderAgent(),
    }
    system._agents = agents

    with (
        patch.object(
            TranslatorAgent,
            "execute",
            new_callable=AsyncMock,
        ) as translate,
        patch.object(
            BuilderAgent,
            "execute",
            new_callable=AsyncMock,
        ) as build,
    ):
        result = asyncio.run(system.execute("Compara la morosidad"))

    translate.assert_not_awaited()
    build.assert_not_awaited()
    assert result["translated_query"] == "Compara la morosidad"
    assert result["final_answer"] == "Respuesta con evidencia para: Compara la morosidad"


def test_custom_translator_and_builder_still_run():
    system = MultiAgentSystem.__new__(MultiAgentSystem)
    agents: dict[AgentRole, Agent] = {
        AgentRole.TRANSLATOR: FakeTranslator(),
        AgentRole.RESEARCHER: FakeResearcher(),
        AgentRole.BUILDER: FakeBuilder(),
    }
    system._agents = agents

    result = asyncio.run(system.execute("Compare delinquency"))

    assert result["translated_query"] == "normalizada: Compare delinquency"
    assert result["final_answer"].startswith("Respuesta personalizada:")


def test_optional_translation_is_used_for_the_research_query():
    system = MultiAgentSystem.__new__(MultiAgentSystem)
    system._agents = {
        AgentRole.TRANSLATOR: TranslatorAgent(),
        AgentRole.RESEARCHER: FakeResearcher(),
        AgentRole.BUILDER: BuilderAgent(),
    }
    with patch.object(
        TranslatorAgent, "execute", new_callable=AsyncMock, return_value="Consulta traducida"
    ) as translate:
        result = asyncio.run(system.execute("Compare delinquency", translate=True))

    translate.assert_awaited_once_with("Compare delinquency")
    assert result["translation_used"] is True
    assert result["translated_query"] == "Consulta traducida"
    assert result["final_answer"] == "Respuesta con evidencia para: Consulta traducida"


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


def test_empty_translation_fails_before_research():
    system = MultiAgentSystem.__new__(MultiAgentSystem)
    system._agents = {
        AgentRole.TRANSLATOR: TranslatorAgent(),
        AgentRole.RESEARCHER: FakeResearcher(),
        AgentRole.BUILDER: BuilderAgent(),
    }
    with patch.object(
        TranslatorAgent, "execute", new_callable=AsyncMock, return_value=""
    ):
        try:
            asyncio.run(system.execute("Compare delinquency", translate=True))
        except RuntimeError as error:
            assert "traductor" in str(error)
        else:
            raise AssertionError("An empty translation must raise an error")


def test_skill_guides_are_allowlisted_and_read_by_section():
    guides = {guide["name"]: guide["status"] for guide in available_skill_guides()}
    assert guides["Compare_Periods"] == "guide_only"
    assert guides["Fetch_From_Storage"] == "empty"
    overview = read_skill_guide("Compare_Periods")
    assert "Required inputs" in overview["content"]
    section = read_skill_guide("Compare_Periods", "Calculation rules")
    assert list(section["content"]) == ["Calculation rules"]
    assert "baseline" in section["content"]["Calculation rules"]
    for name, section_name in [
        ("../README", None),
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


if __name__ == "__main__":
    test_default_pipeline_skips_redundant_translator_and_builder_calls()
    test_custom_translator_and_builder_still_run()
    test_optional_translation_is_used_for_the_research_query()
    test_researcher_reports_actual_tool_arguments_and_failures()
    test_empty_translation_fails_before_research()
    test_skill_guides_are_allowlisted_and_read_by_section()
    test_researcher_consults_guide_and_records_following_analytics()
    print("Agent workflow tests passed.")
