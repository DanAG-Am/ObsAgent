"""Build chart-ready data from validated analytical tool results."""

from __future__ import annotations

from typing import Any


DIMENSION_LABELS = {
    "vintage": "Cosecha",
    "strategy": "Estrategia",
    "strategy_segment": "Segmento de estrategia",
    "product": "Producto",
    "channel": "Canal",
    "age_tag": "Etiqueta de edad",
    "score_tag": "Etiqueta de score",
    "mob": "Mes en libros (MOB)",
}

METRIC_KEYWORDS = (
    ("delinquency_rate_accounts", ("morosidad por cuenta", "morosidad de cuentas")),
    ("gross_chargeoff_rate", ("castigo bruto",)),
    ("net_chargeoff_rate", ("castigo neto",)),
    ("recovery_rate", ("recuperación", "recovery rate")),
    ("utilization_rate", ("utilización", "utilization rate")),
    ("operating_margin_rate", ("tasa de margen", "margen porcentual")),
    ("operating_margin", ("margen operativo",)),
    ("efficiency_ratio", ("eficiencia", "efficiency ratio")),
    (
        "acquisition_cost_per_account",
        ("costo de adquisición", "costo por cuenta"),
    ),
    ("delinquency_rate_amount", ("morosidad", "delinquency")),
)


def _select_metric(
    request: str,
    available_metrics: set[str],
    metric_labels: dict[str, str],
) -> str | None:
    normalized_request = request.casefold()
    for metric, label in metric_labels.items():
        if metric in available_metrics and (
            metric.casefold() in normalized_request
            or label.casefold() in normalized_request
        ):
            return metric
    for metric, keywords in METRIC_KEYWORDS:
        if metric in available_metrics and any(
            keyword in normalized_request for keyword in keywords
        ):
            return metric
    return next(
        (metric for metric in metric_labels if metric in available_metrics),
        None,
    )


def _chart_value(
    value: Any,
    metric: str,
    non_percentage_metrics: set[str],
) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    numeric_value = float(value)
    return numeric_value if metric in non_percentage_metrics else numeric_value * 100


def build_response_chart(
    tool_results: list[dict[str, Any]],
    request: str,
    metric_labels: dict[str, str],
    non_percentage_metrics: set[str],
) -> dict[str, Any] | None:
    """Return one chart specification for the first chartable tool result."""
    for tool_result in tool_results:
        tool = tool_result.get("tool")
        result = tool_result.get("result")

        if tool == "cohort_curve" and isinstance(result, list) and result:
            metric = _select_metric(
                request,
                set(result[0].get("metrics", {})),
                metric_labels,
            )
            if metric is None:
                continue
            label = metric_labels[metric]
            data = [
                {
                    "MOB": row["mob"],
                    "Cosecha": str(row["vintage"]),
                    label: value,
                }
                for row in result
                if (value := _chart_value(
                    row.get("metrics", {}).get(metric),
                    metric,
                    non_percentage_metrics,
                )) is not None
            ]
            if data:
                return {
                    "kind": "line",
                    "data": data,
                    "x": "MOB",
                    "y": label,
                    "color": "Cosecha",
                    "alt": f"{label} por mes en libros y cosecha",
                }

        if tool in {"segment_ranking", "kpis_by_dimension", "anomaly_candidates"}:
            if not isinstance(result, list) or not result:
                continue
            dimension = next(
                (name for name in DIMENSION_LABELS if name in result[0]),
                None,
            )
            metric = _select_metric(
                request,
                set(result[0].get("metrics", {})),
                metric_labels,
            )
            if dimension is None or metric is None:
                continue
            label = metric_labels[metric]
            group_label = DIMENSION_LABELS[dimension]
            chart_rows = result
            if tool == "kpis_by_dimension":
                chart_rows = sorted(
                    result,
                    key=lambda row: row.get("metrics", {}).get(metric)
                    if isinstance(row.get("metrics", {}).get(metric), (int, float))
                    else float("-inf"),
                    reverse=True,
                )
            data = [
                {group_label: str(row[dimension]), label: value}
                for row in chart_rows[:10]
                if (value := _chart_value(
                    row.get("metrics", {}).get(metric),
                    metric,
                    non_percentage_metrics,
                )) is not None
            ]
            if data:
                return {
                    "kind": "bar",
                    "data": data,
                    "x": group_label,
                    "y": label,
                    "alt": f"{label} por {group_label.lower()}",
                }

        if tool == "vintage_comparison" and isinstance(result, dict):
            metric = _select_metric(
                request,
                set(result.get("metric_delta", {})),
                metric_labels,
            )
            if metric is None:
                continue
            label = metric_labels[metric]
            data = [
                {
                    "Cosecha": str(result.get(f"{side}_vintage")),
                    label: value,
                }
                for side in ("baseline", "comparison")
                if (value := _chart_value(
                    result.get(side, {}).get("metrics", {}).get(metric),
                    metric,
                    non_percentage_metrics,
                )) is not None
            ]
            if data:
                return {
                    "kind": "bar",
                    "data": data,
                    "x": "Cosecha",
                    "y": label,
                    "alt": f"{label} para las cosechas comparadas",
                }

    return None
