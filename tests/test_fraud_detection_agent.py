import asyncio
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from fraud_detection.preprocessing import DATA_PATH
from multi_agent_framework.fraud_detection import (
    PROJECT_ROOT,
    TRAINING_DATA_PATH,
    detect_fraud_transactions,
    fraud_feature_names,
    load_fraud_classifier,
)
from multi_agent_framework.query_service import QueryService


def test_fraud_detection_trains_c45_and_classifies_transactions():
    features = fraud_feature_names()
    training = pd.DataFrame([
        {feature: (index + 1 if feature == "Time" else 0.0) for feature in features}
        for index in range(20)
    ])
    labels = pd.Series([0] * 10 + [1] * 10)
    transactions = [
        {feature: (3.0 if feature == "Time" else 0.0) for feature in features},
        {feature: (18.0 if feature == "Time" else 0.0) for feature in features},
    ]

    load_fraud_classifier.cache_clear()
    try:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "fraud_detection.preprocessing.preprocess_data",
                lambda: (training, None, None, labels, None, None),
            )
            result = detect_fraud_transactions(transactions)
    finally:
        load_fraud_classifier.cache_clear()

    assert result["tipo"] == "deteccion_fraude_c45"
    assert result["transacciones_analizadas"] == 2
    assert [row["risk_level"] for row in result["resultados"]] == [
        "Legitimate",
        "Fraudulent",
    ]
    assert all(row["decision_path"] for row in result["resultados"])


def test_fraud_training_paths_point_to_database_csv():
    expected = PROJECT_ROOT / "database" / "creditcard.csv"
    assert DATA_PATH == expected
    assert TRAINING_DATA_PATH == expected


def test_fraud_detection_rejects_incomplete_transaction_before_training():
    features = fraud_feature_names()
    incomplete = {feature: 1.0 for feature in features[:-1]}
    load_fraud_classifier.cache_clear()
    with pytest.raises(ValueError, match="faltan variables"):
        detect_fraud_transactions([incomplete])


def test_fraud_agent_executes_structured_json_request():
    from multi_agent_framework.agent_manager import FraudDetectionAgent

    agent = FraudDetectionAgent()
    result = {"tipo": "deteccion_fraude_c45"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(agent, "detect_transactions", Mock(return_value=result))
        actual = asyncio.run(agent.execute('{"transactions": [{"Time": 1}]}'))
    assert actual == result


def test_query_service_uses_registered_fraud_agent():
    service = QueryService.__new__(QueryService)
    service._system = Mock()
    result = {"tipo": "deteccion_fraude_c45"}
    service._system.detect_fraud.return_value = result

    actual = asyncio.run(service.detect_fraud([{"Time": 1}]))

    assert actual == result
    service._system.detect_fraud.assert_called_once_with([{"Time": 1}])
