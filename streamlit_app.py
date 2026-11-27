"""Streamlit chat and portfolio dashboard for ObsAgent."""

from __future__ import annotations

import asyncio
import os

import altair as alt
import pandas as pd
import requests
import streamlit as st

from multi_agent_framework.agent_manager import DEFAULT_CHROMA_PATH
from multi_agent_framework.query_service import KPIType, QueryService


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


def display_metric(value: float | int | None, metric: str) -> str:
    if value is None:
        return "No disponible"
    if metric in NON_PERCENTAGE_METRICS:
        return f"${value:,.2f}"
    return f"{value:.2%}"


def show_error(error: Exception) -> None:
    st.error(str(error))
    if isinstance(error, requests.exceptions.RequestException):
        st.caption(
            "Verifica que Ollama esté disponible y que la URL y el modelo "
            "configurados sean correctos."
        )
    elif isinstance(error, RuntimeError) and "colección" in str(error).lower():
        st.caption(
            "Prepara las colecciones de origen y agregados siguiendo "
            "ChromaDB/README.md."
        )


st.set_page_config(
    page_title="Banamex | ObsAgent · Análisis de Cartera",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    :root {
        --bnx-red: #E6003C;
        --bnx-navy-dark: #071522;
        --bnx-navy: #0B2030;
        --bnx-teal: #18B9AA;
        --bnx-mint: #53E8C8;
        --bnx-bg: #F4F7F8;
        --bnx-surface: #FFFFFF;
        --bnx-text: #0B2030;
        --bnx-muted: #5C6F7E;
        --bnx-border: #E2E8ED;
    }

    /* Forzar tema claro y alto contraste */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stHeader"] {
        background-color: var(--bnx-bg) !important;
        color: var(--bnx-text) !important;
    }

    [data-testid="stMain"] .block-container {
        padding-top: 2.25rem !important;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--bnx-text);
    }

    h1, h2, h3, h4, h5, .obs-hero__wordmark {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Barra lateral oscura */
    section[data-testid="stSidebar"] {
        background-color: var(--bnx-navy-dark) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    section[data-testid="stSidebar"] * {
        color: #E2ECEA !important;
    }
    section[data-testid="stSidebar"] .stTextInput input {
        background-color: #0F2537 !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 10px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: #0B2030 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }

    /* Inputs y contenedores principales */
    [data-testid="stMain"] .stSelectbox > div > div,
    [data-testid="stMain"] .stNumberInput input,
    [data-testid="stMain"] .stTextInput input {
        background-color: #FFFFFF !important;
        color: var(--bnx-navy-dark) !important;
        border: 1px solid var(--bnx-border) !important;
        border-radius: 10px !important;
    }
    [data-testid="stMain"] label,
    [data-testid="stMain"] p,
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4,
    [data-testid="stMain"] h5 {
        color: var(--bnx-text);
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid var(--bnx-border) !important;
        border-radius: 16px !important;
        box-shadow: 0 2px 12px rgba(7, 21, 34, 0.03) !important;
    }

    /* Hero Banner */
    .obs-hero {
        background:
            radial-gradient(circle at 88% 20%, rgba(24, 185, 170, 0.24), transparent 42%),
            radial-gradient(circle at 96% 85%, rgba(230, 0, 60, 0.25), transparent 38%),
            linear-gradient(125deg, #071522 0%, #0B2030 58%, #103242 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 22px;
        color: #FFFFFF;
        padding: 2rem 2.4rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 18px 40px rgba(7, 21, 34, 0.12);
        display: grid;
        grid-template-columns: 1.65fr 1fr;
        gap: 2rem;
        align-items: center;
    }
    @media (max-width: 900px) {
        .obs-hero {
            grid-template-columns: 1fr;
        }
    }
    .obs-hero__brand {
        align-items: center;
        display: flex;
        gap: 0.65rem;
        margin-bottom: 0.9rem;
    }
    .obs-hero__logo {
        height: 1.6rem;
        width: 1.6rem;
    }
    .obs-hero__wordmark {
        color: #FFFFFF !important;
        font-size: 0.95rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }
    .obs-hero__divider {
        background: rgba(255, 255, 255, 0.28);
        height: 1rem;
        margin: 0 0.2rem;
        width: 1px;
    }
    .obs-hero__product {
        color: #CBE0DC !important;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .obs-hero h1 {
        color: #FFFFFF !important;
        font-size: clamp(1.9rem, 3.3vw, 2.7rem) !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        line-height: 1.1 !important;
        margin: 0 0 0.7rem 0 !important;
    }
    .obs-hero__accent {
        color: var(--bnx-mint) !important;
    }
    .obs-hero p {
        color: #C3D4DC !important;
        font-size: 0.94rem;
        line-height: 1.5;
        margin: 0;
        max-width: 38rem;
    }
    .obs-hero__glass {
        background: rgba(255, 255, 255, 0.06);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 16px;
        padding: 1.25rem 1.4rem;
    }
    .obs-hero__glass-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .obs-hero__glass-title {
        color: #A7BFC9 !important;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .obs-hero__live-pill {
        background: rgba(83, 232, 200, 0.16);
        color: var(--bnx-mint) !important;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
    }
    .obs-hero__glass-metric {
        color: #FFFFFF !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }
    .obs-hero__glass-sub {
        color: #8FAAB7 !important;
        font-size: 0.78rem;
        margin-top: 0.35rem;
    }

    /* Marca en barra lateral */
    .obs-sidebar__brand {
        align-items: center;
        display: flex;
        gap: 0.6rem;
        margin-bottom: 0.25rem;
    }
    .obs-sidebar__logo {
        height: 1.65rem;
        width: 1.65rem;
    }
    .obs-sidebar__wordmark {
        color: #FFFFFF !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.15rem;
        font-weight: 800;
    }
    .obs-sidebar__product {
        color: #8CA3B5 !important;
        font-size: 0.78rem;
        margin-left: 2.25rem;
    }
    .obs-sidebar__status {
        background: rgba(24, 185, 170, 0.12);
        border: 1px solid rgba(24, 185, 170, 0.28);
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        margin-top: 1.25rem;
    }
    .obs-sidebar__status-title {
        color: #53E8C8 !important;
        font-size: 0.78rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }
    .obs-sidebar__dot {
        height: 7px;
        width: 7px;
        background-color: #53E8C8;
        border-radius: 50%;
        display: inline-block;
    }
    .obs-sidebar__status-sub {
        color: #9EB3C2 !important;
        font-size: 0.72rem;
        margin-top: 0.2rem;
    }

    /* Pestañas con contraste corregido en activo e inactivo */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        background-color: #FFFFFF !important;
        padding: 0.4rem;
        border-radius: 12px;
        border: 1px solid var(--bnx-border);
        margin-bottom: 1.25rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 2.5rem;
        border-radius: 8px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 700;
        font-size: 0.88rem;
        background-color: transparent !important;
        padding: 0 1.25rem;
        border: none !important;
    }
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span {
        color: var(--bnx-muted) !important;
        font-weight: 700 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--bnx-navy-dark) !important;
    }
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] span {
        color: #FFFFFF !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }

    /* Tarjetas de métricas */
    .bnx-stat-card {
        background: #FFFFFF;
        border: 1px solid var(--bnx-border);
        border-top: 3px solid var(--bnx-red);
        border-radius: 14px;
        padding: 1.2rem 1.35rem;
        box-shadow: 0 2px 10px rgba(7, 21, 34, 0.03);
    }
    .bnx-stat-card--teal {
        border-top-color: var(--bnx-teal);
    }
    .bnx-stat-card--navy {
        border-top-color: var(--bnx-navy);
    }
    .bnx-stat-label {
        color: var(--bnx-muted) !important;
        font-size: 0.76rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    .bnx-stat-val {
        color: var(--bnx-navy-dark) !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }
    .bnx-stat-foot {
        color: var(--bnx-muted) !important;
        font-size: 0.75rem;
        margin-top: 0.45rem;
    }

    /* Tarjetas de hallazgos */
    .bnx-insight {
        border-radius: 12px;
        padding: 0.95rem 1.15rem;
        margin-bottom: 0.75rem;
        border: 1px solid var(--bnx-border);
        background: #F9FBFC;
    }
    .bnx-insight--alert {
        background: #FFF6F8;
        border-color: #FAD1DC;
    }
    .bnx-insight--positive {
        background: #F2FBF9;
        border-color: #C7EFE7;
    }
    .bnx-insight-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.3rem;
    }
    .bnx-insight-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.86rem;
        font-weight: 700;
        color: var(--bnx-navy-dark) !important;
    }
    .bnx-pill-high {
        background: #FDE2E8;
        color: #B5002F !important;
        font-size: 0.65rem;
        font-weight: 800;
        padding: 0.15rem 0.5rem;
        border-radius: 6px;
        letter-spacing: 0.05em;
    }
    .bnx-pill-pos {
        background: #D6F5EE;
        color: #0D7A6E !important;
        font-size: 0.65rem;
        font-weight: 800;
        padding: 0.15rem 0.5rem;
        border-radius: 6px;
        letter-spacing: 0.05em;
    }
    .bnx-insight-body {
        font-size: 0.8rem;
        color: var(--bnx-muted) !important;
        line-height: 1.45;
    }

    /* Botones */
    .stButton > button {
        border-radius: 10px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 600;
        font-size: 0.82rem;
        border: 1px solid var(--bnx-border);
        background-color: #FFFFFF !important;
        color: var(--bnx-navy-dark) !important;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: var(--bnx-teal);
        background-color: #F2FBF9 !important;
    }

    /* Mensajes y caja de chat */
    [data-testid="stChatMessage"] {
        background-color: #FFFFFF !important;
        border: 1px solid var(--bnx-border) !important;
        border-radius: 14px !important;
        padding: 1rem 1.25rem !important;
    }
    [data-testid="stChatInput"] textarea {
        background-color: #FFFFFF !important;
        color: var(--bnx-navy-dark) !important;
    }
    </style>

    <header class="obs-hero">
        <div>
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
                <span class="obs-hero__product">ObsAgent · Panorama de Cartera</span>
            </div>
            <h1>Claridad para decidir. <span class="obs-hero__accent">Inteligencia para actuar.</span></h1>
            <p>ObsAgent transforma señales financieras y agregados de cosechas en hallazgos claros, trazables y listos para convertir en acción.</p>
        </div>
        <div class="obs-hero__glass">
            <div class="obs-hero__glass-header">
                <span class="obs-hero__glass-title">Centro de Inteligencia</span>
                <span class="obs-hero__live-pill">DATOS VERIFICADOS</span>
            </div>
            <div class="obs-hero__glass-metric">ObsAgent IA</div>
            <div class="obs-hero__glass-sub">Monitoreo continuo de cosechas, riesgo crediticio y margen operativo.</div>
        </div>
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
        <div class="obs-sidebar__product">ObsAgent · Inteligencia de Cartera</div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("##### Fuentes de datos")
    chroma_path = st.text_input(
        "Directorio de ChromaDB",
        value=default_path,
        help="Directorio con base_cards_sintetica y su colección de agregados.",
    )
    st.caption("Usa un directorio local de ChromaDB con las colecciones requeridas.")
    with st.expander("Configuración de conexión"):
        st.caption("Configura Ollama con CHAT_MODEL y OLLAMA_BASE_URL en .env.")

    st.markdown(
        """
        <div class="obs-sidebar__status">
            <div class="obs-sidebar__status-title">
                <span class="obs-sidebar__dot"></span> Sistemas operativos
            </div>
            <div class="obs-sidebar__status-sub">Colecciones locales conectadas</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

try:
    service = get_service(chroma_path)
except (RuntimeError, ValueError, requests.exceptions.RequestException) as error:
    show_error(error)
    st.stop()

chat_tab, dashboard_tab = st.tabs(["Conversar con ObsAgent", "Panel de Cartera"])

with chat_tab:
    col_title, col_clear = st.columns([4.5, 1])
    with col_title:
        st.markdown("### Asistente Analítico de Cartera")
        st.caption(
            "Consulta indicadores, compara cosechas o explora segmentos usando el modelo configurado."
        )
    with col_clear:
        st.write("")
        if st.button("Borrar conversación", key="clear_conversation", use_container_width=True):
            st.session_state.obsagent_messages = []
            st.rerun()

    if "obsagent_messages" not in st.session_state:
        st.session_state.obsagent_messages = []

    sample_prompts = [
        "¿Qué cosechas tienen la mayor tasa de morosidad?",
        "Compara el índice de eficiencia entre las cosechas recientes",
        "¿Cuál es la evolución del margen operativo por cosecha?",
    ]

    selected_sample = None
    if not st.session_state.obsagent_messages:
        st.markdown("##### Consultas sugeridas")
        q_cols = st.columns(3)
        for idx, sample in enumerate(sample_prompts):
            with q_cols[idx]:
                if st.button(sample, key=f"sample_{idx}", use_container_width=True):
                    selected_sample = sample

    for message in st.session_state.obsagent_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    chat_input_prompt = st.chat_input(
        "Por ejemplo: Compara cosechas recientes por tasa de morosidad"
    )
    prompt = selected_sample or chat_input_prompt

    if prompt:
        st.session_state.obsagent_messages.append(
            {"role": "user", "content": prompt}
        )
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analizando tu consulta y preparando la respuesta..."):
                try:
                    prior_messages = st.session_state.obsagent_messages[:-1][-8:]
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
                    result = asyncio.run(service.query(request))
                    answer = result["final_answer"]
                    if not answer:
                        st.warning("El agente no generó una respuesta.")
                    else:
                        st.markdown(answer)
                        st.session_state.obsagent_messages.append(
                            {"role": "assistant", "content": answer}
                        )
                except (
                    RuntimeError,
                    ValueError,
                    KeyError,
                    requests.exceptions.RequestException,
                ) as error:
                    show_error(error)

with dashboard_tab:
    with st.container(border=True):
        st.markdown("#### Filtros de Cartera")
        f_col1, f_col2, f_col3, f_col4 = st.columns([2.1, 1.1, 1.1, 1.3])
        with f_col1:
            selected_metric = st.selectbox(
                "Indicador",
                options=list(KPI_LABELS),
                format_func=lambda metric: KPI_LABELS[metric],
            )
        with f_col2:
            vintage_input = st.number_input(
                "Cosecha (0 = todas)",
                min_value=0,
                max_value=999999,
                value=0,
                step=1,
            )
        with f_col3:
            mob_input = st.number_input(
                "Mes en libros (0 = todos)",
                min_value=0,
                max_value=999,
                value=0,
                step=1,
            )
        with f_col4:
            descending = st.selectbox(
                "Orden de cosechas",
                options=[True, False],
                format_func=lambda highest_first: (
                    "Mayor a menor" if highest_first else "Menor a mayor"
                ),
            )

    vintage = int(vintage_input) or None
    mob = int(mob_input) or None
    is_monetary = selected_metric in NON_PERCENTAGE_METRICS

    try:
        kpi_result = asyncio.run(
            service.query_kpi(
                selected_metric,
                vintage=vintage,
                mob=mob,
            )
        )
        value = kpi_result["value"]
        accounts = kpi_result["measures"]["accounts"]

        secondary_metric = (
            KPIType.OPERATING_MARGIN_RATE.value
            if selected_metric != KPIType.OPERATING_MARGIN_RATE.value
            else KPIType.DELINQUENCY_RATE.value
        )
        secondary_result = asyncio.run(
            service.query_kpi(
                secondary_metric,
                vintage=vintage,
                mob=mob,
            )
        )
        secondary_value = secondary_result["value"]

        rankings = asyncio.run(
            service.get_vintage_ranking(
                sort_metric=selected_metric,
                descending=descending,
                top_n=12,
            )
        )

        valid_rankings = [
            r for r in rankings if r["metrics"].get(selected_metric) is not None
        ]
        avg_val = (
            sum(r["metrics"][selected_metric] for r in valid_rankings) / len(valid_rankings)
            if valid_rankings
            else None
        )

        vintage_label = f"Cosecha {vintage}" if vintage is not None else "Todas las cosechas"
        mob_label = f"Mes {mob}" if mob is not None else "Todos los meses"

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(
                f"""
                <div class="bnx-stat-card">
                    <div class="bnx-stat-label">{KPI_LABELS[selected_metric]}</div>
                    <div class="bnx-stat-val">{display_metric(value, selected_metric)}</div>
                    <div class="bnx-stat-foot">{vintage_label} · {mob_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m_col2:
            st.markdown(
                f"""
                <div class="bnx-stat-card bnx-stat-card--teal">
                    <div class="bnx-stat-label">{KPI_LABELS[secondary_metric]}</div>
                    <div class="bnx-stat-val">{display_metric(secondary_value, secondary_metric)}</div>
                    <div class="bnx-stat-foot">Indicador complementario</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m_col3:
            st.markdown(
                f"""
                <div class="bnx-stat-card bnx-stat-card--navy">
                    <div class="bnx-stat-label">Cuentas analizadas</div>
                    <div class="bnx-stat-val">{accounts:,.0f}</div>
                    <div class="bnx-stat-foot">Bajo filtro activo</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m_col4:
            st.markdown(
                f"""
                <div class="bnx-stat-card bnx-stat-card--teal">
                    <div class="bnx-stat-label">Promedio grupo mostrado</div>
                    <div class="bnx-stat-val">{display_metric(avg_val, selected_metric)}</div>
                    <div class="bnx-stat-foot">Primeras {len(valid_rankings)} cosechas</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        if not valid_rankings:
            st.info("No hay resultados de cosechas para este indicador.")
        else:
            df_chart = pd.DataFrame(
                [
                    {
                        "Cosecha": str(row["vintage"]),
                        "Valor_Raw": float(row["metrics"][selected_metric]),
                        "Valor_Plot": float(
                            row["metrics"][selected_metric]
                            if is_monetary
                            else row["metrics"][selected_metric] * 100
                        ),
                        "Valor_Fmt": display_metric(
                            row["metrics"][selected_metric], selected_metric
                        ),
                        "Cuentas": int(row["measures"]["accounts"]),
                        "Morosidad": float(
                            row["metrics"].get(KPIType.DELINQUENCY_RATE.value) or 0.0
                        ) * 100,
                        "Margen_Rate": float(
                            row["metrics"].get(KPIType.OPERATING_MARGIN_RATE.value) or 0.0
                        ) * 100,
                        "Utilizacion": float(
                            row["metrics"].get(KPIType.UTILIZATION_RATE.value) or 0.0
                        ) * 100,
                    }
                    for row in valid_rankings
                ]
            )

            sort_order = df_chart["Cosecha"].tolist()
            chronological_order = sorted(sort_order)
            y_axis_title = (
                f"{KPI_LABELS[selected_metric]} ($)"
                if is_monetary
                else f"{KPI_LABELS[selected_metric]} (%)"
            )

            row1_left, row1_right = st.columns([1.45, 1])

            with row1_left:
                with st.container(border=True):
                    st.markdown(f"#### Evolución de {KPI_LABELS[selected_metric]}")
                    st.caption("Trayectoria por cosecha (todos los meses en libros) frente al umbral promedio")

                    line_base = alt.Chart(df_chart).encode(
                        x=alt.X(
                            "Cosecha:N",
                            sort=chronological_order,
                            title="Cosecha",
                            axis=alt.Axis(labelAngle=0, labelColor="#5C6F7E", titleColor="#5C6F7E"),
                        ),
                        y=alt.Y(
                            "Valor_Plot:Q",
                            title=y_axis_title,
                            axis=alt.Axis(grid=True, gridColor="#EDF2F5", labelColor="#5C6F7E", titleColor="#5C6F7E"),
                        ),
                        tooltip=[
                            alt.Tooltip("Cosecha:N", title="Cosecha"),
                            alt.Tooltip("Valor_Fmt:N", title=KPI_LABELS[selected_metric]),
                            alt.Tooltip("Cuentas:Q", title="Cuentas", format=",.0f"),
                        ],
                    )

                    area = line_base.mark_area(
                        line={"color": "#18B9AA", "width": 3},
                        color=alt.Gradient(
                            gradient="linear",
                            stops=[
                                alt.GradientStop(color="rgba(24, 185, 170, 0.28)", offset=0),
                                alt.GradientStop(color="rgba(24, 185, 170, 0.01)", offset=1),
                            ],
                            x1=1,
                            x2=1,
                            y1=1,
                            y2=0,
                        ),
                    )

                    points = line_base.mark_circle(size=75, opacity=1).encode(
                        color=alt.condition(
                            alt.datum.Cosecha == str(vintage),
                            alt.value("#E6003C"),
                            alt.value("#18B9AA"),
                        )
                    )

                    mean_rule = (
                        alt.Chart(df_chart)
                        .mark_rule(color="#E6003C", strokeDash=[5, 4], size=1.8)
                        .encode(y="mean(Valor_Plot):Q")
                    )

                    trend_chart = (
                        (area + mean_rule + points)
                        .properties(height=320, background="#FFFFFF")
                        .configure_view(strokeWidth=0, fill="#FFFFFF")
                        .configure_axis(domainColor="#DCE3E8")
                    )
                    st.altair_chart(trend_chart, use_container_width=True)
                    st.caption("La línea punteada roja representa el umbral promedio del grupo mostrado.")

            with row1_right:
                with st.container(border=True):
                    st.markdown("#### Clasificación por Cosecha")
                    st.caption(f"Comparativa ordenada ({'mayor a menor' if descending else 'menor a mayor'})")

                    bar_base = alt.Chart(df_chart).encode(
                        y=alt.Y(
                            "Cosecha:N",
                            sort=sort_order,
                            title=None,
                            axis=alt.Axis(labelColor="#0B2030", labelFontWeight="bold"),
                        ),
                        x=alt.X(
                            "Valor_Plot:Q",
                            title=y_axis_title,
                            axis=alt.Axis(grid=True, gridColor="#EDF2F5", labelColor="#5C6F7E"),
                        ),
                        tooltip=[
                            alt.Tooltip("Cosecha:N", title="Cosecha"),
                            alt.Tooltip("Valor_Fmt:N", title=KPI_LABELS[selected_metric]),
                            alt.Tooltip("Cuentas:Q", title="Cuentas", format=",.0f"),
                        ],
                    )

                    hbar = bar_base.mark_bar(cornerRadiusEnd=5, height=16).encode(
                        color=alt.condition(
                            alt.datum.Cosecha == str(vintage),
                            alt.value("#E6003C"),
                            alt.value("#0B2030"),
                        )
                    )

                    bar_text = bar_base.mark_text(
                        align="left",
                        baseline="middle",
                        dx=6,
                        fontSize=11,
                        fontWeight="bold",
                        color="#0B2030",
                    ).encode(text="Valor_Fmt:N")

                    rank_chart = (
                        (hbar + bar_text)
                        .properties(height=320, background="#FFFFFF")
                        .configure_view(strokeWidth=0, fill="#FFFFFF")
                        .configure_axis(domainColor="#DCE3E8")
                    )
                    st.altair_chart(rank_chart, use_container_width=True)

            st.write("")

            row2_left, row2_right = st.columns([1.15, 1.35])

            with row2_left:
                with st.container(border=True):
                    st.markdown("#### Matriz Riesgo frente a Rentabilidad por Cosecha")
                    st.caption("Relación entre tasa de morosidad, tasa de margen operativo y tamaño de cartera")

                    scatter = (
                        alt.Chart(df_chart)
                        .mark_circle(opacity=0.88, stroke="#071522", strokeWidth=1.2)
                        .encode(
                            x=alt.X(
                                "Morosidad:Q",
                                title="Tasa de morosidad (%)",
                                axis=alt.Axis(grid=True, gridColor="#EDF2F5", labelColor="#5C6F7E", titleColor="#5C6F7E"),
                            ),
                            y=alt.Y(
                                "Margen_Rate:Q",
                                title="Tasa de margen operativo (%)",
                                axis=alt.Axis(grid=True, gridColor="#EDF2F5", labelColor="#5C6F7E", titleColor="#5C6F7E"),
                            ),
                            size=alt.Size(
                                "Cuentas:Q",
                                scale=alt.Scale(range=[120, 950]),
                                legend=None,
                            ),
                            color=alt.condition(
                                alt.datum.Cosecha == str(vintage),
                                alt.value("#E6003C"),
                                alt.value("#18B9AA"),
                            ),
                            tooltip=[
                                alt.Tooltip("Cosecha:N", title="Cosecha"),
                                alt.Tooltip("Morosidad:Q", title="Morosidad (%)", format=".2f"),
                                alt.Tooltip("Margen_Rate:Q", title="Margen operativo (%)", format=".2f"),
                                alt.Tooltip("Utilizacion:Q", title="Utilización (%)", format=".2f"),
                                alt.Tooltip("Cuentas:Q", title="Cuentas", format=",.0f"),
                            ],
                        )
                    )

                    scatter_labels = (
                        alt.Chart(df_chart)
                        .mark_text(dy=-12, fontSize=10, fontWeight="bold", color="#0B2030")
                        .encode(
                            x="Morosidad:Q",
                            y="Margen_Rate:Q",
                            text="Cosecha:N",
                        )
                    )

                    matrix_chart = (
                        (scatter + scatter_labels)
                        .properties(height=275, background="#FFFFFF")
                        .configure_view(strokeWidth=0, fill="#FFFFFF")
                        .configure_axis(domainColor="#DCE3E8")
                    )
                    st.altair_chart(matrix_chart, use_container_width=True)

            with row2_right:
                with st.container(border=True):
                    st.markdown("#### Hallazgos Prioritarios")
                    st.caption("Síntesis automática sobre las cosechas evaluadas")

                    top_row = df_chart.iloc[0]
                    bottom_row = df_chart.iloc[-1]

                    st.markdown(
                        f"""
                        <div class="bnx-insight bnx-insight--alert">
                            <div class="bnx-insight-head">
                                <span class="bnx-insight-title">Extremo superior en cosecha {top_row['Cosecha']}</span>
                                <span class="bnx-pill-high">PRIORIDAD</span>
                            </div>
                            <div class="bnx-insight-body">
                                Registra un nivel de <strong>{top_row['Valor_Fmt']}</strong> sobre un volumen de <strong>{top_row['Cuentas']:,}</strong> cuentas analizadas.
                            </div>
                        </div>
                        <div class="bnx-insight bnx-insight--positive">
                            <div class="bnx-insight-head">
                                <span class="bnx-insight-title">Referencia en cosecha {bottom_row['Cosecha']}</span>
                                <span class="bnx-pill-pos">REFERENCIA</span>
                            </div>
                            <div class="bnx-insight-body">
                                Presenta un valor de <strong>{bottom_row['Valor_Fmt']}</strong> con <strong>{bottom_row['Cuentas']:,}</strong> cuentas en el segmento.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with st.container(border=True):
                st.markdown("#### Detalle Tabular de Cosechas")
                max_plot = float(df_chart["Valor_Plot"].max()) if not df_chart.empty else 1.0
                table_df = pd.DataFrame(
                    [
                        {
                            "Cosecha": str(row["vintage"]),
                            KPI_LABELS[selected_metric]: display_metric(
                                row["metrics"][selected_metric], selected_metric
                            ),
                            "Nivel": float(
                                row["metrics"][selected_metric]
                                if is_monetary
                                else row["metrics"][selected_metric] * 100
                            ),
                            "Morosidad": f'{(row["metrics"].get(KPIType.DELINQUENCY_RATE.value) or 0.0):.2%}',
                            "Margen Op.": f'{(row["metrics"].get(KPIType.OPERATING_MARGIN_RATE.value) or 0.0):.2%}',
                            "Utilización": f'{(row["metrics"].get(KPIType.UTILIZATION_RATE.value) or 0.0):.2%}',
                            "Cuentas": int(row["measures"]["accounts"]),
                        }
                        for row in valid_rankings
                    ]
                )
                st.dataframe(
                    table_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Cosecha": st.column_config.TextColumn("Cosecha", width="small"),
                        KPI_LABELS[selected_metric]: st.column_config.TextColumn(
                            KPI_LABELS[selected_metric], width="medium"
                        ),
                        "Nivel": st.column_config.ProgressColumn(
                            "Distribución",
                            min_value=0.0,
                            max_value=max(max_plot, 0.01),
                            format="%.2f",
                        ),
                        "Morosidad": st.column_config.TextColumn("Morosidad", width="small"),
                        "Margen Op.": st.column_config.TextColumn("Margen Op.", width="small"),
                        "Utilización": st.column_config.TextColumn("Utilización", width="small"),
                        "Cuentas": st.column_config.NumberColumn("Cuentas", format="%,d"),
                    },
                )

    except (
        RuntimeError,
        ValueError,
        KeyError,
        requests.exceptions.RequestException,
    ) as error:
        show_error(error)