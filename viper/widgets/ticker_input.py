"""Ticker input widget with validation and event emission."""

from textual.message import Message
from textual.widgets import Input


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

    def __init__(self) -> None:
        """Initialize the ticker input widget."""
        super().__init__(placeholder="Enter ticker symbol (e.g., AAPL, BTC)")

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

        # Emit the ticker lookup event
        self.post_message(self.TickerLookup(ticker))

        # Clear the input
        self.value = ""
