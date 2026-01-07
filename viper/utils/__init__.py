"""Utility modules for Viper Terminal."""

from viper.utils.error_formatter import format_error_message, is_network_error
from viper.utils.first_run import is_first_run, mark_first_run_complete
from viper.utils.logger import get_logger, setup_logging

__all__ = [
    "format_error_message",
    "get_logger",
    "is_first_run",
    "is_network_error",
    "mark_first_run_complete",
    "setup_logging",
]
