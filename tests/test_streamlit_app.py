from pathlib import Path
from unittest.mock import AsyncMock, patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from multi_agent_framework.query_service import QueryService


def test_dashboard_uses_available_filters_and_reuses_cohort_data():
    rows = [
        {
            "vintage": 202401,
            "mob": 0,
            "measures": {"accounts": 10, "enrolled_amount": 100, "net_chargeoff_amount": 10},
            "metrics": {"delinquency_rate_amount": None, "net_chargeoff_rate": 0.1},
            "row_count": 1,
        },
        {
            "vintage": 202401,
            "mob": 1,
            "measures": {"accounts": 15, "enrolled_amount": 100, "net_chargeoff_amount": 20},
            "metrics": {"delinquency_rate_amount": None, "net_chargeoff_rate": 0.2},
            "row_count": 1,
        },
        {
            "vintage": 202402,
            "mob": 2,
            "measures": {"accounts": 20, "enrolled_amount": 400, "net_chargeoff_amount": 20},
            "metrics": {"delinquency_rate_amount": None, "net_chargeoff_rate": 0.05},
            "row_count": 1,
        },
    ]
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "get_dashboard_cohorts", new_callable=AsyncMock, return_value=rows) as load,
        patch.object(st, "altair_chart", wraps=st.altair_chart) as chart,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_dashboard").click().run()
        assert not app.exception
        assert app.selectbox(key="dashboard_vintage").options == ["Todas", "202401", "202402"]
        assert app.selectbox(key="dashboard_mob").options == ["Todos", "0", "1", "2"]
        app.selectbox(key="dashboard_vintage").select(202401).run()
        assert app.selectbox(key="dashboard_mob").options == ["Todos", "0", "1"]
        app.selectbox(key="dashboard_mob").select(0).run()
        assert not app.exception
        assert any(metric.value == "10" for metric in app.metric)
        app.selectbox(key="dashboard_metric").select("net_chargeoff_rate").run()
        assert not app.exception
        assert any(metric.value == "10.00%" for metric in app.metric)
        indicator_chart, accounts_chart = [call.args[0] for call in chart.call_args_list[-2:]]
        expected = [
            {"MOB": 0, "Cosecha": "202401", "Indicador": 10.0, "Cuentas": 10},
            {"MOB": 1, "Cosecha": "202401", "Indicador": 20.0, "Cuentas": 15},
        ]
        assert indicator_chart.data.values == expected
        assert accounts_chart.data.values == expected
        load.assert_awaited_once()


def test_chat_navigation_translation_and_tool_error_trace():
    result = {
        "final_answer": "No hay resultados válidos.",
        "translated_query": "Consulta traducida",
        "translation_used": True,
        "research_findings": {
            "tool_results": [
                {
                    "tool": "portfolio_kpis",
                    "arguments": {"filters": {"vintage": 2024}},
                    "result": {"error": "Filtro no válido"},
                }
            ]
        },
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result) as query,
        patch.object(st, "download_button", wraps=st.download_button) as download,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        assert not app.exception
        assert app.session_state["obsagent_tabs"] == "Inicio"
        app.button(key="home_chat").click().run()
        assert not app.exception
        assert app.session_state["obsagent_tabs"] == "Conversar con ObsAgent"
        app.toggle(key="translate_prompt").set_value(True).run()
        app.chat_input[0].set_value("Compare vintage 2024").run()
        assert not app.exception
        query.assert_awaited_once_with("Compare vintage 2024", translate=True)
        assert any("error" in warning.value for warning in app.warning)
        assert any(error.value == "Filtro no válido" for error in app.error)
        assert any(expander.label == "Cómo se obtuvo esta respuesta" for expander in app.expander)
        assert download.call_args.kwargs["mime"] == "application/pdf"
        assert download.call_args.kwargs["data"].startswith(b"%PDF-")
        app.run()
        assert not app.exception
        assert any(error.value == "Filtro no válido" for error in app.error)
        assert download.call_count >= 2


def test_guide_only_response_is_not_presented_as_portfolio_evidence():
    result = {
        "final_answer": "Se consultó la guía.",
        "translated_query": "Consulta",
        "translation_used": False,
        "research_findings": {
            "tool_results": [{
                "tool": "consultar_skill",
                "arguments": {"nombre": "Compare_Periods"},
                "result": {"status": "guide_only"},
            }]
        },
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result),
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_chat").click().run()
        app.chat_input[0].set_value("Compara periodos").run()
        assert not app.exception
        assert any("Solo se consultaron guías" in warning.value for warning in app.warning)


if __name__ == "__main__":
    test_dashboard_uses_available_filters_and_reuses_cohort_data()
    test_chat_navigation_translation_and_tool_error_trace()
    test_guide_only_response_is_not_presented_as_portfolio_evidence()
    print("Streamlit workspace test passed.")
