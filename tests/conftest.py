"""Pytest configuration and fixtures for all tests.

CRITICAL: This file ensures all tests are isolated from the real user environment.
Tests must NEVER read from or write to the user's actual config files.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_home_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Automatically isolate ALL tests from the real home directory.

    This fixture runs automatically for every test (autouse=True) and ensures:
    1. Path.home() returns a temp directory, not the real home
    2. Any config files (watchlist, history, etc.) are created in isolation
    3. Tests can never accidentally nuke user data

    The fixture patches Path.home() to return tmp_path, so any code that uses
    Path.home() / ".config" / "viper" will use the temp directory instead.
    """
    # Patch Path.home() to return temp directory
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create the config directory structure that code expects
    config_dir = tmp_path / ".config" / "viper"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Mark first-run as complete to prevent welcome screen in tests
    first_run_file = config_dir / "first_run.json"
    first_run_file.write_text(json.dumps({"first_run_complete": True}))

    return tmp_path
