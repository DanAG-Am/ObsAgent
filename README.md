# ObsAgent

ObsAgent is a local portfolio analytics app with a Streamlit frontend, a
ChromaDB data store, and an Ollama-backed analytical agent. The app combines
natural-language analysis with deterministic KPI calculations over precomputed
aggregates.

## What the app does

- **Ask ObsAgent:** submit questions in Spanish. The Researcher selects
  validated analysis tools, summarizes their evidence, and displays a chart
  when the result contains a useful grouped series. Each answer can be
  downloaded as a local PDF test draft with its question and tool trace.
  The draft is explicitly unverified and is not an approved report.
- **Portfolio dashboard:** view a selected KPI and rank cosechas using the
  local aggregate collection. These dashboard queries use deterministic Python
  calculations; they do not call Ollama. Filters show the available cosechas
  and MOB values (including MOB 0). The first load reads the aggregates; the
  resulting cohort summaries are cached for five minutes. Two charts show the
  selected metric and account observations by MOB and cosecha, across all MOBs
  of the selected cosecha; the MOB filter only affects the KPI cards. Account
  observations summed across MOBs are not necessarily unique accounts.
- **Capabilities and evidence:** inspect registered tools and the actual tool
  arguments, results, and errors for each chat response. The model may consult
  the repository's skill guides using `consultar_skill`; the trace shows whether
  it actually did. Guide consultation does not execute the documented skills.
  The selected guide content is sent to the configured Ollama endpoint, which
  may not be local. The storage guide is empty and unavailable.
- **Optional translation:** enable translation to Spanish in the sidebar. It
  adds an Ollama call and shows the translated request in the response trace.
- **Validated analysis:** the model can call only the analytics tools exposed
  by the Researcher. KPI calculations and supported filters are handled by
  `ChromaDB/precomputed_queries.py`, not invented by the model.

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

## Tests

From the project root, run the tests using the existing environment:

```bash
ChromaDB/.venv/bin/python -m tests.test_agent_manager &&
ChromaDB/.venv/bin/python -m tests.test_csv_validation &&
ChromaDB/.venv/bin/python -m tests.test_draft_report &&
ChromaDB/.venv/bin/python -m tests.test_precomputed_queries &&
ChromaDB/.venv/bin/python -m tests.test_response_charts &&
ChromaDB/.venv/bin/python -m tests.test_streamlit_app
```

The agent and Streamlit tests use mocks and do not call Ollama.

## Frontend appearance

The Streamlit interface and agent responses are in Spanish. Its header combines
the ObsAgent palette from `visual-identity/VISUAL_IDENTITY.md` with Banamex
brand accents; the header styling, logo treatment, and page layout are in
`streamlit_app.py`.

## Agent responsibilities

| Agent | Responsibility | Main code |
|---|---|---|
| Researcher | Selects analytical tools, gathers evidence, and summarizes results in Spanish without inventing numbers. | `ResearcherAgent` in `multi_agent_framework/agent_manager.py` |
| Translator and Builder | Translation is optional in the UI; a custom Builder can be registered for custom workflows. | `TranslatorAgent` and `BuilderAgent` in `multi_agent_framework/agent_manager.py` |

The default app sends the question directly to the Researcher and uses its
response as the final answer. The trace shows whether tools were actually used
and reports any tool errors; check it before relying on the answer. The Streamlit chat keeps the full
conversation in the current session but sends only the previous exchange with
the next request.

## Changing agent behavior or follow-up questions

To make the Researcher ask for clarification instead of guessing when a query
is ambiguous, edit its system prompt in `ResearcherAgent.execute`. For example,
add a rule to ask one concise question when a required vintage, MOB, metric, or
comparison is unclear, and not to call a tool until the user answers. If using
a custom Builder, update its prompt to preserve that clarification as a
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
