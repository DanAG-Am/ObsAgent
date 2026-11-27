# ObsAgent

ObsAgent is a local portfolio analytics app with a Streamlit frontend, a
ChromaDB data store, and an Ollama-backed analytical agent. The app combines
natural-language analysis with deterministic KPI calculations over precomputed
aggregates.

## What the app does

- **Ask ObsAgent:** submit questions in Spanish. The Researcher selects
  validated analysis tools, and the Builder drafts a response. The app displays a chart
  when the result contains a useful grouped series or comparison. Charts are
  displayed in the chat independently of PDF and Excel. Each answer can be
  downloaded as a local PDF or Excel test draft with its question and tool trace.
  The draft is explicitly unverified.
- **Portfolio dashboard:** view a selected KPI and rank cosechas using the
  local aggregate collection. These dashboard queries use deterministic Python
  calculations; they do not call Ollama. Filters show the available cosechas
  and MOB values (including MOB 0). The first load reads the aggregates; the
  resulting cohort summaries are cached for five minutes. Two charts show the
  selected metric and account observations by MOB and cosecha, across all MOBs
  of the selected cosecha; the MOB filter only affects the KPI cards. Account
  observations summed across MOBs are not necessarily unique accounts.
  Product, channel and strategy filters are always visible, default to all
  segments, and apply to all panel results when selected.
  The comparator shows selected vintages at a common MOB and their curves. A
  user-defined minimum warns about small populations only at a selected MOB;
  internal MOB gaps are identified from observed data.
  Optional exploratory delinquency alerts compare products, channels or
  strategies within one selected vintage and MOB using all eligible segments
  and a user-defined minimum account count. They show the numerator, relevant
  denominator, IQR fences, exclusions and data-quality limitations. At least
  four segments and a nonzero IQR are required. These are not fraud alerts or
  regulatory thresholds.
  The local Excel download contains editable charts of both evolution series
  and the top-ten ranking, plus their data and selected KPI. Their different
  filter scopes are noted in the workbook; the interactive comparison is not
  included.
  Ask questions directly below the KPI cards: the selected KPI, filters,
  comparison, ranking and visible quality summaries are sent to the configured
  Ollama endpoint. Evolution points are queried
  through tools when needed. The panel conversation is separate from the chat.
- **Synthetic fraud demonstration:** the separate **Fraude (demo)** view uses
  fixed, invented transaction and incident counts by channel and the same IQR
  convention as the portfolio anomaly tool. The rates, fences and flagged
  outliers are illustrative only: they are not fraud probabilities, real fraud
  detection, or a validated model. The view and tool do not use portfolio data.
  Questions from its separate conversation send the synthetic view and prompt
  to the configured Ollama endpoint, which may be remote. Open it from its tab
  or the shortcut in the portfolio dashboard.
- **Local CSV screening:** `validar_csv_local` checks the repository's source
  CSV for structural errors, selected reconciliation rules, exact duplicate
  rows and internal MOB gaps. It does not check business-key duplicates,
  expected coverage, category catalogs, population thresholds, or whether the
  CSV matches the database aggregates. CSV validation is manual and can be slow.
- **Capabilities and evidence:** inspect registered tools and the actual tool
  arguments, results, and errors for each chat response. The model may consult
  the repository's skill guides using `consultar_skill`; the trace shows whether
  it actually did. Guide consultation does not execute the documented skills.
  A numeric lookup lists possible source fields for answer numbers and warns
  when it finds no match. It is not semantic verification: matching numbers may
  refer to different metrics, units or filters, and ambiguous formats may not
  match. Check each trace and scope manually; downloads remain unverified.
  The selected guide content is sent to the configured Ollama endpoint, which
  may not be local.
- **Synthetic agent evaluation:** an explicit button in **Evaluación sintética** runs
  two cases against a temporary invented collection and synthetic dictionary
  using the configured Ollama endpoint. It checks the selected tool, filters,
  deterministic evidence and the presence of expected numbers in the answer.
  Number presence is not semantic verification or a reliability guarantee.
  The trace displays researcher, builder and individual tool timings.
- **Variable dictionary:** the agent receives short definitions for key
  portfolio fields and can request a full definition with
  `consultar_diccionario`. The definitions describe the source; they do not
  verify the current records or calculated results. Dictionary text is sent to
  the configured Ollama endpoint, which may be remote.
- **Validated analysis:** the model can call only the analytics tools exposed
  by the Researcher. KPI calculations and supported filters are handled by
  `ChromaDB/precomputed_queries.py`, not invented by the model. Scalar vintage
  and MOB filters also accept digit-only strings, converted to integers for the
  query; the trace retains the arguments originally supplied by the model.

## Quick setup

1. Follow [set_up.md](./set_up.md) for the full setup and run instructions.
2. Provide `database/base_cards_sintetica.csv`, install the dependencies, and
   create the source and aggregate ChromaDB collections.
3. Configure and start Ollama with a model that supports tool calling.
4. From the project root, activate the environment and run:

   ```bash
   source ChromaDB/.venv/bin/activate
   streamlit run streamlit_app.py
   ```

The app's default ChromaDB directory is `ChromaDB/chroma_data`. To use another
directory, set `OBSAGENT_CHROMA_PATH` or change the directory in the sidebar.
Place the variable dictionary at
`database/Base Cards para TEC - Diccionario de Variables.csv` on each machine.
CSV files are ignored by Git, so deploy it separately through an authorized
channel. If it is missing or invalid, chat remains available but displays a
warning and the dictionary tool reports the error.

Questions are passed directly to the agents without a translation stage.

## Tests

From the project root, run the tests using the existing environment:

```bash
ChromaDB/.venv/bin/python -m tests.test_agent_manager &&
ChromaDB/.venv/bin/python -m tests.test_csv_validation &&
ChromaDB/.venv/bin/python -m tests.test_draft_report &&
ChromaDB/.venv/bin/python -m tests.test_excel_report &&
ChromaDB/.venv/bin/python -m tests.test_local_validation &&
ChromaDB/.venv/bin/python -m tests.test_precomputed_queries &&
ChromaDB/.venv/bin/python -m tests.test_numeric_evidence &&
ChromaDB/.venv/bin/python -m tests.test_response_charts &&
ChromaDB/.venv/bin/python -m tests.test_streamlit_app
```

The agent and Streamlit tests use mocks and do not call Ollama.

## Frontend appearance

The Streamlit interface and agent responses are in Spanish. Its header combines
the ObsAgent palette from `visual-identity/VISUAL_IDENTITY.md` with Banamex
brand accents; the full hero appears on the home view while the sidebar keeps
the identity visible throughout the app. The blue and red theme, typography,
and chart palette are configured in `.streamlit/config.toml` without external
font downloads.

## Agent responsibilities

| Agent | Responsibility | Main code |
|---|---|---|
| Researcher | Selects analytical tools, gathers evidence, and summarizes results in Spanish without inventing numbers. | `ResearcherAgent` in `multi_agent_framework/agent_manager.py` |
| Builder | Drafts the final Spanish response from the question and research evidence. | `BuilderAgent` in `multi_agent_framework/agent_manager.py` |
| Orchestrator | Coordinates the two stages without a separate model call. | `MultiAgentSystem` in `multi_agent_framework/agent_manager.py` |

The app sends the question to the Researcher and then to the Builder. The
Builder adds a model call and may increase response time. The trace shows whether tools were actually used
and reports any tool errors; check it before relying on the answer. The Streamlit chat keeps the full
conversation in the current session but sends only the previous exchange with
the next request.

## Changing agent behavior or follow-up questions

To make the Researcher ask for clarification instead of guessing when a query
is ambiguous, edit its system prompt in `ResearcherAgent.execute`. For example,
add a rule to ask one concise question when a required vintage, MOB, metric, or
comparison is unclear, and not to call a tool until the user answers. If using
the Builder, update its prompt to preserve that clarification as a
question rather than presenting it as a final analysis.

The Streamlit chat carries the previous user/assistant exchange into the next
request, so the user can answer a follow-up without resending the full history.
This history is session state; it is not persisted as a database conversation.

## Adding or changing analytical capabilities

The Researcher's callable tools are defined together in
`ResearcherAgent._build_tools`:

1. Implement or update deterministic calculations and input validation in
   `ChromaDB/precomputed_queries.py`.
2. Import the function in `multi_agent_framework/agent_manager.py`.
3. Add an `AgentTool` with a JSON parameter schema and a callable handler in
   `_build_tools`.
4. Describe when the Researcher should use it in the system prompt.
5. If users also need the capability outside chat, add a method to
   `multi_agent_framework/query_service.py`. If it needs dashboard controls,
   wire those controls into `streamlit_app.py` as well.

Keep metric and filter validation in Python. Do not let the model create SQL,
arbitrary ChromaDB filters, or numeric results. `MAX_ITERATIONS` limits the
Researcher's tool-call rounds; it is not a limit on how many questions a user
can ask.

For complete installation, data preparation, configuration, and troubleshooting
steps, see [set_up.md](./set_up.md). See
[README_Arquitecture.md](./README_Arquitecture.md) for the workflow and
implementation details.
