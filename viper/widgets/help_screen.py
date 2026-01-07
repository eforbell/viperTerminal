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
                yield Static("j / k                Navigate watchlist items", classes="help-item")
                yield Static("Enter                View selected watchlist item", classes="help-item")
                yield Static("i                    Toggle info panel", classes="help-item")
                yield Static("? / F1               Show this help screen", classes="help-item")
                yield Static("Up / Down            Cycle through command history", classes="help-item")

                # Features Section
                yield Static("\n\nFEATURES", classes="help-section-title")
                yield Static(
                    "• Real-time stock and crypto quotes with intraday charts",
                    classes="help-item",
                )
                yield Static(
                    "• Watchlist with auto-refresh (configurable interval)",
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
