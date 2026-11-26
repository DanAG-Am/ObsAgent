# ObsAgent architecture

ObsAgent combines a Streamlit frontend, local ChromaDB collections, and an
Ollama-backed three-agent pipeline. For installation and end-to-end startup,
see [set_up.md](./set_up.md).

## Application flow

```text
Streamlit chat
    │ user question + recent chat messages
    ▼
Translator ── translated request ──► Researcher
                                        │
                                        ├─ validated analytical tools
                                        ├─ ChromaDB aggregate collection
                                        └─ evidence and summary
                                               │
                                               ▼
                                      Builder ──► response

Streamlit dashboard ──► QueryService ──► deterministic KPI functions
```

### Translator

`TranslatorAgent` sends the request to Ollama and asks it to translate the
request into English while preserving metrics, years, filters, and identifiers.
The model is told to leave already-English requests unchanged.

### Researcher

`ResearcherAgent` runs a bounded tool-calling loop. The model chooses among
registered tools, but Python runs their handlers. The handlers call the
validated analytical functions in `ChromaDB/precomputed_queries.py`; model
output is not used as a KPI calculation or arbitrary database query.

The registered tools are:

| Tool | Purpose |
|---|---|
| `portfolio_kpis` | Portfolio measures and derived KPIs, with optional filters. |
| `cohort_curve` | KPI results grouped by vintage and month-on-book. |
| `kpis_by_dimension` | KPI results grouped by a supported dimension. |
| `vintage_comparison` | Compare two vintages at the same MOB. |
| `segment_ranking` | Rank groups by a supported metric. |
| `anomaly_candidates` | Find IQR-based outliers for a metric and dimension. |

`MAX_ITERATIONS` limits the tool-call loop. Individual and cumulative tool
results are bounded to control how much data is sent back to the model.

### Builder

`BuilderAgent` receives the original request, the Researcher's response, and
the tool results. It writes the final response in the original language and is
instructed not to add unsupported facts or numbers.

Each agent makes its own Ollama call. The pipeline passes the request and
results between stages; it does not share one model conversation object across
the three agents.

## Data flow and responsibilities

Two persistent collections are required in `ChromaDB/chroma_data/`:

- `base_cards_sintetica`: source records ingested from the CSV.
- `base_cards_sintetica_aggregates`: records materialized for deterministic
  KPI and analytical queries.

The source ingestion and aggregation logic is in `ChromaDB/ingest_csv.py` and
`ChromaDB/precomputed_queries.py`. The language model selects tools and
summarizes evidence; Python validates filters and calculates metrics.

The Streamlit app has two paths:

- **Ask ObsAgent** runs Translator → Researcher → Builder. It sends up to eight
  recent chat messages with the next user prompt so that follow-up answers can
  use recent context.
- **Portfolio dashboard** calls `QueryService` for KPIs and vintage rankings.
  Those deterministic calls do not require Ollama.

The chat is stored in Streamlit session state, not in ChromaDB or another
persistent conversation store.

## Main implementation files

| File | Responsibility |
|---|---|
| `streamlit_app.py` | Chat UI, dashboard controls, and Streamlit session history. |
| `multi_agent_framework/agent_manager.py` | Agent roles, prompts, tool schemas, handlers, and orchestration. |
| `multi_agent_framework/query_service.py` | Direct async access to KPI, ranking, comparison, and semantic query methods. |
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
