
import numpy as np
import pandas as pd

from fraud_detection.preprocessing import preprocess_data
from fraud_detection.c45.decision_tree import C45DecisionTree
from fraud_detection.explainability import explain_prediction

from fraud_detection.logger import get_logger


logger = get_logger(__name__)


def analyze_errors():

    logger.info("Starting fraud error analysis.")

    # Load datasets
    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test
    ) = preprocess_data()

    # Train C4.5 using training data only
    model = C45DecisionTree(
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5
    )

    model.fit(X_train, y_train)

    # Generate validation predictions
    predictions = model.predict(X_val)

    actual = y_val.to_numpy()

    # Identify correctly and incorrectly classified frauds
    false_negative_mask = (actual == 1) & (predictions == 0)
    true_positive_mask = (actual == 1) & (predictions == 1)

    missed_frauds = X_val.loc[false_negative_mask].copy()
    detected_frauds = X_val.loc[true_positive_mask].copy()

    print("\n========== FRAUD ERROR ANALYSIS ==========")

    print(f"Total validation transactions: {len(X_val)}")
    print(f"Total actual frauds: {(actual == 1).sum()}")
    print(f"Correctly detected frauds: {len(detected_frauds)}")
    print(f"Missed frauds: {len(missed_frauds)}")

    if missed_frauds.empty:
        print("\nNo false negatives found.")
        return

    # Compare missed and correctly detected frauds
    print("\n========== FRAUD GROUP COMPARISON ==========")

    features_to_inspect = [
        "Amount",
        "Time",
        "V14",
        "V12",
        "V17",
        "V10",
        "V11",
        "V4"
    ]

    comparison = pd.DataFrame({
        "Missed_Mean": missed_frauds[features_to_inspect].mean(),
        "Detected_Mean": detected_frauds[features_to_inspect].mean(),
        "Missed_Median": missed_frauds[features_to_inspect].median(),
        "Detected_Median": detected_frauds[features_to_inspect].median()
    })

    print(comparison.round(4))

    # Identify features that differ most between both groups
    print("\n========== FEATURE DIFFERENCES ==========")

    pooled_std = np.sqrt(
        (
            (len(missed_frauds) - 1) * missed_frauds.std() ** 2
            + (len(detected_frauds) - 1) * detected_frauds.std() ** 2
        )
        / (
            len(missed_frauds) + len(detected_frauds) - 2
        )
    )

    effect_size = (
        missed_frauds.mean() - detected_frauds.mean()
    ) / pooled_std.replace(0, np.nan)

    feature_differences = pd.DataFrame({
        "Missed_Mean": missed_frauds.mean(),
        "Detected_Mean": detected_frauds.mean(),
        "Effect_Size": effect_size,
        "Absolute_Effect": effect_size.abs()
    })

    feature_differences = feature_differences.sort_values(
        "Absolute_Effect",
        ascending=False
    )

    print(feature_differences.head(15).round(4))

    # Display selected missed transactions
    print("\n========== MISSED FRAUD EXAMPLES ==========")

    examples = missed_frauds[
        ["Time", "Amount", "V14", "V12", "V17", "V10", "V11", "V4"]
    ].head(10)

    print(examples.round(4))

    # Inspect the decision paths of the first three missed frauds
    print("\n========== MISSED FRAUD DECISION PATHS ==========")

    for index, transaction in missed_frauds.head(3).iterrows():

        explanation = explain_prediction(
            model,
            transaction.to_numpy(),
            X_train.columns.tolist()
        )

        print(f"\nTransaction index: {index}")
        print(f"Actual class: Fraudulent")
        print(f"Model prediction: {explanation['prediction']}")

        for step in explanation["decision_path"]:
            print(
                f"{step['feature']} = {step['value']:.4f} "
                f"{step['condition']} {step['threshold']:.4f} "
                f"-> {step['branch']}"
            )

    logger.info(
        "Fraud error analysis completed. Missed frauds: %d",
        len(missed_frauds)
    )


if __name__ == "__main__":
    analyze_errors()