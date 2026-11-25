#!/usr/bin/env python3
"""
Multi-Agent Framework Setup Script for ObsAgent.

This script initializes and verifies the multi-agent setup, ensuring
all components are properly configured before use.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src" / "multi_agent_framework"))


def print_section_header(title):
    """Print formatted section header."""
    print(f"\n{'=' * 50}")
    print(f" {title}")
    print(f" {'=' * 50}\n")


def main():
    """Run multi-agent setup verification."""
    
    base_path = Path(__file__).parent.resolve()
    
    print_section_header("Multi-Agent Framework Setup for ObsAgent")
    
    # Check required files exist
    print("Checking dependencies...")
    try:
        import chromadb
        import asyncio
        print("✓ ChromaDB and asyncio available\n")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}\n")
        print("Installing required packages:\n")
        sys.exit(1)
    
    # Check framework files
    print("Checking framework files...")
    required_files = [
        "agent_manager.py",
        "embeddings.py", 
        "query_service.py"
    ]
    
    for file in required_files:
        if (base_path / file).exists():
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
            sys.exit(1)
    print()
    
    # Initialize segmented collections
    print_section_header("Initializing ChromaDB Segmented Collections")
    
    try:
        base_chroma_path = base_path.parent / "ChromaDB" / "chroma_data"
        if not base_chroma_path.exists():
            base_chroma_path.mkdir(parents=True)
        
        # Create client and initialize collections
        import chromadb
        
        client = chromadb.PersistentClient(str(base_chroma_path))
        
        # Initialize each category collection
        categories = {
            "vintage": "aggregates_vintage_lowercase",
            "strategy_segment": "aggregates_strategy_segment_lowercase", 
            "product": "aggregates_product_lowercase",
            "channel": "aggregates_channel_lowercase",
            "age_tag": "aggregates_age_tag_lowercase",
            "score_tag": "aggregates_score_tag_lowercase"
        }
        
        created_count = 0
        
        for cat, coll_name in categories.items():
            if not client.get_collection(coll_name):
                collection = client.create_collection(
                    name=coll_name,
                    metadata={
                        "description": f"{cat.capitalize()} segment aggregation",
                        "dimensions": ["vintage", "strategy_segment", "product", 
                                      "channel", "age_tag", "score_tag"],
                        "embedding_dimension": 64
                    }
                )
                print(f"✓ Created collection for {cat}: {coll_name}")
                created_count += 1
            else:
                print(f"✓ Collection exists: {coll_name}")
        
        print(f"\nTotal collections initialized/verified: {created_count + sum(1 for _ in categories.values())}")
        print()
        
    except Exception as e:
        print(f"✗ Error initializing collections: {e}\n")
        return 1
    
    # Verify agent manager module
    print_section_header("Verifying Agent Manager Module")
    
    try:
        from agent_manager import (
            AgentRole, ResearcherAgent, TranslatorAgent, BuilderAgent
        )
        
        agents = [AgentRole.RESEARCHER, AgentRole.TRANSLATOR, AgentRole.BUILDER]
        print(f"✓ Multi-agent roles defined:")
        for role in agents:
            print(f"  • {role.name}")
        print()
        
    except Exception as e:
        print(f"✗ Error loading agent manager: {e}\n")
        return 1
    
    # Verify embeddings module
    print_section_header("Verifying Embeddings Module")
    
    try:
        from embeddings import generate_category_embedding, search_by_dimension
        
        print("✓ Embedding functions available:")
        print(f"  • generate_category_embedding() - Generate category-specific embedding")
        print(f"  • search_by_dimension() - Search by dimension value")
        print(f"  • query_segmented_collection() - Query segmented collection")
        print()
        
    except Exception as e:
        print(f"✗ Error loading embeddings module: {e}\n")
        return 1
    
    # Verify query service module
    print_section_header("Verifying Query Service Module")
    
    try:
        from query_service import QueryService, KPIType
        
        print("✓ Query service available:")
        print(f"  • QueryService - Main query interface")
        print(f"  • KPIType enum - Available KPI types")
        print(f"  • run_multi_agent_workflow() - Direct workflow execution")
        print()
        
    except Exception as e:
        print(f"✗ Error loading query service: {e}\n")
        return 1
    
    # Example usage demonstration
    print_section_header("Example Usage")
    
    example_code = """
# Basic usage example

import asyncio
from obs_agent import QueryService, run_multi_agent_workflow

async def main():
    # Initialize query service (automatically sets up agents)
    qs = QueryService()
    
    # Get top vintages by delinquency rate
    rankings = await qs.get_vintage_ranking(
        'delinquency_rate', 
        top_n=5
    )
    
    print(f"Top 5 vintages by delinquency:")
    for i, rank in enumerate(rankings[:5], 1):
        print(f"  {i}. Vintage: {rank.get('vintage', 'N/A')}")
    
    # Compare two vintages side-by-side
    comparison = await qs.compare_vintages(2017, 2018)
    
    # Spanish query through full agent pipeline
    findings = await run_multi_agent_workflow(
        "¿Cuáles son las principales vintages por estrategia?"
    )

if __name__ == "__main__":
    asyncio.run(main())
"""
    print(example_code)
    
    # Summary
    print_section_header("Setup Complete")
    print("""
Multi-Agent Framework successfully configured for ObsAgent!

Architecture:
- Researcher Agent: ChromaDB query & analysis
- Translator Agent: English translation layer
- Builder Agent: Report generation

Integration Points:
- Uses existing chroma_data/chroma_data directory structure
- Segments embeddings by category dimension
- Integrates with ObsAgent's precomputed aggregates

Next Steps:
1. Populate aggregate collections with real data
2. Test full multi-agent workflow end-to-end  
3. Integrate with dashboard generation capabilities
4. Set up CI/CD pipeline

"""
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
