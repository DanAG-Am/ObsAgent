import csv
import hashlib
import json
import math
import re
from pathlib import Path

import chromadb

PROJECT_DIR = Path(__file__).resolve().parent
CSV_PATH = PROJECT_DIR.parent / "database" / "base_cards_sintetica.csv"
CHROMA_PATH = PROJECT_DIR / "chroma_data"
COLLECTION_NAME = "base_cards_sintetica"
BATCH_SIZE = 5_000
EMBEDDING_DIMENSION = 64
TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)

REQUIRED_COLUMNS = [
    "VINTAGE",
    "STRATEGY",
    "STRATEGY_SEGMENT",
    "PRODUCT",
    "CHANNEL",
    "AGE_TAG",
    "SCORE_TAG",
    "MOB",
    "ACCOUNTS",
    "CREDITLINESAMTS",
    "ENRACCTS",
    "OVER30ACCTS",
    "OVER30AMTS",
    "GCLAMTS",
    "NCLAMTS",
    "RECOVERYAMTS",
    "ENRAMTS",
    "REVENUE",
    "EXPENSES_ACQ",
    "EXPENSES_ECM_VAR",
    "EXPENSES_ECM_FIX",
    "EXPENSES_TOTAL",
]

INTEGER_COLUMNS = [
    "VINTAGE",
    "MOB",
    "ACCOUNTS",
    "ENRACCTS",
    "OVER30ACCTS",
]

FLOAT_COLUMNS = [
    "CREDITLINESAMTS",
    "OVER30AMTS",
    "GCLAMTS",
    "NCLAMTS",
    "RECOVERYAMTS",
    "ENRAMTS",
    "REVENUE",
    "EXPENSES_ACQ",
    "EXPENSES_ECM_VAR",
    "EXPENSES_ECM_FIX",
    "EXPENSES_TOTAL",
]

def hashed_embedding(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    for token in TOKEN_PATTERN.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % EMBEDDING_DIMENSION
        vector[index] += 1.0 if digest[2] % 2 else -1.0

    magnitude = math.sqrt(sum(value * value for value in vector))
    return [value / magnitude for value in vector] if magnitude else vector


def row_document(row: dict[str, str]) -> str:
    return " | ".join(f"{key}={value}" for key, value in row.items())

def validate_csv(csv_path: Path) -> int:
    """
    Validate CSV headers and numeric values before modifying ChromaDB.

    Returns:
        Number of valid data rows.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path}"
        )

    valid_rows = 0

    with csv_path.open(
        newline="",
        encoding="utf-8-sig"
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        if not reader.fieldnames:
            raise ValueError("The CSV file is empty or has no header.")

        headers = reader.fieldnames

        # Check duplicate columns
        duplicates = [
            column
            for column in set(headers)
            if headers.count(column) > 1
        ]

        if duplicates:
            raise ValueError(
                f"Duplicate CSV columns: {duplicates}"
            )

        # Check required columns
        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in headers
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required CSV columns: {missing_columns}"
            )

        # Validate each row
        for row in reader:
            line_number = reader.line_num

            # Detect rows with extra or missing fields
            if None in row or any(
                value is None for value in row.values()
            ):
                raise ValueError(
                    f"Invalid number of fields at CSV line "
                    f"{line_number}."
                )

            # Validate integer columns
            for column in INTEGER_COLUMNS:
                value = row[column].strip()

                try:
                    int(value)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid integer at CSV line {line_number}, "
                        f"column '{column}': {value!r}"
                    ) from None

            # Validate float columns
            for column in FLOAT_COLUMNS:
                value = row[column].strip()

                try:
                    number = float(value)

                    if not math.isfinite(number):
                        raise ValueError

                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid number at CSV line {line_number}, "
                        f"column '{column}': {value!r}"
                    ) from None

            valid_rows += 1

    if valid_rows == 0:
        raise ValueError("The CSV contains no data rows.")

    return valid_rows

def ingest_csv(collection: chromadb.Collection) -> int:
    total = 0
    with CSV_PATH.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        while rows := [row for _, row in zip(range(BATCH_SIZE), reader)]:
            ids = [f"row-{total + index}" for index in range(len(rows))]
            documents = [row_document(row) for row in rows]
            embeddings = [hashed_embedding(document) for document in documents]
            metadatas = [
                {
                    "vintage": int(row["VINTAGE"]),
                    "strategy": row["STRATEGY"],
                    "strategy_segment": row["STRATEGY_SEGMENT"],
                    "product": row["PRODUCT"],
                    "channel": row["CHANNEL"],
                    "age_tag": row["AGE_TAG"],
                    "score_tag": row["SCORE_TAG"],
                    "mob": int(row["MOB"]),
                    "accounts": int(row["ACCOUNTS"]),
                    "credit_lines_amount": float(row["CREDITLINESAMTS"]),
                    "enrolled_accounts": int(row["ENRACCTS"]),
                    "over30_accounts": int(row["OVER30ACCTS"]),
                    "over30_amount": float(row["OVER30AMTS"]),
                    "gross_chargeoff_amount": float(row["GCLAMTS"]),
                    "net_chargeoff_amount": float(row["NCLAMTS"]),
                    "recovery_amount": float(row["RECOVERYAMTS"]),
                    "enrolled_amount": float(row["ENRAMTS"]),
                    "revenue": float(row["REVENUE"]),
                    "acquisition_expense": float(row["EXPENSES_ACQ"]),
                    "variable_ecm_expense": float(row["EXPENSES_ECM_VAR"]),
                    "fixed_ecm_expense": float(row["EXPENSES_ECM_FIX"]),
                    "total_expense": float(row["EXPENSES_TOTAL"]),
                }
                for row in rows
            ]
            collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            total += len(rows)
            if total % (BATCH_SIZE * 10) == 0:
                print(f"Ingested {total:,} rows...")
    return total


def main() -> None:
    print("Validating CSV...")

    valid_rows = validate_csv(CSV_PATH)

    print(f"CSV validation successful: {valid_rows:,} rows.")

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    ingested = ingest_csv(collection)

    query = "young customers with a high credit score at an airport"
    results = collection.query(
        query_embeddings=[hashed_embedding(query)],
        n_results=5,
        include=["documents", "metadatas", "distances"],
    )

    print(f"\nIngested data: {ingested:,} CSV rows")
    print(f"Collection count: {collection.count():,}")
    print(f"Query: {query}")
    print("Results:")
    for item_id, document, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        print(f"- {item_id} (distance={distance:.4f}, metadata={json.dumps(metadata)})")
        print(f"  {document}")


if __name__ == "__main__":
    main()
