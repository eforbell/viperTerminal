"""Ticker input widget with validation and event emission."""

from textual.events import Key
from textual.message import Message
from textual.widgets import Input

from viper.services.history import HistoryManager


class TickerInput(Input):
    """Input widget for entering ticker symbols."""

    class TickerLookup(Message):
        """Event emitted when a ticker symbol is submitted."""

        def __init__(self, ticker: str) -> None:
            """Initialize the TickerLookup event.

            Args:
                ticker: The normalized ticker symbol (uppercase).
            """
            super().__init__()
            self.ticker = ticker

    def __init__(self, history_manager: HistoryManager | None = None) -> None:
        """Initialize the ticker input widget.

        Args:
            history_manager: Optional history manager for navigation.
        """
        super().__init__(placeholder="Enter ticker symbol (e.g., AAPL, BTC)")
        self.history_manager = history_manager

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission.

        Args:
            event: The submitted event from the Input widget.
        """
        # Get the input value and strip whitespace
        raw_value = event.value.strip()

        # Validate: don't allow empty input
        if not raw_value:
            # Show error message by setting the input to error state
            self.add_class("error")
            # Clear the input even on error
            self.value = ""
            return

        # Remove error state if previously set
        self.remove_class("error")

        # Normalize to uppercase
        ticker = raw_value.upper()

        # Add to history
        if self.history_manager:
            self.history_manager.add(ticker)

        # Emit the ticker lookup event
        self.post_message(self.TickerLookup(ticker))

        # Clear the input
        self.value = ""

    # Keys that should bubble to app when input is empty (bindings + prefix key)
    _APP_BINDING_KEYS = frozenset({"q", "i", "c", "n", "1", "2", "3", "4", "5", "6", "7", "t"})

    def check_consume_key(self, key: str, character: str | None) -> bool:
        """Check if the widget should consume the given key.

        When the input is empty, certain keys should bubble to the app:
        - Binding keys (q, i, c, n, 1-7) for app-level commands
        - 't' for the technical indicator prefix system (t-r, t-a, t-m)
        - Any key when prefix mode is active (for completing t-r, t-a, t-m sequences)

        Other keys (like 'w', 'd', etc.) should be typed into the input
        so users can enter commands like "W AAPL" to add to watchlist.

        Args:
            key: A key identifier.
            character: A character associated with the key, or None.

        Returns:
            True if the widget should capture the key, False otherwise.
        """
        # Check if app's technical prefix mode is active
        prefix_active = getattr(self.app, "_technical_prefix_active", False)

        # When input is empty and key is a binding/prefix key (or prefix active), don't consume it
        if not self.value and (key in self._APP_BINDING_KEYS or prefix_active):
            return False
        # Otherwise, use the default Input behavior
        return super().check_consume_key(key, character)

    def on_key(self, event: Key) -> None:
        """Handle key events for history navigation.

        Args:
            event: The key event.
        """
        # Check if app's technical prefix mode is active
        prefix_active = getattr(self.app, "_technical_prefix_active", False)

        # When input is empty and key is a binding/prefix key, or prefix is active,
        # stop the base Input from consuming it and forward to app
        if not self.value and (event.key in self._APP_BINDING_KEYS or prefix_active):
            event.stop()
            event.prevent_default()
            # Forward to app's on_key handler for prefix system
            if hasattr(self.app, "on_key"):
                self.app.on_key(event)
            return

        if not self.history_manager:
            return

        # Reset navigation when user types
        if event.key not in ("up", "down"):
            self.history_manager.reset_navigation()
            return

        # Navigate history
        if event.key == "up":
            ticker = self.history_manager.navigate_up()
            if ticker is not None:
                self.value = ticker
                # Move cursor to end
                self.cursor_position = len(ticker)
                event.prevent_default()
        elif event.key == "down":
            ticker = self.history_manager.navigate_down()
            if ticker is not None:
                self.value = ticker
                # Move cursor to end
                self.cursor_position = len(ticker)
                event.prevent_default()
