"""Help screen modal for displaying commands and keybindings."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class HelpScreen(ModalScreen[None]):
    """Modal screen displaying help information and keybindings."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $panel;
        border: double $accent;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #help-content {
        height: auto;
        max-height: 70%;
    }

    .help-section {
        margin-top: 1;
        margin-bottom: 1;
    }

    .help-section-title {
        text-style: bold underline;
        color: #00ff00;
        margin-bottom: 1;
    }

    .help-item {
        margin-left: 2;
    }

    #help-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, is_welcome: bool = False) -> None:
        """Initialize the help screen.

        Args:
            is_welcome: If True, display as welcome screen for first-run experience.
        """
        super().__init__()
        self.is_welcome = is_welcome

    def compose(self) -> ComposeResult:
        """Compose the help screen."""
        with Container(id="help-dialog"):
            title = "Welcome to VIPER TERMINAL" if self.is_welcome else "VIPER TERMINAL - Help"
            yield Label(title, id="help-title")

            if self.is_welcome:
                yield Label(
                    "\nThank you for using Viper Terminal!\n"
                    "Your personal Bloomberg-like terminal for stocks and crypto.\n",
                    id="help-welcome-message",
                )

            with VerticalScroll(id="help-content"):
                # Commands Section
                yield Static("COMMANDS", classes="help-section-title")
                yield Static(
                    "TICKER                Look up a stock or crypto quote (e.g., AAPL, BTC)",
                    classes="help-item",
                )
                yield Static(
                    "TICKER:STOCK         Force stock lookup (e.g., AAPL:STOCK)",
                    classes="help-item",
                )
                yield Static(
                    "TICKER:CRYPTO        Force crypto lookup (e.g., BTC:CRYPTO)",
                    classes="help-item",
                )
                yield Static(
                    "W TICKER             Add ticker to watchlist (e.g., W AAPL)",
                    classes="help-item",
                )
                yield Static(
                    "D TICKER             Remove ticker from watchlist (e.g., D AAPL)",
                    classes="help-item",
                )

                # Keybindings Section
                yield Static("\n\nKEYBINDINGS", classes="help-section-title")
                yield Static("q                    Quit application", classes="help-item")
                yield Static("/                    Focus input bar", classes="help-item")
                yield Static("Esc                  Clear input / Close overlays", classes="help-item")
                yield Static("Tab                  Cycle between panels", classes="help-item")
                yield Static("j / k                Navigate list items", classes="help-item")
                yield Static("Enter                Read article / Select item", classes="help-item")
                yield Static("i                    Toggle info panel", classes="help-item")
                yield Static("c                    Toggle chart panel (or view calls in options)", classes="help-item")
                yield Static("n                    Toggle news panel", classes="help-item")
                yield Static("o                    Toggle options panel (or open in browser in news/article)", classes="help-item")
                yield Static("p                    View puts in options panel", classes="help-item")
                yield Static("f                    Cycle filter in options (All/ITM/OTM)", classes="help-item")
                yield Static("t                    Technical indicator prefix (press t, then indicator key)", classes="help-item")
                yield Static("  t-r                Toggle RSI indicator", classes="help-item")
                yield Static("  t-m                Toggle MACD indicator", classes="help-item")
                yield Static("  t-a                Cycle moving averages (Off/SMA20/SMA50/Both)", classes="help-item")
                yield Static("v                    Toggle chart view (Line/Candlestick)", classes="help-item")
                yield Static("r                    Refresh chart data (manual refresh)", classes="help-item")
                yield Static("s                    Toggle real-time streaming mode (watchlist)", classes="help-item")
                yield Static("e                    Expand news item (show summary)", classes="help-item")
                yield Static("1-7                  Select timeframe (chart)", classes="help-item")
                yield Static("? / F1               Show this help screen", classes="help-item")
                yield Static("Up / Down            Cycle through command history", classes="help-item")

                # Charts Section
                yield Static("\n\nCHARTS", classes="help-section-title")
                yield Static(
                    "Press 'c' to toggle the historical price chart panel.",
                    classes="help-item",
                )
                yield Static(
                    "Press 'v' to toggle between line chart and candlestick view.",
                    classes="help-item",
                )
                yield Static(
                    "Use number keys 1-7 to select timeframe:",
                    classes="help-item",
                )
                yield Static(
                    "  1=1W  2=1M  3=3M  4=6M  5=1Y  6=5Y  7=MAX",
                    classes="help-item",
                )
                yield Static(
                    "Candlestick view shows open/high/low/close (OHLC) data per period.",
                    classes="help-item",
                )
                yield Static(
                    "Volume bars are always shown below the price chart.",
                    classes="help-item",
                )
                yield Static(
                    "Technical indicators use prefix keys: press 't' first, then indicator key.",
                    classes="help-item",
                )
                yield Static(
                    "Press 't-a' to cycle moving averages: Off -> SMA20 -> SMA50 -> Both.",
                    classes="help-item",
                )
                yield Static(
                    "Press 't-r' to toggle RSI (Relative Strength Index) indicator panel.",
                    classes="help-item",
                )
                yield Static(
                    "Press 't-m' to toggle MACD (Moving Average Convergence Divergence) indicator.",
                    classes="help-item",
                )
                yield Static(
                    "MACD shows trend direction: cyan MACD line, yellow Signal line, green/red Histogram.",
                    classes="help-item",
                )
                yield Static(
                    "Crossovers between MACD and Signal indicate potential trend changes.",
                    classes="help-item",
                )
                yield Static(
                    "Both RSI and MACD can be visible simultaneously (stacked vertically).",
                    classes="help-item",
                )
                yield Static(
                    "Press 'r' to manually refresh chart data (useful after resize or sleep).",
                    classes="help-item",
                )
                yield Static(
                    "Charts support both stocks and crypto via yfinance.",
                    classes="help-item",
                )

                # News Section
                yield Static("\n\nNEWS", classes="help-section-title")
                yield Static(
                    "Press 'n' to toggle the news panel for the current ticker.",
                    classes="help-item",
                )
                yield Static(
                    "Use j/k to navigate news headlines, Enter to read in terminal.",
                    classes="help-item",
                )
                yield Static(
                    "Press 'o' to open article in browser instead.",
                    classes="help-item",
                )
                yield Static(
                    "Press 'e' to expand a news item and view its summary.",
                    classes="help-item",
                )
                yield Static(
                    "News powered by yfinance - displays recent headlines and summaries.",
                    classes="help-item",
                )

                # Options Section
                yield Static("\n\nOPTIONS", classes="help-section-title")
                yield Static(
                    "Press 'o' to toggle the options panel for the current ticker.",
                    classes="help-item",
                )
                yield Static(
                    "Use j/k to navigate through option contracts (strike prices).",
                    classes="help-item",
                )
                yield Static(
                    "Use PgUp/PgDn to jump 10 items at a time.",
                    classes="help-item",
                )
                yield Static(
                    "Use [ / ] to cycle through expiration dates.",
                    classes="help-item",
                )
                yield Static(
                    "Press 'c' to view calls, 'p' to view puts.",
                    classes="help-item",
                )
                yield Static(
                    "Press 'f' to cycle filter mode: All -> ITM -> OTM -> All.",
                    classes="help-item",
                )
                yield Static(
                    "Press 'a' to jump to the at-the-money (ATM) strike.",
                    classes="help-item",
                )
                yield Static(
                    "Press 's' to toggle summary view (ATM strikes for multiple expirations).",
                    classes="help-item",
                )
                yield Static(
                    "In summary view, press Enter to view full chain for selected expiration.",
                    classes="help-item",
                )
                yield Static(
                    "ITM (In The Money) contracts are highlighted in green.",
                    classes="help-item",
                )
                yield Static(
                    "ATM (At The Money) strikes are highlighted in cyan.",
                    classes="help-item",
                )
                yield Static(
                    "View strike, bid, ask, last price, volume, OI, IV, and ITM status.",
                    classes="help-item",
                )

                # Article Reader Section
                yield Static("\n\nARTICLE READER", classes="help-section-title")
                yield Static(
                    "Press Enter on a news item to read the full article in the terminal.",
                    classes="help-item",
                )
                yield Static(
                    "Keybindings in article reader:",
                    classes="help-item",
                )
                yield Static(
                    "  Esc / q            Close reader and return to news",
                    classes="help-item",
                )
                yield Static(
                    "  j / k              Scroll line by line",
                    classes="help-item",
                )
                yield Static(
                    "  PageUp / PageDown  Scroll page by page",
                    classes="help-item",
                )
                yield Static(
                    "  Home / End         Jump to top / bottom",
                    classes="help-item",
                )
                yield Static(
                    "  o                  Open in browser",
                    classes="help-item",
                )
                yield Static(
                    "  r                  Retry fetching article",
                    classes="help-item",
                )
                yield Static(
                    "Clean, distraction-free reading without leaving the terminal.",
                    classes="help-item",
                )

                # Features Section
                yield Static("\n\nFEATURES", classes="help-section-title")
                yield Static(
                    "• Real-time stock and crypto quotes with intraday charts",
                    classes="help-item",
                )
                yield Static(
                    "• Historical price charts with multiple timeframes",
                    classes="help-item",
                )
                yield Static(
                    "• Volume overlay for price/volume correlation",
                    classes="help-item",
                )
                yield Static(
                    "• Technical indicators: Moving Averages (SMA), RSI, MACD",
                    classes="help-item",
                )
                yield Static(
                    "• News feed with headlines and browser integration",
                    classes="help-item",
                )
                yield Static(
                    "• In-app article reader for distraction-free reading",
                    classes="help-item",
                )
                yield Static(
                    "• Options chain data with navigable table of calls and puts",
                    classes="help-item",
                )
                yield Static(
                    "• Watchlist with auto-refresh (configurable interval)",
                    classes="help-item",
                )
                yield Static(
                    "• Real-time streaming mode for watchlist (press 's' to toggle)",
                    classes="help-item",
                )
                yield Static(
                    "• Command history for quick access to recent lookups",
                    classes="help-item",
                )
                yield Static(
                    "• Extended info panel with company/asset details",
                    classes="help-item",
                )
                yield Static(
                    "• Persistent configuration via ~/.config/viper/config.toml",
                    classes="help-item",
                )

            footer_text = (
                "Press Enter or Esc to continue..."
                if self.is_welcome
                else "Press Enter or Esc to close"
            )
            yield Label(footer_text, id="help-footer")

    def on_key(self, event: object) -> None:
        """Handle key presses."""
        from textual.events import Key

        if isinstance(event, Key):
            if event.key in ("enter", "escape"):
                self.dismiss()
