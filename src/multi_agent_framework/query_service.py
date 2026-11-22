"""
Query Service Module for ObsAgent Multi-Agent System.

This module provides a unified interface for querying the database using 
the multi-agent framework. It abstracts the complexity of agent 
orchestration and ChromaDB segmentation into simple, intuitive API calls.

Key features:
- Natural language query processing through agents
- Semantic search with category segmentation
- Access to all precomputed aggregates
- Integration with dashboard generation capabilities
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from .agent_manager import (
    MultiAgentSystem, 
    run_multi_agent_workflow,
    setup_multi_agent_system
)
from .embeddings import (
    initialize_segmented_collections,
    query_segmented_collection,
    get_collection_info
)


# =============================================================================
# Query Service Classes
# =============================================================================

class QueryService:
    """
    High-level query service for ObsAgent multi-agent system.

    Provides intuitive API for querying data through the agent framework.
    
    Example:
        >>> from obs_agent.query import QueryService, KPIType
        >>> qs = QueryService()
        >>> results = await qs.kpi('delinquency_rate', vintage=2018)
        >>> print(f"KPI result: {results}")
    """

    def __init__(self):
        """Initialize the query service with default agents."""
        self._system = setup_multi_agent_system()
        self._segmented_collections = initialize_segmented_collections()

    def set_source_path(self, path: str) -> None:
        """Set the source ChromaDB data path."""
        pass  # Would update base paths in agent/system configs

    async def query_kpi(
        self,
        kpi_type: KPIType | str,
        vintage: Optional[int] = None,
        mob: Optional[int] = None,
        filters: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Query a specific KPI from the database.

        Args:
            kpi_type: Type of KPI (e.g., 'delinquency_rate', 'revenue')
            vintage: Vintage year to query (optional)
            mob: Month on book (optional)
            filters: Additional filter criteria (optional)

        Returns:
            Dict containing KPI value and context
        
        Example:
            >>> from obs_agent.query import QueryService, KPIType
            >>> qs = QueryService()
            >>> result = await qs.kpi(KPIType.DELINQUENCY_RATE, vintage=2018)
            >>> print(f"2018 vintage delinquency: {result['value']:.2f}%")
        """
        
        # Convert to agent framework language if needed
        query_text = self._format_kpi_query(kpi_type, vintage, mob, filters)
        
        # Run through multi-agent workflow
        result = await run_multi_agent_workflow(query_text)
        
        return result.get('research_findings', {})

    async def get_vintage_ranking(
        self,
        sort_metric: str | KPIType = 'delinquency_rate_amount',
        descending: bool = True,
        top_n: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get ranked vintages by metric.

        Args:
            sort_metric: Metric to rank by (e.g., 'delinquency_rate')
            descending: Sort direction (True for highest first)
            top_n: Number of results
        
        Returns:
            List of ranked vintage objects
        
        Example:
            >>> from obs_agent.query import QueryService, KPIType
            >>> qs = QueryService()
            >>> rankings = await qs.vintage_ranking(KPIType.GROSS_CHARGOFF_RATE)
            >>> print(f"Top vintage: {rankings[0]['vintage']}")
        """
        
        query_text = f"Mejores vintages por {sort_metric.lower()}, {top_n} resultados"
        result = await run_multi_agent_workflow(query_text)
        
        return result.get('research_findings', [])

    async def search_semantically(
        self,
        query: str,
        category: Optional[str] = None,
        n_results: int = 10
    ) -> dict[str, Any]:
        """
        Perform semantic search with optional category segmentation.

        Args:
            query: Natural language query text
            category: Category to segment by (optional)
            n_results: Number of results
        
        Returns:
            Results from segmented collection
        
        Example:
            >>> from obs_agent.query import QueryService, KPIType
            >>> qs = QueryService()
            >>> results = await qs.semantic_search("mejores productos premium", category='product')
            >>> print(f"Found {len(results['metadatas'])} results")
        """
        
        # Use appropriate query method based on category
        if category:
            from .embeddings import query_segmented_collection
            
            return await self._semantic_search_internal(
                category=category,
                query_text=query,
                n_results=n_results
            )
        else:
            return {
                "error": "Category required for segmented search"
            }

    async def get_category_metrics(
        self,
        category: str,
        metrics: list[KPIType | str] = None
    ) -> dict[str, Any]:
        """
        Get aggregated metrics for a category.

        Args:
            category: Category name (vintage, product, strategy_segment, etc.)
            metrics: Specific metrics to retrieve
        
        Returns:
            Aggregated metrics for the category
        
        Example:
            >>> from obs_agent.query import QueryService
            >>> qs = QueryService()
            >>> metrics = await qs.category_metrics('vintage')
            >>> print(f"Vintage aggregated metrics available")
        """
        
        # Use aggregation materialization function
        result = await run_multi_agent_workflow(
            f"Analiza los agregados de {category}"
        )
        
        return result.get('research_findings', {})

    async def compare_vintages(
        self,
        baseline_vintage: int,
        comparison_vintage: int,
        metrics: list[str] = None
    ) -> dict[str, Any]:
        """
        Compare two vintages side by side.

        Args:
            baseline_vintage: Baseline vintage year
            comparison_vintage: Vintage to compare against
            metrics: Metrics to include in comparison
        
        Returns:
            Dict containing comparative analysis including deltas
        
        Example:
            >>> from obs_agent.query import QueryService
            >>> qs = QueryService()
            >>> result = await qs.compare_vintages(2017, 2018)
            >>> print(f"Delta in delinquency: {result['metric_delta']['delinquency_rate_amount']:.2f}pp")
        """
        
        query_text = f"Compara vintage {baseline_vintage} con {comparison_vintage}"
        result = await run_multi_agent_workflow(query_text)
        
        return result.get('research_findings', {})

    def _format_kpi_query(
        self,
        kpi_type: KPIType | str,
        vintage: Optional[int],
        mob: Optional[int],
        filters: Optional[dict]
    ) -> str:
        """Internal method to format query for agent."""
        
        if not vintage:
            return f"¿Cuáles son las principales {kpi_type}?"
        
        if not mob:
            return f"Mejores vintages por {kpi_type}, año {vintage}"
        
        return f"Análisis de KPI {kpi_type} para vintage {vintage} y mes {mob}"


class KPIType(Enum):
    """Enumeration of available KPI types."""

    DELINQUENCY_RATE = "delinquency_rate_amount"
    DELINQUENCY_RATE_ACCOUNTS = "delinquency_rate_accounts"
    GROSS_CHARGOFF_RATE = "gross_chargeoff_rate"
    NET_CHARGOFF_RATE = "net_chargeoff_rate"
    RECOVERY_RATE = "recovery_rate"
    UTILIZATION_RATE = "utilization_rate"
    OPERATING_MARGIN = "operating_margin"


# =============================================================================
# Helper Functions
# =============================================================================

def get_query_service() -> QueryService:
    """Get singleton instance of query service."""
    return QueryService()


def setup_query_system(
    base_path: str = "ChromaDB/chroma_data",
    source_name: str = "base_cards_sintetica"
) -> QueryService:
    """
    Setup the complete query system.

    Initializes all components including agents and segmented collections.

    Args:
        base_path: ChromaDB storage directory
        source_name: Name of source collection in database
        
    Returns:
        Configured QueryService instance
    
    Example:
        >>> from obs_agent.query import setup_query_system
        >>> qs = setup_query_system("ChromaDB/chroma_data", "full_cards")
    """
    
    service = QueryService()
    service._base_path = base_path
    service._source_name = source_name
    
    return service


async def demo():
    """Demonstrate query service functionality."""
    
    # Create instance
    qs = QueryService()
    
    # Example KPI query
    print("=== ObsAgent Query Service Demo ===\n")
    
    print("1. Querying vintage ranking:")
    try:
        rankings = await qs.get_vintage_ranking(KPIType.DELINQUENCY_RATE, top_n=5)
        print(f"Top 5 vintages by delinquency rate:")
        for rank, r in enumerate(rankings[:5], 1):
            print(f"   {rank}. Vintage: {r.get('vintage', 'N/A')}")
    except Exception as e:
        print(f"Demo error (expected without data): {e}\n")
    
    print("2. Querying category metrics:")
    try:
        metrics = await qs.get_category_metrics('vintage')
        print(f"Found categories: {list(metrics.keys())[:5] if isinstance(metrics, dict) else '...'}")
    except Exception as e:
        print(f"Demo error (expected): {e}\n")
    
    print("3. Semantic search example:")
    try:
        results = await qs.search_semantically(
            query="mejores productos",
            category='product',
            n_results=5
        )
        print(f"Semantic search returned {len(results['results'])} results\n")
    except Exception as e:
        print(f"Demo error (expected): {e}\n")
    
    print("=== Demo Complete ===")


# =============================================================================
# Export functions for easy import
# =============================================================================

__all__ = [
    'QueryService',
    'KPIType',
    'get_query_service',
    'setup_query_system',
    'run_multi_agent_workflow',
    'initialize_segmented_collections',
]


if __name__ == "__main__":
    asyncio.run(demo())
