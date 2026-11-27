"""Streamlit chat and portfolio dashboard for ObsAgent."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import altair as alt
import requests
import streamlit as st

from ChromaDB.precomputed_queries import combine_cohort_summaries
from multi_agent_framework.agent_manager import DEFAULT_CHROMA_PATH
from multi_agent_framework.draft_report import build_draft_pdf
from multi_agent_framework.excel_report import build_chat_excel, build_dashboard_excel
from multi_agent_framework.evaluation import run_synthetic_evaluation
from multi_agent_framework.fraud_demo import analyze_synthetic_fraud
from multi_agent_framework.local_validation import validate_local_csv
from multi_agent_framework.numeric_evidence import numeric_evidence
from multi_agent_framework.display_labels import (
    SKILL_LABELS,
    TOOL_LABELS,
    display_answer,
    display_trace_value,
)
from multi_agent_framework.query_service import KPIType, QueryService
from multi_agent_framework.response_charts import build_response_chart
from multi_agent_framework.skill_guides import available_skill_guides


KPI_LABELS = {
    KPIType.DELINQUENCY_RATE.value: "Tasa de morosidad (monto)",
    KPIType.DELINQUENCY_RATE_ACCOUNTS.value: "Tasa de morosidad (cuentas)",
    KPIType.GROSS_CHARGEOFF_RATE.value: "Tasa de castigo bruto",
    KPIType.NET_CHARGEOFF_RATE.value: "Tasa de castigo neto",
    KPIType.RECOVERY_RATE.value: "Tasa de recuperación",
    KPIType.UTILIZATION_RATE.value: "Tasa de utilización",
    KPIType.OPERATING_MARGIN.value: "Margen operativo",
    KPIType.OPERATING_MARGIN_RATE.value: "Tasa de margen operativo",
    KPIType.EFFICIENCY_RATIO.value: "Índice de eficiencia",
    KPIType.ACQUISITION_COST_PER_ACCOUNT.value: "Costo de adquisición por cuenta",
}
NON_PERCENTAGE_METRICS = {
    KPIType.OPERATING_MARGIN.value,
    KPIType.ACQUISITION_COST_PER_ACCOUNT.value,
}


@st.cache_resource(show_spinner=False)
def get_service(chroma_path: str) -> QueryService:
    return QueryService(chroma_path)


@st.cache_data(ttl="5m", max_entries=4, show_spinner="Cargando datos de cartera...")
def load_dashboard_cohorts(
    chroma_path: str, segment_filters: tuple[tuple[str, str], ...] = (),
) -> list[dict[str, Any]]:
    service = get_service(chroma_path)
    if not segment_filters:
        return asyncio.run(service.get_dashboard_cohorts())
    return asyncio.run(service.get_dashboard_cohorts(dict(segment_filters)))


@st.cache_data(ttl="5m", max_entries=4, show_spinner="Cargando opciones de segmentos...")
def load_dashboard_dimensions(chroma_path: str) -> dict[str, list[str]]:
    return asyncio.run(get_service(chroma_path).get_dashboard_dimensions())


@st.cache_data(ttl="5m", max_entries=16, show_spinner="Calculando alertas...")
def load_portfolio_alerts(
    chroma_path: str, group_by: str, metric: str,
    filters: tuple[tuple[str, Any], ...], minimum_accounts: int,
) -> dict[str, Any]:
    return asyncio.run(get_service(chroma_path).get_portfolio_alerts(
        group_by, metric, dict(filters), minimum_accounts
    ))


def display_metric(value: float | int | None, metric: str) -> str:
    if value is None:
        return "No disponible"
    if metric in NON_PERCENTAGE_METRICS:
        return f"{value:,.2f}"
    return f"{value:.2%}"


def render_response_chart(chart: dict[str, Any]) -> None:
    st.caption("Gráfica generada a partir de los resultados de la consulta.")
    if chart["kind"] == "line":
        st.line_chart(
            chart["data"],
            x=chart["x"],
            y=chart["y"],
            color=chart["color"],
            alt=chart["alt"],
        )
    else:
        st.bar_chart(
            chart["data"],
            x=chart["x"],
            y=chart["y"],
            alt=chart["alt"],
        )


def render_trace(trace: dict[str, Any], answer: str) -> None:
    calls = trace["tool_results"]
    claims = numeric_evidence(answer, trace)
    if claims:
        missing = sum(not claim["fuentes_posibles"] for claim in claims)
        if missing:
            st.warning(
                f"{missing} cifra(s) sin coincidencia identificada en los resultados o el contexto. "
                "Revisa las fuentes antes de usar la respuesta."
            )
        with st.expander("Posibles fuentes de las cifras"):
            st.caption(
                "Coincidencia numérica orientativa, no verificación: revisa indicador, "
                "unidad, periodo, segmento y filtros. Las cifras ambiguas pueden tener varias fuentes; "
                "se muestran hasta 10 por cifra. Los formatos ambiguos pueden quedar sin coincidencia."
            )
            st.json(claims)
    if trace.get("dictionary_warning"):
        st.warning(trace["dictionary_warning"])
    errors = [
        call for call in calls
        if isinstance(call.get("result"), dict) and "error" in call["result"]
    ]
    if errors:
        st.warning(
            "Una o más llamadas a herramientas devolvieron un error. "
            "Revisa la trazabilidad antes de usar la respuesta."
        )
    if calls and all(call.get("tool") in {"consultar_skill", "consultar_diccionario"} for call in calls):
        st.warning(
            "Solo se consultaron guías o definiciones; no se obtuvieron datos de cartera "
            "ni se verificó la respuesta."
        )
    with st.expander("Cómo se obtuvo esta respuesta"):
        if trace.get("builder_used"):
            st.caption("El investigador analizó la consulta y el redactor preparó la respuesta.")
        if timings := trace.get("timings_ms"):
            st.caption(
                f"Investigador: {timings['researcher'] / 1000:.2f} s · "
                f"Redactor: {timings['builder'] / 1000:.2f} s · "
                f"Total: {timings['total'] / 1000:.2f} s. "
                "El tiempo del investigador incluye las herramientas."
            )
        if "dashboard_context" in trace:
            st.markdown("**Vista del panel al preguntar**")
            st.json(display_trace_value(trace["dashboard_context"]))
        if not calls:
            st.info("El modelo no llamó a ninguna herramienta en esta respuesta.")
        for index, call in enumerate(calls, start=1):
            tool = call.get("tool")
            st.markdown(f"**{index}. {TOOL_LABELS.get(tool, tool or 'Herramienta desconocida')}**")
            if "duration_ms" in call:
                st.caption(f"Duración de la herramienta: {call['duration_ms'] / 1000:.2f} s")
            if "arguments" in call:
                st.caption("Argumentos solicitados")
                st.json(display_trace_value(call["arguments"]))
            if isinstance(call.get("result"), dict) and "error" in call["result"]:
                st.error(str(call["result"]["error"]))
            else:
                st.caption("Resultado devuelto al modelo")
                st.json(display_trace_value(call["result"]))
        st.caption("La trazabilidad pertenece a esta sesión y no se guarda en la base.")


def render_draft_download(
    question: str, answer: str, trace: dict[str, Any], index: int, prefix: str = ""
) -> None:
    try:
        pdf = build_draft_pdf(question, answer, display_trace_value(trace))
    except ValueError as error:
        st.error(f"No se pudo preparar el PDF de prueba: {error}")
    else:
        st.download_button(
            "Descargar PDF de prueba",
            data=pdf,
            file_name="obsagent-borrador.pdf",
            mime="application/pdf",
            key=f"{prefix}draft_pdf_{index}",
            on_click="ignore",
            help="Borrador no verificado automáticamente.",
        )
    try:
        excel = build_chat_excel(question, answer, display_trace_value(trace))
    except ValueError as error:
        st.error(f"No se pudo preparar el Excel de prueba: {error}")
        return
    st.download_button(
        "Descargar Excel de prueba",
        data=excel,
        file_name="obsagent-borrador.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"{prefix}draft_excel_{index}",
        on_click="ignore",
        help="Borrador no verificado automáticamente.",
    )


def select_view(view: str) -> None:
    st.session_state.obsagent_tabs = view


def show_error(error: Exception) -> None:
    st.error(str(error))
    if isinstance(error, requests.exceptions.RequestException):
        st.caption(
            "Verifica que Ollama esté disponible y que la URL y el modelo "
            "configurados sean correctos."
        )
    elif isinstance(error, RuntimeError) and "collection" in str(error).lower():
        st.caption(
            "Prepara las colecciones de origen y agregados siguiendo "
            "ChromaDB/README.md."
        )


def render_conversation(
    service: QueryService, state_key: str, *, dashboard_context: dict[str, Any] | None = None,
    source_path: str | None = None, widget_prefix: str | None = None,
) -> None:
    if state_key not in st.session_state:
        st.session_state[state_key] = []
    messages = st.session_state[state_key]
    dashboard = dashboard_context is not None
    prefix = widget_prefix if widget_prefix is not None else ("dashboard_" if dashboard else "")

    if not messages:
        st.info("Escribe una pregunta sobre la vista actual." if dashboard else
                "Empieza con una pregunta, por ejemplo: «¿Qué cosechas tienen la mayor tasa de morosidad?»")
    if st.button("Borrar conversación", key=f"{prefix}clear_conversation"):
        messages.clear()

    for index, message in enumerate(messages):
        with st.chat_message(message["role"]):
            content = message["content"]
            if message["role"] == "assistant":
                content = display_answer(content)
            st.markdown(content)
            if chart := message.get("chart"):
                render_response_chart(chart)
            if trace := message.get("trace"):
                render_trace(trace, content)
                question = message.get("question")
                if question is None and index > 0:
                    question = messages[index - 1]["content"]
                render_draft_download(question or "", content, trace, index, prefix)

    prompt = st.chat_input(
        "Pregunta sobre los datos del panel" if dashboard else
        "Por ejemplo: Compara cosechas recientes por tasa de morosidad",
        key=f"{prefix}chat_input",
    )
    if not prompt:
        return
    prior_messages = messages[-2:]
    if dashboard and any(
        message.get("dashboard_context") != dashboard_context or message.get("source_path") != source_path
        for message in prior_messages
    ):
        prior_messages = []
    messages.append({
        "role": "user", "content": prompt, "dashboard_context": dashboard_context,
        "source_path": source_path,
    })
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Analizando tu consulta y preparando la respuesta..."):
            try:
                history = "\n".join(
                    f'{("Usuario" if message["role"] == "user" else "Asistente")}: '
                    f'{message["content"]}' for message in prior_messages
                )
                request = prompt
                if history:
                    request = f"Conversación hasta ahora:\n{history}\n\nÚltima consulta del usuario: {prompt}"
                if dashboard_context is not None:
                    request = (
                        "La consulta procede del panel. Usa el contexto siguiente para interpretar "
                        "referencias a la vista; no supongas que todos los gráficos tienen los mismos "
                        "filtros. Para datos no incluidos, consulta las herramientas. "
                        "Una solicitud explícita del usuario puede pedir otro alcance.\n"
                        f"Contexto del panel: {json.dumps(dashboard_context, ensure_ascii=False)}\n\n"
                        f"{request}"
                    )
                result = asyncio.run(service.query(request))
                answer = display_answer(result["final_answer"])
                if not answer:
                    st.warning("El agente no generó una respuesta.")
                    return
                tool_results = result["research_findings"]["tool_results"]
                if (dashboard_context and dashboard_context.get("tipo") == "demostracion_sintetica") or any(
                    call.get("tool") == "analizar_fraude_simulado" for call in tool_results
                ):
                    answer = (
                        "**Demostración con datos inventados; no detecta fraude real ni "
                        "tiene confiabilidad validada.**\n\n" + answer
                    )
                st.markdown(answer)
                chart = build_response_chart(
                    tool_results,
                    prompt, KPI_LABELS, NON_PERCENTAGE_METRICS,
                )
                if chart:
                    render_response_chart(chart)
                trace = {
                    "tool_results": result["research_findings"]["tool_results"],
                    "dictionary_warning": result["research_findings"].get("dictionary_warning"),
                    "builder_used": True,
                    "timings_ms": result.get("timings_ms"),
                }
                if dashboard_context is not None:
                    trace["dashboard_context"] = dashboard_context
                render_trace(trace, answer)
                messages.append({
                    "role": "assistant", "content": answer, "question": prompt,
                    "chart": chart, "trace": trace, "dashboard_context": dashboard_context,
                    "source_path": source_path,
                })
                render_draft_download(prompt, answer, trace, len(messages) - 1, prefix)
            except (RuntimeError, ValueError, KeyError, requests.exceptions.RequestException) as error:
                show_error(error)


st.set_page_config(
    page_title="ObsAgent | Análisis de cartera",
    page_icon=":material/monitoring:",
    layout="wide",
)
hero_style, hero_markup = (
    """
    <style>
    .obs-hero {
        background:
            radial-gradient(ellipse at 92% 10%, rgba(230, 0, 60, 0.22), transparent 34%),
            linear-gradient(120deg, #071522, #0B2030);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 26px;
        color: #FFFFFF;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 18px 48px rgba(7, 21, 34, 0.14);
    }
    .obs-hero__brand {
        align-items: center;
        display: flex;
        gap: 0.6rem;
        margin-bottom: 1.35rem;
    }
    .obs-hero__logo {
        height: 1.65rem;
        width: 1.65rem;
    }
    .obs-hero__wordmark {
        color: #FFFFFF;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .obs-hero__divider {
        background: rgba(255, 255, 255, 0.34);
        height: 1rem;
        margin: 0 0.25rem;
        width: 1px;
    }
    .obs-hero__product {
        color: #DDE6E4;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .obs-hero__label {
        color: #80F4DC;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .obs-hero h1 {
        color: #FFFFFF;
        font-size: clamp(2rem, 4vw, 3.2rem);
        letter-spacing: -0.035em;
        line-height: 1.1;
        margin: 0.5rem 0;
        padding: 0;
    }
    .obs-hero p {
        color: #DDE6E4;
        margin: 0;
        max-width: 42rem;
    }
    .obs-sidebar__brand {
        align-items: center;
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.15rem;
    }
    .obs-sidebar__logo {
        height: 1.35rem;
        width: 1.35rem;
    }
    .obs-sidebar__wordmark {
        color: #0B2030;
        font-size: 0.9rem;
        font-weight: 700;
    }
    .obs-sidebar__product {
        color: #40505D;
        font-size: 0.75rem;
        margin-left: 1.85rem;
    }
    @media (prefers-reduced-motion: no-preference) {
        .obs-hero {
            animation: obs-hero-enter 220ms ease-out;
        }
        @keyframes obs-hero-enter {
            from { opacity: 0.85; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }
    }
    </style>
    <header class="obs-hero">
        <div class="obs-hero__brand">
            <svg class="obs-hero__logo" role="img" aria-label="Banamex" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                <g fill="#E6003C">
                    <circle cx="20" cy="5.5" r="4.3"/><circle cx="30.3" cy="9.7" r="4.3"/>
                    <circle cx="34.5" cy="20" r="4.3"/><circle cx="30.3" cy="30.3" r="4.3"/>
                    <circle cx="20" cy="34.5" r="4.3"/><circle cx="9.7" cy="30.3" r="4.3"/>
                    <circle cx="5.5" cy="20" r="4.3"/><circle cx="9.7" cy="9.7" r="4.3"/>
                    <circle cx="20" cy="20" r="3.3"/>
                </g>
            </svg>
            <span class="obs-hero__wordmark">Banamex</span>
            <span class="obs-hero__divider"></span>
            <span class="obs-hero__product">ObsAgent · Inteligencia de cartera</span>
        </div>
        <div class="obs-hero__label">Claridad en la complejidad</div>
        <h1>Claridad para decidir. Inteligencia para actuar.</h1>
        <p>Explora tu cartera y convierte los datos en respuestas basadas en evidencia.</p>
    </header>
    """
).split("</style>", 1)
st.markdown(f"{hero_style}</style>", unsafe_allow_html=True)
hero_slot = st.empty()
hero_slot.markdown(hero_markup, unsafe_allow_html=True)

default_path = os.getenv("OBSAGENT_CHROMA_PATH", str(DEFAULT_CHROMA_PATH))
with st.sidebar:
    st.markdown(
        """
        <div class="obs-sidebar__brand">
            <svg class="obs-sidebar__logo" role="img" aria-label="Banamex" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                <g fill="#E6003C">
                    <circle cx="20" cy="5.5" r="4.3"/><circle cx="30.3" cy="9.7" r="4.3"/>
                    <circle cx="34.5" cy="20" r="4.3"/><circle cx="30.3" cy="30.3" r="4.3"/>
                    <circle cx="20" cy="34.5" r="4.3"/><circle cx="9.7" cy="30.3" r="4.3"/>
                    <circle cx="5.5" cy="20" r="4.3"/><circle cx="9.7" cy="9.7" r="4.3"/>
                    <circle cx="20" cy="20" r="3.3"/>
                </g>
            </svg>
            <span class="obs-sidebar__wordmark">Banamex</span>
        </div>
        <div class="obs-sidebar__product">ObsAgent · Inteligencia de cartera</div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.subheader("Origen de datos")
    chroma_path = st.text_input(
        "Directorio de ChromaDB",
        value=default_path,
        help="Directorio con base_cards_sintetica y su colección de agregados.",
    )
    st.caption("Usa un directorio local de ChromaDB con las dos colecciones requeridas.")
    with st.expander("Configuración de conexión"):
        st.caption("Configura Ollama con CHAT_MODEL y OLLAMA_BASE_URL en .env.")

try:
    service = get_service(chroma_path)
except (RuntimeError, ValueError, requests.exceptions.RequestException) as error:
    show_error(error)
    st.stop()

home_tab, chat_tab, dashboard_tab, fraud_tab, evaluation_tab, capabilities_tab = st.tabs(
    ["Inicio", "Conversar con ObsAgent", "Panel de cartera", "Fraude (demo)",
     "Evaluación sintética", "Cómo funciona"],
    on_change="rerun",
    key="obsagent_tabs",
)
if not home_tab.open:
    hero_slot.empty()

with home_tab:
    st.badge("Inteligencia de cartera", icon=":material/analytics:", color="blue")
    st.subheader("Tu espacio de inteligencia de cartera")
    st.caption(
        "Explora indicadores, plantea preguntas y revisa cómo se obtuvo cada respuesta."
    )
    explore, ask, inspect = st.columns(3)
    with explore:
        with st.container(border=True, height="stretch"):
            st.markdown("### :material/monitoring: Explora la cartera")
            st.caption(
                "Consulta indicadores, compara cosechas y visualiza su distribución."
            )
            st.button(
                "Abrir panel",
                key="home_dashboard",
                on_click=select_view,
                args=("Panel de cartera",),
                type="primary",
                icon=":material/arrow_forward:",
                width="stretch",
            )
    with ask:
        with st.container(border=True, height="stretch"):
            st.markdown("### :material/forum: Pregunta al agente")
            st.caption(
                "Analiza segmentos y cosechas con herramientas de cálculo validadas."
            )
            st.button(
                "Iniciar análisis",
                key="home_chat",
                on_click=select_view,
                args=("Conversar con ObsAgent",),
                icon=":material/arrow_forward:",
                width="stretch",
            )
    with inspect:
        with st.container(border=True, height="stretch"):
            st.markdown("### :material/fact_check: Entiende el proceso")
            st.caption(
                "Conoce las herramientas disponibles y los límites del flujo actual."
            )
            st.button(
                "Ver capacidades",
                key="home_capabilities",
                on_click=select_view,
                args=("Cómo funciona",),
                icon=":material/arrow_forward:",
                width="stretch",
            )
    st.caption(
        "El panel consulta agregados locales. El chat requiere Ollama; "
        "los tiempos dependen del modelo y del volumen consultado."
    )

with chat_tab:
    st.subheader("Analiza tu cartera", icon=":material/forum:")
    st.caption(
        "Consulta indicadores, compara cosechas o explora segmentos. "
        "ObsAgent te ayuda a analizar tu cartera."
    )
    if chat_tab.open:
        render_conversation(service, "obsagent_messages")

with capabilities_tab:
    st.subheader("Capacidades y trazabilidad")
    st.caption(
                "La disponibilidad de una herramienta no garantiza que el modelo la use "
                "en cada consulta. Revisa la trazabilidad debajo de cada respuesta."
    )
    left, right = st.columns(2)
    with left:
                with st.container(border=True):
                    st.markdown("### :material/build: Herramientas disponibles")
                    st.caption(
                        "El modelo selecciona herramientas; Python valida los argumentos "
                        "y calcula los indicadores con los agregados de ChromaDB."
                    )
                    for tool in service.available_tools():
                        st.markdown(f"**{TOOL_LABELS.get(tool['name'], tool['name'])}**")
                        st.caption(tool["description"])
    with right:
                with st.container(border=True):
                    st.markdown("### :material/route: Flujo multiagente")
                    st.write(
                        "El orquestador coordina al investigador y al redactor. "
                        "El redactor añade una llamada al modelo."
                    )
                    st.markdown("### :material/menu_book: Diccionario de variables")
                    st.write(
                        "El agente recibe definiciones breves y puede consultar otras "
                        "del diccionario local. Son contexto, no una validación de datos. "
                        "Las definiciones se envían al servidor Ollama configurado."
                    )
                    st.markdown("### :material/menu_book: Guías del repositorio")
                    st.write(
                        "El agente puede consultar estas guías durante una respuesta. "
                        "Consultar una guía no implementa ni ejecuta sus acciones. "
                        "El contenido consultado se envía al servidor Ollama configurado."
                    )
                    if capabilities_tab.open:
                        for skill in available_skill_guides():
                            state = {
                                "guide_only": "guía disponible",
                                "empty": "guía vacía",
                                "missing": "guía ausente",
                            }[skill["status"]]
                            st.caption(f'{SKILL_LABELS.get(skill["name"], skill["name"])}: {state}')
                    st.markdown("### :material/shield: Límites")
                    st.write(
                        "El modelo puede equivocarse, elegir una herramienta incorrecta "
                        "o responder sin usar ninguna. Comprueba los argumentos, "
                        "resultados y errores antes de tomar decisiones."
                    )

with evaluation_tab:
    if evaluation_tab.open:
        st.subheader("Evaluación sintética del agente", icon=":material/science:")
        st.caption(
            "Ejecuta dos consultas con datos y diccionario inventados en una colección temporal. "
            "Se envían al servidor Ollama configurado, que puede ser remoto. "
            "La detección de cifras solo comprueba su presencia, no su significado."
        )
        if st.button("Ejecutar evaluación sintética", key="run_synthetic_evaluation"):
            with st.spinner("Evaluando investigador y redactor..."):
                try:
                    st.session_state["synthetic_evaluation"] = asyncio.run(run_synthetic_evaluation())
                except (RuntimeError, ValueError, requests.exceptions.RequestException) as error:
                    show_error(error)
        if reports := st.session_state.get("synthetic_evaluation"):
            for report in reports:
                st.markdown(f"**{report['caso']}**")
                if "error" in report:
                    st.error(report["error"])
                else:
                    st.write(
                        f"Herramienta: {'sí' if report['herramienta_correcta'] else 'no'} · "
                        f"Evidencia: {'correcta' if report['evidencia_correcta'] else 'incorrecta'} · "
                        f"Cifras presentes: {'sí' if report['cifras_presentes'] else 'no'} · "
                        f"Errores de herramientas: {report['errores_herramientas']}"
                    )
                    st.caption(report["respuesta"])

with fraud_tab:
    if fraud_tab.open:
        st.subheader("Fraude: demostración sintética", icon=":material/biotech:")
        st.warning(
            "Todos los datos son inventados. Esta demostración no detecta fraude real "
            "ni tiene confiabilidad validada; no sirve para tomar decisiones operativas."
        )
        fraud = analyze_synthetic_fraud()
        rows = fraud["resultados"]
        counts = st.columns(3)
        counts[0].metric("Canales simulados", len(rows))
        counts[1].metric("Transacciones simuladas", sum(row["transacciones_simuladas"] for row in rows))
        counts[2].metric("Canales con valor atípico", sum(row["valor_atipico"] for row in rows))
        st.caption(
            "Tasa = incidentes simulados / transacciones simuladas. El límite IQR "
            f"superior es {fraud['limite_superior']:.2%}; un valor atípico no prueba fraude."
        )
        st.caption(
            f"Primer cuartil: {fraud['q1']:.2%}; tercer cuartil: {fraud['q3']:.2%}; "
            f"límite inferior: {fraud['limite_inferior']:.2%}. "
            "Los límites son estadísticos y pueden quedar fuera del rango de las tasas."
        )
        chart_rows = [
            {"Canal simulado": row["canal"], "Tasa de incidentes simulados (%)": row["tasa"] * 100}
            for row in rows
        ]
        st.bar_chart(
            chart_rows, x="Canal simulado", y="Tasa de incidentes simulados (%)",
            alt="Tasas de incidentes simulados por canal",
        )
        st.dataframe(
            [{
                "Canal simulado": row["canal"],
                "Transacciones simuladas": row["transacciones_simuladas"],
                "Incidentes simulados": row["incidentes_simulados"],
                "Tasa": f"{row['tasa']:.2%}",
                "Valor atípico": "Sí" if row["valor_atipico"] else "No",
            } for row in rows],
            hide_index=True,
            alt="Resultados sintéticos por canal",
        )
        st.markdown("#### Pregunta sobre la demostración")
        st.caption(
            "La pregunta y estos resultados sintéticos se envían al servidor Ollama configurado."
        )
        render_conversation(
            service, "fraud_demo_messages", dashboard_context=fraud,
            source_path="demostracion_sintetica", widget_prefix="fraud_",
        )

with dashboard_tab:
    st.subheader("Resumen de cartera", icon=":material/monitoring:")
    st.caption("Selecciona un indicador y explora su distribución por cosecha.")
    if dashboard_tab.open:
        st.button(
            "Ver demostración de fraude",
            key="dashboard_fraud_demo",
            on_click=select_view,
            args=("Fraude (demo)",),
            help="Abrir la demostración con datos inventados; no detecta fraude real.",
        )
        try:
            cohorts = load_dashboard_cohorts(chroma_path)
            if not cohorts:
                st.info("No hay datos agregados disponibles para el panel.")
                st.stop()

            segment_filters: dict[str, str] = {}
            dimensions = load_dashboard_dimensions(chroma_path)
            with st.container(border=True):
                st.markdown("#### :material/tune: Segmentos")
                st.caption("Elige producto, canal o estrategia para acotar la vista.")
                segment_columns = st.columns(3)
                for column, (name, label) in zip(segment_columns, (
                    ("product", "Producto"), ("channel", "Canal"), ("strategy", "Estrategia"),
                )):
                    with column:
                        selected = st.selectbox(
                            label, options=[None, *dimensions[name]],
                            format_func=lambda value: "Todos" if value is None else value,
                            key=f"dashboard_segment_{name}",
                        )
                    if selected is not None:
                        segment_filters[name] = selected
            if segment_filters:
                cohorts = load_dashboard_cohorts(chroma_path, tuple(sorted(segment_filters.items())))
                if not cohorts:
                    st.warning("No hay datos para la combinación de segmentos seleccionada.")
                    st.stop()

            with st.container(border=True):
                st.markdown("#### :material/filter_alt: Ajusta la vista")
                left, right = st.columns(2)
                with left:
                    selected_metric = st.selectbox(
                        "Indicador",
                        options=list(KPI_LABELS),
                        format_func=lambda metric: KPI_LABELS[metric],
                        key="dashboard_metric",
                    )
                    vintage = st.selectbox(
                        "Cosecha",
                        options=[None, *sorted({row["vintage"] for row in cohorts})],
                        format_func=lambda value: "Todas" if value is None else str(value),
                        key="dashboard_vintage",
                    )
                with right:
                    mob = st.selectbox(
                        "Mes en libros (MOB)",
                        options=[
                            None,
                            *sorted({
                                row["mob"] for row in cohorts
                                if vintage is None or row["vintage"] == vintage
                            }),
                        ],
                        format_func=lambda value: "Todos" if value is None else str(value),
                        key="dashboard_mob",
                    )
                    descending = st.selectbox(
                        "Orden de cosechas",
                        options=[True, False],
                        format_func=lambda highest_first: (
                            "Mayor a menor" if highest_first else "Menor a mayor"
                        ),
                        key="dashboard_order",
                    )

            selected_rows = [
                row for row in cohorts
                if (vintage is None or row["vintage"] == vintage)
                and (mob is None or row["mob"] == mob)
            ]
            kpi_result = combine_cohort_summaries(selected_rows)
            value = kpi_result["metrics"][selected_metric]
            accounts = kpi_result["measures"]["accounts"]
            st.markdown("#### Cartera seleccionada")
            st.caption(
                f"Cosecha: {vintage if vintage is not None else 'todas'} "
                f"| Mes en libros (MOB): {mob if mob is not None else 'todos'}"
            )
            kpi_column, account_column = st.columns(2)
            with kpi_column:
                with st.container(border=True, height="stretch"):
                    st.metric(
                        KPI_LABELS[selected_metric],
                        display_metric(value, selected_metric),
                    )
            with account_column:
                with st.container(border=True, height="stretch"):
                    st.metric("Cuentas analizadas", f"{accounts:,.0f}")
            if mob is None:
                st.caption(
                    "Las cuentas se suman entre meses en libros; no representan "
                    "necesariamente cuentas únicas."
                )

            coverage_gaps = []
            for cohort_vintage in sorted({row["vintage"] for row in cohorts}):
                observed = sorted({row["mob"] for row in cohorts if row["vintage"] == cohort_vintage})
                if any(right - left > 1 for left, right in zip(observed, observed[1:])):
                    coverage_gaps.append(cohort_vintage)
            if coverage_gaps:
                st.warning(f"Cosechas con meses intermedios faltantes: {', '.join(map(str, coverage_gaps[:10]))}.")
            minimum = None
            with st.expander("Calidad y cobertura de datos"):
                st.caption(
                    "La cobertura compara los meses intermedios observados por cosecha "
                    "dentro del segmento seleccionado; no identifica periodos faltantes fuera de ese rango."
                )
                if not coverage_gaps:
                    st.caption("No se encontraron huecos intermedios en los meses observados.")
                if st.checkbox("Definir mínimo de cuentas por cosecha", key="dashboard_minimum_enabled"):
                    minimum = st.number_input("Mínimo de cuentas por cosecha", min_value=1, value=1, step=1, key="dashboard_minimum")
                    if mob is None:
                        st.info("Selecciona un MOB para evaluar el mínimo: sumar meses no representa cuentas únicas.")
                st.caption(
                    "La revisión del CSV es manual y puede tardar. No verifica que el archivo coincida con los agregados."
                )
                if st.button("Revisar calidad del CSV local", key="dashboard_validate_csv"):
                    with st.spinner("Revisando el CSV local..."):
                        try:
                            st.session_state["dashboard_csv_quality"] = validate_local_csv()
                        except ValueError as error:
                            st.session_state.pop("dashboard_csv_quality", None)
                            st.error(str(error))
                if quality := st.session_state.get("dashboard_csv_quality"):
                    st.caption(
                        f"CSV: {quality['filas']:,} filas; {quality['filas_rechazadas']:,} rechazadas; "
                        f"{quality['duplicados_exactos']:,} duplicados exactos; "
                        f"{quality['cosechas_con_huecos_internos']:,} cosechas con huecos."
                    )
                    if quality["status"] != "checks_completed":
                        st.warning("La revisión del CSV encontró incidencias; consulta el detalle.")
                    st.json(display_trace_value(quality))
            small_cohorts = []
            if minimum is not None and mob is not None:
                small_cohorts = [
                    row for row in selected_rows if row["measures"]["accounts"] < minimum
                ]
                if small_cohorts:
                    details = ", ".join(
                        f'{row["vintage"]}: {row["measures"]["accounts"]:,.0f}'
                        for row in small_cohorts[:10]
                    )
                    st.warning(
                        f"Cosechas por debajo del mínimo configurado ({minimum:,} cuentas) "
                        f"en MOB {mob}: {details}. Se muestran hasta 10."
                    )

            st.markdown("#### Alertas de cartera por segmento")
            st.caption(
                "Comparación exploratoria entre segmentos de una misma cosecha y MOB; "
                "un valor atípico no indica fraude ni demuestra una causa."
            )
            if st.checkbox("Analizar alertas por segmento", key="dashboard_alerts_enabled"):
                alert_group = st.selectbox(
                    "Comparar segmentos por",
                    options=["product", "channel", "strategy"],
                    format_func=lambda name: {
                        "product": "Producto", "channel": "Canal", "strategy": "Estrategia",
                    }[name],
                    key="dashboard_alert_group",
                )
                alert_metric = st.selectbox(
                    "Indicador de alerta",
                    options=["delinquency_rate_amount", "delinquency_rate_accounts"],
                    format_func=lambda name: KPI_LABELS[name],
                    key="dashboard_alert_metric",
                )
                alert_minimum = st.number_input(
                    "Mínimo de cuentas por segmento",
                    min_value=1, value=None, step=1, key="dashboard_alert_minimum",
                    placeholder="Define un mínimo",
                )
                if vintage is None or mob is None:
                    st.info("Selecciona una cosecha y un MOB para comparar segmentos equivalentes.")
                elif alert_group in segment_filters:
                    st.info("Quita el filtro de la dimensión que quieres comparar.")
                elif alert_minimum is None:
                    st.info("Define el mínimo de cuentas para evaluar los segmentos.")
                else:
                    alert_filters = {**segment_filters, "vintage": vintage, "mob": mob}
                    alerts = load_portfolio_alerts(
                        chroma_path, alert_group, alert_metric,
                        tuple(sorted(alert_filters.items())), int(alert_minimum),
                    )
                    st.caption(
                        f"Cosecha {vintage}, MOB {mob}; filtros de segmento: "
                        f"{segment_filters or 'ninguno'}. Pares elegibles: {alerts['peer_count']}; "
                        f"excluidos por mínimo, denominador o valores inválidos: {alerts['excluded_count']}. "
                        "IQR con cuartiles por mitades ordenadas y límites Q1/Q3 ± 1.5 IQR; "
                        "sin umbral regulatorio. Los resultados dependen de la calidad y cobertura de los datos."
                    )
                    if alerts["status"] == "insufficient_peers":
                        st.info("Se requieren al menos cuatro segmentos elegibles para calcular alertas.")
                    elif alerts["status"] == "zero_iqr":
                        st.info("El IQR es cero; no se clasifican valores atípicos.")
                    else:
                        st.caption(
                            f"Q1: {alerts['q1']:.2%}; Q3: {alerts['q3']:.2%}; "
                            f"límites: {alerts['lower']:.2%} a {alerts['upper']:.2%}."
                        )
                        if alerts["peer_count"] < 8:
                            st.warning("Menos de ocho segmentos elegibles: resultado especialmente exploratorio.")
                        if not alerts["candidates"]:
                            st.info("No se encontraron segmentos fuera de los límites IQR.")
                        else:
                            st.dataframe(
                                [{
                                    "Segmento": row[alert_group],
                                    "Dirección": "Alta" if row["anomaly"] == "high" else "Baja",
                                    "Tasa": f"{row['metrics'][alert_metric]:.2%}",
                                    "Numerador": row["measures"][alerts["numerator"]],
                                    "Denominador": row["measures"][alerts["denominator"]],
                                    "Cuentas": row["measures"]["accounts"],
                                } for row in alerts["candidates"]],
                                hide_index=True, width="stretch",
                                alt="Alertas exploratorias de morosidad por segmento",
                            )
                            st.caption(
                                f"Numerador: {display_trace_value({alerts['numerator']: 0}).popitem()[0]}; "
                                f"denominador: {display_trace_value({alerts['denominator']: 0}).popitem()[0]}."
                            )

            dashboard_chat_slot = st.container()
            st.markdown("#### Evolución por mes en libros")
            st.caption(
                "Se muestran todos los meses disponibles para la cosecha seleccionada; "
                "el filtro MOB solo afecta a los indicadores de arriba. Si seleccionas "
                "todas las cosechas, cada línea representa una cosecha."
            )
            evolution_rows = [
                row for row in cohorts
                if vintage is None or row["vintage"] == vintage
            ]
            chart_data = [
                {
                    "MOB": row["mob"],
                    "Cosecha": str(row["vintage"]),
                    "Indicador": (
                        None if row["metrics"][selected_metric] is None
                        else row["metrics"][selected_metric]
                        * (1 if selected_metric in NON_PERCENTAGE_METRICS else 100)
                    ),
                    "Cuentas": row["measures"]["accounts"],
                }
                for row in evolution_rows
            ]
            data = alt.InlineData(values=chart_data)
            x = alt.X("MOB:Q", title="Mes en libros (MOB)", axis=alt.Axis(format="d"))
            color = alt.Color("Cosecha:N", title="Cosecha")
            left_chart, right_chart = st.columns(2)
            with left_chart:
                st.markdown(f"##### {KPI_LABELS[selected_metric]} por MOB")
                if any(row["Indicador"] is not None for row in chart_data):
                    unit = (
                        KPI_LABELS[selected_metric]
                        if selected_metric in NON_PERCENTAGE_METRICS
                        else f"{KPI_LABELS[selected_metric]} (puntos porcentuales)"
                    )
                    chart = alt.Chart(data, mark=alt.MarkDef(type="line", point=True)).encode(
                        x=x,
                        y=alt.Y("Indicador:Q", title=unit),
                        color=color,
                        tooltip=["Cosecha:N", "MOB:Q", "Indicador:Q"],
                    )
                    st.altair_chart(
                        chart,
                        width="stretch",
                        alt=f"{KPI_LABELS[selected_metric]} por mes en libros y cosecha",
                    )
                else:
                    st.info("Este indicador no tiene valores para las cosechas seleccionadas.")
            with right_chart:
                st.markdown("##### Cuentas por MOB")
                chart = alt.Chart(data, mark=alt.MarkDef(type="line", point=True)).encode(
                    x=x,
                    y=alt.Y("Cuentas:Q", title="Cuentas"),
                    color=color,
                    tooltip=["Cosecha:N", "MOB:Q", "Cuentas:Q"],
                )
                st.altair_chart(
                    chart,
                    width="stretch",
                    alt="Cuentas por mes en libros y cosecha",
                )
                st.caption("Las cuentas son observaciones por mes, no cuentas únicas acumuladas.")

            st.markdown("#### Comparar cosechas")
            comparison_vintages = st.multiselect(
                "Cosechas a comparar",
                options=sorted({row["vintage"] for row in cohorts}),
                key="dashboard_comparison_vintages",
                help="Selecciona al menos dos cosechas; la primera es la referencia.",
            )
            comparison_context: dict[str, Any] | None = None
            if len(comparison_vintages) >= 2:
                mobs_by_vintage = [
                    {row["mob"] for row in cohorts if row["vintage"] == cohort_vintage}
                    for cohort_vintage in comparison_vintages
                ]
                common_mobs = sorted(set.intersection(*mobs_by_vintage))
                if not common_mobs:
                    st.warning("Las cosechas seleccionadas no tienen meses en libros en común.")
                else:
                    default_mob = mob if mob in common_mobs else common_mobs[-1]
                    comparison_mob = st.selectbox(
                        "Mes en libros común",
                        common_mobs, index=common_mobs.index(default_mob),
                        key="dashboard_comparison_mob",
                    )
                    comparison_rows = [
                        next(row for row in cohorts if row["vintage"] == cohort_vintage and row["mob"] == comparison_mob)
                        for cohort_vintage in comparison_vintages
                    ]
                    reference = comparison_rows[0]["metrics"][selected_metric]
                    comparisons = []
                    for row in comparison_rows:
                        metric_value = row["metrics"][selected_metric]
                        delta = None if metric_value is None or reference is None else metric_value - reference
                        comparisons.append({
                            "cosecha": row["vintage"], "valor": metric_value,
                            "diferencia": delta, "cuentas": row["measures"]["accounts"],
                        })
                    delta_label = (
                        "Diferencia respecto a referencia"
                        if selected_metric in NON_PERCENTAGE_METRICS
                        else "Diferencia respecto a referencia (puntos porcentuales)"
                    )
                    st.caption(
                        f"Referencia: cosecha {comparison_vintages[0]}. Todas las filas usan "
                        f"el MOB {comparison_mob} y los filtros de segmento seleccionados."
                    )
                    st.dataframe(
                        [{
                            "Cosecha": row["cosecha"],
                            KPI_LABELS[selected_metric]: display_metric(row["valor"], selected_metric),
                            delta_label: (
                                "No disponible" if row["diferencia"] is None
                                else f'{row["diferencia"] * (1 if selected_metric in NON_PERCENTAGE_METRICS else 100):+.2f}'
                            ),
                            "Cuentas": row["cuentas"],
                        } for row in comparisons],
                        hide_index=True,
                        alt="Comparación de cosechas en el mismo mes en libros",
                    )
                    comparison_curve = [
                        {
                            "Mes en libros": row["mob"], "Cosecha": str(row["vintage"]),
                            "Indicador": (
                                None if row["metrics"][selected_metric] is None
                                else row["metrics"][selected_metric] * (
                                    1 if selected_metric in NON_PERCENTAGE_METRICS else 100
                                )
                            ),
                        }
                        for row in cohorts
                        if row["vintage"] in comparison_vintages
                    ]
                    if any(row["Indicador"] is not None for row in comparison_curve):
                        st.line_chart(
                            comparison_curve, x="Mes en libros", y="Indicador", color="Cosecha",
                            alt="Evolución del indicador para las cosechas seleccionadas",
                        )
                    comparison_context = {
                        "mes_en_libros": comparison_mob, "referencia": comparison_vintages[0],
                        "resultados": comparisons,
                        "alcance": "Mismo MOB y segmentos seleccionados; la gráfica usa todos los MOB disponibles.",
                    }

            rankings = [
                {
                    "vintage": cohort_vintage,
                    **combine_cohort_summaries([
                        row for row in cohorts if row["vintage"] == cohort_vintage
                    ]),
                }
                for cohort_vintage in sorted({row["vintage"] for row in cohorts})
            ]
            rankings = sorted(
                (row for row in rankings if row["metrics"][selected_metric] is not None),
                key=lambda row: row["metrics"][selected_metric],
                reverse=descending,
            )[:10]
            try:
                dashboard_excel = build_dashboard_excel(
                    KPI_LABELS[selected_metric], value, accounts, vintage, mob,
                    evolution_rows, rankings, selected_metric,
                    selected_metric not in NON_PERCENTAGE_METRICS, segment_filters,
                )
                st.download_button(
                    "Descargar Excel del panel",
                    data=dashboard_excel,
                    file_name="obsagent-panel.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dashboard_excel",
                    on_click="ignore",
                    help="Borrador no verificado; no incluye la comparación interactiva de cosechas.",
                )
            except ValueError as error:
                st.error(f"No se pudo preparar el Excel del panel: {error}")
            st.markdown("#### Clasificación de cosechas")
            st.caption(
                "Las 10 principales cosechas en todos los meses en libros. Los filtros "
                "de cosecha y MOB no afectan a esta clasificación; los de segmento sí."
            )
            if not rankings:
                st.info("No hay resultados de cosechas para este indicador.")
            else:
                table_rows = [
                    {
                        "Cosecha": row["vintage"],
                        KPI_LABELS[selected_metric]: display_metric(
                            row["metrics"][selected_metric], selected_metric
                        ),
                        "Cuentas": f'{row["measures"]["accounts"]:,.0f}',
                    }
                    for row in rankings
                ]
                st.dataframe(table_rows, width="stretch", hide_index=True)

                chart_values = [
                    {
                        "Cosecha": str(row["vintage"]),
                        KPI_LABELS[selected_metric]: (
                            row["metrics"][selected_metric]
                            if selected_metric in NON_PERCENTAGE_METRICS
                            else row["metrics"][selected_metric] * 100
                        ),
                    }
                    for row in rankings
                    if row["metrics"][selected_metric] is not None
                ]
                if chart_values:
                    st.markdown(f"##### {KPI_LABELS[selected_metric]} por cosecha")
                    st.bar_chart(
                        chart_values,
                        x="Cosecha",
                        y=KPI_LABELS[selected_metric],
                        color="#005A9C",
                        alt=f'{KPI_LABELS[selected_metric]} por cosecha',
                    )
                    st.caption(
                        "Los indicadores porcentuales se muestran en puntos porcentuales; "
                        "los monetarios conservan sus unidades originales."
                    )
            dashboard_context = {
                "indicador": KPI_LABELS[selected_metric],
                "metric": selected_metric,
                "segmentos": segment_filters,
                "comparacion": comparison_context,
                "calidad": {
                    "cosechas_con_huecos_internos": coverage_gaps[:10],
                    "total_cosechas_con_huecos": len(coverage_gaps),
                    "minimo_de_cuentas": minimum,
                    "mes_en_libros": mob,
                    "cosechas_bajo_minimo": [
                        {"cosecha": row["vintage"], "cuentas": row["measures"]["accounts"]}
                        for row in small_cohorts[:10]
                    ],
                    "total_cosechas_bajo_minimo": len(small_cohorts),
                    "alcance": "Huecos dentro de los meses observados del segmento; mínimo solo con MOB seleccionado.",
                    "revision_csv": (
                        {
                            "estado": quality["status"], "filas": quality["filas"],
                            "filas_rechazadas": quality["filas_rechazadas"],
                            "duplicados_exactos": quality["duplicados_exactos"],
                            "cosechas_con_huecos_internos": quality["cosechas_con_huecos_internos"],
                            "alcance": "CSV local completo, sin validar correspondencia con los agregados.",
                        }
                        if quality else None
                    ),
                },
                "unidad": "valor monetario" if selected_metric in NON_PERCENTAGE_METRICS else "proporción (1 = 100%)",
                "resumen": {
                    "cosecha": vintage,
                    "mes_en_libros": mob,
                    "valor": value,
                    "cuentas": accounts,
                    "alcance": "Cosecha y MOB seleccionados; null significa todos. Las cuentas entre meses no son necesariamente únicas.",
                },
                "evolucion": {
                    "cosecha": vintage,
                    "alcance": "Todos los MOB de la cosecha seleccionada, o de todas si es null; el filtro MOB no aplica. Consultar los puntos mediante herramientas.",
                },
                "clasificacion": {
                    "orden": "mayor a menor" if descending else "menor a mayor",
                    "alcance": "Hasta 10 cosechas; todos los MOB y cosechas, sin aplicar los filtros seleccionados de cosecha y MOB; sí aplican los filtros de segmento.",
                    "resultados": [
                        {"cosecha": row["vintage"], "valor": row["metrics"][selected_metric],
                         "cuentas": row["measures"]["accounts"]}
                        for row in rankings
                    ],
                },
            }
            with dashboard_chat_slot:
                st.markdown("#### Pregúntale a ObsAgent sobre esta vista")
                st.caption(
                    "Se envían al servidor Ollama configurado los filtros, el indicador, "
                    "la comparación, la clasificación y los avisos visibles. La evolución completa se consulta con "
                    "herramientas cuando sea necesaria."
                )
                render_conversation(
                    service, "dashboard_messages", dashboard_context=dashboard_context, source_path=chroma_path
                )
        except (
            RuntimeError,
            ValueError,
            KeyError,
            requests.exceptions.RequestException,
        ) as error:
            show_error(error)
