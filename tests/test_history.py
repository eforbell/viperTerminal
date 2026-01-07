"""Tests for the history manager."""

import json
from pathlib import Path

import pytest

from viper.services.history import HistoryManager


def test_history_manager_initialization(tmp_path: Path) -> None:
    """Test that HistoryManager initializes correctly."""
    manager = HistoryManager(config_dir=tmp_path)
    assert manager.max_size == 20
    assert manager.config_dir == tmp_path
    assert manager.history_file == tmp_path / "history.json"
    assert manager.get_all() == []


def test_add_ticker_to_history(tmp_path: Path) -> None:
    """Test adding a ticker to history."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    assert manager.get_all() == ["AAPL"]


def test_add_normalizes_ticker(tmp_path: Path) -> None:
    """Test that add() normalizes ticker to uppercase and strips whitespace."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("  aapl  ")
    assert manager.get_all() == ["AAPL"]


def test_add_empty_ticker_ignored(tmp_path: Path) -> None:
    """Test that adding empty string is ignored."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("")
    manager.add("   ")
    assert manager.get_all() == []


def test_add_removes_duplicates(tmp_path: Path) -> None:
    """Test that adding duplicate ticker moves it to front."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")
    manager.add("MSFT")
    manager.add("TSLA")  # Duplicate
    assert manager.get_all() == ["TSLA", "MSFT", "AAPL"]


def test_add_respects_max_size(tmp_path: Path) -> None:
    """Test that history is trimmed to max_size."""
    manager = HistoryManager(max_size=3, config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")
    manager.add("MSFT")
    manager.add("NVDA")
    assert manager.get_all() == ["NVDA", "MSFT", "TSLA"]
    assert len(manager.get_all()) == 3


def test_navigate_up_in_history(tmp_path: Path) -> None:
    """Test navigating up (backward) in history."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")
    manager.add("MSFT")

    # Navigate up through history
    assert manager.navigate_up() == "MSFT"
    assert manager.navigate_up() == "TSLA"
    assert manager.navigate_up() == "AAPL"


def test_navigate_up_at_end(tmp_path: Path) -> None:
    """Test that navigating up at the end stays at last item."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")

    # Navigate to end
    manager.navigate_up()
    manager.navigate_up()

    # Try to go further
    assert manager.navigate_up() == "AAPL"  # Stays at end


def test_navigate_up_empty_history(tmp_path: Path) -> None:
    """Test navigating up with empty history returns None."""
    manager = HistoryManager(config_dir=tmp_path)
    assert manager.navigate_up() is None


def test_navigate_down_in_history(tmp_path: Path) -> None:
    """Test navigating down (forward) in history."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")
    manager.add("MSFT")

    # Navigate up first
    manager.navigate_up()
    manager.navigate_up()
    manager.navigate_up()

    # Now navigate down
    assert manager.navigate_down() == "TSLA"
    assert manager.navigate_down() == "MSFT"
    assert manager.navigate_down() == ""  # Back to beginning


def test_navigate_down_at_beginning(tmp_path: Path) -> None:
    """Test that navigating down at beginning returns None."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    assert manager.navigate_down() is None


def test_navigate_down_empty_history(tmp_path: Path) -> None:
    """Test navigating down with empty history returns None."""
    manager = HistoryManager(config_dir=tmp_path)
    assert manager.navigate_down() is None


def test_reset_navigation(tmp_path: Path) -> None:
    """Test resetting navigation state."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")

    # Navigate up
    manager.navigate_up()
    manager.navigate_up()

    # Reset
    manager.reset_navigation()

    # Should start from beginning again
    assert manager.navigate_up() == "TSLA"


def test_add_resets_navigation(tmp_path: Path) -> None:
    """Test that add() resets navigation state."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")

    # Navigate up
    manager.navigate_up()

    # Add new item
    manager.add("MSFT")

    # Navigation should be reset
    assert manager.navigate_up() == "MSFT"


def test_clear_history(tmp_path: Path) -> None:
    """Test clearing all history."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")
    manager.add("MSFT")

    manager.clear()
    assert manager.get_all() == []


def test_persistence_saves_history(tmp_path: Path) -> None:
    """Test that history is saved to file."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")

    # Check file was created
    assert manager.history_file.exists()

    # Check file contents
    with manager.history_file.open("r") as f:
        data = json.load(f)
    assert data == {"history": ["TSLA", "AAPL"]}


def test_persistence_loads_history(tmp_path: Path) -> None:
    """Test that history is loaded from file."""
    # Create history file
    history_file = tmp_path / "history.json"
    with history_file.open("w") as f:
        json.dump({"history": ["MSFT", "NVDA"]}, f)

    # Load it
    manager = HistoryManager(config_dir=tmp_path)
    assert manager.get_all() == ["MSFT", "NVDA"]


def test_persistence_handles_missing_file(tmp_path: Path) -> None:
    """Test that missing history file is handled gracefully."""
    manager = HistoryManager(config_dir=tmp_path)
    assert manager.get_all() == []


def test_persistence_handles_corrupt_json(tmp_path: Path) -> None:
    """Test that corrupt JSON file is handled gracefully."""
    history_file = tmp_path / "history.json"
    history_file.write_text("not valid json {")

    manager = HistoryManager(config_dir=tmp_path)
    assert manager.get_all() == []


def test_persistence_handles_invalid_structure(tmp_path: Path) -> None:
    """Test that invalid JSON structure is handled gracefully."""
    history_file = tmp_path / "history.json"
    with history_file.open("w") as f:
        json.dump({"wrong_key": ["AAPL"]}, f)

    manager = HistoryManager(config_dir=tmp_path)
    assert manager.get_all() == []


def test_persistence_handles_non_list_history(tmp_path: Path) -> None:
    """Test that non-list history value is handled gracefully."""
    history_file = tmp_path / "history.json"
    with history_file.open("w") as f:
        json.dump({"history": "not a list"}, f)

    manager = HistoryManager(config_dir=tmp_path)
    assert manager.get_all() == []


def test_persistence_filters_non_string_items(tmp_path: Path) -> None:
    """Test that non-string items in history are filtered out."""
    history_file = tmp_path / "history.json"
    with history_file.open("w") as f:
        json.dump({"history": ["AAPL", 123, "TSLA", None, "MSFT"]}, f)

    manager = HistoryManager(config_dir=tmp_path)
    assert manager.get_all() == ["AAPL", "TSLA", "MSFT"]


def test_persistence_trims_oversized_history(tmp_path: Path) -> None:
    """Test that oversized history from file is trimmed."""
    # Create file with more items than max_size
    history_file = tmp_path / "history.json"
    large_history = [f"TICK{i}" for i in range(30)]
    with history_file.open("w") as f:
        json.dump({"history": large_history}, f)

    manager = HistoryManager(max_size=20, config_dir=tmp_path)
    assert len(manager.get_all()) == 20
    assert manager.get_all() == large_history[:20]


def test_persistence_creates_directory(tmp_path: Path) -> None:
    """Test that config directory is created if it doesn't exist."""
    nested_dir = tmp_path / "nested" / "config"
    manager = HistoryManager(config_dir=nested_dir)
    manager.add("AAPL")

    assert nested_dir.exists()
    assert manager.history_file.exists()


def test_get_all_returns_copy(tmp_path: Path) -> None:
    """Test that get_all() returns a copy, not the original list."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")

    history1 = manager.get_all()
    history1.append("TSLA")  # Modify the returned list

    history2 = manager.get_all()
    assert history2 == ["AAPL"]  # Original unchanged


def test_clear_persists_empty_history(tmp_path: Path) -> None:
    """Test that clear() persists the empty state."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.clear()

    # Load in new instance
    manager2 = HistoryManager(config_dir=tmp_path)
    assert manager2.get_all() == []
