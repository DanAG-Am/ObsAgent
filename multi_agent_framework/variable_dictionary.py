"""Read the portfolio variable dictionary without treating it as data evidence."""

from __future__ import annotations

import csv
import re
from pathlib import Path


DICTIONARY_PATH = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "Base Cards para TEC - Diccionario de Variables.csv"
)

SOURCE_FIELDS = {
    "vintage": "VINTAGE",
    "strategy": "STRATEGY",
    "strategy_segment": "STRATEGY_SEGMENT",
    "product": "PRODUCT",
    "channel": "CHANNEL",
    "age_tag": "AGE_TAG",
    "score_tag": "SCORE_TAG",
    "mob": "MOB",
    "accounts": "ACCOUNTS",
    "credit_lines_amount": "CREDITLINESAMTS",
    "enrolled_accounts": "ENRACCTS",
    "over30_accounts": "OVER30ACCTS",
    "over30_amount": "OVER30AMTS",
    "gross_chargeoff_amount": "GCLAMTS",
    "net_chargeoff_amount": "NCLAMTS",
    "recovery_amount": "RECOVERYAMTS",
    "enrolled_amount": "ENRAMTS",
    "revenue": "REVENUE",
    "acquisition_expense": "EXPENSES_ACQ",
    "variable_ecm_expense": "EXPENSES_ECM_VAR",
    "fixed_ecm_expense": "EXPENSES_ECM_FIX",
    "total_expense": "EXPENSES_TOTAL",
}


def load_variable_dictionary(path: Path | None = None) -> dict[str, str]:
    path = path or DICTIONARY_PATH
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or not {"Variable", "Descripción"} <= set(reader.fieldnames):
                raise ValueError("El diccionario no contiene las columnas Variable y Descripción.")
            definitions: dict[str, str] = {}
            for row in reader:
                name = (row.get("Variable") or "").strip().upper()
                description = (row.get("Descripción") or "").strip()
                if not name or not description or name in definitions or None in row:
                    raise ValueError(f"Entrada inválida o duplicada en la línea {reader.line_num} del diccionario.")
                definitions[name] = description
    except (OSError, UnicodeError, csv.Error) as error:
        raise ValueError(f"No se pudo leer el diccionario de variables: {error}") from error
    missing = set(SOURCE_FIELDS.values()) - definitions.keys()
    if missing:
        raise ValueError("Faltan variables en el diccionario: " + ", ".join(sorted(missing)))
    return definitions


def dictionary_context(definitions: dict[str, str]) -> str:
    """Provide short source definitions; full entries remain available via the tool."""
    names = ("vintage", "mob", "accounts", "revenue", "total_expense")
    return "\n".join(
        f"{name} ({SOURCE_FIELDS[name]}): "
        + re.split(r"(?<=\.)\s", definitions[SOURCE_FIELDS[name]], maxsplit=1)[0]
        for name in names
    )


def describe_variable(name: str) -> dict[str, str]:
    source_name = SOURCE_FIELDS.get(name.lower(), name.upper())
    definitions = load_variable_dictionary()
    if source_name not in definitions:
        raise ValueError(f"Variable no encontrada en el diccionario: {name}")
    return {
        "variable_fuente": source_name,
        "descripcion": definitions[source_name],
        "aviso": "El diccionario describe el origen; no verifica los datos actuales.",
    }
