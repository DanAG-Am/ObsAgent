"""Example use of ObsAgent's multi-agent analytics workflow."""

import asyncio
from typing import Any

from multi_agent_framework.agent_manager import run_multi_agent_workflow


async def generate_obsagent_analytics(
    query: str = "Compara los principales KPIs de las vintages recientes.",
) -> dict[str, Any]:
    return await run_multi_agent_workflow(query)


def main() -> None:
    result = asyncio.run(generate_obsagent_analytics())
    print(result["final_answer"])


if __name__ == "__main__":
    main()
