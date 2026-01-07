"""Logging configuration for Viper Terminal."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Flag to track if logging has been set up
_logging_configured = False


def setup_logging() -> None:
    """Set up logging to ~/.config/viper/viper.log with rotation.

    - Max file size: 5MB
    - Keep 3 backup files
    - Format: timestamp - level - message

    Note: This function is idempotent - calling it multiple times is safe.
    """
    global _logging_configured

    # Only set up logging once
    if _logging_configured:
        return

    # Create config directory if it doesn't exist
    config_dir = Path.home() / ".config" / "viper"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Log file path
    log_file = config_dir / "viper.log"

    # Create rotating file handler
    # maxBytes: 5MB = 5 * 1024 * 1024 bytes
    # backupCount: keep 3 backups (viper.log.1, viper.log.2, viper.log.3)
    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )

    # Set format: timestamp - level - message
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Get root logger and configure it
    logger = logging.getLogger("viper")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    _logging_configured = True


def get_logger() -> logging.Logger:
    """Get the Viper logger instance.

    Returns:
        The configured logger instance.
    """
    return logging.getLogger("viper")


def _reset_logging() -> None:
    """Reset logging configuration (for testing purposes only)."""
    global _logging_configured
    _logging_configured = False

    # Remove all handlers from the viper logger
    logger = logging.getLogger("viper")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
