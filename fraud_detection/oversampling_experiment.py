
import numpy as np
import pandas as pd

from fraud_detection.preprocessing import preprocess_data
from fraud_detection.c45.decision_tree import C45DecisionTree
from fraud_detection.evaluate_classifier import evaluate_predictions


def oversample_training_data(X_train, y_train, target_ratio, random_state=42):
    """
    Increase the fraud class proportion using random oversampling.

    The original legitimate transactions are preserved.
    Fraudulent transactions are sampled with replacement.
    """
    rng = np.random.default_rng(random_state)

    legitimate_indices = y_train[y_train == 0].index
    fraud_indices = y_train[y_train == 1].index

    target_fraud_count = int(
        np.ceil(target_ratio / (1 - target_ratio) * len(legitimate_indices))
    )

    additional_count = max(0, target_fraud_count - len(fraud_indices))

    sampled_fraud_indices = rng.choice(
        fraud_indices,
        size=additional_count,
        replace=True
    )

    selected_indices = np.concatenate([
        legitimate_indices.to_numpy(),
        fraud_indices.to_numpy(),
        sampled_fraud_indices
    ])

    rng.shuffle(selected_indices)

    X_resampled = X_train.loc[selected_indices].reset_index(drop=True)
    y_resampled = y_train.loc[selected_indices].reset_index(drop=True)

    return X_resampled, y_resampled


def main():
    print("Loading dataset...")

    X_train, X_val, X_test, y_train, y_val, y_test = preprocess_data()

    configurations = [
        ("Baseline", None),
        ("Oversampling 3%", 0.03),
        ("Oversampling 4%", 0.04),
        ("Oversampling 5%", 0.05),
        ("Oversampling 6%", 0.06),
        ("Oversampling 7%", 0.07)
    ]

    results = []

    for name, target_ratio in configurations:
        print(f"\n{'=' * 60}")
        print(f"Experiment: {name}")
        print("=" * 60)

        if target_ratio is None:
            X_resampled = X_train
            y_resampled = y_train
        else:
            X_resampled, y_resampled = oversample_training_data(
                X_train,
                y_train,
                target_ratio
            )

        fraud_count = int((y_resampled == 1).sum())
        legitimate_count = int((y_resampled == 0).sum())
        actual_ratio = fraud_count / len(y_resampled)

        print(f"Training samples: {len(y_resampled)}")
        print(f"Legitimate transactions: {legitimate_count}")
        print(f"Fraudulent transactions: {fraud_count}")
        print(f"Fraud proportion: {actual_ratio:.4%}")

        model = C45DecisionTree(
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5
        )

        print("\nTraining C4.5...")
        model.fit(X_resampled, y_resampled)

        print("Evaluating on original validation data...")
        predictions = model.predict(X_val)

        metrics = evaluate_predictions(y_val, predictions, strategy_name=name)

        results.append({
            "Experiment": name,
            "Precision": metrics["precision"],
            "Recall": metrics["recall"],
            "F1": metrics["f1_score"],
            "FPR": metrics["false_positive_rate"]
        })

    print(f"\n{'=' * 70}")
    print("FINAL COMPARISON")
    print("=" * 70)

    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))


if __name__ == "__main__":
    main()