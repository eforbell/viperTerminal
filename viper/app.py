"""Main Textual application for Viper Terminal."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header

from viper.services.crypto import CryptoError, CryptoQuote
from viper.services.history import HistoryManager
from viper.services.quote import fetch_quote
from viper.services.stock import StockError, StockQuote
from viper.services.watchlist import WatchlistManager
from viper.widgets import QuotePanel, TickerInput, WatchlistPanel


class ViperApp(App[None]):
    """A Bloomberg-like terminal for stocks and crypto quotes."""

    CSS = """
    Screen {
        background: $background;
    }

    Header {
        background: $background;
        color: $accent;
        text-style: bold;
    }

    Footer {
        background: $background;
        color: $accent;
    }

    TickerInput {
        dock: bottom;
        margin: 1 2;
        border: solid $accent;
    }

    TickerInput.error {
        border: solid red;
    }

    #main-container {
        height: 1fr;
    }

    #main-layout {
        height: 100%;
        width: 100%;
    }

    #watchlist-container {
        width: 30%;
        border: solid $accent;
        padding: 0;
    }

    #watchlist-container:focus-within {
        border: double $accent;
    }

    #quote-container {
        width: 70%;
        border: solid $accent;
        padding: 0;
    }

    #quote-container:focus-within {
        border: double $accent;
    }
    """

    # Green on black color theme
    THEME = {
        "background": "#000000",
        "accent": "#00ff00",
        "surface": "#111111",
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("tab", "focus_next", "Next Panel"),
    ]

    def __init__(self) -> None:
        """Initialize the Viper Terminal app."""
        super().__init__()
        self.title = "VIPER TERMINAL"
        self.history_manager = HistoryManager()
        self.watchlist_manager = WatchlistManager()

    def on_resize(self, event: object) -> None:
        """Handle terminal resize to show/hide watchlist on narrow screens.

        Args:
            event: The resize event (not used, but required by Textual).
        """
        # Get terminal width
        width = self.size.width

        # Get watchlist container
        try:
            watchlist_container = self.query_one("#watchlist-container")
            quote_container = self.query_one("#quote-container")
        except Exception:
            # Containers not yet mounted
            return

        # Hide watchlist on narrow terminals (< 80 columns)
        if width < 80:
            watchlist_container.display = False
            quote_container.styles.width = "100%"
        else:
            watchlist_container.display = True
            quote_container.styles.width = "70%"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=False)
        with Container(id="main-container"):
            with Horizontal(id="main-layout"):
                with Container(id="watchlist-container"):
                    yield WatchlistPanel(
                        watchlist_manager=self.watchlist_manager,
                        refresh_interval=60,
                    )
                with Container(id="quote-container"):
                    yield QuotePanel()
        yield TickerInput(history_manager=self.history_manager)
        yield Footer()

    async def on_ticker_input_ticker_lookup(self, event: TickerInput.TickerLookup) -> None:
        """Handle ticker lookup events.

        Args:
            event: The ticker lookup event containing the normalized ticker symbol.
        """
        ticker = event.ticker

        # Check for watchlist commands: 'w TICKER' to add, 'd TICKER' to remove
        if ticker.startswith("W "):
            # Add to watchlist
            ticker_to_add = ticker[2:].strip()
            if ticker_to_add:
                self.watchlist_manager.add(ticker_to_add)
                # Notify watchlist panel to refresh
                watchlist_panel = self.query_one(WatchlistPanel)
                watchlist_panel.on_ticker_added(ticker_to_add)
            return

        if ticker.startswith("D "):
            # Remove from watchlist
            ticker_to_remove = ticker[2:].strip()
            if ticker_to_remove:
                self.watchlist_manager.remove(ticker_to_remove)
                # Notify watchlist panel to refresh
                watchlist_panel = self.query_one(WatchlistPanel)
                watchlist_panel.on_ticker_removed(ticker_to_remove)
            return

        # Regular quote lookup
        # Get the quote panel
        quote_panel = self.query_one(QuotePanel)

        # Show loading state
        quote_panel.show_loading()

        # Fetch the quote using unified service (auto-detects stock vs crypto)
        result = await fetch_quote(ticker)

        # Display result based on type
        if isinstance(result, (StockQuote, CryptoQuote)):
            quote_panel.show_quote(result)
        elif isinstance(result, (StockError, CryptoError)):
            quote_panel.show_error(result)
