"""Watchlist panel widget for displaying watched tickers with live prices."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label

from viper.services.quote import Quote, QuoteError, fetch_quote
from viper.services.stock import StockQuote
from viper.services.watchlist import WatchlistManager


class WatchlistPanel(Widget):
    """Panel for displaying watchlist items with prices and changes."""

    # Make the panel focusable
    can_focus = True

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

    def __init__(
        self, watchlist_manager: WatchlistManager, refresh_interval: int = 60
    ) -> None:
        """Initialize the watchlist panel.

        Args:
            watchlist_manager: The watchlist manager instance.
            refresh_interval: Auto-refresh interval in seconds (default: 60).
        """
        super().__init__()
        self._watchlist_manager = watchlist_manager
        self._refresh_interval = refresh_interval
        self._quotes: dict[str, Quote | QuoteError] = {}
        self._refresh_timer_active = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("WATCHLIST", classes="panel-header")
        yield VerticalScroll(id="watchlist-content")

    def on_mount(self) -> None:
        """Start the auto-refresh timer when mounted."""
        self._refresh_timer_active = True
        self.set_interval(self._refresh_interval, self.refresh_quotes)
        self.run_worker(self.refresh_quotes())

    def on_unmount(self) -> None:
        """Stop the refresh timer when unmounted."""
        self._refresh_timer_active = False

    async def refresh_quotes(self) -> None:
        """Fetch updated quotes for all watchlist items."""
        if not self._refresh_timer_active:
            return

        tickers = self._watchlist_manager.get_all()
        if not tickers:
            self._render_items()
            return

        # Fetch quotes for all tickers
        for ticker in tickers:
            result = await fetch_quote(ticker)
            self._quotes[ticker] = result

        self._render_items()

    def _render_items(self) -> None:
        """Render the watchlist items with current quotes."""
        container = self.query_one("#watchlist-content", VerticalScroll)
        container.remove_children()

        tickers = self._watchlist_manager.get_all()

        if not tickers:
            container.mount(Label("No tickers in watchlist", classes="empty-state"))
            return

        for ticker in tickers:
            quote = self._quotes.get(ticker)
            if quote is None:
                # Quote not loaded yet
                line = f"{ticker}: Loading..."
                label = Label(line, classes="watchlist-item neutral")
            elif isinstance(quote, QuoteError):
                # Error fetching quote
                line = f"{ticker}: Error"
                label = Label(line, classes="watchlist-item neutral")
            else:
                # Successful quote
                line = self._format_quote_line(ticker, quote)
                # Apply color class based on change
                if hasattr(quote, "change_percent"):
                    # Stock quote
                    change_pct = quote.change_percent
                elif hasattr(quote, "change_24h_percent"):
                    # Crypto quote
                    change_pct = quote.change_24h_percent
                else:
                    change_pct = 0.0

                if change_pct > 0:
                    color_class = "positive"
                elif change_pct < 0:
                    color_class = "negative"
                else:
                    color_class = "neutral"

                label = Label(line, classes=f"watchlist-item {color_class}")

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
        self.run_worker(self.refresh_quotes())

    def on_ticker_removed(self, ticker: str) -> None:
        """Handle a ticker being removed from the watchlist.

        Args:
            ticker: The ticker that was removed.
        """
        if ticker in self._quotes:
            del self._quotes[ticker]
        self._render_items()
