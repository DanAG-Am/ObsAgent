
import csv
import tempfile
from pathlib import Path

from ChromaDB.ingest_csv import (
    REQUIRED_COLUMNS,
    validate_csv,
)


def test_valid_csv():
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "valid.csv"

        row = {column: "1" for column in REQUIRED_COLUMNS}

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=REQUIRED_COLUMNS,
            )
            writer.writeheader()
            writer.writerow(row)

        assert validate_csv(path) == 1
        print("PASS: Valid CSV")


def test_missing_column():
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "missing.csv"

        columns = REQUIRED_COLUMNS[:-1]

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerow({column: "1" for column in columns})

        try:
            validate_csv(path)
        except ValueError as error:
            assert "Missing required CSV columns" in str(error)
            print("PASS: Missing column detected")
        else:
            raise AssertionError("Missing column was not detected")


def test_invalid_number():
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "invalid.csv"

        row = {column: "1" for column in REQUIRED_COLUMNS}
        row["VINTAGE"] = "abc"

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=REQUIRED_COLUMNS,
            )
            writer.writeheader()
            writer.writerow(row)

        try:
            validate_csv(path)
        except ValueError as error:
            assert "VINTAGE" in str(error)
            print("PASS: Invalid number detected")
        else:
            raise AssertionError("Invalid number was not detected")


if __name__ == "__main__":
    test_valid_csv()
    test_missing_column()
    test_invalid_number()
    print("\nAll tests passed!")