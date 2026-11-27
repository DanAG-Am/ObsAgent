"""Local, unverified Excel drafts from existing chat or dashboard results."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.chart import BarChart, Reference, ScatterChart, Series
from openpyxl.chart.axis import NumericAxis, TextAxis
from openpyxl.chart.data_source import NumFmt
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet


WARNING = "BORRADOR NO VERIFICADO. Los datos y las conclusiones no se han verificado automáticamente."
MAX_CELL_CHARS = 32_000


def _append(sheet: Worksheet, values: list[Any]) -> None:
    for value in values:
        if isinstance(value, str) and (
            ILLEGAL_CHARACTERS_RE.search(value) or len(value) > MAX_CELL_CHARS
        ):
            raise ValueError("El contenido contiene caracteres o texto no compatibles con Excel.")
    sheet.append(values)
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def _add_text(sheet: Worksheet, label: str, text: str) -> None:
    for index in range(0, len(text), MAX_CELL_CHARS):
        _append(sheet, [label if index == 0 else f"{label} (continuación)", text[index:index + MAX_CELL_CHARS]])
    if not text:
        _append(sheet, [label, ""])


def _finish(workbook: Workbook) -> bytes:
    for sheet in workbook.worksheets:
        sheet.freeze_panes = "B2"
        sheet.column_dimensions["A"].width = 28
        sheet.column_dimensions["B"].width = 72
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="0B2030")
    buffer = BytesIO()
    workbook.save(buffer)
    data = buffer.getvalue()
    checked = load_workbook(BytesIO(data), read_only=True)
    try:
        if checked.sheetnames != workbook.sheetnames:
            raise ValueError("No se pudieron validar las hojas del archivo Excel.")
    finally:
        checked.close()
    return data


def build_chat_excel(question: str, answer: str, trace: dict[str, Any]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Respuesta"
    _append(sheet, ["Campo", "Contenido"])
    _add_text(sheet, "Aviso", WARNING)
    _add_text(sheet, "Pregunta", question)
    _add_text(sheet, "Respuesta", answer)
    evidence = workbook.create_sheet("Trazabilidad")
    _append(evidence, ["Campo", "Contenido"])
    _add_text(evidence, "Trazabilidad", json.dumps(trace, ensure_ascii=False, indent=2, default=str))
    return _finish(workbook)


def build_dashboard_excel(
    metric_label: str,
    metric_value: float | None,
    accounts: float,
    vintage: int | None,
    mob: int | None,
    evolution: list[dict[str, Any]],
    rankings: list[dict[str, Any]],
    metric: str,
    is_percentage: bool,
    segment_filters: dict[str, str] | None = None,
) -> bytes:
    workbook = Workbook()
    summary = workbook.active
    assert summary is not None
    summary.title = "Resumen"
    _append(summary, ["Campo", "Valor"])
    _add_text(summary, "Aviso", WARNING)
    _append(summary, ["Cosecha", vintage if vintage is not None else "Todas"])
    _append(summary, ["Mes en libros", mob if mob is not None else "Todos"])
    _append(summary, [metric_label, metric_value])
    if is_percentage and metric_value is not None:
        summary.cell(summary.max_row, 2).number_format = "0.00%"
    _append(summary, ["Cuentas analizadas", accounts])
    _add_text(summary, "Alcance", "Las cuentas sumadas entre meses no son necesariamente únicas.")
    _add_text(summary, "Evolución", "Todos los meses de las cosechas seleccionadas; no aplica el filtro de mes.")
    _add_text(summary, "Clasificación", "Hasta 10 cosechas; no aplican los filtros de cosecha ni mes.")
    if segment_filters:
        labels = {"product": "Producto", "channel": "Canal", "strategy": "Estrategia"}
        _add_text(summary, "Segmentos", "; ".join(
            f"{labels[name]}: {value}" for name, value in segment_filters.items()
        ))

    ordered_evolution = sorted(evolution, key=lambda row: (row["vintage"], row["mob"]))
    for name, rows, header in (
        ("Evolución", ordered_evolution, ["Cosecha", "Mes en libros", metric_label, "Cuentas"]),
        ("Clasificación", rankings, ["Cosecha", metric_label, "Cuentas"]),
    ):
        sheet = workbook.create_sheet(name)
        _append(sheet, header)
        for row in rows:
            values = [row["vintage"]]
            if name == "Evolución":
                values.append(row["mob"])
            values.extend([row["metrics"][metric], row["measures"]["accounts"]])
            _append(sheet, values)
            metric_column = 3 if name == "Evolución" else 2
            if is_percentage and row["metrics"][metric] is not None:
                sheet.cell(sheet.max_row, metric_column).number_format = "0.00%"
        sheet.auto_filter.ref = sheet.dimensions

    charts = workbook.create_sheet("Gráficas")
    _append(charts, ["Gráficas del panel", "Alcance"])
    _add_text(charts, "Aviso", WARNING)
    _add_text(charts, "Evolución", "Todos los meses de las cosechas seleccionadas; no aplica el filtro de mes.")
    _add_text(charts, "Clasificación", "Hasta 10 cosechas; no aplican los filtros de cosecha ni mes.")
    _add_text(charts, "Cuentas", "Observaciones por mes; no son necesariamente cuentas únicas.")
    if segment_filters:
        _add_text(charts, "Segmentos", "; ".join(
            f"{labels[name]}: {value}" for name, value in segment_filters.items()
        ))
    workbook.active = workbook.sheetnames.index("Gráficas")

    evolution_sheet = workbook["Evolución"]
    groups: dict[int, list[int]] = {}
    for index, row in enumerate(ordered_evolution, start=2):
        groups.setdefault(row["vintage"], []).append(index)

    for column, title, anchor in (
        (3, f"{metric_label} por mes en libros", "A8"),
        (4, "Cuentas por mes en libros", "A27"),
    ):
        chart = ScatterChart(scatterStyle="lineMarker")
        chart.title = title
        chart.x_axis = NumericAxis(axId=10, crossAx=20, axPos="b", title="Mes en libros (MOB)")
        chart.y_axis = NumericAxis(
            axId=20, crossAx=10, title=metric_label if column == 3 else "Cuentas",
            numFmt=NumFmt(formatCode="0.00%") if column == 3 and is_percentage else None,
        )
        chart.width, chart.height = 24, 9
        for vintage_value, indices in groups.items():
            if column == 3 and all(
                ordered_evolution[index - 2]["metrics"][metric] is None for index in indices
            ):
                continue
            x_values = Reference(evolution_sheet, min_col=2, min_row=indices[0], max_row=indices[-1])
            y_values = Reference(evolution_sheet, min_col=column, min_row=indices[0], max_row=indices[-1])
            series = Series(y_values, x_values, title=str(vintage_value))
            series.marker.symbol = "circle"
            chart.series.append(series)
        if chart.series:
            charts.add_chart(chart, anchor)

    if rankings and any(row["metrics"][metric] is not None for row in rankings):
        ranking_sheet = workbook["Clasificación"]
        chart = BarChart()
        chart.title = f"{metric_label} por cosecha"
        chart.x_axis = TextAxis(axPos="b", title="Cosecha")
        chart.y_axis = NumericAxis(
            title=metric_label, numFmt=NumFmt(formatCode="0.00%") if is_percentage else None,
        )
        chart.width, chart.height = 24, 9
        chart.legend = None
        chart.add_data(Reference(ranking_sheet, min_col=2, min_row=1, max_row=len(rankings) + 1), titles_from_data=True)
        chart.set_categories(Reference(ranking_sheet, min_col=1, min_row=2, max_row=len(rankings) + 1))
        charts.add_chart(chart, "A46")
    return _finish(workbook)
