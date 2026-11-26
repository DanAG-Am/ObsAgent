#!/usr/bin/env python3
"""Check ObsAgent's local ChromaDB and Ollama configuration."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    import chromadb

    from multi_agent_framework.agent_manager import DEFAULT_CHROMA_PATH
    from multi_agent_framework.agentlib.ollama import base_url, modelo_configurado

    if not DEFAULT_CHROMA_PATH.exists():
        print(f"ChromaDB directory not found: {DEFAULT_CHROMA_PATH}")
        return 1

    client = chromadb.PersistentClient(path=str(DEFAULT_CHROMA_PATH))
    collections = {
        collection.name if hasattr(collection, "name") else collection
        for collection in client.list_collections()
    }
    required = {"base_cards_sintetica", "base_cards_sintetica_aggregates"}
    missing = sorted(required - collections)
    if missing:
        print(f"Missing ChromaDB collections: {', '.join(missing)}")
        print("Follow ChromaDB/README.md to ingest data and build aggregates.")
        return 1

    source = client.get_collection("base_cards_sintetica")
    aggregates = client.get_collection("base_cards_sintetica_aggregates")
    if aggregates.count() == 0:
        print("The aggregate collection is empty; build aggregates before use.")
        return 1

    print(f"Source records: {source.count():,}")
    print(f"Aggregate records: {aggregates.count():,}")
    print(f"Ollama URL: {base_url()}")
    print(f"Ollama model: {modelo_configurado()}")
    print("ObsAgent multi-agent prerequisites are available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
