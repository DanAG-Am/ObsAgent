"""Deterministic analytical queries backed by precomputed ChromaDB aggregates.

The language model supplies validated filters and metric names. It never
supplies SQL or arbitrary ChromaDB expressions. Numeric calculations happen
only in this module.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, Iterable

import chromadb


DIMENSIONS = (
    "vintage",
    "strategy",
    "strategy_segment",
    "product",
    "channel",
    "age_tag",
    "score_tag",
    "mob",
)

STRING_DIMENSIONS = {
    "strategy",
    "strategy_segment",
    "product",
    "channel",
    "age_tag",
    "score_tag",
}

MEASURES = (
    "accounts",
    "credit_lines_amount",
    "enrolled_accounts",
    "over30_accounts",
    "over30_amount",
    "gross_chargeoff_amount",
    "net_chargeoff_amount",
    "recovery_amount",
    "enrolled_amount",
    "revenue",
    "acquisition_expense",
    "variable_ecm_expense",
    "fixed_ecm_expense",
    "total_expense",
)

DEFAULT_METRICS = (
    "delinquency_rate_amount",
    "delinquency_rate_accounts",
    "gross_chargeoff_rate",
    "net_chargeoff_rate",
    "recovery_rate",
    "utilization_rate",
    "operating_margin",
    "operating_margin_rate",
    "efficiency_ratio",
    "acquisition_cost_per_account",
)
EMBEDDING_DIMENSION = 64


def _aggregate_id(key: tuple[Any, ...]) -> str:
    digest = hashlib.sha256(json.dumps(key, ensure_ascii=True).encode()).hexdigest()
    return f"aggregate-{digest}"


def _aggregate_embedding(key: tuple[Any, ...]) -> list[float]:
    """Provide a stable lightweight embedding without invoking an EF."""
    digest = hashlib.sha256(json.dumps(key, ensure_ascii=True).encode()).digest()
    vector = [0.0] * EMBEDDING_DIMENSION
    for index, value in enumerate(digest):
        vector[(index * 7) % EMBEDDING_DIMENSION] += 1.0 if value % 2 else -1.0
    magnitude = sum(value * value for value in vector) ** 0.5
    return [value / magnitude for value in vector]


def _empty_totals() -> dict[str, float]:
    return {measure: 0.0 for measure in MEASURES}


def _add_row(totals: dict[str, float], row: Mapping[str, Any]) -> None:
    for measure in MEASURES:
        totals[measure] += float(row.get(measure, 0) or 0)


def _chunks(items: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def build_aggregate_collection(
    source: chromadb.Collection,
    target: chromadb.Collection,
    batch_size: int = 5_000,
) -> int:
    """Materialize one additive row per full business grain in ChromaDB."""
    existing_ids = target.get(include=[])["ids"]
    if existing_ids:
        target.delete(ids=existing_ids)

    grouped: dict[tuple[Any, ...], dict[str, float]] = defaultdict(_empty_totals)
    offset = 0

    while True:
        batch = source.get(
            limit=batch_size,
            offset=offset,
            include=["metadatas"],
        )
        metadatas = batch.get("metadatas") or []
        if not metadatas:
            break
        for row in metadatas:
            key = tuple(row[dimension] for dimension in DIMENSIONS)
            _add_row(grouped[key], row)
        offset += len(metadatas)
        if len(metadatas) < batch_size:
            break

    for entries in _chunks(list(grouped.items()), batch_size):
        target.upsert(
            ids=[_aggregate_id(key) for key, _ in entries],
            documents=[
                " | ".join(f"{dimension}={value}" for dimension, value in zip(DIMENSIONS, key))
                for key, _ in entries
            ],
            embeddings=[_aggregate_embedding(key) for key, _ in entries],
            metadatas=[
                {
                    **dict(zip(DIMENSIONS, key)),
                    **{measure: value for measure, value in totals.items()},
                }
                for key, totals in entries
            ],
        )
    return len(grouped)


def _where(filters: dict[str, Any] | None) -> dict[str, Any] | None:
    if not filters:
        return None
    clauses: list[dict[str, Any]] = []
    for name, value in filters.items():
        if name not in DIMENSIONS:
            raise ValueError(f"Unsupported filter dimension: {name}")
        if name in STRING_DIMENSIONS:
            if not isinstance(value, str):
                raise ValueError(f"{name} requires a string value")
            clauses.append({name: value})
        elif isinstance(value, int):
            clauses.append({name: value})
        elif isinstance(value, dict):
            allowed = {"$gte", "$lte", "$gt", "$lt"}
            if set(value) - allowed:
                raise ValueError(f"Unsupported range operator for {name}")
            clauses.extend({name: {operator: bound}} for operator, bound in value.items())
        elif isinstance(value, list) and value:
            clauses.append({name: {"$in": value}})
        else:
            raise ValueError(f"Invalid filter for {name}")
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}



def _rows(
    aggregates: chromadb.Collection,
    filters: dict[str, Any] | None = None,
) -> list[Mapping[str, Any]]:
    """Retrieve aggregate metadata without offset-scanning unfiltered pages."""
    where = _where(filters)
    if where is None:
        count = aggregates.count()
        if not count:
            return []
        ids = aggregates.get(limit=count, include=[])["ids"]
        rows: list[Mapping[str, Any]] = []
        for id_batch in _chunks(ids, 900):
            result = aggregates.get(ids=id_batch, include=["metadatas"])
            rows.extend(result.get("metadatas") or [])
        return rows

    batch_size = 5_000
    offset = 0
    rows: list[Mapping[str, Any]] = []

    while True:
        result = aggregates.get(
            where=where,
            include=["metadatas"],
            limit=batch_size,
            offset=offset,
        )

        batch = result.get("metadatas") or []

        if not batch:
            break

        rows.extend(batch)
        offset += len(batch)

        if len(batch) < batch_size:
            break

    return rows

def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def _metrics(totals: dict[str, float]) -> dict[str, float | None]:
    margin = totals["revenue"] - totals["total_expense"]
    return {
        "delinquency_rate_amount": _ratio(totals["over30_amount"], totals["enrolled_amount"]),
        "delinquency_rate_accounts": _ratio(totals["over30_accounts"], totals["enrolled_accounts"]),
        "gross_chargeoff_rate": _ratio(totals["gross_chargeoff_amount"], totals["enrolled_amount"]),
        "net_chargeoff_rate": _ratio(totals["net_chargeoff_amount"], totals["enrolled_amount"]),
        "recovery_rate": _ratio(totals["recovery_amount"], totals["gross_chargeoff_amount"]),
        "utilization_rate": _ratio(totals["enrolled_amount"], totals["credit_lines_amount"]),
        "operating_margin": margin,
        "operating_margin_rate": _ratio(margin, totals["revenue"]),
        "efficiency_ratio": _ratio(totals["total_expense"], totals["revenue"]),
        "acquisition_cost_per_account": _ratio(
            totals["acquisition_expense"], totals["accounts"]
        ),
    }


def _summarize(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    totals = _empty_totals()
    for row in rows:
        _add_row(totals, row)
    return {"measures": totals, "metrics": _metrics(totals), "row_count": len(rows)}


def portfolio_kpis(
    aggregates: chromadb.Collection,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return portfolio measures and derived KPIs for validated filters."""
    return _summarize(_rows(aggregates, filters))


def kpis_by_dimension(
    aggregates: chromadb.Collection,
    group_by: str,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Compare KPIs by one allowlisted dimension."""
    if group_by not in DIMENSIONS:
        raise ValueError(f"Unsupported grouping dimension: {group_by}")
    groups: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
    for row in _rows(aggregates, filters):
        groups[row[group_by]].append(row)
    return [{group_by: value, **_summarize(rows)} for value, rows in groups.items()]


def cohort_curve(
    aggregates: chromadb.Collection,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return KPI rows ordered by vintage and MOB for cohort charts."""
    # Keep MOB visible by querying the aggregate records at the requested grain.
    grouped: dict[tuple[Any, Any], list[Mapping[str, Any]]] = defaultdict(list)
    for row in _rows(aggregates, filters):
        grouped[(row["vintage"], row["mob"])].append(row)
    return [
        {"vintage": vintage, "mob": mob, **_summarize(group)}
        for (vintage, mob), group in sorted(grouped.items())
    ]


def combine_cohort_summaries(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine cohort totals before calculating ratios."""
    totals = _empty_totals()
    for row in rows:
        _add_row(totals, row["measures"])
    return {
        "measures": totals,
        "metrics": _metrics(totals),
        "row_count": sum(row["row_count"] for row in rows),
    }


def vintage_comparison(
    aggregates: chromadb.Collection,
    baseline_vintage: int,
    comparison_vintage: int,
    mob: int,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare two vintages at the same MOB with metric deltas."""
    common_filters = dict(filters or {})
    common_filters["mob"] = mob
    baseline = dict(common_filters, vintage=baseline_vintage)
    comparison = dict(common_filters, vintage=comparison_vintage)
    baseline_result = _summarize(_rows(aggregates, baseline))
    comparison_result = _summarize(_rows(aggregates, comparison))
    delta = {
        metric: (
            comparison_result["metrics"][metric] - baseline_result["metrics"][metric]
            if comparison_result["metrics"][metric] is not None
            and baseline_result["metrics"][metric] is not None
            else None
        )
        for metric in DEFAULT_METRICS
    }
    return {
        "baseline_vintage": baseline_vintage,
        "comparison_vintage": comparison_vintage,
        "mob": mob,
        "baseline": baseline_result,
        "comparison": comparison_result,
        "metric_delta": delta,
    }


def segment_ranking(
    aggregates: chromadb.Collection,
    group_by: str,
    metric: str,
    filters: dict[str, Any] | None = None,
    limit: int = 10,
    descending: bool = True,
    minimum_accounts: int = 0,
) -> list[dict[str, Any]]:
    """Rank groups while retaining measures and denominator context."""
    if metric not in DEFAULT_METRICS:
        raise ValueError(f"Unsupported metric: {metric}")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    results = [
        row for row in kpis_by_dimension(aggregates, group_by, filters)
        if row["measures"]["accounts"] >= minimum_accounts
        and row["metrics"][metric] is not None
    ]
    return sorted(
        results,
        key=lambda row: row["metrics"][metric],
        reverse=descending,
    )[:limit]


def anomaly_candidates(
    aggregates: chromadb.Collection,
    group_by: str,
    metric: str,
    filters: dict[str, Any] | None = None,
    minimum_accounts: int = 0,
) -> list[dict[str, Any]]:
    """Flag IQR outliers over deterministic group KPI results."""
    values = segment_ranking(
        aggregates,
        group_by,
        metric,
        filters,
        limit=100,
        descending=False,
        minimum_accounts=minimum_accounts,
    )
    if len(values) < 4:
        return []
    ordered = sorted(row["metrics"][metric] for row in values)
    midpoint = len(ordered) // 2
    q1 = ordered[len(ordered[:midpoint]) // 2]
    q3 = ordered[midpoint + len(ordered[midpoint:]) // 2]
    spread = q3 - q1
    lower, upper = q1 - 1.5 * spread, q3 + 1.5 * spread
    return [
        {**row, "anomaly": "low" if row["metrics"][metric] < lower else "high"}
        for row in values
        if row["metrics"][metric] < lower or row["metrics"][metric] > upper
    ]


def open_collections(
    path: str = "ChromaDB/chroma_data",
    source_name: str = "base_cards_sintetica",
    aggregate_name: str = "base_cards_sintetica_aggregates",
) -> tuple[chromadb.Collection, chromadb.Collection]:
    """Open source and aggregate collections for a query service."""
    client = chromadb.PersistentClient(path=path)
    return (
        client.get_collection(source_name),
        client.get_or_create_collection(aggregate_name),
    )
