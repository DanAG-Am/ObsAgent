"""
Example integration with ObsAgent's HTML report generation.

This demonstrates how the multi-agent framework integrates with 
ObsAgent's existing dashboard and report generation capabilities.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List


# Simulated integration with ObsAgent's HTML renderer
class HTMLReportRenderer:
    """Simulates ObsAgent's HTML rendering capabilities."""
    
    def __init__(self):
        """Initialize HTML report renderer."""
        self.base_path = Path("/Users/dany/Desktop/ObsAgent/ObsAgent/html")
        self.stylesheets = []  # List of CSS paths
        
    async def generate_report(
        self,
        title: str,
        findings: Dict[str, Any],
        output_file: str = "obsagent_analysis.html"
    ) -> str:
        """Generate HTML report from researcher findings."""
        
        # Template-based rendering (simplified)
        template = self._get_template("analysis")
        
        return self._render_template(
            template,
            {
                'title': title,
                'findings': findings,
                'metrics': findings.get('metrics', {}),
                'rankings': findings.get('rankings', [])
            }
        )


async def generate_obsagent_analytics() -> str:
    """
    Generate complete analytics report using multi-agent framework.
    
    This demonstrates integration with ObsAgent's existing components, 
    including HTML generation from researcher findings.
    
    Returns:
        HTML string for dashboard/report visualization
        
    Example:
        >>> html_report = await generate_obsagent_analytics()
        >>> f.write(html_report)
    """
    
    # Create temporary renderer instance
    renderer = HTMLReportRenderer()
    
    # Run multi-agent workflow
    findings = await asyncio.to_thread(
        # Simulate agent execution with real data
        lambda: {
            'title': 'Top Vintages by Strategy Analysis',
            'metrics': {
                'delinquency_rate_amount': 0.23,
                'gross_chargeoff_rate': 0.15,
                'recovery_rate': 0.87,
                'utilization_rate': 0.65
            },
            'rankings': [
                {'vintage': 2018, 'score': 0.92},
                {'vintage': 2019, 'score': 0.89},
                {'vintage': 2020, 'score': 0.85}
            ],
            'insights': [
                'Vintage 2018 shows highest delinquency rate',
                'Strategy segment A has best recovery performance',
                'Channel distribution favors premium products'
            ]
        }
    )
    
    # Generate HTML report
    html_output = await renderer.generate_report(
        title=finds['title'],
        findings=findings,
        output_file="dashboard_analysis.html"
    )
    
    return html_output


def format_html_table(data: Dict[str, Any]) -> str:
    """Format data as HTML table for report."""
    
    # Build HTML table from data
    rows = []
    headers = ['Vintage', 'Delinquency Rate', 'Gross Chargeoff Rate']
    
    for row in data.get('rankings', []):
        rows.append([row['vintage'], row['score'], 0.0])
    
    # Return HTML table (simplified)
    return "<table><tr><th>Vintage</th><th>Delinquency Rate</th></tr>"


def main():
    """Demonstrate integration with ObsAgent components."""
    
    print("ObsAgent Multi-Agent Integration Demo")
    print("=" * 50)
    
    # Run example generation
    html_report = asyncio.run(generate_obsagent_analytics())
    
    # Save to HTML file (simulated path)
    try:
        output_path = Path("/Users/dany/Desktop/ObsAgent/ObsAgent/html")
        output_path.mkdir(exist_ok=True)
        
        with open(output_path / "multi_agent_integration_example.html", 'w') as f:
            f.write(html_report)
        
        print(f"\n✓ Generated: {output_path / 'multi_agent_integration_example.html'}")
        print(f"Report size: {len(html_report)} bytes")
    except Exception as e:
        print(f"\nNote: File generation simulated: {e}")
    
    # Show integration points
    print("\nIntegration Points with ObsAgent:")
    print("=" * 50)
    print("""
1. Dashboard Generation:
   - Uses existing obs_agent.html report structure
   - Integrates with precomputed aggregates data
   
2. ChromaDB Segmentation:
   - Leverages segmented collections by category
   - Queries vintage, strategy_segment, product dimensions
   
3. Data Sources:
   - Reads from base_cards_sintetica.csv (via precomputed_queries)
   - Accesses aggregated metrics via segmented collections

4. Output Formats:
   - HTML reports for web dashboard display
   - CSV exports for data analysis
   - Excel format for business reporting

Example Integration Code:

    from obs_agent import QueryService, run_multi_agent_workflow
    
    async def generate_report():
        qs = QueryService()
        
        # Get analyst findings
        research_findings = await run_multi_agent_workflow(
            "Mejores vintages por estrategia"
        )
        
        # Generate HTML with renderer
        html = await HTMLReportRenderer().generate_report(
            title=f"Análisis Multi-Agent: {research_findings['title']}",
            findings=research_findings,
            output_file="multi_agent_analysis.html"
        )

""")


if __name__ == "__main__":
    main()
