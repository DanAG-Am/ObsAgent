"""Streamlit chat and portfolio dashboard for ObsAgent."""

from __future__ import annotations

import asyncio
import os

import requests
import streamlit as st

from multi_agent_framework.agent_manager import DEFAULT_CHROMA_PATH
from multi_agent_framework.query_service import KPIType, QueryService


KPI_LABELS = {
    KPIType.DELINQUENCY_RATE.value: "Delinquency rate (amount)",
    KPIType.DELINQUENCY_RATE_ACCOUNTS.value: "Delinquency rate (accounts)",
    KPIType.GROSS_CHARGEOFF_RATE.value: "Gross charge-off rate",
    KPIType.NET_CHARGEOFF_RATE.value: "Net charge-off rate",
    KPIType.RECOVERY_RATE.value: "Recovery rate",
    KPIType.UTILIZATION_RATE.value: "Utilization rate",
    KPIType.OPERATING_MARGIN.value: "Operating margin",
    KPIType.OPERATING_MARGIN_RATE.value: "Operating margin rate",
    KPIType.EFFICIENCY_RATIO.value: "Efficiency ratio",
    KPIType.ACQUISITION_COST_PER_ACCOUNT.value: "Acquisition cost per account",
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
        return "N/A"
    if metric in NON_PERCENTAGE_METRICS:
        return f"{value:,.2f}"
    return f"{value:.2%}"


def show_error(error: Exception) -> None:
    st.error(str(error))
    if isinstance(error, requests.exceptions.RequestException):
        st.caption(
            "Check that Ollama is running and that the configured URL and model "
            "are available."
        )
    elif isinstance(error, RuntimeError) and "collection" in str(error).lower():
        st.caption(
            "Prepare the source and aggregate collections using ChromaDB/README.md."
        )


st.set_page_config(page_title="ObsAgent", layout="wide")
st.markdown(
    """
    <style>
    .obs-hero {
        background: linear-gradient(120deg, #071522, #0B2030);
        border-radius: 24px;
        color: #FFFFFF;
        padding: 2rem;
        margin-bottom: 1.5rem;
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
    </style>
    <header class="obs-hero">
        <div class="obs-hero__label">ObsAgent / Portfolio intelligence</div>
        <h1>Clarity to decide. Intelligence to act.</h1>
        <p>Explore your portfolio and turn data into evidence-based answers.</p>
    </header>
    """,
    unsafe_allow_html=True,
)

default_path = os.getenv("OBSAGENT_CHROMA_PATH", str(DEFAULT_CHROMA_PATH))
with st.sidebar:
    st.title("ObsAgent")
    st.caption("Portfolio intelligence")
    st.divider()
    st.subheader("Data source")
    chroma_path = st.text_input(
        "ChromaDB directory",
        value=default_path,
        help="Directory containing base_cards_sintetica and its aggregate collection.",
    )
    st.caption("Use a local ChromaDB directory containing both required collections.")
    with st.expander("Connection settings"):
        st.caption("Configure Ollama with CHAT_MODEL and OLLAMA_BASE_URL in .env.")

try:
    service = get_service(chroma_path)
except (RuntimeError, ValueError, requests.exceptions.RequestException) as error:
    show_error(error)
    st.stop()

chat_tab, dashboard_tab = st.tabs(["Ask ObsAgent", "Portfolio dashboard"])

with chat_tab:
    st.subheader("Explore your questions")
    st.caption(
        "Ask about portfolio KPIs, vintage comparisons, or segments. "
        "ObsAgent uses your configured Ollama model and local data."
    )
    if "obsagent_messages" not in st.session_state:
        st.session_state.obsagent_messages = []

    if not st.session_state.obsagent_messages:
        st.info(
            "Start with a question such as: "
            '"Which vintages have the highest delinquency rate?"'
        )

    if st.button("Clear conversation", key="clear_conversation"):
        st.session_state.obsagent_messages = []

    for message in st.session_state.obsagent_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(
        "For example: Compare recent vintages by delinquency rate"
    )
    if prompt:
        st.session_state.obsagent_messages.append(
            {"role": "user", "content": prompt}
        )
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Translating, researching, and preparing your answer..."):
                try:
                    prior_messages = st.session_state.obsagent_messages[:-1][-8:]
                    if prior_messages:
                        history = "\n".join(
                            f'{message["role"]}: {message["content"]}'
                            for message in prior_messages
                        )
                        request = (
                            "Conversation so far:\n"
                            f"{history}\n\n"
                            f"Latest user request: {prompt}"
                        )
                    else:
                        request = prompt
                    result = asyncio.run(service.query(request))
                    answer = result["final_answer"]
                    if not answer:
                        st.warning("The agent workflow returned an empty answer.")
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
    st.subheader("Portfolio overview")
    st.caption("Choose a KPI and explore the underlying vintage distribution.")
    with st.container(border=True):
        st.markdown("#### Refine your view")
        left, right = st.columns(2)
        with left:
            selected_metric = st.selectbox(
                "KPI",
                options=list(KPI_LABELS),
                format_func=lambda metric: KPI_LABELS[metric],
            )
            vintage_input = st.number_input(
                "Vintage (0 for all)",
                min_value=0,
                max_value=9999,
                value=0,
                step=1,
            )
        with right:
            mob_input = st.number_input(
                "Month on book (0 for all)",
                min_value=0,
                max_value=9999,
                value=0,
                step=1,
            )
            descending = st.selectbox(
                "Rank vintages",
                options=[True, False],
                format_func=lambda highest_first: (
                    "Highest first" if highest_first else "Lowest first"
                ),
            )

    vintage = int(vintage_input) or None
    mob = int(mob_input) or None
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
        st.markdown("#### Selected portfolio")
        st.caption(
            f"Vintage: {vintage if vintage is not None else 'all'} "
            f"| Month on book: {mob if mob is not None else 'all'}"
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
                st.metric("Accounts in scope", f"{accounts:,.0f}")

        rankings = asyncio.run(
            service.get_vintage_ranking(
                sort_metric=selected_metric,
                descending=descending,
                top_n=10,
            )
        )
        st.markdown("#### Vintage ranking")
        st.caption(
            "Top 10 vintages across all months on book; the vintage and MOB "
            "controls above apply to the selected portfolio metrics only."
        )
        if not rankings:
            st.info("No vintage results are available for this KPI.")
        else:
            table_rows = [
                {
                    "Vintage": row["vintage"],
                    KPI_LABELS[selected_metric]: display_metric(
                        row["metrics"][selected_metric], selected_metric
                    ),
                    "Accounts": f'{row["measures"]["accounts"]:,.0f}',
                }
                for row in rankings
            ]
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

            chart_values = [
                {
                    "Vintage": str(row["vintage"]),
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
                st.markdown(f"##### {KPI_LABELS[selected_metric]} by vintage")
                st.bar_chart(
                    chart_values,
                    x="Vintage",
                    y=KPI_LABELS[selected_metric],
                    color="#18B9AA",
                )
                st.caption(
                    "Percentage KPIs are charted in percentage points; monetary "
                    "KPIs use their original units."
                )
    except (
        RuntimeError,
        ValueError,
        KeyError,
        requests.exceptions.RequestException,
    ) as error:
        show_error(error)
