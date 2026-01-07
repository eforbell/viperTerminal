"""Tests for first-run detection."""

import json
from pathlib import Path
from unittest.mock import patch

from viper.utils.first_run import get_first_run_flag_path, is_first_run, mark_first_run_complete


def test_get_first_run_flag_path() -> None:
    """Test that get_first_run_flag_path returns correct path."""
    path = get_first_run_flag_path()
    assert path == Path.home() / ".config" / "viper" / "first_run.json"


def test_is_first_run_when_file_does_not_exist(tmp_path: Path) -> None:
    """Test that is_first_run returns True when flag file doesn't exist."""
    flag_path = tmp_path / "first_run.json"

    with patch("viper.utils.first_run.get_first_run_flag_path", return_value=flag_path):
        assert is_first_run() is True


def test_is_first_run_when_file_exists(tmp_path: Path) -> None:
    """Test that is_first_run returns False when flag file exists."""
    flag_path = tmp_path / "first_run.json"
    flag_path.write_text(json.dumps({"first_run_complete": True}))

    with patch("viper.utils.first_run.get_first_run_flag_path", return_value=flag_path):
        assert is_first_run() is False


def test_mark_first_run_complete_creates_file(tmp_path: Path) -> None:
    """Test that mark_first_run_complete creates the flag file."""
    flag_path = tmp_path / "first_run.json"

    with patch("viper.utils.first_run.get_first_run_flag_path", return_value=flag_path):
        mark_first_run_complete()

        assert flag_path.exists()
        data = json.loads(flag_path.read_text())
        assert data["first_run_complete"] is True


def test_mark_first_run_complete_creates_parent_directory(tmp_path: Path) -> None:
    """Test that mark_first_run_complete creates parent directories."""
    flag_path = tmp_path / "nested" / "dir" / "first_run.json"

    with patch("viper.utils.first_run.get_first_run_flag_path", return_value=flag_path):
        mark_first_run_complete()

        assert flag_path.exists()
        assert flag_path.parent.exists()


def test_mark_first_run_complete_handles_os_error(tmp_path: Path) -> None:
    """Test that mark_first_run_complete handles OSError gracefully."""
    flag_path = tmp_path / "first_run.json"

    # Make the path unwritable
    with (
        patch("viper.utils.first_run.get_first_run_flag_path", return_value=flag_path),
        patch("pathlib.Path.write_text", side_effect=OSError("Permission denied")),
    ):
        # Should not raise - fail silently
        mark_first_run_complete()


def test_is_first_run_after_mark_complete(tmp_path: Path) -> None:
    """Test that is_first_run returns False after marking complete."""
    flag_path = tmp_path / "first_run.json"

    with patch("viper.utils.first_run.get_first_run_flag_path", return_value=flag_path):
        # First run
        assert is_first_run() is True

        # Mark complete
        mark_first_run_complete()

        # No longer first run
        assert is_first_run() is False
