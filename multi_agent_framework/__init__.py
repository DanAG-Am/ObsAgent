"""
Multi-Agent Framework - Main Package Module

This module provides entry points for using the ObsAgent multi-agent 
system with ChromaDB segmentation capabilities.

Overview:
===========
ObsAgent implements a multi-agent architecture where three specialized agents work together:

1. Researcher Agent
   - Consults ChromaDB to answer data-based questions
   - Analyzes trends across vintages, strategies, and categories
   - Returns structured analytical findings

2. Translator Agent  
   - Translates user queries to English for efficient processing
   - Converts researcher findings back to source language
   - Reduces token usage through English intermediate representation

3. Builder Agent
   - Generates HTML reports from analysis results
   - Creates dashboard specifications
   - Produces downloadable outputs (CSV, Excel)

Architecture:
============
- Agents are registered by role in MultiAgentSystem
- Each agent has specialized tools for its function
- QueryService abstracts agent orchestration for simple API usage
- Segmented embeddings allow separate collections per category dimension

Usage Pattern:
============
>>> from obs_agent import QueryService, run_multi_agent_workflow
   
   # Simple query using high-level interface
   >>> results = await QueryService().query_kpi('delinquency_rate', vintage=2018)
   
   # Direct agent workflow
   >>> findings = await run_multi_agent_workflow("Mejores vintages")

Integration:
===========
The framework integrates with ObsAgent's existing ChromaDB setup:
- Reads from base_cards_sintetica.csv
- Uses precomputed aggregates collections
- Supports all predefined KPIs and metrics

Example Integration:
============
>>> import asyncio
>>> from obs_agent.query import QueryService, KPIType
   
   async def main():
       qs = QueryService()
       
       # Get top vintages by delinquency rate
       rankings = await qs.get_vintage_ranking(KPIType.DELINQUENCY_RATE, top_n=5)
       
       # Compare two vintages
       comparison = await qs.compare_vintages(2017, 2018)

This module re-exports convenience functions from submodules.

Submodules:
===========
- agent_manager.py: Multi-agent orchestration and agent definitions
- embeddings.py: Embedding segmentation and ChromaDB operations
- query_service.py: High-level query interface for user applications
"""

from .agent_manager import (
    Agent,
    AgentRole,
    AgentTool,
    AgentContext,
    MultiAgentSystem,
    ResearcherAgent,
    TranslatorAgent,
    BuilderAgent,
    run_multi_agent_workflow,
    setup_multi_agent_system
)
from .embeddings import (
    initialize_segmented_collections,
    get_collection_info,
    query_segmented_collection,
    generate_category_embedding,
    search_by_dimension
)
from .query_service import (
    QueryService,
    KPIType,
    get_query_service,
    setup_query_system
)

__all__ = [
    # Core classes
    'Agent',
    'AgentRole',
    'AgentTool',
    'AgentContext',
    'MultiAgentSystem',
    'ResearcherAgent',
    'TranslatorAgent',
    'BuilderAgent',
    
    # High-level functions
    'run_multi_agent_workflow',
    'setup_multi_agent_system',
    
    # Embedding functions
    'initialize_segmented_collections',
    'get_collection_info',
    'query_segmented_collection',
    'generate_category_embedding',
    'search_by_dimension',
    
    # Query service classes and functions
    'QueryService',
    'KPIType',
    'get_query_service',
    'setup_query_system',
]

# Convenience imports for common patterns
from .query_service import QueryService as QueryServiceImport


def create_multi_agent_setup():
    """Create a complete multi-agent setup."""
    return setup_multi_agent_system()


async def example_workflow():
    """Example workflow using the full system."""
    
    print("=== ObsAgent Multi-Agent Framework Demo ===\n")
    
    # Setup agents and segments
    system = setup_multi_agent_system()
    print(f"Multi-agent system initialized with {len(system._agents)} agents\n")
    
    # Initialize segmented collections
    try:
        collections = initialize_segmented_collections()
        print(f"Segmented collections initialized: {list(collections.keys())}\n")
    except Exception as e:
        print(f"Note: Collection initialization ({e})\n")
    
    # Run example query
    print("Querying data through agent workflow:")
    try:
        results = await run_multi_agent_workflow(
            "¿Cuáles son las principales vintages por estrategia?"
        )
        print(f"Results received: {type(results).__name__}")
        print(f"Keys: {results.keys() if isinstance(results, dict) else 'N/A'}")
    except Exception as e:
        print(f"(Data not available in demo)")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(example_workflow())
