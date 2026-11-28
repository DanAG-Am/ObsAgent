
import numpy as np
import pytest

from fraud_detection.c45.decision_tree import C45DecisionTree
from fraud_detection.risk_classifier import FraudRiskClassifier


@pytest.fixture
def classifier():
    X = np.array([
        [1, 10],
        [2, 20],
        [3, 30],
        [4, 40],
        [5, 50],
        [6, 60],
        [7, 70],
        [8, 80]
    ])

    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])

    model = C45DecisionTree(
        max_depth=5,
        min_samples_split=2,
        min_samples_leaf=1
    )

    model.fit(X, y)

    return FraudRiskClassifier(
        model,
        feature_names=[
            "Transaction_Feature_1",
            "Transaction_Feature_2"
        ],
        threshold=0.60
    )


def test_legitimate_transaction(classifier):
    result = classifier.classify_transaction(
        np.array([2, 20])
    )

    assert result["prediction"] == 0
    assert result["risk_level"] == "Legitimate"


def test_fraudulent_transaction(classifier):
    result = classifier.classify_transaction(
        np.array([7, 70])
    )

    assert result["prediction"] == 1
    assert result["risk_level"] == "Fraudulent"


def test_classification_threshold(classifier):
    result = classifier.classify_transaction(
        np.array([7, 70])
    )

    assert result["fraud_probability"] >= result["threshold"]


def test_decision_path(classifier):
    result = classifier.classify_transaction(
        np.array([7, 70])
    )

    assert len(result["decision_path"]) > 0
    assert "Transaction_Feature_1" in result["explanation"]


@pytest.mark.parametrize(
    "transaction",
    [
        np.array([1]),
        np.array([1, np.nan]),
        np.array([1, np.inf]),
        np.array([[1, 10]])
    ]
)
def test_invalid_transactions(classifier, transaction):
    with pytest.raises(ValueError):
        classifier.classify_transaction(transaction)

def test_suspicious_transaction(classifier):
    def custom_risk_rule(transaction, feature_names):
        return ["Unusual transaction amount."]

    classifier.risk_rule_evaluator = custom_risk_rule

    result = classifier.classify_transaction(
        np.array([2, 20])
    )

    assert result["prediction"] == 0
    assert result["risk_level"] == "Suspicious"
    assert len(result["risk_reasons"]) > 0