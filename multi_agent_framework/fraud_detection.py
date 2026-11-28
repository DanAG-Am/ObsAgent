"""C4.5 fraud scoring backed by the fraud_detection project."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_METADATA_PATH = PROJECT_ROOT / "models" / "model_metadata.json"
TRAINING_DATA_PATH = PROJECT_ROOT / "database" / "creditcard.csv"
MAX_FRAUD_TRANSACTIONS = 20


def _read_model_metadata() -> dict[str, Any]:
    try:
        metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"No se pudo leer la configuración del modelo de fraude: {error}") from error
    if not isinstance(metadata, dict):
        raise ValueError("La configuración del modelo de fraude debe ser un objeto JSON.")
    features = metadata.get("features")
    if not isinstance(features, list) or not features or not all(
        isinstance(feature, str) and feature for feature in features
    ):
        raise ValueError("La configuración del modelo no contiene una lista de variables válida.")
    if len(set(features)) != len(features):
        raise ValueError("La configuración del modelo contiene variables duplicadas.")
    return metadata


def fraud_feature_names() -> list[str]:
    metadata = _read_model_metadata()
    features = metadata["features"]
    return features


@lru_cache(maxsize=1)
def load_fraud_classifier() -> Any:
    from fraud_detection.c45.decision_tree import C45DecisionTree
    from fraud_detection.preprocessing import preprocess_data
    from fraud_detection.risk_classifier import FraudRiskClassifier

    metadata = _read_model_metadata()
    feature_names = metadata["features"]
    required_settings = {
        "max_depth",
        "min_samples_split",
        "min_samples_leaf",
        "classification_threshold",
    }
    missing_settings = sorted(required_settings - metadata.keys())
    if missing_settings:
        raise ValueError(
            "La configuración del modelo no contiene: "
            + ", ".join(missing_settings)
            + "."
        )

    X_train, _, _, y_train, _, _ = preprocess_data()
    if X_train.columns.tolist() != feature_names:
        raise ValueError(
            "Las variables del conjunto de entrenamiento no coinciden con la configuración del modelo."
        )
    if set(y_train.tolist()) != {0, 1}:
        raise ValueError(
            "El conjunto de entrenamiento debe contener ejemplos de transacciones legítimas y fraudulentas."
        )

    model = C45DecisionTree(
        max_depth=metadata["max_depth"],
        min_samples_split=metadata["min_samples_split"],
        min_samples_leaf=metadata["min_samples_leaf"],
    )
    model.fit(X_train.to_numpy(), y_train.to_numpy())
    return FraudRiskClassifier(
        model,
        feature_names=feature_names,
        threshold=metadata["classification_threshold"],
    )


def detect_fraud_transactions(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(transactions, list) or not transactions:
        raise ValueError("Proporciona al menos una transacción para analizar.")
    if len(transactions) > MAX_FRAUD_TRANSACTIONS:
        raise ValueError(
            f"Se pueden analizar hasta {MAX_FRAUD_TRANSACTIONS} transacciones por llamada."
        )

    feature_names = fraud_feature_names()
    expected = set(feature_names)
    validated_transactions = []

    for index, transaction in enumerate(transactions, start=1):
        if not isinstance(transaction, dict):
            raise ValueError(f"La transacción {index} debe ser un objeto de variables y valores.")
        received = set(transaction)
        missing = [feature for feature in feature_names if feature not in received]
        extra = sorted(received - expected)
        if missing or extra:
            details = []
            if missing:
                details.append(f"faltan variables: {', '.join(missing)}")
            if extra:
                details.append(f"variables desconocidas: {', '.join(extra)}")
            raise ValueError(f"Transacción {index}: {'; '.join(details)}.")

        values = []
        for feature in feature_names:
            value = transaction[feature]
            if isinstance(value, bool):
                raise ValueError(f"Transacción {index}: {feature} debe ser numérica.")
            try:
                values.append(float(value))
            except (TypeError, ValueError) as error:
                raise ValueError(f"Transacción {index}: {feature} debe ser numérica.") from error
        validated_transactions.append(values)

    classifier = load_fraud_classifier()
    results = []
    for index, values in enumerate(validated_transactions, start=1):
        result = classifier.classify_transaction(values)
        results.append({"transaccion": index, **result})

    return {
        "tipo": "deteccion_fraude_c45",
        "modelo": "C4.5",
        "aviso": (
            "Las clasificaciones y puntuaciones son resultados del modelo, no una "
            "confirmación de fraude ni una decisión operativa."
        ),
        "transacciones_analizadas": len(results),
        "resultados": results,
    }
