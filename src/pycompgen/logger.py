import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger("pycompgen")

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    # Get log directory
    log_dir = get_log_dir()
    log_file = log_dir / "pycompgen.log"

    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=3,
    )
    file_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)

    # If verbose, also log to console
    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_log_dir() -> Path:
    """Get the log directory."""
    # Use XDG_STATE_HOME if set, otherwise use ~/.local/state
    state_home = os.environ.get("XDG_STATE_HOME")
    if state_home:
        log_dir = Path(state_home) / "pycompgen"
    else:
        log_dir = Path.home() / ".local" / "state" / "pycompgen"

    # Create directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_logger() -> logging.Logger:
    """Get the pycompgen logger."""
    return logging.getLogger("pycompgen")
