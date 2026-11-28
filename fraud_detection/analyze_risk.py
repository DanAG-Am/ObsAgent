
import pandas as pd

from fraud_detection.preprocessing import preprocess_data

from itertools import combinations


def analyze_risk_features():
    """
    Compares legitimate and fraudulent transactions
    using the training and validation datasets.
    """

    # Load chronological training, validation and testing splits
    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test
    ) = preprocess_data()

    # Combine features and labels
    train_data = X_train.copy()
    train_data["Class"] = y_train

    val_data = X_val.copy()
    val_data["Class"] = y_val

    # Analyze Amount and Time
    features = ["Amount", "Time"]

    print("\n========== TRAINING DATA ANALYSIS ==========")

    print("\nClass distribution:")
    print(train_data["Class"].value_counts())

    print("\nClass percentages:")
    print(
        (train_data["Class"].value_counts(normalize=True) * 100)
        .round(4)
    )

    print("\nFeature statistics by class:")

    statistics = train_data.groupby("Class")[features].agg(
        ["count", "mean", "median", "std", "min", "max"]
    )

    print(statistics.round(2))

    print("\n========== VALIDATION DATA ANALYSIS ==========")

    print("\nClass distribution:")
    print(val_data["Class"].value_counts())

    print("\nFeature statistics by class:")

    val_statistics = val_data.groupby("Class")[features].agg(
        ["count", "mean", "median", "std", "min", "max"]
    )

    print(val_statistics.round(2))

    # Calculate selected percentiles for transaction amounts
    print("\n========== AMOUNT PERCENTILES ==========")

    for class_value, class_name in [
        (0, "Legitimate"),
        (1, "Fraudulent")
    ]:
        amounts = train_data.loc[
            train_data["Class"] == class_value,
            "Amount"
        ]

        print(f"\n{class_name} transactions:")

        print(
            amounts.quantile(
                [0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
            ).round(2)
        )
    
    # Analyze PCA features
    print("\n========== PCA FEATURE ANALYSIS ==========")

    pca_features = [
        column for column in X_train.columns
        if column.startswith("V")
    ]

    def calculate_feature_differences(data):
        legitimate = data[data["Class"] == 0][pca_features]
        fraudulent = data[data["Class"] == 1][pca_features]

        mean_legitimate = legitimate.mean()
        mean_fraudulent = fraudulent.mean()

        std_legitimate = legitimate.std()
        std_fraudulent = fraudulent.std()

        # Calculate pooled standard deviation
        pooled_std = (
            (
                (len(legitimate) - 1) * std_legitimate ** 2
                + (len(fraudulent) - 1) * std_fraudulent ** 2
            )
            / (len(legitimate) + len(fraudulent) - 2)
        ) ** 0.5

        # Calculate standardized mean difference (Cohen's d)
        effect_size = (
            (mean_fraudulent - mean_legitimate)
            / pooled_std.replace(0, float("nan"))
        )

        return pd.DataFrame({
            "Legitimate_Mean": mean_legitimate,
            "Fraudulent_Mean": mean_fraudulent,
            "Effect_Size": effect_size,
            "Absolute_Effect": effect_size.abs()
        }).sort_values(
            "Absolute_Effect",
            ascending=False
        )

    # Compare training and validation data
    train_features = calculate_feature_differences(train_data)
    val_features = calculate_feature_differences(val_data)

    print("\nTop 10 PCA features in training data:")
    print(train_features.head(10).round(4))

    print("\nTop 10 PCA features in validation data:")
    print(val_features.head(10).round(4))

    # Analyze distributions of selected PCA features
    print("\n========== SELECTED PCA FEATURE DISTRIBUTIONS ==========")

    selected_features = [
        "V14", "V12", "V17", "V10", "V11", "V4"
    ]

    percentiles = [0.10, 0.25, 0.50, 0.75, 0.90]

    for dataset_name, data in [
        ("Training", train_data),
        ("Validation", val_data)
    ]:

        print(f"\n========== {dataset_name} ==========")

        for feature in selected_features:

            print(f"\nFeature: {feature}")

            distribution = data.groupby("Class")[feature].quantile(
                percentiles
            ).unstack()

            distribution.columns = [
                f"P{int(p * 100)}" for p in percentiles
            ]

            distribution.index = [
                "Legitimate" if value == 0 else "Fraudulent"
                for value in distribution.index
            ]

            print(distribution.round(3))


    # Evaluate individual PCA risk indicators
    print("\n========== RISK RULE EVALUATION ==========")

    risk_directions = {
        "V14": "low",
        "V12": "low",
        "V17": "low",
        "V10": "low",
        "V11": "high",
        "V4": "high"
    }

    candidate_percentiles = [0.10, 0.25, 0.50]

    for feature, direction in risk_directions.items():

        fraud_train = train_data.loc[
            train_data["Class"] == 1,
            feature
        ]

        print(f"\nFeature: {feature} ({direction} values)")

        for percentile in candidate_percentiles:

            # Derive the threshold exclusively from training fraud data
            if direction == "low":
                threshold = fraud_train.quantile(percentile)
            else:
                threshold = fraud_train.quantile(1 - percentile)

            # Evaluate the rule on validation data
            if direction == "low":
                predictions = (
                    val_data[feature] <= threshold
                )
            else:
                predictions = (
                    val_data[feature] >= threshold
                )

            actual = val_data["Class"] == 1

            tp = int((predictions & actual).sum())
            fp = int((predictions & ~actual).sum())
            fn = int((~predictions & actual).sum())
            tn = int((~predictions & ~actual).sum())

            precision = tp / (tp + fp) if (tp + fp) else 0
            recall = tp / (tp + fn) if (tp + fn) else 0
            fpr = fp / (fp + tn) if (fp + tn) else 0

            print(
                f"\nPercentile: {percentile:.0%}"
                f"\nThreshold: {threshold:.4f}"
                f"\nTP: {tp} | FP: {fp}"
                f"\nFN: {fn} | TN: {tn}"
                f"\nPrecision: {precision:.4f}"
                f"\nRecall: {recall:.4f}"
                f"\nFalse Positive Rate: {fpr:.4f}"
            )

    
    # Evaluate combinations of risk indicators
    print("\n========== COMBINED RISK RULE EVALUATION ==========")

    # Use the median of training fraud transactions
    thresholds = {}

    for feature, direction in risk_directions.items():

        fraud_values = train_data.loc[
            train_data["Class"] == 1,
            feature
        ]

        if direction == "low":
            thresholds[feature] = fraud_values.quantile(0.50)
        else:
            thresholds[feature] = fraud_values.quantile(0.50)

    # Generate one risk signal per feature
    risk_signals = pd.DataFrame(index=val_data.index)

    for feature, direction in risk_directions.items():

        threshold = thresholds[feature]

        if direction == "low":
            risk_signals[feature] = (
                val_data[feature] <= threshold
            )
        else:
            risk_signals[feature] = (
                val_data[feature] >= threshold
            )

    actual = val_data["Class"] == 1

    # Compare different numbers of required risk signals
    for min_signals in [1, 2, 3]:

        predictions = (
            risk_signals.sum(axis=1) >= min_signals
        )

        tp = int((predictions & actual).sum())
        fp = int((predictions & ~actual).sum())
        fn = int((~predictions & actual).sum())
        tn = int((~predictions & ~actual).sum())

        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        fpr = fp / (fp + tn) if (fp + tn) else 0

        print(f"\nMinimum risk signals: {min_signals}")
        print(f"TP: {tp} | FP: {fp}")
        print(f"FN: {fn} | TN: {tn}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall: {recall:.4f}")
        print(f"False Positive Rate: {fpr:.4f}")

    print("\nRisk thresholds:")
    for feature, threshold in thresholds.items():
        print(f"{feature}: {threshold:.4f}")


    # Evaluate every possible pair of risk indicators
    print("\n========== PAIRWISE RISK RULE EVALUATION ==========")

    pair_results = []

    actual = val_data["Class"] == 1

    for feature_pair in combinations(risk_signals.columns, 2):

        # A transaction must activate both indicators
        predictions = risk_signals[list(feature_pair)].all(axis=1)

        tp = int((predictions & actual).sum())
        fp = int((predictions & ~actual).sum())
        fn = int((~predictions & actual).sum())
        tn = int((~predictions & ~actual).sum())

        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        fpr = fp / (fp + tn) if (fp + tn) else 0

        pair_results.append({
            "Features": " + ".join(feature_pair),
            "TP": tp,
            "FP": fp,
            "Precision": precision,
            "Recall": recall,
            "FPR": fpr
        })

    pair_results = pd.DataFrame(pair_results)

    pair_results = pair_results.sort_values(
        by=["Recall", "Precision"],
        ascending=False
    )

    print(pair_results.to_string(
        index=False,
        formatters={
            "Precision": "{:.4f}".format,
            "Recall": "{:.4f}".format,
            "FPR": "{:.6f}".format
        }
    ))


if __name__ == "__main__":
    analyze_risk_features()