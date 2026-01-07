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

    def on_key(self, event: Key) -> None:
        """Handle key events for history navigation.

        Args:
            event: The key event.
        """
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
