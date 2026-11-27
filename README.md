# ObsAgent

ObsAgent is a local portfolio analytics app with a Streamlit frontend, a
ChromaDB data store, and an Ollama-backed multi-agent workflow. The app combines
natural-language analysis with deterministic KPI calculations over precomputed
aggregates.

## What the app does

- **Ask ObsAgent:** submit questions in Spanish. A Translator, Researcher, and
  Builder handle the request in Spanish in sequence.
- **Portfolio dashboard:** view a selected KPI and rank cosechas using the
  local aggregate collection. These dashboard queries use deterministic Python
  calculations; they do not call Ollama.
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

## Frontend appearance

The Streamlit interface and agent responses are in Spanish. Its header combines
the ObsAgent palette from `visual-identity/VISUAL_IDENTITY.md` with Banamex
brand accents; the header styling, logo treatment, and page layout are in
`streamlit_app.py`.

## Agent responsibilities

| Agent | Responsibility | Main code |
|---|---|---|
| Translator | Normalizes the user's request in Spanish while preserving its intent, filters, and identifiers. | `TranslatorAgent.execute` in `multi_agent_framework/agent_manager.py` |
| Researcher | Selects analytical tools, gathers evidence, and summarizes results in Spanish without inventing numbers. | `ResearcherAgent` in `multi_agent_framework/agent_manager.py` |
| Builder | Presents the evidence-based response in Spanish. | `BuilderAgent.execute` in `multi_agent_framework/agent_manager.py` |

The workflow is a pipeline: only the previous agent's output and the query
context are handed to the next agent. The Streamlit chat keeps recent messages
in the current session and includes them with the next request.

## Changing agent behavior or follow-up questions

To make the Researcher ask for clarification instead of guessing when a query
is ambiguous, edit its system prompt in `ResearcherAgent.execute`. For example,
add a rule to ask one concise question when a required vintage, MOB, metric, or
comparison is unclear, and not to call a tool until the user answers. Update
the Builder prompt in `BuilderAgent.execute` to preserve that clarification as
a question rather than presenting it as a final analysis.

The Streamlit chat carries up to the eight most recent messages into the next
request, so the user can answer a follow-up in the same conversation. To retain
more context, change the `[-8:]` history window in `streamlit_app.py`. This
history is session state; it is not persisted as a database conversation.

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
