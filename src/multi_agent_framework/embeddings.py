"""
Embedding Segmentation Module for ObsAgent.

This module handles semantic segmentation of ChromaDB embeddings by category,
allowing separate collections for different business dimensions:
- vintages (temporal segmentation)
- strategy segments (product/strategy breakdown)
- products (individual product lines)
- channels (distribution channels)
- age_tags and score_tags

Each segmented collection provides focused analytical capability with 
reduced noise from unrelated categories.

Key patterns:
- Each category has its own ChromaDB collection
- Aggregates are materialized per category dimension
- Queries can be scoped to specific segments for targeted analysis
"""

from __future__ import annotations

import hashlib
import chromadb
from typing import Any, Callable, Optional


# =============================================================================
# Configuration Constants
# =============================================================================

EMBEDDING_DIMENSION = 64  # Standard ChromaDB embedding dimension
BATCH_SIZE = 5000  # Batch size for aggregation materialization

CATEGORIES = {
    "vintage": "Temporal segmentation by vintage year",
    "strategy_segment": "Strategy segment breakdown", 
    "product": "Individual product lines",
    "channel": "Distribution channel analysis",
    "age_tag": "Age cohort segmentation",
    "score_tag": "Score-based customer segmentation",
}

# Dimension mapping for data retrieval
DIMENSIONS = {
    "vintage": 0,
    "strategy": 1, 
    "strategy_segment": 2,
    "product": 3,
    "channel": 4,
    "age_tag": 5,
    "score_tag": 6,
}


# =============================================================================
# Embedding Generation Functions
# =============================================================================

def generate_category_embedding(category: str) -> list[float]:
    """
    Generate a deterministic embedding for a category dimension.

    Creates a stable, reproducible vector using hash-based approach.
    
    Args:
        category: Category name or identifier
        
    Returns:
        Normalized embedding vector of specified dimension
    """
    # Create hash from category name
    category_hash = hashlib.sha256(category.encode('utf-8')).digest()
    
    # Distribute across dimensions using hash values
    embedding = []
    for i in range(EMBEDDING_DIMENSION):
        value = (i * 13 + sum(category_hash[j:i % len(category_hash)] 
                           for j in range(len(category_hash)))) / 256.0
        embedding.append(value)
    
    # Normalize to unit vector
    magnitude = sum(x**2 for x in embedding)**0.5
    
    return [val / magnitude for val in embedding]


def generate_aggregate_embedding(category: str, filters: dict[str, Any]) -> list[float]:
    """
    Generate embedding for aggregated data with specific filters.

    Combines category and filter information into a composite embedding.
    
    Args:
        category: Primary category for aggregation
        filters: Dict of filter criteria
        
    Returns:
        Composite embedding vector incorporating filters
    """
    # Create composite key from category + filters
    key_str = f"{category}:{filters}"
    combined_hash = hashlib.sha256(key_str.encode('utf-8')).digest()
    
    # Merge with category base embedding
    base_embedding = generate_category_embedding(category)
    filter_contributions = [0.0] * EMBEDDING_DIMENSION
    
    for i, val in enumerate(combined_hash):
        if val % 2:
            filter_contributions[i] = 1.0
    
    # Weighted combination
    final_embedding = []
    for i in range(EMBEDDING_DIMENSION):
        weight = 0.6 * base_embedding[i] + 0.4 * filter_contributions[i]
        final_embedding.append(weight)
    
    return [val / sum(x**2 for x in final_embedding) if final_embedding else 0.0 
             for val in final_embedding]


# =============================================================================
# Collection Management Functions
# =============================================================================

def initialize_segmented_collections(
    base_path: str = "ChromaDB/chroma_data"
) -> dict[str, chromadb.Collection]:
    """
    Initialize ChromaDB collections for each category.

    Creates separate persistent collections for segmentation by dimension.
    
    Args:
        base_path: Base directory for ChromaDB storage
        
    Returns:
        Dict mapping category names to their collection objects
        
    Example:
        >>> from obs_agent.embeddings import initialize_segmented_collections
        >>> collections = initialize_segmented_collections()
        >>> vintage_collection = collections['vintage']
        >>> product_collection = collections['product']
    """
    
    client = chromadb.PersistentClient(path=base_path)
    
    # Initialize collections for each category
    collections = {}
    for category, description in CATEGORIES.items():
        collection_name = f"aggregates_{category}_lowercase"
        
        try:
            if not client.get_collection(collection_name):
                # Create new collection with appropriate metadata schema
                collection = client.create_collection(
                    name=collection_name,
                    metadata={
                        "description": description,
                        "dimensions": list(DIMENSIONS.values()),
                        "supported_metrics": [
                            "delinquency_rate_amount",
                            "delinquency_rate_accounts", 
                            "gross_chargeoff_rate",
                            "net_chargeoff_rate",
                            "recovery_rate",
                            "utilization_rate"
                        ]
                    }
                )
                collections[category] = collection
                print(f"Created collection: {collection_name}")
        except Exception as e:
            # Try to get if it already exists
            try:
                collections[category] = client.get_collection(collection_name)
            except Exception as e2:
                raise RuntimeError(
                    f"Failed to create or retrieve collection '{category}': "
                    f"{e}, {e2}"
                )

    print(f"Initialized {len(collections)} segmented collections")
    return collections


def get_or_create_segmented_collection(category: str, base_path: str) -> chromadb.Collection:
    """
    Get existing or create new collection for category.

    Ensures the collection exists, creating if necessary.
    
    Args:
        category: Category name
        
    Returns:
        Collection object ready for queries
        
    Example:
        >>> from obs_agent.embeddings import get_or_create_segmented_collection
        >>> vintage_collection = get_or_create_segmented_collection('vintage')
        >>> documents = vintage_collection.get()
    """
    
    client = chromadb.PersistentClient(path=base_path)
    
    collection_name = f"aggregates_{category}_lowercase"
    
    # Try to get existing
    try:
        return client.get_collection(collection_name)
    except Exception:
        # Create new if doesn't exist
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "description": CATEGORIES.get(category, f"Segmented {category} data"),
                "dimensions": list(DIMENSIONS.values()),
                "supported_metrics": DEFAULT_METRICS_LIST
            }
        )
        
        return collection


def get_collection_info(category: str) -> dict[str, Any]:
    """
    Get information about a segmented collection.

    Returns metadata and statistics for the specified category collection.
    
    Args:
        category: Category name
        
    Returns:
        Dict containing collection info (dimension, document count, etc.)
        
    Example:
        >>> from obs_agent.embeddings import get_collection_info
        >>> info = get_collection_info('vintage')
        >>> print(f"Vintage collection has {info['document_count']} documents")
    """
    
    client = chromadb.PersistentClient("ChromaDB/chroma_data")
    collection_name = f"aggregates_{category}_lowercase"
    
    try:
        collection = client.get_collection(collection_name)
        return {
            "name": collection_name,
            "dimension": EMBEDDING_DIMENSION,
            "document_count": len(collection.count() or []),
            "description": CATEGORIES.get(category, f"Segmented {category} data")
        }
    except Exception:
        return {
            "name": collection_name,
            "status": "not_found",
            "message": f"Collection '{category}' not found"
        }


# =============================================================================
# Query Functions
# =============================================================================

def query_segmented_collection(
    category: str,
    query_text: str,
    n_results: int = 10,
    where: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Query a segmented collection with semantic search.

    Retrieves similar documents from the specific category embedding 
    collection.
    
    Args:
        category: Category to query within
        query_text: Text for semantic similarity search
        n_results: Number of results to return
        where: Filter criteria for precise queries
        
    Returns:
        Dict with results, documents, and distances
        
    Example:
        >>> from obs_agent.embeddings import query_segmented_collection
        >>> results = query_segmented_collection('vintage', 'mejores vintages')
        >>> print(f"Found {len(results['results'])} similar records")
    """
    
    client = chromadb.PersistentClient("ChromaDB/chroma_data")
    collection_name = f"aggregates_{category}_lowercase"
    
    # Query with segmentation and optional filters
    results = client.query(
        collection_name=collection_name,
        texts=[query_text],
        n_results=n_results,
        where=where
    )
    
    return {
        "category": category,
        "n_results": results["ids"][0] if results["ids"] and results["ids"][0] else 0,
        "results": results.get("results", []),
        "metadatas": results.get("metadatas", [])
    }


def search_by_dimension(
    category: str,
    dimension_value: Any,
    metric: str,
    n_results: int = 10
) -> dict[str, Any]:
    """
    Search by specific dimension value within category.

    Performs exact match filtering on a categorical dimension combined 
    with semantic search in the embedding space.
    
    Args:
        category: Category to search in
        dimension_value: Value to filter by (string or numeric)
        metric: Metric column for ranking results
        n_results: Number of top results
        
    Returns:
        Results sorted by specified metric
        
    Example:
        >>> from obs_agent.embeddings import search_by_dimension
        >>> ranked = search_by_dimension('product', 'premium', 'revenue')
        >>> print(f"Top 5 products: {len(ranked)} results")
    """
    
    client = chromadb.PersistentClient("ChromaDB/chroma_data")
    collection_name = f"aggregates_{category}_lowercase"
    
    # Build filter with dimension and metric
    filters = {dimension_value: dimension_value}  # Exact match
    
    results = client.query(
        collection_name=collection_name,
        where=filters,
        n_results=n_results,
        include=["metadatas"]
    )
    
    return {
        "category": category,
        "dimension": dimension_value,
        "metric": metric,
        "n_results": len(results.get("results", [])) if results else 0,
        "ranked_items": [r["metadata"] for r in results.get("results", [])] if results else []
    }


# =============================================================================
# Aggregation Materialization Functions
# =============================================================================

def materialize_aggregates_for_category(
    category: str,
    base_path: str = "ChromaDB/chroma_data"
) -> int:
    """
    Materialize precomputed aggregates for a category.

    Creates or updates the aggregation collection with aggregated 
    data from the source database, organized by category dimension.
    
    Args:
        category: Category to materialize
        
    Returns:
        Number of aggregate records created/update
        
    Example:
        >>> from obs_agent.embeddings import materialize_aggregates_for_category
        >>> count = materialize_aggregates_for_category('vintage')
        >>> print(f"Materialized {count} vintage aggregates")
    """
    
    client = chromadb.PersistentClient(base_path)
    collection_name = f"aggregates_{category}_lowercase"
    
    # Get existing aggregate count from source  
    source_collection = client.get_collection(
        "base_cards_sintetica"  # or configurable name
    )
    
    # Perform aggregation (simplified implementation)
    # Would process full dataset, group by category dimensions
    aggregates_created = compute_aggregates_for_category(category, source_collection)
    
    # Upsert to ChromaDB collection
    try:
        client.get_or_create_collection(collection_name)
        upsert_result = client.upsert(
            ids=[f"agg-{category}-{i}" for i in range(aggregates_created)],
            documents=["Aggregated data"],
            embeddings=[generate_category_embedding(category)] * aggregates_created
        )
    except Exception:
        # Collection might already exist
        pass
    
    return aggregates_created


def compute_aggregates_for_category(
    category: str,
    source_collection: chromadb.Collection
) -> int:
    """
    Compute aggregated statistics for a category.

    Groups data by specified dimensions and computes measures/KPIs.
    
    Args:
        category: Category to aggregate
        
    Returns:
        Number of aggregate records
        
    Note: This would process actual CSV data in production
    """
    # Simplified aggregation logic - would use pandas or similar
    return 1


# =============================================================================
# Utility Functions
# =============================================================================

def get_default_base_path() -> str:
    """Get default ChromaDB path for ObsAgent."""
    import os
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "ChromaDB", "chroma_data"
    )


def reset_category_collection(category: str) -> bool:
    """
    Reset/reinitialize collection for category.

    Deletes existing aggregates and prepares for fresh computation.
    
    Args:
        category: Category to reset
        
    Returns:
        Whether operation succeeded
        
    Example:
        >>> from obs_agent.embeddings import reset_category_collection
        >>> success = reset_category_collection('vintage')
    """
    import chromadb
    
    client = chromadb.PersistentClient("ChromaDB/chroma_data")
    collection_name = f"aggregates_{category}_lowercase"
    
    try:
        if collection_exists := client.get_collections().get(collection_name):
            client.delete_collection(collection_name)
        return True
    except Exception:
        return False


def collection_exists(category: str) -> bool:
    """Check if segmented collection exists."""
    import chromadb
    
    client = chromadb.PersistentClient("ChromaDB/chroma_data")
    collection_name = f"aggregates_{category}_lowercase"
    
    try:
        collections = client.get_collections()
        return collection_name in collections
    except Exception:
        return False


# =============================================================================
# Main entry point for testing
# =============================================================================

def demo():
    """Demonstrate embedding segmentation functionality."""
    
    print("=== ObsAgent Embedding Segmentation Demo ===\n")
    
    # Initialize collections
    print("Initializing segmented collections...")
    collections = initialize_segmented_collections()
    print(f"Created {len(collections)} category collections\n")
    
    # Query example
    print("Querying vintage aggregation...")
    results = query_segmented_collection('vintage', 'mejores vintages')
    print(f"Found {results['n_results']} similar records\n")
    
    # Check collection info
    print("Collection information:")
    for cat, info in collections.items():
        print(f"  {cat}: {info}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    demo()
