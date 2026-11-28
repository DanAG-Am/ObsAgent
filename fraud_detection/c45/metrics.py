
import numpy as np


def entropy(y):
    """
    Calculates the entropy of a set of labels.

    Entropy measures how mixed the classes
    are within the dataset.
    """

    if len(y) == 0:
        return 0.0

    _, counts = np.unique(y, return_counts=True)

    probabilities = counts / len(y)

    return -np.sum(
        probabilities * np.log2(probabilities)
    )


def information_gain(y, partitions):
    """
    Calculates the information gain.

    partitions: list of groups of labels
    after splitting the dataset.
    """

    total_entropy = entropy(y)
    total_samples = len(y)

    weighted_entropy = 0.0

    for group in partitions:
        if len(group) == 0:
            continue

        weight = len(group) / total_samples
        weighted_entropy += weight * entropy(group)

    return total_entropy - weighted_entropy


def split_information(partitions):
    """
    Calculates the Split Information.
    """

    total_samples = sum(len(group) for group in partitions)

    if total_samples == 0:
        return 0.0

    result = 0.0

    for group in partitions:
        if len(group) == 0:
            continue

        probability = len(group) / total_samples
        result -= probability * np.log2(probability)

    return result


def gain_ratio(y, partitions):
    """
    Calculates the Gain Ratio, a criterion used by C4.5.
    """

    gain = information_gain(y, partitions)
    split_info = split_information(partitions)

    if split_info == 0:
        return 0.0

    return gain / split_info


def best_threshold(X, y, min_samples_leaf=2):
    """
    Finds the best numerical threshold using Gain Ratio.

    Uses cumulative sums to avoid recalculating
    the groups at every possible split.

    Considers candidates where:
    - Consecutive values are different.
    - Consecutive labels are different.
    - Both groups satisfy the minimum number of samples.
    """

    X = np.asarray(X)
    y = np.asarray(y)

    if len(X) != len(y):
        raise ValueError("X and y must have the same length.")

    if len(y) < 2 * min_samples_leaf:
        return None, 0.0

    # Sort values and labels
    indices = np.argsort(X, kind="mergesort")

    X_sorted = X[indices]
    y_sorted = y[indices]

    # Encode the classes
    _, y_codes = np.unique(y_sorted, return_inverse=True)

    num_classes = len(np.unique(y_sorted))
    n = len(y_sorted)

    # Count classes cumulatively
    one_hot = np.eye(num_classes, dtype=np.int64)[y_codes]
    cumulative_counts = np.cumsum(one_hot, axis=0)

    total_counts = cumulative_counts[-1]

    # Find positions where a split is possible
    valid = (
        (X_sorted[:-1] < X_sorted[1:]) &
        (y_sorted[:-1] != y_sorted[1:])
    )

    candidate_indices = np.where(valid)[0]

    if len(candidate_indices) == 0:
        return None, 0.0

    # Avoid splits with groups that are too small
    candidate_indices = candidate_indices[
        (candidate_indices + 1 >= min_samples_leaf) &
        (n - candidate_indices - 1 >= min_samples_leaf)
    ]

    if len(candidate_indices) == 0:
        return None, 0.0

    # Get class frequencies in both groups
    left_counts = cumulative_counts[candidate_indices]

    right_counts = total_counts - left_counts

    left_sizes = candidate_indices + 1
    right_sizes = n - left_sizes

    # Calculate group entropy
    def entropy_from_counts(counts):
        probabilities = counts / counts.sum(axis=1, keepdims=True)

        terms = np.zeros_like(probabilities, dtype=float)

        mask = probabilities > 0

        terms[mask] = (
            probabilities[mask] *
            np.log2(probabilities[mask])
        )

        return -terms.sum(axis=1)

    left_entropy = entropy_from_counts(left_counts)
    right_entropy = entropy_from_counts(right_counts)

    # Calculate parent entropy
    parent_entropy = entropy(y_sorted)

    # Information Gain
    weighted_entropy = (
        (left_sizes / n) * left_entropy +
        (right_sizes / n) * right_entropy
    )

    gains = parent_entropy - weighted_entropy

    # Split Information
    p_left = left_sizes / n
    p_right = right_sizes / n

    split_info = -(
        p_left * np.log2(p_left) +
        p_right * np.log2(p_right)
    )

    # Gain Ratio
    ratios = np.divide(
        gains,
        split_info,
        out=np.zeros_like(gains),
        where=split_info > 0
    )

    # Select the best candidate
    best_index = np.argmax(ratios)

    position = candidate_indices[best_index]

    threshold = (
        X_sorted[position] +
        X_sorted[position + 1]
    ) / 2

    return threshold, ratios[best_index]


if __name__ == "__main__":

    example_1 = [0, 0, 0, 0, 0]
    example_2 = [0, 0, 1, 1]
    example_3 = [0, 0, 0, 0, 1]

    print("========== ENTROPY ==========")
    print("All legitimate:", entropy(example_1))
    print("Half and half:", entropy(example_2))
    print("Mostly legitimate:", entropy(example_3))

    # Example of a split:
    # Group A: three legitimate transactions
    # Group B: two legitimate and one fraudulent transaction
    y = np.array([0, 0, 0, 0, 0, 1])

    group_a = np.array([0, 0, 0])
    group_b = np.array([0, 0, 1])

    partitions = [group_a, group_b]

    print("\n========== INFORMATION GAIN ==========")
    print("Information Gain:", information_gain(y, partitions))

    print("\n========== SPLIT INFORMATION ==========")
    print("Split Information:", split_information(partitions))

    print("\n========== GAIN RATIO ==========")
    print("Gain Ratio:", gain_ratio(y, partitions))

    print("\n========== BEST THRESHOLD ==========")

    X_example = np.array([-5.2, -4.8, -2.1, -1.5, 0.5])
    y_example = np.array([1, 1, 0, 0, 0])

    threshold, ratio = best_threshold(
        X_example,
        y_example
    )

    print("Best threshold:", threshold)
    print("Best Gain Ratio:", ratio)