# ObsAgent
This repository holds source code for TC3009C class. ObsAgent is an Ollama-powered, conversational implementation that automatically fetches databases, creates dashboard and html reports with insightful bullets.

## Local ChromaDB CSV ingest

The complete local ChromaDB example is in [`ChromaDB/`](ChromaDB/). It
ingests `database/base_cards_sintetica.csv` into a persistent collection
without using Chroma Cloud. Follow the setup, ingestion, and verification
steps in [`ChromaDB/README.md`](ChromaDB/README.md).
