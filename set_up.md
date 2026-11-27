# ObsAgent setup guide

This guide covers preparing the data, configuring Ollama, and running the full
Streamlit app. Commands below are instructions for you to run; they have not
been run as part of this documentation change.

## 1. Prerequisites

- Python 3.12 is recommended.
- Ollama installed and available on the machine or network.
- The source CSV at `database/base_cards_sintetica.csv`.
- Enough local disk space for ChromaDB. The full source collection may require
  several gigabytes.

The CSV is not included in this project folder. Obtain the permitted project
dataset and place it at the path above before ingestion. The ingestion script
expects these CSV headers:

```text
VINTAGE, STRATEGY, STRATEGY_SEGMENT, PRODUCT, CHANNEL, AGE_TAG, SCORE_TAG,
MOB, ACCOUNTS, CREDITLINESAMTS, ENRACCTS, OVER30ACCTS, OVER30AMTS, GCLAMTS,
NCLAMTS, RECOVERYAMTS, ENRAMTS, REVENUE, EXPENSES_ACQ, EXPENSES_ECM_VAR,
EXPENSES_ECM_FIX, EXPENSES_TOTAL
```

## 2. Create the Python environment

Run these commands from the ObsAgent project root:

```bash
python3.12 -m venv ChromaDB/.venv
ChromaDB/.venv/bin/python -m pip install --upgrade pip
ChromaDB/.venv/bin/python -m pip install -r ChromaDB/requirements.txt
```

If `ChromaDB/.venv` already exists, keep using it rather than creating another
environment. To activate it for the rest of the session:

```bash
source ChromaDB/.venv/bin/activate
```

On Windows, use a standard x64 CPython installation, not the Python bundled
with MSYS2. MSYS2's `mingw` platform tags do not match ChromaDB's Windows
wheel. Check installed Python versions, then create a separate Windows
environment from the project root:

```powershell
py -0p
py -3.12 -m venv .\ChromaDB\.venv
& ".\ChromaDB\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\ChromaDB\.venv\Scripts\python.exe" -m pip install -r ".\ChromaDB\requirements.txt"
```

If using Python 3.xx instead of the recommended 3.12, replace `-3.12` with
`-3.xx`. Activate the environment in PowerShell with:

```powershell
.\ChromaDB\.venv\Scripts\Activate.ps1
```

## 3. Configure and start Ollama

Make sure the Ollama service is running. On macOS, opening Ollama starts its
service; on other setups, use the launch method for your Ollama installation.
The model must be present on the same Ollama host configured below and should
support tool calling.

For the default model, download it through Ollama:

```bash
ollama pull qwen3.5:9b
```

Create a `.env` file in the ObsAgent project root with:

```dotenv
CHAT_MODEL=ollama:qwen3.5:9b
OLLAMA_BASE_URL=http://localhost:11434
```

`CHAT_MODEL` uses the `ollama:model-name` format. Set it to the Ollama model
you have available. The project `.gitignore` excludes `.env`; do not commit
credentials or private service configuration.

### Ollama on another machine

Use the reachable HTTP address of the Ollama host, for example:

```dotenv
OLLAMA_BASE_URL=http://192.0.2.10:11434
```

Use the actual address and port available in your environment. Ollama's API
uses `http://`, not `https://`. If `OLLAMA_DESTINO` is set in the environment or
`.env`, it takes precedence over `OLLAMA_BASE_URL`; provide the matching
`OLLAMA_URL_<DESTINO>` setting, such as `OLLAMA_URL_TEC`, or remove
`OLLAMA_DESTINO` to use the simple configuration above.

## 4. Ingest the source CSV

From the project root, run:

```bash
ChromaDB/.venv/bin/python ChromaDB/ingest_csv.py
```

In Windows PowerShell, use the Windows virtual environment instead:

```powershell
& ".\ChromaDB\.venv\Scripts\python.exe" ".\ChromaDB\ingest_csv.py"
```

This creates or updates the `base_cards_sintetica` collection in
`ChromaDB/chroma_data/`. It processes the CSV in batches and runs a sample
similarity query at the end. The first ingestion can take several minutes.

The ingestion script reads the fixed path
`database/base_cards_sintetica.csv`; changing the file location requires
updating `CSV_PATH` in `ChromaDB/ingest_csv.py`.

## 5. Build the aggregate collection

After ingestion, create the analytical collection from the source records:

```bash
ChromaDB/.venv/bin/python - <<'PY'
from ChromaDB.precomputed_queries import (
    build_aggregate_collection,
    open_collections,
)

source, aggregates = open_collections()
count = build_aggregate_collection(source, aggregates)
print("Aggregate rows:", count)
PY
```

In Windows PowerShell, run the same operation with the Windows virtual
environment:

```powershell
& ".\ChromaDB\.venv\Scripts\python.exe" -c "from ChromaDB.precomputed_queries import build_aggregate_collection, open_collections; source, aggregates = open_collections(); count = build_aggregate_collection(source, aggregates); print('Aggregate rows:', count)"
```

This creates `base_cards_sintetica_aggregates`, grouped at the project's
business grain. The current implementation clears and rebuilds the aggregate
collection when this function runs. It does not delete the source collection.
Rebuild after changing or re-ingesting the source CSV so dashboard and agent
results reflect the latest data.

The app requires both `base_cards_sintetica` and a non-empty
`base_cards_sintetica_aggregates` collection.

## 6. Start the frontend

From the project root, with the virtual environment activated:

```bash
streamlit run streamlit_app.py
```

Alternatively, run Streamlit directly from the environment:

```bash
ChromaDB/.venv/bin/streamlit run streamlit_app.py
```

Open the local URL printed by Streamlit in your browser. The workspace includes
an overview and the following views:

- **Ask ObsAgent:** sends the request directly to the Researcher, which calls
  validated tools and returns an evidence-backed answer. Grouped results can
  also appear as a chart. Ollama must be running for this tab.
- **Portfolio dashboard:** calculates KPIs and vintage rankings directly from
  the aggregates. These calculations are deterministic, do not call Ollama,
  and only run while the dashboard tab is selected.
- **Cómo funciona:** lists the registered tools and explains the current
  limitations. The agent can consult allowlisted `SKILLS/` guides using
  `consultar_skill`. Reading a guide does not execute the documented procedure;
  the model may also choose not to call it. Guide content is sent to the
  configured Ollama endpoint, which may be remote. The storage guide is empty.

The sidebar offers optional translation of a request to Spanish before analysis.
This adds a model call. Expand the trace under an answer to see whether
translation ran and which tools, arguments, results, or errors were returned.

By default, the app reads `ChromaDB/chroma_data`. To select a different
ChromaDB directory, set `OBSAGENT_CHROMA_PATH` before starting Streamlit or
enter the directory in the sidebar. Both required collections must exist in
that directory.

## 7. How the agents work

The roles and default prompts are in
`multi_agent_framework/agent_manager.py`.

| Stage | Agent | What it does |
|---|---|---|
| Default | Researcher | Uses an Ollama tool-calling loop to choose from registered analytics tools and returns a concise Spanish summary with evidence. |

Translator and Builder remain available for custom workflows, but the default
app skips their extra model calls.

Available Researcher tools:

- `portfolio_kpis`: portfolio measures and derived KPIs, optionally filtered.
- `cohort_curve`: KPI results by vintage and month-on-book.
- `kpis_by_dimension`: KPI results grouped by a supported dimension.
- `vintage_comparison`: compares two vintages at the same MOB.
- `segment_ranking`: ranks groups by a supported metric.
- `anomaly_candidates`: flags statistical outliers by a supported dimension.

These call validated functions in `ChromaDB/precomputed_queries.py`. Python
code, not the language model, performs the calculations. The Researcher's tool
loop is capped by `MAX_ITERATIONS` (default `8`); tool outputs are also bounded
to keep context manageable.

## 8. Make the agent ask clarifying questions

If the agent should ask for more information instead of assuming missing
details, adjust the system instructions inside `ResearcherAgent.execute`.
Specify:

1. What information is required for the request (for example, metric, vintage,
   MOB, comparison baseline, or grouping dimension).
2. Which ambiguities require clarification.
3. That it should ask one concise question and not call an analytical tool
   until the user answers.
4. That it must not guess when the user has not supplied the required
   information.

For a custom workflow that uses the Builder, adjust its instructions in
`BuilderAgent.execute` so it passes a clarification question through clearly
instead of turning it into an analysis.
The Streamlit app sends the previous user/assistant exchange with the next
request, so the user's answer is available during the follow-up. Chat history
is held in Streamlit session state, not persisted between sessions.

If the follow-up needs a new data operation rather than missing user input,
implement that operation as a validated Python function first, then expose it
as an `AgentTool` in `ResearcherAgent._build_tools`. Add its JSON argument
schema and guidance in the Researcher prompt. Avoid giving the model arbitrary
SQL or unrestricted ChromaDB access.

## 9. Customize or register agents

To change the default behavior, edit the corresponding agent class and prompt
in `multi_agent_framework/agent_manager.py`:

- `TranslatorAgent.execute`: translation and preservation of query details.
- `ResearcherAgent.execute`: research policy, tool-call policy, and evidence
  summary.
- `ResearcherAgent._build_tools`: available tools, descriptions, argument
  schemas, and Python handlers.
- `BuilderAgent.execute`: final-answer style, language, and treatment of
  incomplete results or clarification questions.

`MultiAgentSystem` registers one agent for each `AgentRole`:
`TRANSLATOR`, `RESEARCHER`, and `BUILDER`. For a custom Python workflow, create
an agent with the matching role and register it:

```python
from multi_agent_framework.agent_manager import (
    AgentRole,
    setup_multi_agent_system,
)

system = setup_multi_agent_system()
# system.register_agent(AgentRole.RESEARCHER, your_researcher)
# result = await system.execute("Your question")
```

The `QueryService` and Streamlit app initialize the default agents. If you
replace a default agent for the UI, update the service construction path in
`streamlit_app.py` / `multi_agent_framework/query_service.py` so the custom
system is the one the app uses.

## Troubleshooting

- **ChromaDB install fails with `Unsupported platform: 312` or no matching
  distribution:** on Windows, use standard x64 CPython as shown in section 2,
  not MSYS2 Python. MSYS2's platform tags prevent pip from selecting ChromaDB's
  Windows wheel, so it falls back to a source build that may fail in Maturin.
- **Missing collection:** complete the ingestion and aggregate-building steps.
- **CSV not found:** place the input file at
  `database/base_cards_sintetica.csv`, relative to the project root.
- **Missing CSV columns or parse errors:** compare its headers and value types
  with `ChromaDB/ingest_csv.py`.
- **Ollama connection error:** make sure the service is running and
  `OLLAMA_BASE_URL` or the selected `OLLAMA_DESTINO` address is reachable.
- **Model not found:** pull the model on the configured Ollama host and make
  sure `CHAT_MODEL` names it as `ollama:<model>`.
- **Incorrect or incomplete analysis:** inspect the Researcher's tool schema,
  prompt, and the deterministic query implementation. Do not solve numeric
  errors by asking the language model to calculate the KPI.

For the ChromaDB ingestion and aggregate implementation details, see
[ChromaDB/README.md](./ChromaDB/README.md). For the architecture overview, see
[README_Arquitecture.md](./README_Arquitecture.md).
