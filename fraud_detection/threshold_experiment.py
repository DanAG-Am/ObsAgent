
import numpy as np
import pandas as pd

from fraud_detection.preprocessing import preprocess_data
from fraud_detection.c45.decision_tree import C45DecisionTree
from fraud_detection.evaluate_classifier import evaluate_predictions


def oversample_training_data(X_train, y_train, target_ratio, random_state=42):
    """
    Increase the fraud class proportion using random oversampling.
    """
    rng = np.random.default_rng(random_state)

    legitimate_indices = y_train[y_train == 0].index
    fraud_indices = y_train[y_train == 1].index

    target_fraud_count = int(
        np.ceil(
            target_ratio / (1 - target_ratio)
            * len(legitimate_indices)
        )
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


def evaluate_thresholds(model, X_val, y_val, model_name, thresholds):
    """
    Evaluate a trained model using different fraud probability thresholds.
    """
    print(f"\n{'=' * 70}")
    print(f"Threshold experiments: {model_name}")
    print("=" * 70)

    probabilities = model.predict_proba(X_val)

    results = []

    for threshold in thresholds:
        print(f"\nTesting threshold: {threshold:.2f}")

        predictions = (probabilities >= threshold).astype(int)

        metrics = evaluate_predictions(
            y_val,
            predictions,
            strategy_name=f"{model_name} - Threshold {threshold:.2f}"
        )

        results.append({
            "Model": model_name,
            "Threshold": threshold,
            "Precision": metrics["precision"],
            "Recall": metrics["recall"],
            "F1": metrics["f1_score"],
            "FPR": metrics["false_positive_rate"],
            "TP": metrics["tp"],
            "FP": metrics["fp"],
            "FN": metrics["fn"],
            "TN": metrics["tn"]
        })

    return results


def main():
    print("Loading dataset...")

    X_train, X_val, X_test, y_train, y_val, y_test = preprocess_data()

    thresholds = [
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85
    ]

    configurations = [
        ("Baseline", X_train, y_train)
    ]

    all_results = []

    for model_name, X_model, y_model in configurations:
        print(f"\nTraining model: {model_name}")

        model = C45DecisionTree(
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5
        )

        model.fit(X_model, y_model)

        results = evaluate_thresholds(
            model,
            X_val,
            y_val,
            model_name,
            thresholds
        )

        all_results.extend(results)

    results_df = pd.DataFrame(all_results)

    print("\n" + "=" * 90)
    print("FINAL THRESHOLD COMPARISON")
    print("=" * 90)

    print(
        results_df[
            [
                "Model",
                "Threshold",
                "Precision",
                "Recall",
                "F1",
                "FPR",
                "TP",
                "FP",
                "FN"
            ]
        ].to_string(index=False)
    )

    print("\nBest configuration by F1-score:")

    best_f1 = results_df.loc[results_df["F1"].idxmax()]
    print(best_f1.to_string())

    print("\nBest configuration by Recall:")

    best_recall = results_df.loc[results_df["Recall"].idxmax()]
    print(best_recall.to_string())


if __name__ == "__main__":
    main()