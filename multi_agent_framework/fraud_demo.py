"""Statistical demonstration using exclusively invented aggregate counts."""

from typing import Any

from ChromaDB.precomputed_queries import iqr_fences


def analyze_synthetic_fraud() -> dict[str, Any]:
    """Analyze fixed synthetic counts; this is not a real fraud detector."""
    observations = [
        ("Canal simulado A", 1_000, 1),
        ("Canal simulado B", 1_000, 2),
        ("Canal simulado C", 1_000, 3),
        ("Canal simulado D", 1_000, 4),
        ("Canal simulado E", 1_000, 4),
        ("Canal simulado F", 1_000, 20),
    ]
    rates = [incidents / transactions for _, transactions, incidents in observations]
    q1, q3, lower, upper = iqr_fences(rates)
    rows = [
        {
            "canal": channel,
            "transacciones_simuladas": transactions,
            "incidentes_simulados": incidents,
            "tasa": rate,
            "valor_atipico": rate < lower or rate > upper,
        }
        for (channel, transactions, incidents), rate in zip(observations, rates)
    ]
    return {
        "tipo": "demostracion_sintetica",
        "aviso": (
            "Datos inventados exclusivamente para demostración. La tasa es una proporción "
            "de incidentes supuestos, no una probabilidad de fraude. El IQR no detecta "
            "fraude real y su confiabilidad no está validada."
        ),
        "metodo": (
            "IQR: ordenar las tasas, dividir en dos mitades (la central queda en la "
            "superior si el total es impar) y elegir el elemento central superior "
            "de cada mitad; límites a 1.5 × IQR."
        ),
        "unidad_tasa": "proporción; 1 equivale al 100%",
        "q1": q1,
        "q3": q3,
        "limite_inferior": lower,
        "limite_superior": upper,
        "resultados": rows,
    }
