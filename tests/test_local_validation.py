import csv
import tempfile
from pathlib import Path

from ChromaDB.ingest_csv import REQUIRED_COLUMNS
from multi_agent_framework.local_validation import validate_local_csv


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def base_row() -> dict[str, str]:
    row = {name: "0" for name in REQUIRED_COLUMNS}
    row.update({
        "VINTAGE": "202401", "STRATEGY": "Estrategia",
        "STRATEGY_SEGMENT": "Segmento", "PRODUCT": "Producto",
        "CHANNEL": "Canal", "AGE_TAG": "Edad", "SCORE_TAG": "Puntaje",
    })
    return row


def test_valid_schema_reports_only_the_checks_performed():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "data.csv"
        write_rows(path, [base_row()])
        result = validate_local_csv(path)
    assert result["status"] == "checks_completed"
    assert result["filas_validas"] == 1
    assert "snapshot_id" not in result
    assert "human_review_required" not in result
    assert result["incidencias"] == {}


def test_invalid_rows_and_reconciliation_are_reported_without_repair():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "data.csv"
        bad = base_row()
        bad.update({"VINTAGE": "202413", "MOB": "-1"})
        inconsistent = base_row()
        inconsistent.update({"MOB": "1", "GCLAMTS": "5", "NCLAMTS": "1", "EXPENSES_ACQ": "2"})
        write_rows(path, [bad, inconsistent])
        original = path.read_bytes()
        result = validate_local_csv(path)
        assert path.read_bytes() == original
    assert result["status"] == "rejected"
    assert result["filas_rechazadas"] == 1
    assert result["incidencias"]["cosecha_invalida"] == 1
    assert result["incidencias"]["perdida_neta_no_conciliada"] == 1
    assert result["incidencias"]["gastos_no_conciliados"] == 1
    assert result["incidencias"]["gasto_adquisicion_fuera_de_mob_cero"] == 1


def test_reconciliation_issue_is_not_reported_as_clean():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "data.csv"
        row = base_row()
        row["GCLAMTS"] = "5"
        write_rows(path, [row])
        result = validate_local_csv(path)
    assert result["status"] == "issues_found"
    assert result["incidencias"]["perdida_neta_no_conciliada"] == 1


def test_duplicate_rows_and_internal_mob_gaps_are_reported():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "data.csv"
        row = base_row()
        later = {**row, "MOB": "1000000000"}
        write_rows(path, [row, row, later])
        result = validate_local_csv(path)
    assert result["status"] == "issues_found"
    assert result["duplicados_exactos"] == 1
    assert result["cosechas_con_huecos_internos"] == 1
    assert result["cobertura"][0]["intervalos_faltantes"] == [{"desde": 1, "hasta": 999999999}]


if __name__ == "__main__":
    test_valid_schema_reports_only_the_checks_performed()
    test_invalid_rows_and_reconciliation_are_reported_without_repair()
    test_reconciliation_issue_is_not_reported_as_clean()
    test_duplicate_rows_and_internal_mob_gaps_are_reported()
    print("Local validation tests passed.")
