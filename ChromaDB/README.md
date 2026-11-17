# Local ChromaDB CSV example

This project ingests `../database/base_cards_sintetica.csv` into a local,
persistent Chroma collection. 

## Setup

Run these commands from the repository root. Meaning, 
try to always cd into ChromaDB folder before running.
Python 3.12 is recommended:

```bash
python3.12 -m venv ChromaDB/.venv
ChromaDB/.venv/bin/python -m pip install --upgrade pip
ChromaDB/.venv/bin/python -m pip install -r ChromaDB/requirements.txt
```

If `ChromaDB/.venv` already exists, skip the first command.
If your terminal prompt ends in `ChromaDB %`, first run `cd ..`, or use
`.venv/bin/python` and paths relative to the current directory instead. 

## Ingest the CSV

```bash
ChromaDB/.venv/bin/python ChromaDB/ingest_csv.py
```

The script reads the CSV in batches, upserts every row into the
`base_cards_sintetica` collection, and runs a sample similarity query. It
prints the number of ingested rows, collection count, query, and results.
The first full ingestion can take several minutes and requires several
gigabytes of local disk space.

The local database is stored in `ChromaDB/chroma_data/`. Running the script
again is safe: the same row IDs are upserted, so records are preserved rather
than deleted.

## Confirm the database and data

Check the installed Chroma version:

```bash
ChromaDB/.venv/bin/python -c "import chromadb; print(chromadb.__version__)"
```

Confirm that the collection exists and contains the expected rows:

```bash
ChromaDB/.venv/bin/python - <<'PY'
import chromadb

client = chromadb.PersistentClient(path="ChromaDB/chroma_data")
collection = client.get_collection("base_cards_sintetica")
print("collection:", collection.name)
print("row count:", collection.count())
print("sample IDs:", collection.peek(3)["ids"])
PY
```

The command above must be run from the repository root. If you are already
inside `ChromaDB`, use this equivalent command instead:

```bash
.venv/bin/python - <<'PY'
import chromadb

client = chromadb.PersistentClient(path="chroma_data")
collection = client.get_collection("base_cards_sintetica")
print("collection:", collection.name)
print("row count:", collection.count())
print("sample IDs:", collection.peek(3)["ids"])
PY
```

When copying a command from this README, copy only the contents of the code
block; do not copy the ``` markers.

The current CSV contains 1,089,833 rows, so a successful import should report
that count. You can also confirm that the persisted files exist:

```bash
du -sh ChromaDB/chroma_data
```

## Precomputed analytical queries

`precomputed_queries.py` materializes the source collection into
`base_cards_sintetica_aggregates`, grouped by vintage, MOB, product, channel,
strategy, strategy segment, age band, and score band. The query functions then
apply validated ChromaDB metadata filters and calculate KPIs deterministically.

Run this from the repository root after ingestion:

```bash
ChromaDB/.venv/bin/python - <<'PY'
from ChromaDB.precomputed_queries import (
    build_aggregate_collection,
    open_collections,
)

source, aggregates = open_collections()
print("aggregate rows:", build_aggregate_collection(source, aggregates))
PY
```

The language model should call `portfolio_kpis`, `cohort_curve`,
`vintage_comparison`, `kpis_by_dimension`, `segment_ranking`, or
`anomaly_candidates` with validated parameters. It must not construct
arbitrary ChromaDB filters or SQL.

To confirm retrieval as well as storage, rerun the ingestion command and check
that its output includes `Collection count: 1,089,833` and a `Results:` section.
