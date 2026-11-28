
from fraud_detection.explainability import (
    explain_prediction,
    format_explanation
)
from fraud_detection.validation import validate_transaction
from fraud_detection.logger import get_logger


logger = get_logger(__name__)


# Thresholds obtained from the training fraud distributions
RISK_THRESHOLDS = {
    "V14": -7.0199,
    "V4": 4.3282,
    "V10": -5.0525,
    "V11": 4.0663
}


def default_risk_rules(transaction, feature_names):
    """
    Evaluates additional risk indicators.

    No additional risk rules are configured.
    """
    return []


def create_pairwise_risk_evaluator(feature_names, strategy="V14_V4"):
    """
    Creates a configurable evaluator using two PCA features.
    """

    strategies = {
        "V14_V4": ["V14", "V4"],
        "V14_V10": ["V14", "V10"],
        "V11": ["V11"]
    }

    if strategy not in strategies:
        raise ValueError(
            f"Unknown risk strategy: {strategy}"
        )

    if feature_names is None:
        raise ValueError(
            "Feature names are required for PCA risk rules."
        )

    feature_indices = {
        name: index
        for index, name in enumerate(feature_names)
    }

    required_features = strategies[strategy]

    missing_features = [
        feature for feature in required_features
        if feature not in feature_indices
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    def evaluate(transaction, current_feature_names):

        if strategy == "V14_V4":

            v14 = transaction[feature_indices["V14"]]
            v4 = transaction[feature_indices["V4"]]

            v14_triggered = v14 <= RISK_THRESHOLDS["V14"]
            v4_triggered = v4 >= RISK_THRESHOLDS["V4"]

            if v14_triggered and v4_triggered:
                return [
                    "V14 is unusually low.",
                    "V4 is unusually high."
                ]

        elif strategy == "V14_V10":

            v14 = transaction[feature_indices["V14"]]
            v10 = transaction[feature_indices["V10"]]

            v14_triggered = v14 <= RISK_THRESHOLDS["V14"]
            v10_triggered = v10 <= RISK_THRESHOLDS["V10"]

            if v14_triggered and v10_triggered:
                return [
                    "V14 is unusually low.",
                    "V10 is unusually low."
                ]

        elif strategy == "V11":
    
            v11 = transaction[feature_indices["V11"]]

            if v11 >= RISK_THRESHOLDS["V11"]:
                return [
                    "V11 is unusually high."
                ]

        return []

    return evaluate


class FraudRiskClassifier:

    def __init__(
        self,
        model,
        feature_names=None,
        risk_rule_evaluator=None,
        risk_strategy=None,
        threshold=0.60
    ):
        self.model = model
        self.feature_names = feature_names

        if self.model.tree is None:
            raise ValueError(
                "The decision tree has not been trained yet."
            )

        if risk_rule_evaluator is not None and risk_strategy is not None:
            raise ValueError(
                "Provide either a custom evaluator or a risk strategy, not both."
            )

        if risk_strategy is not None:
            self.risk_rule_evaluator = create_pairwise_risk_evaluator(
                feature_names,
                risk_strategy
            )

        elif risk_rule_evaluator is not None:
            self.risk_rule_evaluator = risk_rule_evaluator

        else:
            self.risk_rule_evaluator = default_risk_rules

        self.risk_strategy = risk_strategy
        self.threshold = threshold

        if not 0 <= self.threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1.")

        logger.info(
            "Fraud risk classifier initialized. Strategy: %s",
            risk_strategy or "None"
        )

    def classify_transaction(self, transaction):
        """
        Classifies a transaction using C4.5 and additional risk rules.
        """

        # Validate transaction data
        transaction = validate_transaction(
            transaction,
            self.model.n_features
        )

        # Get the C4.5 prediction and explanation
        result = explain_prediction(
            self.model,
            transaction,
            self.feature_names
        )

        fraud_probability = self.model.predict_proba_one(transaction)

        prediction = int(fraud_probability >= self.threshold)

        result["prediction"] = prediction

        # Evaluate additional risk indicators
        risk_reasons = self.risk_rule_evaluator(
            transaction,
            self.feature_names
        )

        if not isinstance(risk_reasons, list):
            raise TypeError(
                "The risk rule evaluator must return a list of strings."
            )

        if not all(isinstance(reason, str) for reason in risk_reasons):
            raise TypeError(
                "Every risk reason must be a string."
            )

        # Determine the final risk level
        if prediction == 1:
            risk_level = "Fraudulent"

        elif risk_reasons:
            risk_level = "Suspicious"

        else:
            risk_level = "Legitimate"

        # Generate the explanation
        explanation = format_explanation(result)

        if risk_reasons:
            explanation += "\n\nAdditional risk indicators:"

            for reason in risk_reasons:
                explanation += f"\n- {reason}"

        # Log classification result
        logger.info(
            "Transaction classified: prediction=%s, risk_level=%s.",
            prediction,
            risk_level
        )

        if risk_level == "Fraudulent":
            logger.warning("Transaction classified as fraudulent.")

        elif risk_level == "Suspicious":
            logger.warning("Transaction classified as suspicious.")

        return {
            "prediction": prediction,
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
            "explanation": explanation,
            "decision_path": result["decision_path"],
            "fraud_probability": float(fraud_probability),
            "threshold": self.threshold,
        }


if __name__ == "__main__":
    
    import numpy as np
    from fraud_detection.c45.decision_tree import C45DecisionTree

    # Example training dataset
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

    # Train the C4.5 model
    model = C45DecisionTree(
        max_depth=5,
        min_samples_split=2,
        min_samples_leaf=1
    )

    model.fit(X, y)

    # Initialize the classifier
    classifier = FraudRiskClassifier(
        model,
        feature_names=[
            "Transaction_Feature_1",
            "Transaction_Feature_2"
        ],
        threshold=0.60
    )

    # Define test transactions
    test_transactions = {
        "Legitimate": np.array([2, 20]),
        "Fraudulent": np.array([7, 70])
    }

    # Test each transaction
    for scenario, transaction in test_transactions.items():

        result = classifier.classify_transaction(transaction)

        print(f"\n========== {scenario.upper()} TEST ==========")
        print(f"Prediction: {result['prediction']}")
        print(f"Risk Level: {result['risk_level']}")
        print(f"Fraud Probability: {result['fraud_probability']:.4f}")
        print(f"Threshold: {result['threshold']:.2f}")
        print(f"Risk Reasons: {result['risk_reasons']}")

        print("\nExplanation:")
        print(result["explanation"])

    # Test invalid transactions
    invalid_transactions = {
        "Missing feature": np.array([1]),
        "NaN value": np.array([1, np.nan]),
        "Infinite value": np.array([1, np.inf]),
        "Unexpected dimensions": np.array([[1, 10]])
    }

    for scenario, transaction in invalid_transactions.items():

        print(f"\n========== {scenario.upper()} TEST ==========")

        try:
            classifier.classify_transaction(transaction)
            print("ERROR: Invalid transaction was accepted.")

        except (ValueError, TypeError) as error:
            print(f"Invalid transaction rejected: {error}")