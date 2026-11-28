
import numpy as np

from fraud_detection.logger import get_logger

logger = get_logger(__name__)


def validate_transaction(transaction, expected_features):
    """
    Validates a transaction before passing it
    to the fraud detection model.
    """

    try:
        transaction = np.asarray(transaction, dtype=float)

    except (ValueError, TypeError):
        logger.error("Transaction contains non-numeric values.")
        raise ValueError("Transaction must contain numeric values.")

    if transaction.ndim != 1:
        logger.error("Invalid transaction dimensions.")
        raise ValueError("Transaction must be a one-dimensional array.")

    if len(transaction) != expected_features:
        logger.error(
            "Invalid feature count: expected %d, received %d.",
            expected_features,
            len(transaction)
        )
        raise ValueError("Incorrect number of transaction features.")

    if not np.all(np.isfinite(transaction)):
        logger.error("Transaction contains missing or infinite values.")
        raise ValueError("Transaction contains NaN or infinite values.")

    logger.info("Transaction validation completed successfully.")

    return transaction


def validate_transactions(transactions, expected_features):
    """
    Validates a batch of transactions before prediction.
    """

    try:
        transactions = np.asarray(transactions, dtype=float)

    except (ValueError, TypeError):
        logger.error("Transaction batch contains non-numeric values.")
        raise ValueError("Transactions must contain numeric values.")

    if transactions.ndim != 2:
        logger.error("Invalid transaction batch dimensions.")
        raise ValueError("Transactions must be a two-dimensional matrix.")

    if transactions.shape[1] != expected_features:
        logger.error(
            "Invalid feature count: expected %d, received %d.",
            expected_features,
            transactions.shape[1]
        )
        raise ValueError("Incorrect number of transaction features.")

    if not np.all(np.isfinite(transactions)):
        logger.error("Transaction batch contains missing or infinite values.")
        raise ValueError("Transactions contain NaN or infinite values.")

    logger.info(
        "Transaction batch validation completed: %d transactions.",
        len(transactions)
    )

    return transactions


if __name__ == "__main__":
    
    valid_transaction = [1.5, 2.5, 3.5]

    print("\n========== VALID TRANSACTION ==========")
    print(validate_transaction(valid_transaction, 3))

    print("\n========== INVALID TRANSACTION ==========")

    try:
        validate_transaction([1.5, np.nan, 3.5], 3)
    except ValueError as error:
        print("Validation error:", error)