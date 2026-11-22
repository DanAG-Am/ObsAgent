"""
Multi-Agent Framework for ObsAgent.

This framework implements a multi-agent system where each agent has specific roles:
- Researcher: Consults ChromaDB to answer data-based questions, analyze trends
- Translator: Translates user queries from local language to English and back
- Builder: Executes actions and generates output (HTML reports, dashboards, etc.)

Agent architecture follows agentlib patterns with specialized tools per role.
Each agent operates independently but coordinates through shared contexts.

Key features:
- Modular agent registration system
- Semantic segmentation of embeddings by category
- Chain-of-thought deliberation between agents
- Token-efficient English intermediate representation
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import chromadb


class AgentRole(Enum):
    """Enumeration of agent roles in the multi-agent system."""
    
    RESEARCHER = "researcher"
    TRANSLATOR = "translator"
    BUILDER = "builder"


@dataclass
class Agent:
    """Base class for all agents in the system."""
    
    name: str
    role: AgentRole
    description: str
    tools: list[AgentTool]
    
    @abstractmethod
    async def execute(self, request: str) -> Any:
        """Execute the agent's primary task."""
        pass
    
    async def collaborate(self, other_agent: 'Agent', context: dict[str, Any]) -> Any:
        """Collaborate with another agent, passing context through."""
        return await other_agent.execute(request)


@dataclass
class AgentTool:
    """Represents a tool available to an agent."""
    
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, name: str, description: str, parameters: dict | None = None):
        self.name = name
        self.description = description
        self.parameters = parameters or {}


@dataclass
class AgentContext:
    """Shared context passed between agents."""
    
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    query_context: dict[str, Any] = field(default_factory=dict)
    retrieved_data: Any = None
    translation_state: str = ""
    working_memory: list[str] = field(default_factory=list)


class MultiAgentSystem:
    """
    Orchestrates the multi-agent workflow.

    The system runs three agents in sequence:
    1. Translator: Converts queries to English for efficient processing
    2. Researcher: Consults database and performs analysis  
    3. Builder: Generates final output (reports, dashboards)

    Agent segmentation by category uses separate ChromaDB collections
    for embeddings per category (vintage, strategy, product, etc.)
    """

    def __init__(self):
        """Initialize the multi-agent system."""
        self._agents: dict[AgentRole, Agent] = {}
        self._context = AgentContext()
        self._embedding_collections: dict[str, chromadb.Collection] = {}
        
        # Register agents (to be called with agent instances)
        self.register_agent(AgentRole.RESEARCHER, None)
        self.register_agent(AgentRole.TRANSLATOR, None)
        self.register_agent(AgentRole.BUILDER, None)
    
    def register_agent(
        self, 
        role: AgentRole, 
        agent: Optional[Agent] = None,
        name: str | None = None
    ) -> None:
        """Register an agent by role."""
        if not agent:
            # Create default agent instances for each role
            if role == AgentRole.RESEARCHER:
                agent = ResearcherAgent(role.name)
            elif role == AgentRole.TRANSLATOR:
                agent = TranslatorAgent(role.name)
            elif role == AgentRole.BUILDER:
                agent = BuilderAgent(role.name)
            else:
                raise ValueError(f"Unknown agent role: {role}")
        
        self._agents[role] = agent
        
        # Register tools for each agent
        for tool in agent.tools:
            setattr(self, tool.name, getattr(self, tool.name) or tool.execute)

    def register_embedding_collection(
        self,
        category: str,
        collection_name: str | None = None
    ) -> None:
        """Register a segmented embedding collection for a category."""
        if not collection_name:
            collection_name = f"aggregates_{category}_lowercase"
        
        try:
            client = chromadb.PersistentClient(path="ChromaDB/chroma_data")
            self._embedding_collections[category] = client.get_or_create_collection(collection_name)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize collection {category}: {e}")

    def get_segmented_embeddings(self, category: str, query: str) -> dict[str, Any]:
        """Retrieve embeddings for a specific category."""
        if category not in self._embedding_collections:
            raise KeyError(f"No embedding collection registered for category: {category}")
        
        return self._embedding_collections[category].query(
            texts=[query],
            n_results=10
        )


class BaseAgent:
    """Base agent class implementing common patterns."""
    
    def __init__(self, name: str, role: AgentRole):
        self.name = name
        self.role = role
        self.tools = []

    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool for this agent."""
        self.tools.append(tool)


# =============================================================================
# Researcher Agent - Consults ChromaDB and performs analysis
# =============================================================================

class ResearcherAgent(BaseAgent):
    """
    The researcher agent consults the database to answer data-based questions.

    Responsibilities:
    - Query ChromaDB for specific metrics and aggregations
    - Analy trends across vintages, strategies, and categories
    - Return structured analytical findings
    """

    SYSTEM_PROMPT = """You are a Data Researcher in ObsAgent. Your job is to:

1. Interpret user questions about the financial database (TC3009C cards)
2. Translate questions into precise ChromaDB queries
3. Fetch aggregated data from segmented collections by category
4. Calculate KPIs and metrics as needed
5. Present findings in clear, actionable Spanish

Remember: You only access what you query. Users provide filters; you return aggregated results."""

    def __init__(self, name: str = "Researcher"):
        super().__init__(name=name, role=AgentRole.RESEARCHER)
        
        self.tools = [
            AgentTool(
                name="query_aggregates",
                description="Fetch precomputed aggregates from ChromaDB for a category",
                parameters={
                    "category": {"type": "string", "description": "Category to query (vintage, strategy_segment, product, channel)"},
                    "filters": {"type": "object", "description": "Filter criteria for the aggregation"}
                }
            ),
            AgentTool(
                name="calculate_metrics",
                description="Calculate KPIs from raw data for specific vintages or cohorts",
                parameters={
                    "vintage": {"type": "integer", "description": "Vintage year"},
                    "mob": {"type": "integer", "description": "Month on book"}
                }
            ),
            AgentTool(
                name="compare_vintage",
                description="Compare two vintages side by side with metric deltas",
                parameters={
                    "baseline": {"type": "integer", "description": "Baseline vintage"},
                    "comparison": {"type": "integer", "description": "Vintage to compare against"}
                }
            ),
        ]

    async def execute(self, request: str) -> Any:
        """Execute the researcher agent's task."""
        # Parse user request and extract filters/questions
        # Query appropriate segmented collection
        # Return structured analysis
        
        context = await self._analyze_request(request)
        
        return {
            "role": "researcher",
            "query": context.retrieved_data,
            "findings": self._summarize_findings(context.query),
            "insights": self._identify_patterns(context.query)
        }

    def _analyze_request(self, request: str) -> AgentContext:
        """Parse user request and prepare for database query."""
        context = AgentContext()
        
        # Extract potential filters from request
        # Map to ChromaDB dimensions
        
        return context

    def _summarize_findings(self, data: dict) -> list[str]:
        """Generate summary of findings."""
        return [
            f"Total accounts analyzed: {data.get('measures', {}).get('accounts', 0)}",
            f"Overall delinquency rate: {data.get('metrics', {}).get('delinquency_rate_amount'):.2f}" if data.get('metrics', {}).get('delinquency_rate_amount') is not None else "Delinquency analysis pending"
        ]

    def _identify_patterns(self, data: dict) -> list[str]:
        """Identify key patterns from the data."""
        return [
            f"Cohort analysis shows performance trajectory across vintages",
            "Segment ranking reveals top-performing and at-risk categories"
        ]


# =============================================================================
# Translator Agent - Language translation layer
# =============================================================================

class TranslatorAgent(BaseAgent):
    """
    The translator agent converts queries between languages.

    Responsibilities:
    - Translate user input to English for efficient processing
    - Translate researcher findings back to source language
    - Reduce token usage by using English as intermediate representation
    """

    SYSTEM_PROMPT = """You are the Translator in ObsAgent's multi-agent system. Your job is to:

1. Translate user questions from local languages (Spanish, etc.) to English
2. Present researcher findings in the source language of the original query
3. Maintain context through translation chains
4. Keep responses concise for token efficiency

Remember: You bridge the gap between human intent and machine analysis."""

    def __init__(self, name: str = "Translator"):
        super().__init__(name=name, role=AgentRole.TRANSLATOR)
        
        self.tools = [
            AgentTool(
                name="translate_query",
                description="Translate user question to English",
                parameters={}
            ),
            AgentTool(
                name="translate_response",
                researcher_findings: "Translate researcher's findings back to source language"
    )

    async def execute(self, request: str) -> Any:
        """Execute the translator agent's task."""
        
        # Step 1: Translate query if needed
        if self._should_translate(request):
            context = AgentContext()
            translation = self._translate_to_english(request)
            
            # Pass to researcher
            research_results = await ResearcherAgent.execute(translation)
            
            return {
                "original_query": request,
                "translated": translation,
                "findings": research_results.get('findings', []),
                "insights": research_results.get('insights', [])
            }

        return {
            "role": "translator",
            "message": "Query already in English; can delegate to researcher"
        }

    def _should_translate(self, text: str) -> bool:
        """Determine if translation is needed."""
        # Simple heuristic: check for non-ASCII characters or known Spanish words
        return any(char not in 'abcdefghijklmnopqrstuvwxyz' for char in text[:20])


# =============================================================================
# Builder Agent - Generates output and executes actions
# =============================================================================

class BuilderAgent(BaseAgent):
    """
    The builder agent generates final output.

    Responsibilities:
    - Create HTML reports from analysis results
    - Generate dashboard specifications
    - Produce downloadable files (CSV, Excel)
    - Format outputs for specific use cases
    """

    SYSTEM_PROMPT = """You are the Builder in ObsAgent's multi-agent system. Your job is to:

1. Convert research findings into formatted reports
2. Generate HTML representations with tables and charts
3. Create downloadable files in various formats
4. Structure data for visualization and analysis

Remember: Output must be actionable, well-formatted, and ready for use."""

    def __init__(self, name: str = "Builder"):
        super().__init__(name=name, role=AgentRole.BUILDER)
        
        self.tools = [
            AgentTool(
                name="generate_report",
                description="Create HTML report from analysis results",
                parameters={
                    "findings": {"type": "object", "description": "Research findings to format"},
                    "style": {"type": "string", "description": "Report style (academic, executive, summary)"}
                }
            ),
            AgentTool(
                name="create_dashboard_spec",
                description="Generate dashboard configuration and specs",
                parameters={
                    "metrics": {"type": "array", "description": "List of metrics to display"},
                    "layout": {"type": "string", "description": "Dashboard layout preference"}
                }
            ),
            AgentTool(
                name="export_data",
                description="Export data to specified format (CSV, Excel)",
                parameters={
                    "data": {"type": "object", "description": "Data to export"},
                    "format": {"type": "string", "enum": ["csv", "excel"], "description": "Output format"}
                }
            ),
        ]

    async def execute(self, request: str) -> Any:
        """Execute the builder agent's task."""
        
        # Parse builder requirements
        if "report" in request.lower() or "dashboard" in request.lower():
            return {
                "role": "builder",
                "output_format": "html",
                "content": self._format_output(request)
            }

        return {
            "role": "builder",
            "message": "Ready to generate output from provided data"
        }

    def _format_output(self, request: str) -> str:
        """Format research output for the requested format."""
        # Simplified formatter - will be expanded with actual HTML generation
        return "<html><body><h1>Analysis Report</h1></body></html>"


# =============================================================================
# Workflow Orchestration
# =============================================================================

async def run_multi_agent_workflow(query: str, source_language: str = "es") -> Any:
    """
    Execute the complete multi-agent workflow.

    The system runs agents in this sequence:
    1. Translator: Convert query to English (if needed)
    2. Researcher: Perform database analysis  
    3. Builder: Generate final output

    Args:
        query: User's natural language query
        source_language: Original language of user query

    Returns:
        Combined results from all agents with translations back to source language
    """
    
    # Initialize system
    system = MultiAgentSystem()

    # Execute workflow
    result = await _orchestrate(query, system)
    
    return result


async def _orchestrate(
    query: str,
    system: MultiAgentSystem
) -> dict[str, Any]:
    """Orchestrate agents through the workflow chain."""
    
    # Step 1: Translator
    translator_result = await system._agents[AgentRole.TRANSLATOR].execute(query)
    
    # Step 2: Researcher (uses translated query if available)
    if "translated" in translator_result:
        research_query = translator_result["translated"]
    else:
        research_query = query
    
    researcher_result = await system._agents[AgentRole.RESEARCHER].execute(research_query)
    
    # Step 3: Builder (generates output from findings)
    builder_input = {
        "findings": researcher_result.get("findings", []),
        "insights": researcher_result.get("insights", [])
    }
    
    builder_output = await system._agents[AgentRole.BUILDER].execute(builder_input)

    # Compile results
    return {
        "original_query": query,
        "translator_translation": translator_result.get("translated", None),
        "research_findings": researcher_result.get("findings", []),
        "builder_output": builder_output
    }


# =============================================================================
# Setup and Registration
# =============================================================================

def setup_multi_agent_system() -> MultiAgentSystem:
    """
    Set up the complete multi-agent system with default agents.

    Creates instances of:
    - ResearcherAgent with ChromaDB query tools
    - TranslatorAgent with translation capabilities
    - BuilderAgent with report generation tools

    Returns:
        Configured MultiAgentSystem ready for queries

    Example:
        >>> system = setup_multi_agent_system()
        >>> results = await run_multi_agent_workflow("¿Cuáles son las mejores vintages?")
    """
    
    system = MultiAgentSystem()
    
    # Register default agents (already created in __init__)
    return system


# =============================================================================
# Main entry point for testing/demo
# =============================================================================

async def demo():
    """Demonstrate the multi-agent workflow."""
    
    async with asyncio.current_event_loop().create_task(run_multi_agent_workflow("¿Cuáles son las principales vintages por estrategia?")) as result:
        # Return results to user
        print(f"Researcher findings: {result.get('research_findings', [])}")


if __name__ == "__main__":
    asyncio.run(demo())
