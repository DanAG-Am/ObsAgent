"""Conservative numeric source lookup, not semantic claim verification."""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator


ANALYTICAL_TOOLS = {
    "portfolio_kpis", "cohort_curve", "kpis_by_dimension", "vintage_comparison",
    "segment_ranking", "anomaly_candidates", "detectar_fraude",
    "validar_csv_local",
}
NON_RATE_METRICS = {"operating_margin", "acquisition_cost_per_account"}
NUMBER = re.compile(
    r"(?<![\w.])[-+]?\d+(?:[.,]\d+)*(?:\s*(?:%|puntos?\s+porcentuales?|p\.?\s*p\.?))?",
    re.IGNORECASE,
)


def _leaves(value: Any, path: str = "") -> Iterator[tuple[str, float]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _leaves(child, f"{path}[{index}]")
    elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        yield path, value


def _parse_number(token: str) -> tuple[Decimal, int, str] | None:
    unit_match = re.search(r"%|puntos?\s+porcentuales?|p\.?\s*p\.?", token, re.IGNORECASE)
    unit = "percentage_points" if unit_match and unit_match.group() != "%" else (
        "percent" if unit_match else "number"
    )
    text = token[:unit_match.start()].strip() if unit_match else token.strip()
    # Accept both common grouping conventions; an isolated separator followed
    # by three digits is ambiguous, so do not claim a match for it.
    if "," in text and "." in text:
        decimal_sep = "," if text.rfind(",") > text.rfind(".") else "."
        text = text.replace("." if decimal_sep == "," else ",", "").replace(decimal_sep, ".")
    elif "," in text:
        parts = text.split(",")
        if len(parts) != 2 or len(parts[-1]) == 3:
            return None
        text = ".".join(parts)
    elif text.count(".") > 1:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int):
        return None
    return value, max(0, -exponent), unit


def numeric_evidence(answer: str, trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Find possible numeric sources; a match never validates meaning or scope."""
    sources: list[tuple[str, str, float, str]] = []
    for index, call in enumerate(trace.get("tool_results", []), 1):
        result = call.get("result")
        if call.get("tool") not in ANALYTICAL_TOOLS or (
            isinstance(result, dict) and "error" in result
        ):
            continue
        for path, value in _leaves(result):
            kind = "number"
            if "metric_delta." in path and path.rsplit(".", 1)[-1] not in NON_RATE_METRICS:
                kind = "percentage_points"
            elif "metrics." in path and path.rsplit(".", 1)[-1] not in NON_RATE_METRICS:
                kind = "percent"
            sources.append((f"Herramienta {index}: {call['tool']}", path, value, kind))
    context = trace.get("dashboard_context")
    if isinstance(context, dict):
        for path, value in _leaves(context):
            kind = "number"
            if path.endswith(".valor") and context.get("metric") not in (None, *NON_RATE_METRICS):
                kind = "percent"
            sources.append(("Contexto del panel", path, value, kind))

    claims = []
    for match in NUMBER.finditer(answer):
        token = match.group().strip()
        parsed = _parse_number(token)
        candidates = []
        if parsed is not None:
            number, decimals, unit = parsed
            tolerance = Decimal("0.5").scaleb(-decimals)
            for label, path, value, kind in sources:
                if unit != "number" and kind != unit:
                    continue
                source_value = Decimal(str(value)) * (100 if unit != "number" else 1)
                if abs(number - source_value) <= tolerance:
                    candidates.append(f"{label} → {path}")
        claims.append({
            "cifra": token,
            "fuentes_posibles": candidates[:10],
            "total_fuentes_posibles": len(candidates),
            "estado": "coincidencia posible" if candidates else "sin coincidencia identificada",
        })
    return claims
