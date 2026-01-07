"""History management for ticker lookups."""

import json
from pathlib import Path
from typing import Any


class HistoryManager:
    """Manages ticker lookup history with persistence."""

    def __init__(self, max_size: int = 20, config_dir: Path | None = None) -> None:
        """Initialize the history manager.

        Args:
            max_size: Maximum number of history items to store.
            config_dir: Directory for config files. Defaults to ~/.config/viper.
        """
        self.max_size = max_size
        if config_dir is None:
            config_dir = Path.home() / ".config" / "viper"
        self.config_dir = config_dir
        self.history_file = self.config_dir / "history.json"
        self._history: list[str] = []
        self._current_index: int = -1  # -1 means not navigating
        self._load()

    def add(self, ticker: str) -> None:
        """Add a ticker to history.

        Args:
            ticker: The ticker symbol to add.
        """
        ticker = ticker.strip().upper()
        if not ticker:
            return

        # Remove duplicate if it exists
        if ticker in self._history:
            self._history.remove(ticker)

        # Add to front
        self._history.insert(0, ticker)

        # Trim to max size
        if len(self._history) > self.max_size:
            self._history = self._history[: self.max_size]

        # Reset navigation index
        self._current_index = -1

        # Persist
        self._save()

    def navigate_up(self) -> str | None:
        """Navigate to previous (older) history item.

        Returns:
            The ticker symbol or None if at the end.
        """
        if not self._history:
            return None

        # Move deeper into history
        if self._current_index < len(self._history) - 1:
            self._current_index += 1
            return self._history[self._current_index]

        # Already at the end
        return self._history[self._current_index] if self._current_index >= 0 else None

    def navigate_down(self) -> str | None:
        """Navigate to next (newer) history item.

        Returns:
            The ticker symbol or None if at the beginning.
        """
        if not self._history:
            return None

        # Move back toward recent history
        if self._current_index > 0:
            self._current_index -= 1
            return self._history[self._current_index]

        # At the beginning, return to empty state
        if self._current_index == 0:
            self._current_index = -1
            return ""  # Empty string to clear input

        return None

    def reset_navigation(self) -> None:
        """Reset navigation state (call when user types in input)."""
        self._current_index = -1

    def get_all(self) -> list[str]:
        """Get all history items.

        Returns:
            List of ticker symbols, most recent first.
        """
        return self._history.copy()

    def clear(self) -> None:
        """Clear all history."""
        self._history = []
        self._current_index = -1
        self._save()

    def _load(self) -> None:
        """Load history from file."""
        try:
            if self.history_file.exists():
                with self.history_file.open("r") as f:
                    data: Any = json.load(f)
                    if isinstance(data, dict) and "history" in data:
                        history = data["history"]
                        if isinstance(history, list):
                            # Validate all items are strings
                            self._history = [
                                str(item) for item in history if isinstance(item, str)
                            ]
                            # Trim to max size in case it was larger
                            self._history = self._history[: self.max_size]
        except (json.JSONDecodeError, OSError, KeyError):
            # File is corrupt or can't be read - start fresh
            self._history = []

    def _save(self) -> None:
        """Save history to file."""
        try:
            # Create config directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Write history
            with self.history_file.open("w") as f:
                json.dump({"history": self._history}, f, indent=2)
        except OSError:
            # Can't write - fail silently, history just won't persist
            pass
