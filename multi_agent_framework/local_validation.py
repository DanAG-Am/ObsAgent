"""Read-only structural and reconciliation checks for the local source CSV."""

from __future__ import annotations

import csv
import hashlib
import itertools
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ChromaDB.ingest_csv import CSV_PATH, FLOAT_COLUMNS, INTEGER_COLUMNS, REQUIRED_COLUMNS


TEXT_COLUMNS = set(REQUIRED_COLUMNS) - set(INTEGER_COLUMNS) - set(FLOAT_COLUMNS)
INTEGER_PATTERN = re.compile(r"[0-9]+\Z", re.ASCII)
DECIMAL_PATTERN = re.compile(r"-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z", re.ASCII)
RECONCILIATION_TOLERANCE = Decimal("0.01")


def validate_local_csv(path: Path = CSV_PATH) -> dict[str, Any]:
    """Screen selected properties of the local source without modifying it."""
    issues: Counter[str] = Counter()
    rows = valid_rows = 0
    header: list[str] = []
    unexpected: list[str] = []
    seen_rows: set[bytes] = set()
    duplicate_rows = 0
    coverage: dict[int, set[int]] = {}
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, strict=True)
            header = next(reader, [])
            if (
                not header
                or any(not name or name != name.strip() or "\x00" in name for name in header)
                or len(header) != len(set(header))
            ):
                raise ValueError("El encabezado está vacío, duplicado o mal formado.")
            missing = sorted(set(REQUIRED_COLUMNS) - set(header))
            if missing:
                raise ValueError("Faltan columnas requeridas: " + ", ".join(missing))
            unexpected = sorted(set(header) - set(REQUIRED_COLUMNS))
            indexes = {name: header.index(name) for name in REQUIRED_COLUMNS}
            for record in reader:
                rows += 1
                row_issues: set[str] = set()
                if len(record) != len(header):
                    issues["numero_de_campos_incorrecto"] += 1
                    continue
                if any("\x00" in value for value in record):
                    issues["caracter_nulo"] += 1
                    continue
                digest = hashlib.sha256(repr(record).encode("utf-8")).digest()
                if digest in seen_rows:
                    duplicate_rows += 1
                else:
                    seen_rows.add(digest)
                for name in TEXT_COLUMNS:
                    if not record[indexes[name]].strip():
                        row_issues.add("texto_requerido_vacio")
                numbers: dict[str, Decimal] = {}
                for name in INTEGER_COLUMNS + FLOAT_COLUMNS:
                    value = record[indexes[name]]
                    if not value or value != value.strip():
                        row_issues.add("numero_invalido")
                        continue
                    if name in INTEGER_COLUMNS and not INTEGER_PATTERN.fullmatch(value):
                        row_issues.add("entero_invalido")
                        continue
                    if name in FLOAT_COLUMNS and not DECIMAL_PATTERN.fullmatch(value):
                        row_issues.add("numero_invalido")
                        continue
                    try:
                        number = Decimal(value)
                    except InvalidOperation:
                        row_issues.add("numero_invalido")
                        continue
                    if not number.is_finite() or number < 0:
                        row_issues.add("numero_negativo_o_no_finito")
                        continue
                    numbers[name] = number
                vintage = record[indexes["VINTAGE"]]
                if not re.fullmatch(r"[0-9]{6}", vintage, re.ASCII) or not 1 <= int(vintage[-2:]) <= 12:
                    row_issues.add("cosecha_invalida")
                if row_issues:
                    issues.update(row_issues)
                    continue
                valid_rows += 1
                coverage.setdefault(int(vintage), set()).add(int(numbers["MOB"]))
                if abs(numbers["NCLAMTS"] - (numbers["GCLAMTS"] - numbers["RECOVERYAMTS"])) > RECONCILIATION_TOLERANCE:
                    issues["perdida_neta_no_conciliada"] += 1
                expenses = numbers["EXPENSES_ACQ"] + numbers["EXPENSES_ECM_VAR"] + numbers["EXPENSES_ECM_FIX"]
                if abs(numbers["EXPENSES_TOTAL"] - expenses) > RECONCILIATION_TOLERANCE:
                    issues["gastos_no_conciliados"] += 1
                if numbers["MOB"] != 0 and numbers["EXPENSES_ACQ"] != 0:
                    issues["gasto_adquisicion_fuera_de_mob_cero"] += 1
    except (OSError, UnicodeError, csv.Error) as error:
        raise ValueError(f"No se pudo validar el CSV local: {error}") from error
    if not rows:
        raise ValueError("El CSV local no contiene registros.")
    rejected = rows - valid_rows
    gaps = [
        {
            "cosecha": vintage,
            "primer_mob": min(mobs),
            "ultimo_mob": max(mobs),
            "intervalos_faltantes": list(itertools.islice((
                {"desde": left + 1, "hasta": right - 1}
                for left, right in zip(sorted(mobs), sorted(mobs)[1:])
                if right - left > 1
            ), 20)),
        }
        for vintage, mobs in sorted(coverage.items())
        if len(mobs) < max(mobs) - min(mobs) + 1
    ]
    return {
        "status": "rejected" if rejected else ("issues_found" if issues or duplicate_rows or gaps else "checks_completed"),
        "archivo": path.name,
        "filas": rows,
        "filas_validas": valid_rows,
        "filas_rechazadas": rejected,
        "columnas_adicionales": unexpected,
        "incidencias": dict(issues),
        "tolerancia_conciliacion": str(RECONCILIATION_TOLERANCE),
        "duplicados_exactos": duplicate_rows,
        "cosechas_con_huecos_internos": len(gaps),
        "cobertura": gaps[:20],
        "advertencias": [
            "La revisión aplica al CSV local, no acredita que coincida con los agregados.",
            "Los duplicados son filas completas idénticas, no posibles duplicados de negocio.",
            "La cobertura solo identifica meses intermedios faltantes dentro del rango observado.",
            "No se comprobaron catálogos ni umbrales de población. Se muestran hasta 20 cosechas y 20 intervalos por cosecha.",
            "La tolerancia de 0.01 es un control interno de conciliación, no un límite regulatorio.",
        ],
    }
