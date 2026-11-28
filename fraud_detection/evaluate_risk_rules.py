
import numpy as np

from fraud_detection.preprocessing import preprocess_data
from fraud_detection.c45.decision_tree import C45DecisionTree
from itertools import combinations


RISK_THRESHOLDS = {
    "V17": -6.4654
}

THRESHOLD = 0.60


def main():

    print("=" * 65)
    print("C4.5 AND ADDITIONAL RISK RULE EVALUATION")
    print("=" * 65)

    # 1. Load dataset
    X_train, X_val, _, y_train, y_val, _ = preprocess_data()

    # 2. Train C4.5 using training data only
    model = C45DecisionTree(
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5
    )

    model.fit(X_train, y_train)

    # 3. Generate C4.5 predictions on validation data
    probabilities = model.predict_proba(X_val)
    c45_predictions = (probabilities >= THRESHOLD).astype(int)

    # Candidate thresholds obtained from training fraud distributions
    RISK_THRESHOLDS = {
        "V14": -7.0199,
        "V12": -6.4891,
        "V17": -6.4654,
        "V10": -5.0525,
        "V11": 4.0663,
        "V4": 4.3282
    }

    # Generate one signal per feature
    risk_signals = {}

    for feature, threshold in RISK_THRESHOLDS.items():

        values = X_val[feature].to_numpy()

        if feature in ["V14", "V12", "V17", "V10"]:
            risk_signals[feature] = values <= threshold
        else:
            risk_signals[feature] = values >= threshold

    actual = np.asarray(y_val).astype(int)

    # Only transactions not classified as fraudulent by C4.5
    missed_by_c45 = c45_predictions == 0

    print("\n========== ADDITIONAL RISK RULE EVALUATION ==========")

    candidate_results = []

    # Evaluate individual rules
    for feature, signal in risk_signals.items():

        additional = signal & missed_by_c45

        tp = int((additional & (actual == 1)).sum())
        fp = int((additional & (actual == 0)).sum())

        candidate_results.append({
            "Rule": feature,
            "TP": tp,
            "FP": fp
        })

    # Evaluate all pairs
    for feature_pair in combinations(risk_signals.keys(), 2):

        pair_signal = (
            risk_signals[feature_pair[0]] &
            risk_signals[feature_pair[1]]
        )

        additional = pair_signal & missed_by_c45

        tp = int((additional & (actual == 1)).sum())
        fp = int((additional & (actual == 0)).sum())

        candidate_results.append({
            "Rule": " + ".join(feature_pair),
            "TP": tp,
            "FP": fp
        })

    # Display results
    candidate_results.sort(
        key=lambda result: (result["TP"], -result["FP"]),
        reverse=True
    )

    for result in candidate_results:

        precision = (
            result["TP"] / (result["TP"] + result["FP"])
            if result["TP"] + result["FP"] > 0
            else 0
        )

        print(
            f"{result['Rule']}: "
            f"Additional TP={result['TP']}, "
            f"Additional FP={result['FP']}, "
            f"Precision={precision:.4f}"
        )


    # 4. Evaluate V14 + V10 risk rule
    v17 = X_val["V17"].to_numpy()

    risk_rule = v17 <= RISK_THRESHOLDS["V17"]

    actual = np.asarray(y_val).astype(int)

    # 5. Identify classification categories
    risk_levels = np.full(len(actual), "Legitimate", dtype=object)

    risk_levels[risk_rule] = "Suspicious"

    risk_levels[c45_predictions == 1] = "Fraudulent"

    # 6. Evaluate C4.5 baseline
    tp = int(((c45_predictions == 1) & (actual == 1)).sum())
    fp = int(((c45_predictions == 1) & (actual == 0)).sum())
    fn = int(((c45_predictions == 0) & (actual == 1)).sum())
    tn = int(((c45_predictions == 0) & (actual == 0)).sum())

    print("\n========== C4.5 BASELINE ==========")
    print(f"TP: {tp}")
    print(f"FP: {fp}")
    print(f"FN: {fn}")
    print(f"TN: {tn}")

    # 7. Evaluate additional risk rule
    rule_tp = int((risk_rule & (actual == 1)).sum())
    rule_fp = int((risk_rule & (actual == 0)).sum())

    print("\n========== V14 + V10 RULE ==========")
    print(f"Activated rules: {int(risk_rule.sum())}")
    print(f"Fraudulent transactions flagged: {rule_tp}")
    print(f"Legitimate transactions flagged: {rule_fp}")

    # 8. Evaluate additional suspicious detections
    suspicious = risk_levels == "Suspicious"

    suspicious_fraud = int((suspicious & (actual == 1)).sum())
    suspicious_legitimate = int((suspicious & (actual == 0)).sum())

    print("\n========== ADDITIONAL SUSPICIOUS DETECTIONS ==========")
    print(f"Suspicious transactions: {int(suspicious.sum())}")
    print(f"Actual frauds marked suspicious: {suspicious_fraud}")
    print(f"Legitimate transactions marked suspicious: {suspicious_legitimate}")

    # 9. Check whether the rule catches missed frauds
    missed_fraud_detected = int(
        (
            (c45_predictions == 0) &
            risk_rule &
            (actual == 1)
        ).sum()
    )

    missed_fraud_not_detected = int(
        (
            (c45_predictions == 0) &
            (~risk_rule) &
            (actual == 1)
        ).sum()
    )

    print("\n========== RULE CONTRIBUTION ==========")
    print(f"Missed C4.5 frauds flagged as suspicious: {missed_fraud_detected}")
    print(f"Missed C4.5 frauds not flagged: {missed_fraud_not_detected}")

    # 10. Final category distribution
    print("\n========== FINAL RISK DISTRIBUTION ==========")

    for category in ["Legitimate", "Suspicious", "Fraudulent"]:
        mask = risk_levels == category

        print(f"\n{category}:")
        print(f"Total: {int(mask.sum())}")
        print(f"Actual frauds: {int(((actual == 1) & mask).sum())}")
        print(f"Actual legitimate: {int(((actual == 0) & mask).sum())}")

    print("\nEvaluation completed.")


if __name__ == "__main__":
    main()