from io import BytesIO

from openpyxl import load_workbook

from multi_agent_framework.excel_report import build_chat_excel, build_dashboard_excel


def test_chat_excel_preserves_long_text_and_treats_formulas_as_text():
    question = "=HYPERLINK(\"https://example.invalid\",\"click\")"
    answer = "A" * 32001
    data = build_chat_excel(question, answer, {"tool_results": []})
    workbook = load_workbook(BytesIO(data), data_only=False)
    sheet = workbook["Respuesta"]
    assert sheet["B3"].value == question
    assert sheet["B3"].data_type == "s"
    assert sheet["B4"].value + sheet["B5"].value == answer
    assert "NO VERIFICADO" in sheet["B2"].value
    workbook.close()


def test_dashboard_excel_preserves_null_zero_and_percent_units():
    rows = [
        {"vintage": 202401, "mob": 0, "metrics": {"rate": None}, "measures": {"accounts": 0}},
        {"vintage": 202401, "mob": 1, "metrics": {"rate": 0.125}, "measures": {"accounts": 10}},
    ]
    data = build_dashboard_excel("Tasa", 0.0, 0, 202401, 0, rows, [], "rate", True)
    workbook = load_workbook(BytesIO(data))
    assert workbook["Resumen"]["B4"].value == 0
    assert workbook["Resumen"]["B5"].value == 0
    assert workbook["Resumen"]["B5"].number_format == "0.00%"
    assert workbook["Evolución"]["C2"].value is None
    assert workbook["Evolución"]["C3"].value == 0.125
    assert workbook["Evolución"]["C3"].number_format == "0.00%"
    assert len(workbook["Gráficas"]._charts) == 2
    workbook.close()


def test_dashboard_excel_charts_reference_separate_cohorts_and_ranking():
    rows = [
        {"vintage": 202402, "mob": 2, "metrics": {"rate": 0.2}, "measures": {"accounts": 30}},
        {"vintage": 202401, "mob": 1, "metrics": {"rate": None}, "measures": {"accounts": 10}},
        {"vintage": 202401, "mob": 0, "metrics": {"rate": 0.125}, "measures": {"accounts": 5}},
    ]
    rankings = [
        {"vintage": 202402, "metrics": {"rate": 0.2}, "measures": {"accounts": 30}},
        {"vintage": 202401, "metrics": {"rate": 0.125}, "measures": {"accounts": 15}},
    ]
    data = build_dashboard_excel(
        "Tasa", 0.125, 5, 202401, 0, rows, rankings, "rate", True, {"product": "A"},
    )
    workbook = load_workbook(BytesIO(data))
    assert workbook.active.title == "Gráficas"
    assert workbook["Resumen"]["B10"].value == "Producto: A"
    assert workbook["Gráficas"]["B6"].value == "Producto: A"
    evolution = workbook["Evolución"]
    assert [(evolution.cell(i, 1).value, evolution.cell(i, 2).value) for i in range(2, 5)] == [
        (202401, 0), (202401, 1), (202402, 2),
    ]
    assert evolution["C3"].value is None
    charts = workbook["Gráficas"]._charts
    assert len(charts) == 3
    metric, accounts, ranking = charts
    assert metric.y_axis.numFmt.formatCode == "0.00%"
    assert metric.display_blanks == "gap"
    assert [series.tx.v for series in metric.series] == ["202401", "202402"]
    assert metric.series[0].xVal.numRef.f == "'Evolución'!$B$2:$B$3"
    assert metric.series[0].yVal.numRef.f == "'Evolución'!$C$2:$C$3"
    assert accounts.series[1].yVal.numRef.f == "'Evolución'!$D$4"
    assert ranking.series[0].val.numRef.f == "'Clasificación'!$B$2:$B$3"
    assert ranking.series[0].cat.numRef.f == "'Clasificación'!$A$2:$A$3"
    assert ranking.y_axis.numFmt.formatCode == "0.00%"
    workbook.close()


def test_dashboard_excel_keeps_monetary_chart_units_and_skips_empty_series():
    rows = [{"vintage": 202401, "mob": 0, "metrics": {"amount": None}, "measures": {"accounts": 5}}]
    data = build_dashboard_excel("Monto", None, 5, None, None, rows, [], "amount", False)
    workbook = load_workbook(BytesIO(data))
    charts = workbook["Gráficas"]._charts
    assert len(charts) == 1
    assert charts[0].y_axis.numFmt is None
    workbook.close()


if __name__ == "__main__":
    test_chat_excel_preserves_long_text_and_treats_formulas_as_text()
    test_dashboard_excel_preserves_null_zero_and_percent_units()
    test_dashboard_excel_charts_reference_separate_cohorts_and_ranking()
    test_dashboard_excel_keeps_monetary_chart_units_and_skips_empty_series()
    print("Excel report tests passed.")
