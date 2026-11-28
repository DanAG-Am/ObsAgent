
import numpy as np

from fraud_detection.c45.metrics import (
    entropy,
    information_gain,
    split_information,
    gain_ratio,
    best_threshold
)
from fraud_detection.validation import (
    validate_transaction,
    validate_transactions
)
from fraud_detection.logger import get_logger

logger = get_logger(__name__)

class C45DecisionTree:

    def __init__(self, max_depth=10, min_samples_split=10, min_samples_leaf=5):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.tree = None

    def _create_leaf(self, y):
        values, counts = np.unique(y, return_counts=True)

        class_counts = dict(zip(values.tolist(), counts.tolist()))

        total_samples = len(y)

        probabilities = {
            int(class_label): count / total_samples
            for class_label, count in class_counts.items()
        }

        majority_class = values[np.argmax(counts)]

        return {
            "type": "leaf",
            "prediction": majority_class,
            "probabilities": probabilities,
            "samples": total_samples
        }

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y)

        if X.ndim != 2:
            raise ValueError("X must be a two-dimensional matrix.")

        if len(X) != len(y):
            raise ValueError("X and y must have the same number of observations.")

        if len(X) == 0:
            raise ValueError("The training dataset is empty.")

        if X.shape[1] == 0:
            raise ValueError("X must contain at least one feature.")

        if not np.all(np.isfinite(X)):
            raise ValueError("X contains NaN or infinite values.")

        self.n_features = X.shape[1]
        self.classes = np.unique(y)

        logger.info(
            "Starting C4.5 training: %d samples, %d features.",
            X.shape[0],
            X.shape[1]
        )

        try:
            self.tree = self._build_tree(X, y, depth=0)

        except Exception:
            logger.exception("An error occurred during C4.5 training.")
            raise

        logger.info("C4.5 training completed successfully.")

        return self

    def _build_tree(self, X, y, depth):
        # 1. Get the most frequent class
        values, counts = np.unique(y, return_counts=True)
        majority_class = values[np.argmax(counts)]

        # 2. Stopping criteria
        if (
            len(values) == 1
            or depth >= self.max_depth
            or len(y) < self.min_samples_split
        ):
            return self._create_leaf(y)

        # 3. Find the best split
        best_split = self._find_best_split(X, y)

        # 4. If no useful split is found, create a leaf
        if best_split is None:
            return self._create_leaf(y)

        # 5. Split the data
        feature = best_split["feature"]
        threshold = best_split["threshold"]

        left_mask = X[:, feature] <= threshold
        right_mask = X[:, feature] > threshold

        # 6. Build child nodes recursively
        return {
            "type": "node",
            "feature": feature,
            "threshold": threshold,
            "gain_ratio": best_split["gain_ratio"],
            "left": self._build_tree(
                X[left_mask], y[left_mask], depth + 1
            ),
            "right": self._build_tree(
                X[right_mask], y[right_mask], depth + 1
            )
        }

    def _find_best_split(self, X, y):
        candidates = []

        # Evaluate each feature
        for feature in range(X.shape[1]):

            threshold, ratio = best_threshold(
                X[:, feature],
                y,
                min_samples_leaf=self.min_samples_leaf
            )

            if threshold is None:
                continue

            left_mask = X[:, feature] <= threshold
            right_mask = X[:, feature] > threshold

            partitions = [
                y[left_mask],
                y[right_mask]
            ]

            ig = information_gain(y, partitions)
            si = split_information(partitions)

            candidates.append({
                "feature": feature,
                "threshold": threshold,
                "information_gain": ig,
                "split_information": si,
                "gain_ratio": ratio
            })

        if not candidates:
            return None

        # Calculate the average Information Gain
        average_gain = np.mean([
            candidate["information_gain"]
            for candidate in candidates
        ])

        # C4.5 filter: consider features with IG >= average
        eligible = [
            candidate
            for candidate in candidates
            if candidate["information_gain"] >= average_gain
        ]

        if not eligible:
            return None

        # Select the feature with the highest Gain Ratio
        best = max(
            eligible,
            key=lambda candidate: candidate["gain_ratio"]
        )

        if best["information_gain"] <= 0:
            return None

        return best


    def predict_one(self, x):
        if self.tree is None:
            raise ValueError("The model has not been trained yet.")

        x = validate_transaction(x, self.n_features)

        node = self.tree

        while node["type"] != "leaf":
            feature = node["feature"]
            threshold = node["threshold"]

            if x[feature] <= threshold:
                node = node["left"]
            else:
                node = node["right"]

        return node["prediction"]


    def predict(self, X):
        if self.tree is None:
            raise ValueError("The model has not been trained yet.")

        X = validate_transactions(X, self.n_features)

        predictions = np.array([
            self._predict_validated(x) for x in X
        ])

        logger.info(
            "Prediction completed: %d transactions evaluated.",
            len(predictions)
        )

        return predictions


    def _predict_validated(self, x):
        """
        Predicts a transaction that has already been validated.
        """

        node = self.tree

        while node["type"] != "leaf":
            feature = node["feature"]
            threshold = node["threshold"]

            if x[feature] <= threshold:
                node = node["left"]
            else:
                node = node["right"]

        return node["prediction"]

    def predict_proba_one(self, x):
        if self.tree is None:
            raise ValueError("The model has not been trained yet.")

        x = validate_transaction(x, self.n_features)

        node = self._traverse_tree(x)

        return node["probabilities"].get(1, 0.0)

    def predict_proba(self, X):
        if self.tree is None:
            raise ValueError("The model has not been trained yet.")

        X = validate_transactions(X, self.n_features)

        probabilities = np.array([
            self._traverse_tree(x)["probabilities"].get(1, 0.0)
            for x in X
        ])

        return probabilities

    def _traverse_tree(self, x):
        node = self.tree

        while node["type"] != "leaf":
            feature = node["feature"]
            threshold = node["threshold"]

            if x[feature] <= threshold:
                node = node["left"]
            else:
                node = node["right"]

        return node


if __name__ == "__main__":

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

    predictions = model.predict(X)

    print("Predictions:", predictions)
    print("Actual labels:", y)
    print("Accuracy:", np.mean(predictions == y))

    probabilities = model.predict_proba(X)

    print("Fraud probabilities:", probabilities)