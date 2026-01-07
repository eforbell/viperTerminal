"""Watchlist manager for storing and managing watched tickers."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WatchlistItem:
    """A single watchlist item with ticker symbol."""

    ticker: str


class WatchlistManager:
    """Manages watchlist persistence and operations."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize watchlist manager.

        Args:
            config_dir: Optional config directory path. Defaults to ~/.config/viper
        """
        self._config_dir = config_dir or Path.home() / ".config" / "viper"
        self._file_path = self._config_dir / "watchlist.json"
        self._items: list[str] = []
        self._load()

    def add(self, ticker: str) -> None:
        """Add a ticker to the watchlist.

        Args:
            ticker: Ticker symbol to add (will be normalized to uppercase)
        """
        normalized = ticker.strip().upper()
        if not normalized:
            return

        # Remove if already exists (deduplicate)
        if normalized in self._items:
            self._items.remove(normalized)

        # Add to the end of the list
        self._items.append(normalized)
        self._save()

    def remove(self, ticker: str) -> bool:
        """Remove a ticker from the watchlist.

        Args:
            ticker: Ticker symbol to remove

        Returns:
            True if ticker was removed, False if not found
        """
        normalized = ticker.strip().upper()
        if normalized in self._items:
            self._items.remove(normalized)
            self._save()
            return True
        return False

    def get_all(self) -> list[str]:
        """Get all tickers in the watchlist.

        Returns:
            Copy of the watchlist items
        """
        return self._items.copy()

    def clear(self) -> None:
        """Clear all items from the watchlist."""
        self._items = []
        self._save()

    def _load(self) -> None:
        """Load watchlist from disk. Creates file if missing, handles corruption."""
        try:
            if not self._file_path.exists():
                return

            with open(self._file_path) as f:
                data = json.load(f)

            # Validate structure
            if not isinstance(data, dict) or "watchlist" not in data:
                return

            items = data["watchlist"]
            if not isinstance(items, list):
                return

            # Filter valid strings only
            self._items = [
                item for item in items if isinstance(item, str) and item.strip()
            ]

        except (OSError, json.JSONDecodeError):
            # Silently handle errors, start with empty watchlist
            self._items = []

    def _save(self) -> None:
        """Save watchlist to disk. Fails silently on errors."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._file_path, "w") as f:
                json.dump({"watchlist": self._items}, f, indent=2)
        except OSError:
            # Silently fail - don't crash the app
            pass
