"""Streamlit chat and portfolio dashboard for ObsAgent."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import altair as alt
import requests
import streamlit as st

from ChromaDB.precomputed_queries import combine_cohort_summaries
from multi_agent_framework.agent_manager import DEFAULT_CHROMA_PATH
from multi_agent_framework.draft_report import build_draft_pdf
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
def load_dashboard_cohorts(chroma_path: str) -> list[dict[str, Any]]:
    return asyncio.run(get_service(chroma_path).get_dashboard_cohorts())


def display_metric(value: float | int | None, metric: str) -> str:
    if value is None:
        return "No disponible"
    if metric in NON_PERCENTAGE_METRICS:
        return f"{value:,.2f}"
    return f"{value:.2%}"


def render_response_chart(chart: dict[str, Any]) -> None:
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


def render_trace(trace: dict[str, Any]) -> None:
    calls = trace["tool_results"]
    errors = [
        call for call in calls
        if isinstance(call.get("result"), dict) and "error" in call["result"]
    ]
    if errors:
        st.warning(
            "Una o más llamadas a herramientas devolvieron un error. "
            "Revisa la trazabilidad antes de usar la respuesta."
        )
    if calls and all(call.get("tool") == "consultar_skill" for call in calls):
        st.warning(
            "Solo se consultaron guías; no se obtuvieron datos de cartera "
            "ni se verificó la respuesta."
        )
    with st.expander("Cómo se obtuvo esta respuesta"):
        if trace["translation_used"]:
            st.markdown("**Consulta enviada después de traducción**")
            st.text(trace["translated_query"])
        else:
            st.caption("Traducción previa desactivada para esta consulta.")
        if not calls:
            st.info("El modelo no llamó a ninguna herramienta en esta respuesta.")
        for index, call in enumerate(calls, start=1):
            st.markdown(f"**{index}. {call.get('tool') or 'Herramienta desconocida'}**")
            if "arguments" in call:
                st.caption("Argumentos solicitados")
                st.json(call["arguments"])
            if isinstance(call.get("result"), dict) and "error" in call["result"]:
                st.error(str(call["result"]["error"]))
            else:
                st.caption("Resultado devuelto al modelo")
                st.json(call["result"])
        st.caption("La trazabilidad pertenece a esta sesión y no se guarda en la base.")


def render_draft_download(
    question: str, answer: str, trace: dict[str, Any], index: int
) -> None:
    try:
        pdf = build_draft_pdf(question, answer, trace)
    except ValueError as error:
        st.error(f"No se pudo preparar el PDF de prueba: {error}")
        return
    st.download_button(
        "Descargar PDF de prueba",
        data=pdf,
        file_name="obsagent-borrador.pdf",
        mime="application/pdf",
        key=f"draft_pdf_{index}",
        on_click="ignore",
        help="Borrador no verificado; requiere revisión humana.",
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


st.set_page_config(page_title="ObsAgent | Análisis de cartera", layout="wide")
st.markdown(
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
    """,
    unsafe_allow_html=True,
)

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
    translate_prompt = st.toggle(
        "Traducir consulta antes de analizar",
        value=False,
        key="translate_prompt",
        help=(
            "Usa una llamada adicional a Ollama para traducir al español. "
            "Puede aumentar el tiempo de respuesta."
        ),
    )
    with st.expander("Configuración de conexión"):
        st.caption("Configura Ollama con CHAT_MODEL y OLLAMA_BASE_URL en .env.")

try:
    service = get_service(chroma_path)
except (RuntimeError, ValueError, requests.exceptions.RequestException) as error:
    show_error(error)
    st.stop()

home_tab, chat_tab, dashboard_tab, capabilities_tab = st.tabs(
    ["Inicio", "Conversar con ObsAgent", "Panel de cartera", "Cómo funciona"],
    on_change="rerun",
    key="obsagent_tabs",
)

with home_tab:
    st.subheader("Tu espacio de inteligencia de cartera")
    st.caption(
        "Explora indicadores, plantea preguntas y revisa cómo se obtuvo cada respuesta."
    )
    explore, ask, inspect = st.columns(3)
    with explore:
        with st.container(border=True):
            st.markdown("### :material/monitoring: Explora la cartera")
            st.caption(
                "Consulta indicadores, compara cosechas y visualiza su distribución."
            )
            st.button(
                "Abrir panel",
                key="home_dashboard",
                on_click=select_view,
                args=("Panel de cartera",),
                width="stretch",
            )
    with ask:
        with st.container(border=True):
            st.markdown("### :material/forum: Pregunta al agente")
            st.caption(
                "Analiza segmentos y cosechas con herramientas de cálculo validadas."
            )
            st.button(
                "Iniciar análisis",
                key="home_chat",
                on_click=select_view,
                args=("Conversar con ObsAgent",),
                width="stretch",
            )
    with inspect:
        with st.container(border=True):
            st.markdown("### :material/fact_check: Entiende el proceso")
            st.caption(
                "Conoce las herramientas disponibles y los límites del flujo actual."
            )
            st.button(
                "Ver capacidades",
                key="home_capabilities",
                on_click=select_view,
                args=("Cómo funciona",),
                width="stretch",
            )
    st.caption(
        "El panel consulta agregados locales. El chat requiere Ollama; "
        "los tiempos dependen del modelo y del volumen consultado."
    )

with chat_tab:
    st.subheader("Analiza tu cartera en español")
    st.caption(
        "Consulta indicadores, compara vintages o explora segmentos. "
        "ObsAgent usa el modelo de Ollama configurado y tus datos locales."
    )
    if "obsagent_messages" not in st.session_state:
        st.session_state.obsagent_messages = []

    if not st.session_state.obsagent_messages:
        st.info(
            "Empieza con una pregunta, por ejemplo: "
            "«¿Qué cosechas tienen la mayor tasa de morosidad?»"
        )

    if st.button("Borrar conversación", key="clear_conversation"):
        st.session_state.obsagent_messages = []

    for index, message in enumerate(st.session_state.obsagent_messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if chart := message.get("chart"):
                render_response_chart(chart)
            if trace := message.get("trace"):
                render_trace(trace)
                question = message.get("question")
                if question is None and index > 0:
                    question = st.session_state.obsagent_messages[index - 1]["content"]
                render_draft_download(question or "", message["content"], trace, index)

    prompt = st.chat_input(
        "Por ejemplo: Compara cosechas recientes por tasa de morosidad"
    )
    if prompt:
        st.session_state.obsagent_messages.append(
            {"role": "user", "content": prompt}
        )
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analizando tu consulta y preparando la respuesta..."):
                try:
                    prior_messages = st.session_state.obsagent_messages[:-1][-2:]
                    if prior_messages:
                        history = "\n".join(
                            f'{("Usuario" if message["role"] == "user" else "Asistente")}: '
                            f'{message["content"]}'
                            for message in prior_messages
                        )
                        request = (
                            "Conversación hasta ahora:\n"
                            f"{history}\n\n"
                            f"Última consulta del usuario: {prompt}"
                        )
                    else:
                        request = prompt
                    result = asyncio.run(
                        service.query(request, translate=translate_prompt)
                    )
                    answer = result["final_answer"]
                    if not answer:
                        st.warning("El agente no generó una respuesta.")
                    else:
                        st.markdown(answer)
                        chart = build_response_chart(
                            result.get("research_findings", {}).get(
                                "tool_results", []
                            ),
                            prompt,
                            KPI_LABELS,
                            NON_PERCENTAGE_METRICS,
                        )
                        if chart:
                            render_response_chart(chart)
                        trace = {
                            "translation_used": result["translation_used"],
                            "translated_query": result["translated_query"],
                            "tool_results": result["research_findings"]["tool_results"],
                        }
                        render_trace(trace)
                        st.session_state.obsagent_messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                                "question": prompt,
                                "chart": chart,
                                "trace": trace,
                            }
                        )
                        render_draft_download(
                            prompt, answer, trace, len(st.session_state.obsagent_messages) - 1
                        )
                except (
                    RuntimeError,
                    ValueError,
                    KeyError,
                    requests.exceptions.RequestException,
                ) as error:
                    show_error(error)

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
                        st.markdown(f"**`{tool['name']}`**")
                        st.caption(tool["description"])
    with right:
                with st.container(border=True):
                    st.markdown("### :material/translate: Traducción")
                    st.write(
                        "Puedes activar la traducción previa en la barra lateral. "
                        "Añade una llamada al modelo y la consulta resultante aparece "
                        "en la trazabilidad."
                    )
                    st.markdown("### :material/menu_book: Skills del repositorio")
                    st.write(
                        "El agente puede consultar estas guías durante una respuesta. "
                        "Consultar una guía no implementa ni ejecuta sus acciones. "
                        "El contenido consultado se envía al servidor Ollama configurado."
                    )
                    if capabilities_tab.open:
                        for skill in available_skill_guides():
                            state = {
                                "guide_only": "guía disponible; ejecución no garantizada",
                                "empty": "guía vacía",
                                "missing": "guía ausente",
                            }[skill["status"]]
                            st.caption(f'{skill["name"]}: {state}')
                    st.markdown("### :material/shield: Límites")
                    st.write(
                        "El modelo puede equivocarse, elegir una herramienta incorrecta "
                        "o responder sin usar ninguna. Comprueba los argumentos, "
                        "resultados y errores antes de tomar decisiones."
                    )

with dashboard_tab:
    st.subheader("Resumen de cartera")
    st.caption("Selecciona un indicador y explora su distribución por vintage.")
    if dashboard_tab.open:
        try:
            cohorts = load_dashboard_cohorts(chroma_path)
            if not cohorts:
                st.info("No hay datos agregados disponibles para el panel.")
                st.stop()

            with st.container(border=True):
                st.markdown("#### Ajusta la vista")
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
                with st.container(border=True):
                    st.metric(
                        KPI_LABELS[selected_metric],
                        display_metric(value, selected_metric),
                    )
            with account_column:
                with st.container(border=True):
                    st.metric("Cuentas analizadas", f"{accounts:,.0f}")
            if mob is None:
                st.caption(
                    "Las cuentas se suman entre meses en libros; no representan "
                    "necesariamente cuentas únicas."
                )

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
            st.markdown("#### Ranking de cosechas")
            st.caption(
                "Las 10 principales cosechas en todos los meses en libros. Los filtros "
                "de cosecha y MOB no afectan a este ranking."
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
                        color="#18B9AA",
                        alt=f'{KPI_LABELS[selected_metric]} por cosecha',
                    )
                    st.caption(
                        "Los indicadores porcentuales se muestran en puntos porcentuales; "
                        "los monetarios conservan sus unidades originales."
                    )
        except (
            RuntimeError,
            ValueError,
            KeyError,
            requests.exceptions.RequestException,
        ) as error:
            show_error(error)
