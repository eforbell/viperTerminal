"""Tests for MCP logging configuration."""

from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from viper.mcp.logging import _reset_mcp_logging, get_mcp_logger, setup_mcp_logging


@pytest.fixture(autouse=True)
def reset_mcp_logging() -> None:
    """Reset MCP logging before each test."""
    _reset_mcp_logging()


def test_setup_mcp_logging_creates_log_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should create MCP log file and write messages."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    setup_mcp_logging()
    logger = get_mcp_logger()
    logger.info("MCP test log")

    log_file = fake_home / ".config" / "viper" / "viper-mcp.log"
    assert log_file.exists()
    assert "MCP test log" in log_file.read_text()


def test_setup_mcp_logging_uses_rotating_handler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should use RotatingFileHandler with expected limits."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    setup_mcp_logging()
    logger = get_mcp_logger()
    handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    assert len(handlers) > 0
    handler = handlers[0]
    assert handler.maxBytes == 5 * 1024 * 1024
    assert handler.backupCount == 3
