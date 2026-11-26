"""ObsAgent's Ollama-backed multi-agent framework."""

from .agent_manager import (
    Agent,
    AgentContext,
    AgentRole,
    AgentTool,
    BuilderAgent,
    MultiAgentSystem,
    ResearcherAgent,
    TranslatorAgent,
    run_multi_agent_workflow,
    setup_multi_agent_system,
)
from .embeddings import (
    generate_category_embedding,
    get_collection_info,
    initialize_segmented_collections,
    query_segmented_collection,
    search_by_dimension,
)
from .query_service import (
    KPIType,
    QueryService,
    get_query_service,
    setup_query_system,
)

__all__ = [
    "Agent",
    "AgentContext",
    "AgentRole",
    "AgentTool",
    "BuilderAgent",
    "generate_category_embedding",
    "get_collection_info",
    "KPIType",
    "MultiAgentSystem",
    "QueryService",
    "ResearcherAgent",
    "TranslatorAgent",
    "get_query_service",
    "initialize_segmented_collections",
    "query_segmented_collection",
    "run_multi_agent_workflow",
    "setup_multi_agent_system",
    "setup_query_system",
    "search_by_dimension",
]
