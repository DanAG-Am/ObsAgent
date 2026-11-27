# ObsAgent architecture

ObsAgent combines a Streamlit frontend, local ChromaDB collections, and an
Ollama-backed agent with deterministic analytical tools. For installation and
end-to-end startup, see [set_up.md](./set_up.md).

## Application flow

```text
Streamlit chat / dashboard question ──► MultiAgentSystem
                                        ├─ Researcher ──► tools and ChromaDB
                                        └─ Builder ──► final answer
Streamlit dashboard ──► deterministic KPI functions
```

The orchestrator is Python code, not an additional model call. The Builder
adds a model call after research. There is no translation stage. Custom
workflows can replace either agent. The `SKILLS/` documents are not loaded or
executed automatically. The model may call `consultar_skill` to read an
allowlisted guide or one of its sections. The trace records each call. The
guides are instructions, not data evidence or implementations; using one does
not mean its procedure was completed. Selected guide content is sent to the
configured Ollama endpoint, which may be remote.
The existing analytics and draft PDF cover only parts of the documented
procedures; automated report-number verification remains unimplemented.
The chat's numeric lookup suggests possible source fields and reports missing
matches; it does not verify units, context, meaning, or report correctness.
Reports are downloaded locally; there is no email or external distribution.

### Researcher

`ResearcherAgent` runs a bounded tool-calling loop. The model chooses among
registered tools, but Python runs their handlers. The handlers call the
validated analytical functions in `ChromaDB/precomputed_queries.py`; model
output is not used as a KPI calculation or arbitrary database query.

The registered tools are:

| Tool | Purpose |
|---|---|
| `consultar_diccionario` | Read a complete source-variable definition. |
| `validar_csv_local` | Screen the local CSV structure and selected reconciliations without verifying the database aggregates. |
| `consultar_skill` | Read a skill guide or section; does not execute its procedure. |
| `portfolio_kpis` | Portfolio measures and derived KPIs, with optional filters. |
| `cohort_curve` | KPI results grouped by vintage and month-on-book. |
| `kpis_by_dimension` | KPI results grouped by a supported dimension. |
| `vintage_comparison` | Compare two vintages at the same MOB. |
| `segment_ranking` | Rank groups by a supported metric. |
| `anomaly_candidates` | Find IQR-based outliers for a metric and dimension. |
| `analizar_fraude_simulado` | Analyze fixed invented transaction and incident counts with IQR; not real fraud detection. |

`MAX_ITERATIONS` limits the tool-call loop. Individual and cumulative tool
results are bounded to control how much data is sent back to the model.
Every research request includes short dictionary definitions for vintage, MOB,
accounts, revenue and total expenses. The full source definitions can be
retrieved individually. Missing or invalid dictionary files produce a visible
warning; the dictionary is context, not verification of the database.

`ResearcherAgent` returns research and tool results to the Builder, which drafts
the final answer in Spanish. When a
tool returns grouped results or a comparison, the chat can render those values
as a chart alongside the answer. The response trace records tool names,
arguments, returned results, and errors; a response without tool calls is
explicitly identified. Timings are measured in-process for each tool, the
researcher and the builder; tool time is included in researcher time.

The optional synthetic evaluation uses two invented aggregate rows and a
synthetic dictionary in a temporary in-memory collection. Only the two relevant
analytics tools are available in that run. It calls the configured Ollama
endpoint only when requested, and reports evidence checks and number presence
separately; it does not establish semantic correctness or reliability.

## Data flow and responsibilities

Two persistent collections are required in `ChromaDB/chroma_data/`:

- `base_cards_sintetica`: source records ingested from the CSV.
- `base_cards_sintetica_aggregates`: records materialized for deterministic
  KPI and analytical queries.

The source ingestion and aggregation logic is in `ChromaDB/ingest_csv.py` and
`ChromaDB/precomputed_queries.py`. The language model selects tools and
summarizes evidence; Python validates filters and calculates metrics.

The Streamlit app has two paths:

- **Ask ObsAgent** sends the current prompt and previous user/assistant exchange
  to the multi-agent workflow. The chat keeps older messages in the session but does not
  send the entire conversation back to the model on every request.
- **Portfolio dashboard** calls `QueryService` for KPIs and vintage rankings.
  Those deterministic calls do not require Ollama and only run when the
  dashboard tab is selected. Questions submitted there also send the selected
  KPI, filters and displayed ranking to Ollama; evolution points are requested
  through tools. Follow-ups include the previous exchange only while the view
  and data source remain unchanged. Visible segment filters default to all
  segments and affect all panel
  results. The comparator aligns vintages on a common MOB; the quality check
  flags observed internal gaps and applies a user-specified minimum only to
  a selected MOB.
  Optional delinquency alerts require a vintage, MOB and user-specified
  minimum accounts. They compare all eligible product, channel or strategy
  groups using split-median IQR, preserving the rate numerator and denominator;
  fewer than four peers or a zero IQR produces no classification. The alerts
  are exploratory, not fraud detection.
- **Fraude (demo)** displays fixed synthetic channel counts and IQR outliers
  without querying the portfolio for the analysis. Its separate chat sends
  that synthetic view and the question to the configured Ollama endpoint.
  This is not a validated detector or evidence of real fraud.

The chat is stored in Streamlit session state, not in ChromaDB or another
persistent conversation store.

## Main implementation files

| File | Responsibility |
|---|---|
| `streamlit_app.py` | Chat UI, dashboard controls, and Streamlit session history. |
| `multi_agent_framework/agent_manager.py` | Agent roles, prompts, tool schemas, handlers, and orchestration. |
| `multi_agent_framework/query_service.py` | Direct async access to KPI, ranking, comparison, and semantic query methods. |
| `multi_agent_framework/skill_guides.py` | Allowlisted, read-only access to skill guide sections. |
| `multi_agent_framework/variable_dictionary.py` | Reads and validates the local source-variable dictionary. |
| `multi_agent_framework/display_labels.py` | Spanish labels for tools and evidence without changing stored identifiers. |
| `multi_agent_framework/numeric_evidence.py` | Conservative numeric source suggestions, not semantic verification. |
| `multi_agent_framework/local_validation.py` | Read-only CSV schema and selected reconciliation checks. |
| `multi_agent_framework/fraud_demo.py` | Fixed synthetic incident rates and IQR demonstration. |
| `multi_agent_framework/excel_report.py` | In-memory, unverified local chat and dashboard Excel drafts. |
| `multi_agent_framework/response_charts.py` | Builds chat charts from validated tool results. |
| `multi_agent_framework/agentlib/ollama.py` | Ollama HTTP client and model/endpoint configuration. |
| `ChromaDB/ingest_csv.py` | CSV ingestion into the source collection. |
| `ChromaDB/precomputed_queries.py` | Aggregates, filter validation, and deterministic analysis functions. |

## Extending the system

To change how an agent reasons or communicates, edit its system prompt in
`multi_agent_framework/agent_manager.py`. In particular, to ask the user a
clarifying question instead of assuming missing input:

1. Add a Researcher instruction that identifies required details, asks one
   concise question when they are unclear, and avoids making tool calls until
   the user answers.
2. Update the Builder instruction to preserve the clarification question.
3. Keep the Streamlit chat-history window large enough for the user response
   and the prior question to be included in the next request.

To add data-analysis capability, first implement a validated Python function
in `ChromaDB/precomputed_queries.py`. Then import and register it in
`ResearcherAgent._build_tools` with a JSON schema, handler, and prompt guidance.
Expose it in `QueryService` or `streamlit_app.py` only if direct API or dashboard
access is also needed. Do not give the model arbitrary SQL or direct
unrestricted ChromaDB access.

For runnable commands, requirements, data expectations, Ollama setup, and
custom agent registration, see [set_up.md](./set_up.md).
