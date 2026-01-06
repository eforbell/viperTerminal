"""Main Textual application for Viper Terminal."""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header

from viper.widgets import TickerInput


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
        yield Container(id="main-container")
        yield TickerInput()
        yield Footer()

    def on_ticker_input_ticker_lookup(self, event: TickerInput.TickerLookup) -> None:
        """Handle ticker lookup events.

        Args:
            event: The ticker lookup event containing the normalized ticker symbol.
        """
        # For now, just log the ticker (future stories will handle actual lookup)
        self.log(f"Looking up ticker: {event.ticker}")
