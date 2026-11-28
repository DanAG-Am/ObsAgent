
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

from fraud_detection.preprocessing import preprocess_data
from fraud_detection.c45.decision_tree import C45DecisionTree
from fraud_detection.logger import get_logger


logger = get_logger(__name__)


def tune_c45():

    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test
    ) = preprocess_data()

    # Candidate hyperparameter configurations
    configurations = [
        {"max_depth": 5, "min_samples_split": 10, "min_samples_leaf": 5},
        {"max_depth": 10, "min_samples_split": 10, "min_samples_leaf": 5},
        {"max_depth": 15, "min_samples_split": 10, "min_samples_leaf": 5},
        {"max_depth": 10, "min_samples_split": 20, "min_samples_leaf": 10},
        {"max_depth": 10, "min_samples_split": 10, "min_samples_leaf": 2},
        {"max_depth": 15, "min_samples_split": 20, "min_samples_leaf": 2}
    ]

    results = []

    for config in configurations:

        print("\n========================================")
        print(f"Testing configuration: {config}")

        model = C45DecisionTree(**config)

        model.fit(X_train, y_train)

        predictions = model.predict(X_val)

        precision = precision_score(
            y_val, predictions, zero_division=0
        )

        recall = recall_score(
            y_val, predictions, zero_division=0
        )

        f1 = f1_score(
            y_val, predictions, zero_division=0
        )

        tn, fp, fn, tp = confusion_matrix(
            y_val,
            predictions,
            labels=[0, 1]
        ).ravel()

        fpr = fp / (fp + tn) if (fp + tn) else 0

        result = {
            **config,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "fpr": fpr,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn
        }

        results.append(result)

        print(f"Precision: {precision:.4f}")
        print(f"Recall: {recall:.4f}")
        print(f"F1-score: {f1:.4f}")
        print(f"FPR: {fpr:.4f}")
        print(f"TP: {tp} | FP: {fp} | FN: {fn} | TN: {tn}")

    # Rank configurations by F1-score
    results.sort(
        key=lambda result: result["f1"],
        reverse=True
    )

    print("\n========== HYPERPARAMETER COMPARISON ==========")

    for result in results:

        print(
            f"Depth: {result['max_depth']:>2} | "
            f"Split: {result['min_samples_split']:>2} | "
            f"Leaf: {result['min_samples_leaf']:>2} | "
            f"Precision: {result['precision']:.4f} | "
            f"Recall: {result['recall']:.4f} | "
            f"F1: {result['f1']:.4f} | "
            f"FPR: {result['fpr']:.4f}"
        )

    logger.info("C4.5 hyperparameter evaluation completed.")


if __name__ == "__main__":
    tune_c45()