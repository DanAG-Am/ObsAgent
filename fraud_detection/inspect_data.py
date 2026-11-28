
import pandas as pd

DATA_PATH = "data/raw/creditcard.csv"

def inspect_dataset():
    df = pd.read_csv(DATA_PATH)

    print("\n========== DATASET ==========")
    print("Dimensiones:", df.shape)

    print("\n========== NULL VALUES ==========")
    print(df.isnull().sum().sum())

    print("\n========== DUPLICATED RECORDS ==========")
    print(df.duplicated().sum())

    print("\n========== DISTRIBUTION OF CLASSES ==========")
    print(df["Class"].value_counts())

    print("\n========== PERCENTAGE OF CLASSES ==========")
    print(df["Class"].value_counts(normalize=True) * 100)

    print("\n========== AMOUNT STATISTICS ==========")
    print(df["Amount"].describe())

    print("\n========== TIME INTERVAL ==========")
    print("Minimum:", df["Time"].min())
    print("Maximum:", df["Time"].max())

    print("\n========== TIME IS MONOTONIC INCREASING ==========")
    print(df["Time"].is_monotonic_increasing)


def investigate_duplicates():
    df = pd.read_csv(DATA_PATH)

    # Find duplicated records based on all columns
    duplicated = df[df.duplicated(keep=False)]

    print("\n========== DUPLICATED RECORDS BY CLASS ==========")
    print(duplicated["Class"].value_counts())

    print("\n========== TOTAL DUPLICATED RECORDS ==========")
    print("Total duplicated records:", df.duplicated().sum())

    # Find duplicated records based on all columns except "Class"
    # This will help identify records that have the same features but different labels.
    duplicated_features = df[
        df.duplicated(subset=df.columns.drop("Class"), keep=False)
    ]

    print("\n========== DUPLICATED RECORDS WITHOUT CONSIDERING CLASS ==========")
    print("Number of duplicated records:", len(duplicated_features))

    if not duplicated_features.empty:
        print(
            duplicated_features.groupby(
                list(df.columns.drop("Class"))
            )["Class"].nunique().value_counts()
        )


def investigate_conflicting_labels():
    df = pd.read_csv(DATA_PATH)

    feature_columns = [
        col for col in df.columns if col != "Class"
    ]

    duplicated_features = df[
        df.duplicated(
            subset=feature_columns,
            keep=False
        )
    ]

    # Group by the feature columns and aggregate to find groups with conflicting labels
    groups = duplicated_features.groupby(
        feature_columns,
        dropna=False
    )["Class"].agg(["count", "nunique", "sum"])

    # Filter groups where there are conflicting labels (more than one unique label)
    conflicts = groups[groups["nunique"] > 1]

    print("\n========== CONFLICTS OF LABELS ==========")
    print("Number of conflicting groups:", len(conflicts))

    print("\nNumber of records in these groups:")
    print(conflicts["count"].sum())

    print("\nDistribution of groups:")
    print(conflicts.groupby("sum").size())

    print("\nExamples:")
    print(conflicts.head(10))


if __name__ == "__main__":
    inspect_dataset()
    investigate_duplicates()
    investigate_conflicting_labels()