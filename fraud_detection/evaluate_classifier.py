
import numpy as np

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

from fraud_detection.preprocessing import preprocess_data
from fraud_detection.c45.decision_tree import C45DecisionTree
from fraud_detection.risk_classifier import FraudRiskClassifier

from fraud_detection.logger import get_logger


logger = get_logger(__name__)


def evaluate_predictions(y_true, y_pred, strategy_name):
    """
    Calculates and displays classification metrics.
    """

    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(
        y_true, y_pred, zero_division=0
    )
    recall = recall_score(
        y_true, y_pred, zero_division=0
    )
    f1 = f1_score(
        y_true, y_pred, zero_division=0
    )

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1]
    )

    tn, fp, fn, tp = matrix.ravel()

    false_positive_rate = (
        fp / (fp + tn) if (fp + tn) else 0
    )

    print(f"\n========== {strategy_name} ==========")

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1-score: {f1:.4f}")
    print(f"False Positive Rate: {false_positive_rate:.4f}")

    print("\nConfusion Matrix:")
    print(matrix)

    print(f"\nTrue Negatives: {tn}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"True Positives: {tp}")

    return {
        "strategy": strategy_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": false_positive_rate,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp
    }


def apply_risk_strategy(
    classifier,
    X,
    model_predictions
):
    """
    Applies additional risk rules to legitimate C4.5 predictions.

    Suspicious transactions are counted as positive risk alerts.
    """

    combined_predictions = model_predictions.copy()

    transactions = X.to_numpy()

    for index, transaction in enumerate(transactions):

        # C4.5 fraudulent predictions remain unchanged
        if model_predictions[index] == 1:
            continue

        # Evaluate additional risk indicators
        risk_reasons = classifier.risk_rule_evaluator(
            transaction,
            classifier.feature_names
        )

        # Suspicious transactions count as positive alerts
        if risk_reasons:
            combined_predictions[index] = 1

    return combined_predictions


def main():

    logger.info("Starting fraud classifier evaluation.")

    # Load chronological datasets
    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test
    ) = preprocess_data()

    logger.info(
        "Training samples: %d | Validation samples: %d",
        len(X_train),
        len(X_val)
    )

    # Train C4.5 using training data only
    logger.info("Training C4.5 model.")

    model = C45DecisionTree(
        max_depth=10,
        min_samples_split=10,
        min_samples_leaf=5
    )

    model.fit(X_train, y_train)

    # Get baseline predictions
    logger.info("Evaluating baseline C4.5 model.")

    baseline_predictions = model.predict(X_val)

    results = []

    baseline_result = evaluate_predictions(
        y_val,
        baseline_predictions,
        "C4.5 BASELINE"
    )

    results.append(baseline_result)

    # Evaluate both risk strategies
    strategies = [
        "V14_V4",
        "V14_V10"
    ]

    feature_names = X_train.columns.tolist()

    for strategy in strategies:

        logger.info(
            "Evaluating risk strategy: %s",
            strategy
        )

        classifier = FraudRiskClassifier(
            model=model,
            feature_names=feature_names,
            risk_strategy=strategy
        )

        combined_predictions = apply_risk_strategy(
            classifier,
            X_val,
            baseline_predictions
        )

        strategy_result = evaluate_predictions(
            y_val,
            combined_predictions,
            f"C4.5 + {strategy}"
        )

        results.append(strategy_result)

    # Compare all strategies
    print("\n========== FINAL COMPARISON ==========")

    print(
        f"{'Strategy':<20}"
        f"{'Precision':>12}"
        f"{'Recall':>12}"
        f"{'F1-score':>12}"
        f"{'FPR':>12}"
    )

    for result in results:

        print(
            f"{result['strategy']:<20}"
            f"{result['precision']:>12.4f}"
            f"{result['recall']:>12.4f}"
            f"{result['f1_score']:>12.4f}"
            f"{result['false_positive_rate']:>12.4f}"
        )

    logger.info("Fraud classifier evaluation completed.")


if __name__ == "__main__":
    main()