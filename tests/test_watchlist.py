"""Tests for the watchlist manager."""

import json
from pathlib import Path

import pytest

from viper.services.watchlist import WatchlistManager


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def manager(temp_config_dir: Path) -> WatchlistManager:
    """Create a WatchlistManager with a temporary config directory."""
    return WatchlistManager(config_dir=temp_config_dir)


def test_init_creates_empty_watchlist(temp_config_dir: Path) -> None:
    """Test that a new manager starts with an empty watchlist."""
    manager = WatchlistManager(config_dir=temp_config_dir)
    assert manager.get_all() == []


def test_add_ticker(manager: WatchlistManager) -> None:
    """Test adding a ticker to the watchlist."""
    manager.add("AAPL")
    assert manager.get_all() == ["AAPL"]


def test_add_multiple_tickers(manager: WatchlistManager) -> None:
    """Test adding multiple tickers."""
    manager.add("AAPL")
    manager.add("GOOGL")
    manager.add("MSFT")
    assert manager.get_all() == ["AAPL", "GOOGL", "MSFT"]


def test_add_normalizes_to_uppercase(manager: WatchlistManager) -> None:
    """Test that tickers are normalized to uppercase."""
    manager.add("aapl")
    manager.add("GooGL")
    assert manager.get_all() == ["AAPL", "GOOGL"]


def test_add_strips_whitespace(manager: WatchlistManager) -> None:
    """Test that whitespace is stripped from tickers."""
    manager.add("  AAPL  ")
    manager.add("\tGOOGL\n")
    assert manager.get_all() == ["AAPL", "GOOGL"]


def test_add_empty_ticker_ignored(manager: WatchlistManager) -> None:
    """Test that empty tickers are ignored."""
    manager.add("")
    manager.add("   ")
    assert manager.get_all() == []


def test_add_duplicate_moves_to_end(manager: WatchlistManager) -> None:
    """Test that adding a duplicate ticker removes the old one and adds at end."""
    manager.add("AAPL")
    manager.add("GOOGL")
    manager.add("MSFT")
    manager.add("AAPL")  # Should move AAPL to end
    assert manager.get_all() == ["GOOGL", "MSFT", "AAPL"]


def test_remove_existing_ticker(manager: WatchlistManager) -> None:
    """Test removing an existing ticker."""
    manager.add("AAPL")
    manager.add("GOOGL")
    result = manager.remove("AAPL")
    assert result is True
    assert manager.get_all() == ["GOOGL"]


def test_remove_nonexistent_ticker(manager: WatchlistManager) -> None:
    """Test removing a ticker that doesn't exist."""
    manager.add("AAPL")
    result = manager.remove("GOOGL")
    assert result is False
    assert manager.get_all() == ["AAPL"]


def test_remove_normalizes_ticker(manager: WatchlistManager) -> None:
    """Test that remove normalizes the ticker before searching."""
    manager.add("AAPL")
    result = manager.remove("aapl")
    assert result is True
    assert manager.get_all() == []


def test_remove_strips_whitespace(manager: WatchlistManager) -> None:
    """Test that remove strips whitespace."""
    manager.add("AAPL")
    result = manager.remove("  AAPL  ")
    assert result is True
    assert manager.get_all() == []


def test_get_all_returns_copy(manager: WatchlistManager) -> None:
    """Test that get_all returns a copy, not the internal list."""
    manager.add("AAPL")
    items = manager.get_all()
    items.append("GOOGL")
    # Internal list should not be modified
    assert manager.get_all() == ["AAPL"]


def test_clear_removes_all_tickers(manager: WatchlistManager) -> None:
    """Test clearing all tickers from watchlist."""
    manager.add("AAPL")
    manager.add("GOOGL")
    manager.add("MSFT")
    manager.clear()
    assert manager.get_all() == []


def test_persistence_saves_to_file(temp_config_dir: Path) -> None:
    """Test that watchlist is saved to file."""
    manager = WatchlistManager(config_dir=temp_config_dir)
    manager.add("AAPL")
    manager.add("GOOGL")

    # Check file was created and contains correct data
    watchlist_file = temp_config_dir / "watchlist.json"
    assert watchlist_file.exists()

    with open(watchlist_file) as f:
        data = json.load(f)

    assert data == {"watchlist": ["AAPL", "GOOGL"]}


def test_persistence_loads_from_file(temp_config_dir: Path) -> None:
    """Test that watchlist is loaded from file on init."""
    # Create watchlist file manually
    watchlist_file = temp_config_dir / "watchlist.json"
    with open(watchlist_file, "w") as f:
        json.dump({"watchlist": ["AAPL", "GOOGL", "MSFT"]}, f)

    # Create manager - should load from file
    manager = WatchlistManager(config_dir=temp_config_dir)
    assert manager.get_all() == ["AAPL", "GOOGL", "MSFT"]


def test_persistence_missing_file_handled(temp_config_dir: Path) -> None:
    """Test that missing watchlist file is handled gracefully."""
    manager = WatchlistManager(config_dir=temp_config_dir)
    assert manager.get_all() == []


def test_persistence_corrupt_json_handled(temp_config_dir: Path) -> None:
    """Test that corrupt JSON file is handled gracefully."""
    # Create corrupt JSON file
    watchlist_file = temp_config_dir / "watchlist.json"
    with open(watchlist_file, "w") as f:
        f.write("{ invalid json }")

    # Should handle corruption and start with empty watchlist
    manager = WatchlistManager(config_dir=temp_config_dir)
    assert manager.get_all() == []


def test_persistence_invalid_structure_handled(temp_config_dir: Path) -> None:
    """Test that invalid JSON structure is handled gracefully."""
    # Create file with wrong structure
    watchlist_file = temp_config_dir / "watchlist.json"
    with open(watchlist_file, "w") as f:
        json.dump({"wrong_key": ["AAPL"]}, f)

    # Should handle invalid structure and start with empty watchlist
    manager = WatchlistManager(config_dir=temp_config_dir)
    assert manager.get_all() == []


def test_persistence_watchlist_not_list_handled(temp_config_dir: Path) -> None:
    """Test that non-list watchlist value is handled gracefully."""
    # Create file with watchlist as non-list
    watchlist_file = temp_config_dir / "watchlist.json"
    with open(watchlist_file, "w") as f:
        json.dump({"watchlist": "not a list"}, f)

    # Should handle invalid type and start with empty watchlist
    manager = WatchlistManager(config_dir=temp_config_dir)
    assert manager.get_all() == []


def test_persistence_filters_invalid_items(temp_config_dir: Path) -> None:
    """Test that invalid items in watchlist are filtered out."""
    # Create file with mixed valid/invalid items
    watchlist_file = temp_config_dir / "watchlist.json"
    with open(watchlist_file, "w") as f:
        json.dump({"watchlist": ["AAPL", 123, "", "GOOGL", None, "  ", "MSFT"]}, f)

    # Should filter out invalid items (non-strings and empty strings)
    manager = WatchlistManager(config_dir=temp_config_dir)
    assert manager.get_all() == ["AAPL", "GOOGL", "MSFT"]


def test_persistence_updates_on_add(temp_config_dir: Path) -> None:
    """Test that file is updated when ticker is added."""
    manager = WatchlistManager(config_dir=temp_config_dir)
    manager.add("AAPL")

    # Verify file was updated
    watchlist_file = temp_config_dir / "watchlist.json"
    with open(watchlist_file) as f:
        data = json.load(f)

    assert data == {"watchlist": ["AAPL"]}


def test_persistence_updates_on_remove(temp_config_dir: Path) -> None:
    """Test that file is updated when ticker is removed."""
    manager = WatchlistManager(config_dir=temp_config_dir)
    manager.add("AAPL")
    manager.add("GOOGL")
    manager.remove("AAPL")

    # Verify file was updated
    watchlist_file = temp_config_dir / "watchlist.json"
    with open(watchlist_file) as f:
        data = json.load(f)

    assert data == {"watchlist": ["GOOGL"]}


def test_persistence_updates_on_clear(temp_config_dir: Path) -> None:
    """Test that file is updated when watchlist is cleared."""
    manager = WatchlistManager(config_dir=temp_config_dir)
    manager.add("AAPL")
    manager.add("GOOGL")
    manager.clear()

    # Verify file was updated
    watchlist_file = temp_config_dir / "watchlist.json"
    with open(watchlist_file) as f:
        data = json.load(f)

    assert data == {"watchlist": []}


def test_default_config_dir_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that default config directory is used when none specified."""
    # Mock Path.home() to return temp directory
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    manager = WatchlistManager()
    manager.add("AAPL")

    # Check file was created in default location
    expected_file = tmp_path / ".config" / "viper" / "watchlist.json"
    assert expected_file.exists()


def test_save_error_handled_silently(
    temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that save errors are handled silently without crashing."""
    manager = WatchlistManager(config_dir=temp_config_dir)

    # Mock open to raise OSError
    def mock_open(*args: object, **kwargs: object) -> None:
        raise OSError("Disk full")

    monkeypatch.setattr("builtins.open", mock_open)

    # Should not raise exception
    manager.add("AAPL")
    # In-memory state should still be updated
    assert manager.get_all() == ["AAPL"]
