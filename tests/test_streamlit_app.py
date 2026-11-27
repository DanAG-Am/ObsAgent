from pathlib import Path
from io import BytesIO
from unittest.mock import AsyncMock, patch

import streamlit as st
from openpyxl import load_workbook
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
        patch.object(QueryService, "get_dashboard_dimensions", new_callable=AsyncMock, return_value={
            "product": ["A"], "channel": ["Web"], "strategy": ["S"],
        }),
        patch.object(st, "altair_chart", wraps=st.altair_chart) as chart,
        patch.object(st, "download_button", wraps=st.download_button) as download,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        assert any('<header class="obs-hero">' in item.value for item in app.markdown)
        app.button(key="home_dashboard").click().run()
        assert not app.exception
        assert not any('<header class="obs-hero">' in item.value for item in app.markdown)
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
        workbook = load_workbook(BytesIO(download.call_args.kwargs["data"]), data_only=False)
        assert workbook.sheetnames == ["Resumen", "Evolución", "Clasificación", "Gráficas"]
        assert workbook.active.title == "Gráficas"
        assert len(workbook["Gráficas"]._charts) == 3
        assert workbook["Resumen"]["B3"].value == 202401
        assert workbook["Resumen"]["B4"].value == 0
        assert workbook["Resumen"]["B5"].value == 0.1
        assert workbook["Evolución"].max_row == 3
        assert workbook["Clasificación"].max_row == 3
        workbook.close()
        load.assert_awaited_once()


def test_chat_navigation_and_tool_error_trace():
    result = {
        "final_answer": "No hay resultados válidos.",
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
        app.chat_input[0].set_value("Compare vintage 2024").run()
        assert not app.exception
        query.assert_awaited_once_with("Compare vintage 2024")
        assert any("error" in warning.value for warning in app.warning)
        assert any(error.value == "Filtro no válido" for error in app.error)
        assert any(expander.label == "Cómo se obtuvo esta respuesta" for expander in app.expander)
        pdf = next(call.kwargs for call in download.call_args_list if call.kwargs["mime"] == "application/pdf")
        excel = next(call.kwargs for call in download.call_args_list if call.kwargs["file_name"].endswith(".xlsx"))
        assert pdf["data"].startswith(b"%PDF-")
        workbook = load_workbook(BytesIO(excel["data"]))
        assert workbook.sheetnames == ["Respuesta", "Trazabilidad"]
        assert workbook["Respuesta"]["B3"].value == "Compare vintage 2024"
        workbook.close()
        app.run()
        assert not app.exception
        assert any(error.value == "Filtro no válido" for error in app.error)
        assert download.call_count >= 2


def test_dashboard_chat_uses_current_view_and_resets_follow_up_context_on_filter_change():
    rows = [
        {
            "vintage": 202401, "mob": 0,
            "measures": {"accounts": 10, "enrolled_amount": 100, "net_chargeoff_amount": 10},
            "metrics": {"delinquency_rate_amount": None, "net_chargeoff_rate": 0.1}, "row_count": 1,
        },
        {
            "vintage": 202402, "mob": 1,
            "measures": {"accounts": 20, "enrolled_amount": 100, "net_chargeoff_amount": 20},
            "metrics": {"delinquency_rate_amount": None, "net_chargeoff_rate": 0.2}, "row_count": 1,
        },
    ]
    result = {
        "final_answer": "Respuesta del panel.",
        "research_findings": {"tool_results": []},
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "get_dashboard_cohorts", new_callable=AsyncMock, return_value=rows),
        patch.object(QueryService, "get_dashboard_dimensions", new_callable=AsyncMock, return_value={
            "product": ["A"], "channel": ["Web"], "strategy": ["S"],
        }),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result) as query,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_dashboard").click().run()
        headings = [item.value for item in app.markdown]
        assert headings.index("#### Pregúntale a ObsAgent sobre esta vista") < headings.index(
            "#### Evolución por mes en libros"
        )
        app.selectbox(key="dashboard_metric").select("net_chargeoff_rate").run()
        app.selectbox(key="dashboard_vintage").select(202401).run()
        app.selectbox(key="dashboard_mob").select(0).run()
        app.chat_input(key="dashboard_chat_input").set_value("Explica esta vista").run()
        assert not app.exception
        request = query.await_args_list[-1].args[0]
        assert '"cosecha": 202401' in request
        assert '"mes_en_libros": 0' in request
        assert '"valor": 0.1' in request
        assert '"cosecha": 202402' in request
        assert "sin aplicar los filtros seleccionados" in request
        app.chat_input(key="dashboard_chat_input").set_value("¿Y antes?").run()
        assert "Explica esta vista" in query.await_args_list[-1].args[0]
        app.selectbox(key="dashboard_mob").select(None).run()
        app.chat_input(key="dashboard_chat_input").set_value("¿Qué veo ahora?").run()
        assert '"mes_en_libros": null' in query.await_args_list[-1].args[0]
        assert "¿Y antes?" not in query.await_args_list[-1].args[0]
        assert len(app.session_state["dashboard_messages"]) == 6
        assert not app.exception
        app.button(key="dashboard_fraud_demo").click().run()
        assert app.session_state["obsagent_tabs"] == "Fraude (demo)"
        assert any("no detecta fraude real" in warning.value for warning in app.warning)


def test_guide_status_uses_concise_available_label():
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_capabilities").click().run()
        captions = [item.value for item in app.caption]
        assert any("guía disponible" in value for value in captions)
        assert all("Obtener datos del almacenamiento" not in value for value in captions)
        assert all("ejecución no garantizada" not in value for value in captions)


def test_portfolio_alerts_require_scope_and_population():
    rows = [{
        "vintage": 202401, "mob": 6, "metrics": {"delinquency_rate_amount": 0.1},
        "measures": {"accounts": 100, "enrolled_amount": 200, "over30_amount": 20},
        "row_count": 1,
    }]
    alert = {
        "status": "evaluated", "peer_count": 4, "excluded_count": 1,
        "q1": 0.1, "q3": 0.2, "lower": -0.05, "upper": 0.35,
        "numerator": "over30_amount", "denominator": "enrolled_amount",
        "candidates": [{"product": "B", "anomaly": "high",
                        "metrics": {"delinquency_rate_amount": 0.5},
                        "measures": {"accounts": 50, "over30_amount": 100, "enrolled_amount": 200}}],
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "get_dashboard_cohorts", new_callable=AsyncMock, return_value=rows),
        patch.object(QueryService, "get_dashboard_dimensions", new_callable=AsyncMock, return_value={
            "product": ["A"], "channel": ["Web"], "strategy": ["S"],
        }),
        patch.object(QueryService, "get_portfolio_alerts", new_callable=AsyncMock, return_value=alert) as run,
        patch.object(st, "dataframe", wraps=st.dataframe) as dataframes,
    ):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"), default_timeout=30).run()
        app.button(key="home_dashboard").click().run()
        app.checkbox(key="dashboard_alerts_enabled").check().run()
        run.assert_not_awaited()
        app.selectbox(key="dashboard_vintage").select(202401).run()
        app.selectbox(key="dashboard_mob").select(6).run()
        run.assert_not_awaited()
        app.number_input(key="dashboard_alert_minimum").set_value(10).run()
        assert not app.exception
        run.assert_awaited_once_with("product", "delinquency_rate_amount",
                                    {"mob": 6, "vintage": 202401}, 10)
        table = next(call.args[0] for call in dataframes.call_args_list
                     if call.kwargs.get("alt") == "Alertas exploratorias de morosidad por segmento")
        assert table[0]["Denominador"] == 200 and table[0]["Tasa"] == "50.00%"
        assert any("no indica fraude" in caption.value for caption in app.caption)
    st.cache_data.clear()


def test_chat_shows_unmatched_numeric_evidence():
    result = {
        "final_answer": "La tasa es 10.00% y hay 999 cuentas.",
        "research_findings": {"tool_results": [{
            "tool": "portfolio_kpis", "arguments": {},
            "result": {"metrics": {"delinquency_rate_amount": 0.1}, "measures": {"accounts": 20}},
        }]},
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result),
    ):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"), default_timeout=30).run()
        app.button(key="home_chat").click().run()
        app.chat_input[0].set_value("Dame la tasa y cuentas").run()
        assert not app.exception
        assert any("sin coincidencia identificada" in warning.value for warning in app.warning)
        assert any(item.label == "Posibles fuentes de las cifras" for item in app.expander)
        app.run()
        assert any("sin coincidencia identificada" in warning.value for warning in app.warning)


def test_synthetic_evaluation_requires_explicit_click():
    report = [{
        "caso": "Prueba", "herramienta_correcta": True, "evidencia_correcta": True,
        "cifras_presentes": True, "errores_herramientas": 0, "respuesta": "10%",
    }]
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch("multi_agent_framework.evaluation.run_synthetic_evaluation", new_callable=AsyncMock, return_value=report) as run,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_capabilities").click().run()
        run.assert_not_awaited()
        assert not any(button.key == "run_synthetic_evaluation" for button in app.button)
        app.session_state["obsagent_tabs"] = "Evaluación sintética"
        app.run()
        assert not app.exception
        run.assert_not_awaited()
        app.button(key="run_synthetic_evaluation").click().run()
        assert not app.exception
        run.assert_awaited_once()
        assert any("Evidencia: correcta" in item.value for item in app.markdown)
        app.session_state["obsagent_tabs"] = "Cómo funciona"
        app.run()
        app.session_state["obsagent_tabs"] = "Evaluación sintética"
        app.run()
        assert any("Evidencia: correcta" in item.value for item in app.markdown)
        run.assert_awaited_once()


def test_dashboard_segments_comparison_and_population_warning():
    st.cache_data.clear()
    all_rows = [
        {"vintage": 202401, "mob": 0, "metrics": {"delinquency_rate_amount": 0.1},
         "measures": {"accounts": 5, "enrolled_amount": 100, "over30_amount": 10}, "row_count": 1},
        {"vintage": 202401, "mob": 2, "metrics": {"delinquency_rate_amount": 0.15},
         "measures": {"accounts": 6, "enrolled_amount": 100, "over30_amount": 15}, "row_count": 1},
        {"vintage": 202402, "mob": 2, "metrics": {"delinquency_rate_amount": 0.25},
         "measures": {"accounts": 7, "enrolled_amount": 100, "over30_amount": 25}, "row_count": 1},
    ]
    result = {"final_answer": "Respuesta.", "research_findings": {"tool_results": []}}
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "get_dashboard_cohorts", new_callable=AsyncMock, return_value=all_rows) as cohorts,
        patch.object(QueryService, "get_dashboard_dimensions", new_callable=AsyncMock, return_value={
            "product": ["A"], "channel": ["Web"], "strategy": ["S"],
        }),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result) as query,
        patch.object(st, "dataframe", wraps=st.dataframe) as dataframes,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_dashboard").click().run()
        assert not app.exception
        assert all(app.selectbox(key=f"dashboard_segment_{name}").value is None
                   for name in ("product", "channel", "strategy"))
        assert not any(box.key == "dashboard_segments_enabled" for box in app.checkbox)
        cohorts.assert_awaited_once_with()
        app.selectbox(key="dashboard_segment_product").select("A").run()
        assert cohorts.await_args_list[-1].args == ({"product": "A"},)
        app.multiselect(key="dashboard_comparison_vintages").set_value([202401, 202402]).run()
        assert not app.exception
        comparison = next(call.args[0] for call in reversed(dataframes.call_args_list)
                          if call.kwargs.get("alt") == "Comparación de cosechas en el mismo mes en libros")
        assert comparison[1]["Diferencia respecto a referencia (puntos porcentuales)"] == "+10.00"
        assert app.selectbox(key="dashboard_comparison_mob").value == 2
        app.selectbox(key="dashboard_mob").select(2).run()
        app.checkbox(key="dashboard_minimum_enabled").check().run()
        app.number_input(key="dashboard_minimum").set_value(20).run()
        assert any("por debajo del mínimo" in warning.value for warning in app.warning)
        assert any("meses intermedios faltantes" in warning.value for warning in app.warning)
        app.chat_input(key="dashboard_chat_input").set_value("Explica la comparación").run()
        request = query.await_args_list[-1].args[0]
        assert '"segmentos": {"product": "A"}' in request
        assert '"comparacion": {' in request
        assert '"minimo_de_cuentas": 20' in request
        assert '"total_cosechas_bajo_minimo": 2' in request
        assert not app.exception
        app.selectbox(key="dashboard_segment_product").select(None).run()
        assert app.selectbox(key="dashboard_segment_product").value is None
        assert not app.exception
    st.cache_data.clear()


def test_vintage_comparison_requires_common_mob():
    rows = [
        {"vintage": 202401, "mob": 0, "metrics": {"delinquency_rate_amount": 0.1},
         "measures": {"accounts": 5, "enrolled_amount": 100, "over30_amount": 10}, "row_count": 1},
        {"vintage": 202402, "mob": 2, "metrics": {"delinquency_rate_amount": 0.25},
         "measures": {"accounts": 7, "enrolled_amount": 100, "over30_amount": 25}, "row_count": 1},
    ]
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "get_dashboard_cohorts", new_callable=AsyncMock, return_value=rows),
        patch.object(QueryService, "get_dashboard_dimensions", new_callable=AsyncMock, return_value={
            "product": ["A"], "channel": ["Web"], "strategy": ["S"],
        }),
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_dashboard").click().run()
        app.multiselect(key="dashboard_comparison_vintages").set_value([202401, 202402]).run()
        assert not app.exception
        assert any("no tienen meses en libros en común" in warning.value for warning in app.warning)


def test_guide_only_response_is_not_presented_as_portfolio_evidence():
    result = {
        "final_answer": "Se consultó la guía.",
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


def test_excel_remains_available_when_pdf_fails():
    result = {
        "final_answer": "Se requiere revisión.",
        "research_findings": {
            "tool_results": [{
                "tool": "validar_csv_local",
                "arguments": {},
                "result": {"status": "checks_completed"},
            }]
        },
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result),
        patch("multi_agent_framework.draft_report.build_draft_pdf", side_effect=ValueError("PDF inválido")),
        patch.object(st, "download_button", wraps=st.download_button) as download,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_chat").click().run()
        app.chat_input[0].set_value("Valida los datos").run()
        assert not app.exception
        assert any("PDF inválido" in error.value for error in app.error)
        assert any(call.kwargs["file_name"].endswith(".xlsx") for call in download.call_args_list)


def test_trace_displays_spanish_labels_without_modifying_filter_values():
    result = {
        "final_answer": "Resultado.",
        "research_findings": {
            "tool_results": [{
                "tool": "segment_ranking",
                "arguments": {
                    "group_by": "product",
                    "metric": "delinquency_rate_amount",
                    "filters": {"channel": "Branch"},
                },
                "result": [{"product": "Affinity", "metrics": {"delinquency_rate_amount": 0.1}}],
            }]
        },
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result),
        patch.object(st, "json", wraps=st.json) as render_json,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_chat").click().run()
        app.chat_input[0].set_value("Clasifica productos").run()
        assert not app.exception
        assert render_json.call_args_list[0].args[0] == {
            "Agrupar por": "Producto",
            "Indicador": "Tasa de morosidad (monto)",
            "Filtros": {"Canal": "Branch"},
        }
        assert render_json.call_args_list[1].args[0] == [
            {"Producto": "Affinity", "Indicadores": {"Tasa de morosidad (monto)": 0.1}}
        ]


def test_missing_dictionary_warning_is_visible_in_chat():
    result = {
        "final_answer": "Respuesta sin diccionario.",
        "research_findings": {
            "tool_results": [],
            "dictionary_warning": "No se pudo leer el diccionario de variables.",
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
        app.chat_input[0].set_value("Hola").run()
        assert not app.exception
        assert any("diccionario de variables" in warning.value for warning in app.warning)


def test_comparison_chart_and_spanish_response_are_shown_and_survive_rerun():
    answer = (
        "Cosecha 202401 (baseline): 9.58%. Cosecha 202402 (comparison): 9.41%. "
        "Monto inscrito (enrolled_amount). Herramienta `vintage_comparison`; "
        "diferencia `metric_delta`. Producto (Affinity), mes (MOB)."
    )
    result = {
        "final_answer": answer,
        "research_findings": {
            "tool_results": [{
                "tool": "vintage_comparison",
                "arguments": {"baseline_vintage": 202401, "comparison_vintage": 202402, "mob": 6},
                "result": {
                    "baseline_vintage": 202401,
                    "comparison_vintage": 202402,
                    "baseline": {"metrics": {"delinquency_rate_amount": 0.0958}},
                    "comparison": {"metrics": {"delinquency_rate_amount": 0.0941}},
                    "metric_delta": {"delinquency_rate_amount": -0.0017},
                },
            }]
        },
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result),
        patch.object(st, "bar_chart", wraps=st.bar_chart) as bar_chart,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_chat").click().run()
        app.chat_input[0].set_value("Compara morosidad de dos cosechas y genera una gráfica").run()
        assert not app.exception
        shown = app.session_state["obsagent_messages"][-1]["content"]
        assert "(referencia)" in shown and "(comparación)" in shown
        assert all(name not in shown for name in (
            "baseline", "comparison", "enrolled_amount", "vintage_comparison", "metric_delta"
        ))
        assert "9.58%" in shown and "9.41%" in shown and "(Affinity)" in shown and "(MOB)" in shown
        assert bar_chart.call_args.args[0] == [
            {"Cosecha": "202401", "Tasa de morosidad (monto)": 9.58},
            {"Cosecha": "202402", "Tasa de morosidad (monto)": 9.41},
        ]
        app.run()
        assert not app.exception
        assert bar_chart.call_count == 2
        assert any("Gráfica generada" in caption.value for caption in app.caption)


def test_synthetic_fraud_view_and_separate_contextual_chat():
    result = {
        "final_answer": "El canal F es atípico.",
        "research_findings": {"tool_results": []},
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result) as query,
        patch.object(st, "bar_chart", wraps=st.bar_chart) as chart,
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.session_state["obsagent_tabs"] = "Fraude (demo)"
        app.run()
        assert not app.exception
        assert any("no detecta fraude real" in warning.value for warning in app.warning)
        assert any("0.70%" in caption.value for caption in app.caption)
        assert chart.call_args.args[0][-1]["Tasa de incidentes simulados (%)"] == 2.0
        app.chat_input(key="fraud_chat_input").set_value("Explica esta vista").run()
        assert not app.exception
        request = query.await_args_list[-1].args[0]
        assert '"tipo": "demostracion_sintetica"' in request
        assert '"incidentes_simulados": 20' in request
        assert "no detecta fraude real" in app.session_state["fraud_demo_messages"][-1]["content"]
        app.run()
        assert any("no detecta fraude real" in msg.value for msg in app.markdown)
        app.session_state["obsagent_tabs"] = "Conversar con ObsAgent"
        app.run()
        assert not app.exception
        assert app.session_state["obsagent_messages"] == []


def test_synthetic_tool_result_in_general_chat_keeps_warning():
    result = {
        "final_answer": "El canal F es atípico.",
        "research_findings": {"tool_results": [{
            "tool": "analizar_fraude_simulado",
            "arguments": {},
            "result": {"tipo": "demostracion_sintetica"},
        }]},
    }
    with (
        patch.object(QueryService, "__init__", return_value=None),
        patch.object(QueryService, "available_tools", return_value=[]),
        patch.object(QueryService, "query", new_callable=AsyncMock, return_value=result),
    ):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.button(key="home_chat").click().run()
        app.chat_input[0].set_value("Analiza el fraude simulado").run()
        assert not app.exception
        assert "no detecta fraude real" in app.session_state["obsagent_messages"][-1]["content"]


if __name__ == "__main__":
    test_portfolio_alerts_require_scope_and_population()
    test_chat_shows_unmatched_numeric_evidence()
    test_dashboard_uses_available_filters_and_reuses_cohort_data()
    test_chat_navigation_and_tool_error_trace()
    test_dashboard_chat_uses_current_view_and_resets_follow_up_context_on_filter_change()
    test_guide_status_uses_concise_available_label()
    test_synthetic_evaluation_requires_explicit_click()
    test_dashboard_segments_comparison_and_population_warning()
    test_vintage_comparison_requires_common_mob()
    test_guide_only_response_is_not_presented_as_portfolio_evidence()
    test_excel_remains_available_when_pdf_fails()
    test_trace_displays_spanish_labels_without_modifying_filter_values()
    test_missing_dictionary_warning_is_visible_in_chat()
    test_comparison_chart_and_spanish_response_are_shown_and_survive_rerun()
    test_synthetic_fraud_view_and_separate_contextual_chat()
    test_synthetic_tool_result_in_general_chat_keeps_warning()
    print("Streamlit workspace test passed.")
