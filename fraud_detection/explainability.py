
import numpy as np


def explain_prediction(model, transaction, feature_names=None):
    """
    Explains a prediction by returning the decision path
    followed by the C4.5 decision tree.
    """

    if model.tree is None:
        raise ValueError("The model has not been trained yet.")

    transaction = np.asarray(transaction, dtype=float)

    if transaction.ndim != 1:
        raise ValueError("The transaction must be a one-dimensional array.")

    if len(transaction) != model.n_features:
        raise ValueError("The number of features does not match.")

    if not np.all(np.isfinite(transaction)):
        raise ValueError("The transaction contains NaN or infinite values.")

    if feature_names is None:
        feature_names = [
            f"feature_{i}" for i in range(model.n_features)
        ]

    if len(feature_names) != model.n_features:
        raise ValueError("The number of feature names does not match.")

    node = model.tree
    decision_path = []

    # Traverse the decision tree
    while node["type"] != "leaf":

        feature_index = node["feature"]
        threshold = node["threshold"]

        feature_name = feature_names[feature_index]
        feature_value = transaction[feature_index]

        if feature_value <= threshold:
            condition = "<="
            branch = "left"
            node = node["left"]
        else:
            condition = ">"
            branch = "right"
            node = node["right"]

        decision_path.append({
            "feature": feature_name,
            "value": float(feature_value),
            "condition": condition,
            "threshold": float(threshold),
            "branch": branch
        })

    prediction = node["prediction"]

    return {
        "prediction": prediction.item()
        if isinstance(prediction, np.generic)
        else prediction,
        "decision_path": decision_path
    }


def format_explanation(result):
    """
    Formats the prediction and decision path
    into a readable explanation.
    """

    labels = {
        0: "Legitimate",
        1: "Fraudulent"
    }

    prediction = result["prediction"]
    decision_path = result["decision_path"]

    prediction_label = labels.get(
        prediction,
        str(prediction)
    )

    lines = [
        "========== FRAUD DETECTION RESULT ==========",
        f"Prediction: {prediction_label}",
        "",
        "Decision path:"
    ]

    if not decision_path:
        lines.append("No decision rules were required.")
    else:
        for index, step in enumerate(decision_path, start=1):
            lines.append(
                f"{index}. {step['feature']} = {step['value']:.4f} "
                f"{step['condition']} {step['threshold']:.4f}"
            )

    return "\n".join(lines)


if __name__ == "__main__":

    from fraud_detection.c45.decision_tree import C45DecisionTree

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

    transaction = np.array([7, 70])

    feature_names = ["Transaction_Feature_1", "Transaction_Feature_2"]

    result = explain_prediction(
        model,
        transaction,
        feature_names
    )

    print(format_explanation(result))