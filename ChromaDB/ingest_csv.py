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
                    "vintage": row["VINTAGE"],
                    "product": row["PRODUCT"],
                    "channel": row["CHANNEL"],
                    "age_tag": row["AGE_TAG"],
                    "score_tag": row["SCORE_TAG"],
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
