"""Main Textual application for Viper Terminal."""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header

from viper.services.crypto import CryptoError, CryptoQuote
from viper.services.quote import fetch_quote
from viper.services.stock import StockError, StockQuote
from viper.widgets import QuotePanel, TickerInput


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
    """

    # Green on black color theme
    THEME = {
        "background": "#000000",
        "accent": "#00ff00",
        "surface": "#111111",
    }

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        """Initialize the Viper Terminal app."""
        super().__init__()
        self.title = "VIPER TERMINAL"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=False)
        with Container(id="main-container"):
            yield QuotePanel()
        yield TickerInput()
        yield Footer()

    async def on_ticker_input_ticker_lookup(self, event: TickerInput.TickerLookup) -> None:
        """Handle ticker lookup events.

        Args:
            event: The ticker lookup event containing the normalized ticker symbol.
        """
        # Get the quote panel
        quote_panel = self.query_one(QuotePanel)

        # Show loading state
        quote_panel.show_loading()

        # Fetch the quote using unified service (auto-detects stock vs crypto)
        result = await fetch_quote(event.ticker)

        # Display result based on type
        if isinstance(result, (StockQuote, CryptoQuote)):
            quote_panel.show_quote(result)
        elif isinstance(result, (StockError, CryptoError)):
            quote_panel.show_error(result)
