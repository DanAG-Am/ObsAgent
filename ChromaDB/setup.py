import chromadb
import pandas as pd

CSV_PATH = "archivo.csv"
DB_PATH = "./my_db"
COLLECTION_NAME = "mi_coleccion"

# 1. Leer el CSV
df = pd.read_csv(CSV_PATH)

# 2. Cliente local persistente y colección
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# 3. Construir ids, documents y metadatas (todas las columnas)
def to_native(v):
    return v.item() if hasattr(v, "item") else v  # numpy -> tipo nativo de Python

ids, documents, metadatas = [], [], []
for i, row in df.iterrows():
    row = row.dropna()  # omitir NA/vacíos: la metadata no los acepta
    ids.append(str(i))
    documents.append(" | ".join(f"{c}: {v}" for c, v in row.items()))
    metadatas.append({c: to_native(v) for c, v in row.items()})

# 4. Enviar por lotes
batch_size = client.get_max_batch_size()
for start in range(0, len(ids), batch_size):
    end = start + batch_size
    collection.upsert(
        ids=ids[start:end],
        documents=documents[start:end],
        metadatas=metadatas[start:end],
    )

print("Registros:", collection.count())

# 5. Prueba de consulta
res = collection.query(query_texts=["pérdida neta"], n_results=3)
print(res["documents"])