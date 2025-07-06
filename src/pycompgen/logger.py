import logging
import logging.handlers


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger("pycompgen")

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # If verbose, also log to console
    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    """Get the pycompgen logger."""
    return logging.getLogger("pycompgen")
