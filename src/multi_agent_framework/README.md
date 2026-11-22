# ObsAgent Multi-Agent Configuration Guide

## Overview

This document outlines the multi-agent architecture for ObsAgent, adapting patterns from agenticai while leveraging ChromaDB with semantic segmentation by category.

### Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    OBSAGENT MULTI-AGENT SYSTEM               │
└─────────────────────────────────────────────────────────────┘

           ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
           │    TRANSLATOR│      │ RESEARCHER  │      │    BUILDER   │
           │             │      │              │      │            │
           │ • Spanish    │      │ • ChromaDB   │      │ • Reports   │
           │   → English  │      │   Query      │      │ • Dashboards│
           │             │      │   Analysis    │      │ • Output   │
           └──────┬───────┘      └─────────────┘      └──────┬───────┘
                  │                                      │
                  │              (context shared)          │
                  │◄──────────────────────────────────────►│
                  │              ←→                         │
                    └───────────────────────────────────────┘
```

## Agent Roles

### 1. Researcher Agent (`ResearcherAgent`)

**Primary Responsibility:** Consult ChromaDB and perform analysis

**Tools:**
- `query_aggregates`: Fetch precomputed aggregates from ChromaDB
- `calculate_metrics`: Calculate KPIs from raw data  
- `compare_vintage`: Compare two vintages side-by-side

**Integration Points:**
- Directly interfaces with segmented ChromaDB collections
- Supports all default metrics: delinquency_rate, chargeoff_rate, recovery_rate, etc.
- Operates on precomputed aggregates materialized by category

### 2. Translator Agent (`TranslatorAgent`)

**Primary Responsibility:** Language translation layer

**Tools:**
- `translate_query`: Convert user input to English (if needed)
- `translate_response`: Present findings back in source language

**Integration Points:**
- Translates queries before researcher processes them
- Converts analysis results for human consumption
- Bridges gap between user intent and machine analysis

### 3. Builder Agent (`BuilderAgent`)

**Primary Responsibility:** Generate output

**Tools:**
- `generate_report`: Create HTML reports from findings
- `create_dashboard_spec`: Generate dashboard specifications
- `export_data`: Export data to various formats

**Integration Points:**
- Receives structured analysis from researcher agent
- Generates formatted, actionable output for consumption

## Multi-Agent Workflow

### Query Flow

```
User Question (Spanish)
       │
       ▼
┌─────┴─────┐
│ Translator │
│   Agent    │
└─────┬─────┘
       │
       ├─► Translates to: "What are top vintages by strategy?"
       │
       ▼
┌─────┴─────┐
│ Researcher │
│    Agent   │
│     Tool   │
└─────┬─────┘
       │
       ├─► Query aggregates from ChromaDB
       │    by category dimension
       │
       ▼
┌─────┴─────┐
│ Researcher │
│     Return │
└─────┬─────┘
       │
       │◄─── Returns findings (English)
       │
       ▼
┌─────┴─────┐
│ Translator │
│    Agent   │
└─────┬─────┘
       │
       ├─► Translates to Spanish
       │
       ▼
┌─────┴─────┐
│ Builder    │
│    Agent   │
│     Tool   │
└─────┬─────┘
       │
       └─► Returns HTML report / CSV
```

## ChromaDB Segmentation Strategy

### Collections Structure

Each category dimension gets its own persistent collection:

| Collection Name | Description | Dimension |
|-----------------|-------------|-----------|
| `aggregates_vintage_lowercase` | Vintage temporal segmentation | 0 |
| `aggregates_strategy_segment_lowercase` | Strategy segment breakdown | 1 |
| `aggregates_product_lowercase` | Product line analysis | 2 |
| `aggregates_channel_lowercase` | Channel distribution | 3 |
| `aggregates_age_tag_lowercase` | Age cohort segmentation | 4 |
| `aggregates_score_tag_lowercase` | Score-based segmentation | 5 |

### Embedding Dimensions

Each dimension vector uses 64 dimensions:

```python
embedding_vector = [f0, f1, f2, ..., f63]
```

Where each component is normalized and derived from:
- Category name hash (60%)
- Filter criteria hash (40%)

### Materialization Flow

```
CSV Data (base_cards_sintetica.csv)
        │
        ▼
Precompute Aggregates
└─────────────┬──────────┐
              │          │
              ▼          │
    ┌─────────────────────┤
    │ Group by Dimension  │
    ├─► Vintage           │ (dim: vintage year)
    ├─► Strategy Segment │
    ├─► Product          │
    └─► Channel          │
                          │
                          ▼
                   ChromaDB Collection
                    (Persistent)
```

## Integration with Existing ObsAgent

### File Locations

| Module | Path | Purpose |
|--------|------|---------|
| Agent Manager | `src/multi_agent_framework/agent_manager.py` | Core agent orchestration |
| Embeddings | `src/multi_agent_framework/embeddings.py` | ChromaDB operations & segmentation |
| Query Service | `src/multi_agent_framework/query_service.py` | High-level query interface |

### Configuration Files

| File | Purpose |
|------|---------|
| `ChromaDB/README.md` | Existing setup guidance |
| `setup_multi_agent_config.yaml` | Multi-agent configuration (new) |

### ChromaDB Setup Integration

The multi-agent system integrates with ObsAgent's existing ChromaDB:

```python
# Read from existing source
from obs_agent import QueryService

qs = QueryService()
# Uses same base path as existing chroma_data.py
qs._base_path = "ChromaDB/chroma_data"

# Precomputed aggregates available via segmented collections
aggregates_collection = qs._system._embedding_collections['vintage']
```

## Usage Examples

### Basic Query Flow

```python
import asyncio
from obs_agent import run_multi_agent_workflow

async def example():
    # Spanish query through full pipeline
    results = await run_multi_agent_workflow(
        "¿Cuáles son las principales vintages por estrategia?"
    )
    
    # Extract findings from researcher agent
    findings = results['research_findings']
    
    # Format output with builder if needed
    html_report = format_output(findings)
```

### KPI Queries

```python
from obs_agent import QueryService, KPIType

qs = QueryService()

# Query delinquency rate for specific vintage
rankings = await qs.get_vintage_ranking(
    KPIType.DELINQUENCY_RATE,
    top_n=5
)

# Compare two vintages
comparison = await qs.compare_vintages(2017, 2018)
```

### Category-Segmented Query

```python
async def segment_query():
    # Query segmented by product category
    results = await run_multi_agent_workflow(
        "Mejores productos por rendimiento", 
        category='product'
    )
    
    # Or use high-level query
    top_products = await qs.get_vintage_ranking(
        metric='revenue',
        group_by='product',
        n_results=10
    )
```

## Configuration Options

### Setup Configuration

Create `setup_multi_agent_config.yaml`:

```yaml
multi_agent:
  agents:
    translator:
      model: "llama3-8b"  # or your choice
      language_pairs:
        - es→en
        - es→es
    
    researcher:
      model: "llama3-8b"
      kpis: ["delinquency_rate", "recovery_rate"]
      
    builder:
      model: "llama3-8b"
      output_formats:
        - html
        - csv
        - excel

chroma_db:
  path: "ChromaDB/chroma_data"
  source_collection: "base_cards_sintetica"
  
  collections:
    - vintage
    - strategy_segment
    - product
    - channel
    - age_tag
    - score_tag
  
embedding:
  dimension: 64
  batch_size: 5000

workflow:
  agent_sequence: [translator, researcher, builder]
  max_iterations: 10
```

## Next Steps

1. **Implement actual ChromaDB integration** in `embeddings.py`
2. **Create concrete tool implementations** for each agent
3. **Add unit tests** for multi-agent interactions
4. **Integrate with existing ObsAgent dashboard generation**
5. **Set up CI/CD pipeline** for multi-agent system

## References

- Agenticai patterns: `/agenticai/src/nas_agente/agentes.py`
- ChromaDB setup: `/ObsAgent/ChromaDB/README.md`
- Precomputed queries: `/ObsAgent/ChromaDB/precomputed_queries.py`
