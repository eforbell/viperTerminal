"""Watchlist panel widget for displaying watched tickers with live prices."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator

from viper.services.quote import Quote, QuoteError, fetch_quote
from viper.services.stock import StockQuote
from viper.services.streaming import (
    ConnectionState,
    StreamingQuote,
    StreamingService,
)
from viper.services.watchlist import WatchlistManager


class WatchlistPanel(Widget):
    """Panel for displaying watchlist items with prices and changes."""

    # Make the panel focusable
    can_focus = True

    # Keyboard bindings for navigation - use priority=True so they work when focused
    BINDINGS = [
        Binding("j", "navigate_down", "Next", show=False, priority=True),
        Binding("k", "navigate_up", "Previous", show=False, priority=True),
        Binding("enter", "select_item", "Select", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    WatchlistPanel {
        height: 100%;
        width: 100%;
        padding: 1 2;
    }

    WatchlistPanel .panel-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        width: 100%;
    }

    WatchlistPanel .watchlist-item {
        width: 100%;
        margin-bottom: 0;
    }

    WatchlistPanel .ticker-symbol {
        text-style: bold;
        color: $accent;
    }

    WatchlistPanel .positive {
        color: #00ff00;
    }

    WatchlistPanel .negative {
        color: #ff0000;
    }

    WatchlistPanel .neutral {
        color: #666666;
    }

    WatchlistPanel .empty-state {
        color: #666666;
        text-align: center;
        margin-top: 3;
    }

    WatchlistPanel .loading-container {
        align: center middle;
        height: 100%;
    }

    WatchlistPanel .loading-text {
        color: #666666;
        margin-top: 1;
    }

    WatchlistPanel .selected {
        background: #003300;
        text-style: bold;
    }

    WatchlistPanel VerticalScroll {
        height: 100%;
    }
    """

    class TickerSelected(Message):
        """Message sent when a watchlist item is clicked."""

        def __init__(self, ticker: str) -> None:
            """Initialize the message.

            Args:
                ticker: The ticker symbol that was selected.
            """
            super().__init__()
            self.ticker = ticker

    class StreamingQuoteReceived(Message):
        """Message sent when a streaming quote is received."""

        def __init__(self, quote: StreamingQuote) -> None:
            """Initialize the message.

            Args:
                quote: The streaming quote data.
            """
            super().__init__()
            self.quote = quote

    class StreamingStateChanged(Message):
        """Message sent when streaming connection state changes."""

        def __init__(self, state: ConnectionState) -> None:
            """Initialize the message.

            Args:
                state: The new connection state.
            """
            super().__init__()
            self.state = state

    def __init__(
        self, watchlist_manager: WatchlistManager, refresh_interval: int = 60, streaming_enabled: bool = False
    ) -> None:
        """Initialize the watchlist panel.

        Args:
            watchlist_manager: The watchlist manager instance.
            refresh_interval: Auto-refresh interval in seconds (default: 60).
            streaming_enabled: Enable real-time streaming mode on mount (default: False).
        """
        super().__init__()
        self._watchlist_manager = watchlist_manager
        self._refresh_interval = refresh_interval
        self._quotes: dict[str, Quote | QuoteError] = {}
        self._refresh_timer_active = False
        self._selected_index = 0
        self._initial_load = True  # Track if this is the first load
        self._auto_enable_streaming = streaming_enabled  # Store for on_mount
        self._streaming_enabled: bool = False
        self._streaming_quotes: dict[str, StreamingQuote] = {}
        self._streaming_service: StreamingService | None = None
        self._connection_state: ConnectionState = ConnectionState.DISCONNECTED

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("WATCHLIST", id="watchlist-header", classes="panel-header")
        yield VerticalScroll(id="watchlist-content")

    def on_mount(self) -> None:
        """Start the auto-refresh timer when mounted."""
        self._refresh_timer_active = True
        # Show loading state if we have tickers to load
        if self._watchlist_manager.get_all():
            self._render_items()  # Will show loading spinner
        self.set_interval(self._refresh_interval, self.refresh_quotes)
        self.run_worker(self.refresh_quotes())

        # Enable streaming if configured
        if self._auto_enable_streaming:
            self.run_worker(self._enable_streaming())

    def on_unmount(self) -> None:
        """Stop the refresh timer and streaming when unmounted."""
        self._refresh_timer_active = False
        # Stop streaming service if running
        if self._streaming_enabled and self._streaming_service:
            self.run_worker(self._streaming_service.stop())

    async def refresh_quotes(self) -> None:
        """Fetch updated quotes for all watchlist items."""
        if not self._refresh_timer_active:
            return

        tickers = self._watchlist_manager.get_all()
        if not tickers:
            self._initial_load = False
            self._render_items()
            return

        # Fetch quotes for all tickers
        for ticker in tickers:
            result = await fetch_quote(ticker)
            self._quotes[ticker] = result

        self._initial_load = False
        self._render_items()

    def _render_items(self) -> None:
        """Render the watchlist items with current quotes."""
        # Update header to show streaming state
        header = self.query_one("#watchlist-header", Label)
        if self._streaming_enabled:
            if self._connection_state == ConnectionState.CONNECTED:
                header.update("WATCHLIST [LIVE]")
            elif self._connection_state == ConnectionState.CONNECTING:
                header.update("WATCHLIST [CONNECTING...]")
            elif self._connection_state == ConnectionState.RECONNECTING:
                header.update("WATCHLIST [RECONNECTING...]")
            else:
                header.update("WATCHLIST")
        else:
            header.update("WATCHLIST")

        container = self.query_one("#watchlist-content", VerticalScroll)
        container.remove_children()

        tickers = self._watchlist_manager.get_all()

        if not tickers:
            container.mount(Label("No tickers in watchlist", classes="empty-state"))
            self._selected_index = 0
            return

        # Show loading spinner during initial load
        if self._initial_load and not self._quotes:
            loading_container = Container(
                LoadingIndicator(),
                Label(f"Loading {len(tickers)} ticker{'s' if len(tickers) > 1 else ''}...",
                      classes="loading-text"),
                classes="loading-container",
            )
            container.mount(loading_container)
            return

        # Clamp selected index to valid range
        if self._selected_index >= len(tickers):
            self._selected_index = len(tickers) - 1
        if self._selected_index < 0:
            self._selected_index = 0

        for i, ticker in enumerate(tickers):
            # Prefer streaming quote if available and streaming is enabled
            streaming_quote = (
                self._streaming_quotes.get(ticker) if self._streaming_enabled else None
            )
            polling_quote = self._quotes.get(ticker)

            if streaming_quote:
                # Use streaming data - format it for display
                line = self._format_streaming_quote_line(ticker, streaming_quote)
                change_pct = streaming_quote.change_percent
            elif polling_quote and not isinstance(polling_quote, QuoteError):
                # Fall back to polling data
                line = self._format_quote_line(ticker, polling_quote)
                # Apply color class based on change
                if hasattr(polling_quote, "change_percent"):
                    # Stock quote
                    change_pct = polling_quote.change_percent
                elif hasattr(polling_quote, "change_24h_percent"):
                    # Crypto quote
                    change_pct = polling_quote.change_24h_percent
                else:
                    change_pct = 0.0
            elif polling_quote:  # QuoteError
                line = f"{ticker}: Error"
                change_pct = 0.0
            else:
                line = f"{ticker}: Loading..."
                change_pct = 0.0

            # Determine color class
            if change_pct > 0:
                color_class = "positive"
            elif change_pct < 0:
                color_class = "negative"
            else:
                color_class = "neutral"

            # Add selected class if this is the selected item
            classes = f"watchlist-item {color_class}"
            if i == self._selected_index:
                classes += " selected"

            label = Label(line, classes=classes)
            container.mount(label)

    def _format_quote_line(self, ticker: str, quote: Quote) -> str:
        """Format a single watchlist line with ticker, price, and change.

        Args:
            ticker: The ticker symbol.
            quote: The quote data (StockQuote or CryptoQuote).

        Returns:
            Formatted string for display.
        """
        # Determine price and change based on quote type
        if isinstance(quote, StockQuote):
            # Stock quote
            price = quote.price
            change_pct = quote.change_percent
        else:
            # Crypto quote (isinstance narrowing)
            price = quote.price_usd
            change_pct = quote.change_24h_percent

        # Format price
        price_str = f"${price:,.2f}"

        # Format change with sign
        if change_pct > 0:
            change_str = f"+{change_pct:.2f}%"
        elif change_pct < 0:
            change_str = f"{change_pct:.2f}%"
        else:
            change_str = "0.00%"

        return f"{ticker:8s} {price_str:>12s} {change_str:>8s}"

    def on_ticker_added(self, ticker: str) -> None:
        """Handle a ticker being added to the watchlist.

        Args:
            ticker: The ticker that was added.
        """
        # Subscribe to streaming if active
        if self._streaming_enabled and self._streaming_service:
            self.run_worker(self._streaming_service.subscribe([ticker]))
        # Always refresh polling quotes
        self.run_worker(self.refresh_quotes())

    def on_ticker_removed(self, ticker: str) -> None:
        """Handle a ticker being removed from the watchlist.

        Args:
            ticker: The ticker that was removed.
        """
        # Unsubscribe from streaming if active
        if self._streaming_enabled and self._streaming_service:
            self.run_worker(self._streaming_service.unsubscribe([ticker]))
        # Clean up cached quotes
        if ticker in self._quotes:
            del self._quotes[ticker]
        if ticker in self._streaming_quotes:
            del self._streaming_quotes[ticker]
        self._render_items()

    def action_navigate_down(self) -> None:
        """Navigate down to the next item in the watchlist (j key)."""
        tickers = self._watchlist_manager.get_all()
        if not tickers:
            return

        # Move selection down
        self._selected_index = min(self._selected_index + 1, len(tickers) - 1)
        self._render_items()

    def action_navigate_up(self) -> None:
        """Navigate up to the previous item in the watchlist (k key)."""
        tickers = self._watchlist_manager.get_all()
        if not tickers:
            return

        # Move selection up
        self._selected_index = max(self._selected_index - 1, 0)
        self._render_items()

    def action_select_item(self) -> None:
        """Select the currently highlighted item and emit TickerSelected event."""
        tickers = self._watchlist_manager.get_all()
        if not tickers or self._selected_index >= len(tickers):
            return

        # Get the selected ticker
        selected_ticker = tickers[self._selected_index]

        # Emit the TickerSelected message
        self.post_message(self.TickerSelected(selected_ticker))

    def _on_streaming_quote(self, quote: StreamingQuote) -> None:
        """Callback from StreamingService - runs in same asyncio event loop.

        Args:
            quote: The streaming quote data.
        """
        self._streaming_quotes[quote.symbol] = quote
        # Post message directly - we're in the same event loop as Textual
        self.post_message(self.StreamingQuoteReceived(quote))

    def _on_connection_state_change(self, state: ConnectionState) -> None:
        """Callback from StreamingService when connection state changes.

        Args:
            state: The new connection state.
        """
        self._connection_state = state
        # Update UI directly - we're in the same event loop as Textual
        self._render_items()
        # Also post message for any other listeners (like StatusBar)
        self.post_message(self.StreamingStateChanged(state))

    async def _enable_streaming(self) -> None:
        """Enable real-time streaming mode."""
        if self._streaming_enabled:
            return  # Already enabled

        try:
            self._streaming_service = StreamingService.get_instance()
            # Set flag BEFORE start/subscribe so callbacks see it as enabled
            self._streaming_enabled = True

            await self._streaming_service.start(
                on_quote=self._on_streaming_quote,
                on_state_change=self._on_connection_state_change,
            )

            # Subscribe to all current watchlist tickers
            tickers = self._watchlist_manager.get_all()
            if tickers:
                await self._streaming_service.subscribe(tickers)

            self._render_items()  # Re-render to show [LIVE] header
        except Exception as e:
            # Failed to start - stay in polling mode
            from viper.utils.logger import get_logger

            get_logger().error(f"Failed to enable streaming: {e}")
            self._streaming_enabled = False
            self._streaming_service = None
            # Notify user via app notification if available
            if self.app:
                self.app.notify(
                    "Streaming unavailable - using polling", severity="warning"
                )

    async def _disable_streaming(self) -> None:
        """Disable streaming and return to polling-only mode."""
        if not self._streaming_enabled:
            return  # Already disabled

        if self._streaming_service:
            await self._streaming_service.stop()
            self._streaming_service = None

        self._streaming_enabled = False
        self._streaming_quotes.clear()
        self._connection_state = ConnectionState.DISCONNECTED
        self._render_items()  # Re-render to remove [LIVE] header

    def toggle_streaming(self) -> None:
        """Toggle between polling and streaming modes."""
        if self._streaming_enabled:
            self.run_worker(self._disable_streaming())
        else:
            self.run_worker(self._enable_streaming())

    def _format_streaming_quote_line(
        self, ticker: str, quote: StreamingQuote
    ) -> str:
        """Format a streaming quote for display.

        Args:
            ticker: The ticker symbol.
            quote: The streaming quote data.

        Returns:
            Formatted string for display.
        """
        price_str = f"${quote.price:,.2f}"

        if quote.change_percent > 0:
            change_str = f"+{quote.change_percent:.2f}%"
        elif quote.change_percent < 0:
            change_str = f"{quote.change_percent:.2f}%"
        else:
            change_str = "0.00%"

        return f"{ticker:8s} {price_str:>12s} {change_str:>8s}"

    def on_watchlist_panel_streaming_quote_received(
        self, event: StreamingQuoteReceived
    ) -> None:
        """Handle streaming quote message - re-render display.

        Args:
            event: The StreamingQuoteReceived message.
        """
        self._render_items()

    def on_watchlist_panel_streaming_state_changed(
        self, event: StreamingStateChanged
    ) -> None:
        """Handle connection state change - update header.

        Args:
            event: The StreamingStateChanged message.
        """
        self._connection_state = event.state
        self._render_items()
