
import logging
from pathlib import Path


# Create the logs directory if it does not exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "fraud_detection.log"


def get_logger(name="fraud_detection"):
    """
    Creates and returns a configured logger.
    """

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Log format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


if __name__ == "__main__":

    logger = get_logger()

    logger.info("Fraud detection logging initialized.")
    logger.info("C4.5 decision tree module is ready.")

    logger.warning("This is an example warning.")

    logger.error("This is an example error.")