"""Logging configuration for the Viper MCP server."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_mcp_logging_configured = False


def setup_mcp_logging() -> None:
    """Set up MCP logging to ~/.config/viper/viper-mcp.log with rotation."""
    global _mcp_logging_configured

    if _mcp_logging_configured:
        return

    config_dir = Path.home() / ".config" / "viper"
    config_dir.mkdir(parents=True, exist_ok=True)

    log_file = config_dir / "viper-mcp.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger = logging.getLogger("viper.mcp")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    _mcp_logging_configured = True


def get_mcp_logger() -> logging.Logger:
    """Get the MCP logger instance."""
    return logging.getLogger("viper.mcp")


def _reset_mcp_logging() -> None:
    """Reset MCP logging configuration (for tests)."""
    global _mcp_logging_configured
    _mcp_logging_configured = False

    logger = logging.getLogger("viper.mcp")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
