
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "database" / "creditcard.csv"


def load_data(remove_duplicates=False):
    """
    Loads the dataset and preserves its chronological order.
    """

    df = pd.read_csv(DATA_PATH)

    if remove_duplicates:
        df = df.drop_duplicates().copy()

    return df.sort_values("Time").reset_index(drop=True)


def preprocess_data(remove_duplicates=False):
    """
    Splits the data chronologically into:
    70% training, 15% validation, and 15% testing.

    No scaling is applied because C4.5 works
    directly with numerical values.
    """

    df = load_data(remove_duplicates)

    # Separate features and target variable
    X = df.drop(columns=["Class"]).copy()
    y = df["Class"].copy()

    # Get unique timestamps in chronological order
    unique_times = df["Time"].drop_duplicates().sort_values().to_numpy()

    # Define temporal cutoffs
    train_cutoff = unique_times[int(len(unique_times) * 0.70)]
    val_cutoff = unique_times[int(len(unique_times) * 0.85)]

    # Split the data without separating transactions
    # that share the same timestamp
    train_mask = df["Time"] < train_cutoff

    val_mask = (
        (df["Time"] >= train_cutoff) &
        (df["Time"] < val_cutoff)
    )

    test_mask = df["Time"] >= val_cutoff

    X_train = X.loc[train_mask].copy()
    X_val = X.loc[val_mask].copy()
    X_test = X.loc[test_mask].copy()

    y_train = y.loc[train_mask].copy()
    y_val = y.loc[val_mask].copy()
    y_test = y.loc[test_mask].copy()

    return (
        X_train, X_val, X_test,
        y_train, y_val, y_test
    )


if __name__ == "__main__":

    (
        X_train, X_val, X_test,
        y_train, y_val, y_test
    ) = preprocess_data()

    datasets = {
        "Training": (X_train, y_train),
        "Validation": (X_val, y_val),
        "Testing": (X_test, y_test)
    }

    print("\n========== TEMPORAL DATA SPLIT ==========")

    for name, (X, y) in datasets.items():

        print(f"\n{name}")
        print("Features:", X.shape)
        print("Fraudulent transactions:", int(y.sum()))
        print("Legitimate transactions:", int((y == 0).sum()))
        print(
            "Fraud percentage:",
            round(y.mean() * 100, 4),
            "%"
        )

        print("Minimum Time:", X["Time"].min())
        print("Maximum Time:", X["Time"].max())

    print("\n========== FEATURES ==========")
    print("Columns:", list(X_train.columns))
    print("Number of features:", X_train.shape[1])

    print("\n========== DATA VALIDATION ==========")
    print("Missing values:", X_train.isnull().sum().sum())
    print(
        "Numerical features:",
        X_train.select_dtypes(include="number").shape[1]
    )

    print("\nPreprocessing completed successfully.")