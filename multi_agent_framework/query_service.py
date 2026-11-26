"""High-level API for ObsAgent's Ollama and ChromaDB workflow."""

from __future__ import annotations

import asyncio
from enum import Enum
from pathlib import Path
from typing import Any

from ChromaDB.ingest_csv import hashed_embedding
from ChromaDB.precomputed_queries import (
    DEFAULT_METRICS,
    cohort_curve,
    kpis_by_dimension,
    portfolio_kpis,
    segment_ranking,
    vintage_comparison,
)

from .agent_manager import (
    DEFAULT_CHROMA_PATH,
    MultiAgentSystem,
    setup_multi_agent_system,
)


class KPIType(Enum):
    DELINQUENCY_RATE = "delinquency_rate_amount"
    DELINQUENCY_RATE_ACCOUNTS = "delinquency_rate_accounts"
    GROSS_CHARGEOFF_RATE = "gross_chargeoff_rate"
    NET_CHARGEOFF_RATE = "net_chargeoff_rate"
    RECOVERY_RATE = "recovery_rate"
    UTILIZATION_RATE = "utilization_rate"
    OPERATING_MARGIN = "operating_margin"
    OPERATING_MARGIN_RATE = "operating_margin_rate"
    EFFICIENCY_RATIO = "efficiency_ratio"
    ACQUISITION_COST_PER_ACCOUNT = "acquisition_cost_per_account"


class QueryService:
    """Query ObsAgent data directly or through the multi-agent workflow."""

    def __init__(self, chroma_path: str | Path | None = None):
        self._chroma_path = Path(chroma_path) if chroma_path else DEFAULT_CHROMA_PATH
        self._system = setup_multi_agent_system(self._chroma_path)

    def set_source_path(self, path: str | Path) -> None:
        self._chroma_path = Path(path)
        self._system = setup_multi_agent_system(self._chroma_path)

    async def query(self, request: str) -> dict[str, Any]:
        return await self._system.execute(request)

    async def query_kpi(
        self,
        kpi_type: KPIType | str,
        vintage: int | None = None,
        mob: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metric = kpi_type.value if isinstance(kpi_type, KPIType) else str(kpi_type)
        if metric not in DEFAULT_METRICS:
            raise ValueError(f"Unsupported KPI: {metric}")
        selected_filters = dict(filters or {})
        if vintage is not None:
            selected_filters["vintage"] = vintage
        if mob is not None:
            selected_filters["mob"] = mob
        result = await asyncio.to_thread(
            portfolio_kpis, self._system.aggregates, selected_filters
        )
        return {
            "metric": metric,
            "value": result["metrics"][metric],
            **result,
        }

    async def get_vintage_ranking(
        self,
        sort_metric: str | KPIType = KPIType.DELINQUENCY_RATE,
        descending: bool = True,
        top_n: int = 10,
    ) -> list[dict[str, Any]]:
        metric = sort_metric.value if isinstance(sort_metric, KPIType) else sort_metric
        return await asyncio.to_thread(
            segment_ranking,
            self._system.aggregates,
            "vintage",
            metric,
            None,
            top_n,
            descending,
        )

    async def search_semantically(
        self,
        query: str,
        category: str | None = None,
        n_results: int = 10,
    ) -> dict[str, Any]:
        if category is not None:
            raise ValueError(
                "Semantic search uses the source collection; category filtering "
                "is available through the validated analytical query tools."
            )
        if n_results < 1:
            raise ValueError("n_results must be at least 1")
        return await asyncio.to_thread(
            self._system.source.query,
            query_embeddings=[hashed_embedding(query)],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    async def get_category_metrics(
        self,
        category: str,
        metrics: list[KPIType | str] | None = None,
    ) -> list[dict[str, Any]]:
        result = await asyncio.to_thread(
            kpis_by_dimension, self._system.aggregates, category
        )
        if metrics is None:
            return result
        selected = {
            metric.value if isinstance(metric, KPIType) else metric
            for metric in metrics
        }
        unsupported = selected - set(DEFAULT_METRICS)
        if unsupported:
            raise ValueError(f"Unsupported KPIs: {', '.join(sorted(unsupported))}")
        return [
            {
                **row,
                "metrics": {
                    name: value
                    for name, value in row["metrics"].items()
                    if name in selected
                },
            }
            for row in result
        ]

    async def compare_vintages(
        self,
        baseline_vintage: int,
        comparison_vintage: int,
        metrics: list[str] | None = None,
        mob: int | None = None,
    ) -> dict[str, Any]:
        if mob is None:
            curve = await asyncio.to_thread(
                cohort_curve,
                self._system.aggregates,
                {"vintage": [baseline_vintage, comparison_vintage]},
            )
            mob_sets = {
                vintage: {
                    row["mob"] for row in curve if row["vintage"] == vintage
                }
                for vintage in (baseline_vintage, comparison_vintage)
            }
            common_mobs = mob_sets[baseline_vintage] & mob_sets[comparison_vintage]
            if not common_mobs:
                raise ValueError(
                    "The selected vintages have no common month-on-book to compare."
                )
            mob = max(common_mobs)

        result = await asyncio.to_thread(
            vintage_comparison,
            self._system.aggregates,
            baseline_vintage,
            comparison_vintage,
            mob,
        )
        if metrics is not None:
            selected = set(metrics)
            unsupported = selected - set(DEFAULT_METRICS)
            if unsupported:
                raise ValueError(f"Unsupported KPIs: {', '.join(sorted(unsupported))}")
            result["metric_delta"] = {
                name: value
                for name, value in result["metric_delta"].items()
                if name in selected
            }
        return result


_query_service: QueryService | None = None


def get_query_service(chroma_path: str | Path | None = None) -> QueryService:
    global _query_service
    if _query_service is None or chroma_path is not None:
        _query_service = QueryService(chroma_path)
    return _query_service


def setup_query_system(chroma_path: str | Path | None = None) -> MultiAgentSystem:
    return setup_multi_agent_system(chroma_path)
