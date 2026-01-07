"""Tests for logging configuration."""

import logging
from pathlib import Path

import pytest

from viper.utils.logger import _reset_logging, get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_logging() -> None:
    """Reset logging state before each test."""
    _reset_logging()


def test_setup_logging_creates_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that setup_logging creates the config directory."""
    # Use a temporary directory for testing
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Set up logging
    setup_logging()

    # Check that the config directory was created
    config_dir = fake_home / ".config" / "viper"
    assert config_dir.exists()
    assert config_dir.is_dir()


def test_setup_logging_creates_log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that setup_logging creates the log file."""
    # Use a temporary directory for testing
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Set up logging
    setup_logging()

    # Get logger and write a message
    logger = get_logger()
    logger.info("Test message")

    # Check that the log file was created
    log_file = fake_home / ".config" / "viper" / "viper.log"
    assert log_file.exists()


def test_setup_logging_writes_to_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that logging writes messages to the log file."""
    # Use a temporary directory for testing
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Set up logging
    setup_logging()

    # Get logger and write a message
    logger = get_logger()
    test_message = "This is a test log message"
    logger.info(test_message)

    # Read the log file
    log_file = fake_home / ".config" / "viper" / "viper.log"
    log_content = log_file.read_text()

    # Check that the message was written
    assert test_message in log_content


def test_setup_logging_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that log messages have the correct format."""
    # Use a temporary directory for testing
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Set up logging
    setup_logging()

    # Get logger and write a message
    logger = get_logger()
    logger.info("Test message")

    # Read the log file
    log_file = fake_home / ".config" / "viper" / "viper.log"
    log_content = log_file.read_text()

    # Check format: timestamp - level - message
    # Should contain " - INFO - "
    assert " - INFO - " in log_content
    assert "Test message" in log_content


def test_setup_logging_different_levels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that different log levels are written correctly."""
    # Use a temporary directory for testing
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Set up logging
    setup_logging()

    # Get logger and write messages at different levels
    logger = get_logger()
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Read the log file
    log_file = fake_home / ".config" / "viper" / "viper.log"
    log_content = log_file.read_text()

    # Check that all levels were written
    assert "INFO" in log_content
    assert "WARNING" in log_content
    assert "ERROR" in log_content
    assert "Info message" in log_content
    assert "Warning message" in log_content
    assert "Error message" in log_content


def test_get_logger_returns_viper_logger() -> None:
    """Test that get_logger returns the viper logger."""
    logger = get_logger()
    assert logger.name == "viper"


def test_get_logger_returns_same_instance() -> None:
    """Test that get_logger returns the same logger instance."""
    logger1 = get_logger()
    logger2 = get_logger()
    assert logger1 is logger2


def test_setup_logging_rotating_handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that setup_logging uses RotatingFileHandler."""
    # Use a temporary directory for testing
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Set up logging
    setup_logging()

    # Get logger
    logger = get_logger()

    # Check that the logger has a RotatingFileHandler
    from logging.handlers import RotatingFileHandler

    handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    assert len(handlers) > 0

    # Check handler configuration
    handler = handlers[0]
    # Max size: 5MB
    assert handler.maxBytes == 5 * 1024 * 1024
    # Keep 3 backups
    assert handler.backupCount == 3


def test_setup_logging_multiple_calls_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that calling setup_logging multiple times is safe."""
    # Use a temporary directory for testing
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Call setup_logging multiple times
    setup_logging()
    setup_logging()
    setup_logging()

    # Get logger
    logger = get_logger()

    # Should still work correctly
    logger.info("Test message")

    # Read the log file
    log_file = fake_home / ".config" / "viper" / "viper.log"
    log_content = log_file.read_text()

    assert "Test message" in log_content
