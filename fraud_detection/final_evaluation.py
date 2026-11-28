
import numpy as np

from fraud_detection.preprocessing import preprocess_data
from fraud_detection.c45.decision_tree import C45DecisionTree
from fraud_detection.evaluate_classifier import evaluate_predictions


def main():
    print("=" * 70)
    print("FINAL FRAUD DETECTION MODEL EVALUATION")
    print("=" * 70)

    # 1. Load the original dataset split
    print("\nLoading dataset...")

    X_train, X_val, X_test, y_train, y_val, y_test = preprocess_data()

    print(f"Training samples: {len(X_train)}")
    print(f"Validation samples: {len(X_val)}")
    print(f"Test samples: {len(X_test)}")

    # 2. Define the selected configuration
    model = C45DecisionTree(
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5
    )

    threshold = 0.60

    print("\nSelected configuration:")
    print(f"Maximum depth: {model.max_depth}")
    print(f"Minimum samples split: {model.min_samples_split}")
    print(f"Minimum samples leaf: {model.min_samples_leaf}")
    print(f"Classification threshold: {threshold}")

    # 3. Train using only the original training data
    print("\nTraining final C4.5 model...")

    model.fit(X_train, y_train)

    # 4. Obtain fraud probabilities on unseen test data
    print("\nGenerating predictions on test data...")

    probabilities = model.predict_proba(X_test)

    predictions = (probabilities >= threshold).astype(int)

    # 5. Evaluate final predictions
    print("\nEvaluating final model...")

    metrics = evaluate_predictions(
        y_test,
        predictions,
        strategy_name="Final C4.5 - Threshold 0.60"
    )

    # 6. Additional summary
    print("\n" + "=" * 70)
    print("FINAL MODEL SUMMARY")
    print("=" * 70)

    print(f"Test samples: {len(X_test)}")
    print(f"Fraudulent transactions: {int(np.sum(y_test == 1))}")
    print(f"Detected frauds: {metrics['tp']}")
    print(f"Missed frauds: {metrics['fn']}")
    print(f"False alarms: {metrics['fp']}")

    print("\nFinal metrics:")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1-score: {metrics['f1_score']:.4f}")
    print(f"False Positive Rate: {metrics['false_positive_rate']:.6f}")

    print("\nFinal evaluation completed successfully.")


if __name__ == "__main__":
    main()