"""Main Textual application for Viper Terminal."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header

from viper.config import load_config
from viper.services.crypto import CryptoError, CryptoInfo, CryptoInfoError, CryptoQuote, fetch_crypto_info
from viper.services.history import HistoryManager
from viper.services.quote import fetch_quote, is_crypto_quote
from viper.services.stock import StockError, StockInfo, StockInfoError, StockQuote, fetch_stock_info
from viper.services.watchlist import WatchlistManager
from viper.utils import (
    format_error_message,
    get_logger,
    is_first_run,
    is_network_error,
    mark_first_run_complete,
    setup_logging,
)
from viper.widgets import ChartPanel, HelpScreen, InfoPanel, QuotePanel, StatusBar, TickerInput, WatchlistPanel


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

    StatusBar {
        dock: bottom;
        height: 1;
        background: $background;
        color: $accent;
        padding: 0 2;
    }

    StatusBar Horizontal {
        width: 100%;
        height: 1;
    }

    StatusBar Label {
        width: 1fr;
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

    #info-container {
        width: 70%;
        border: solid $accent;
        padding: 1;
        display: none;
    }

    #info-container:focus-within {
        border: double $accent;
    }

    #chart-container {
        width: 70%;
        border: solid $accent;
        padding: 0;
        display: none;
    }

    #chart-container:focus-within {
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
        ("slash", "focus_input", "Focus Input"),
        ("escape", "clear_or_close", "Clear/Close"),
        ("i", "toggle_info", "Toggle Info"),
        ("c", "toggle_chart", "Toggle Chart"),
        ("1", "timeframe_1", "1W"),
        ("2", "timeframe_2", "1M"),
        ("3", "timeframe_3", "3M"),
        ("4", "timeframe_4", "6M"),
        ("5", "timeframe_5", "1Y"),
        ("6", "timeframe_6", "5Y"),
        ("7", "timeframe_7", "MAX"),
        ("question_mark,f1", "show_help", "Help"),
    ]

    def __init__(self) -> None:
        """Initialize the Viper Terminal app."""
        super().__init__()
        self.title = "VIPER TERMINAL"

        # Set up logging
        setup_logging()
        self.logger = get_logger()

        # Load configuration
        self.config = load_config()
        self.logger.info(f"Using refresh interval: {self.config.refresh_interval}s")

        # Initialize managers
        self.history_manager = HistoryManager()
        self.watchlist_manager = WatchlistManager()

        # Load default watchlist from config if provided
        for ticker in self.config.default_watchlist:
            self.watchlist_manager.add(ticker)

        self._info_panel_visible = False
        self._chart_panel_visible = False
        self._current_ticker: str | None = None

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
                        refresh_interval=self.config.refresh_interval,
                    )
                with Container(id="quote-container"):
                    yield QuotePanel()
                with Container(id="info-container"):
                    yield InfoPanel()
                with Container(id="chart-container"):
                    yield ChartPanel()
        yield TickerInput(history_manager=self.history_manager)
        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is first mounted."""
        # Set initial focus to the ticker input
        self.query_one(TickerInput).focus()
        
        # Check if this is the first run and show welcome screen
        if is_first_run():
            self.push_screen(HelpScreen(is_welcome=True))
            mark_first_run_complete()

    def action_focus_input(self) -> None:
        """Focus the ticker input bar."""
        ticker_input = self.query_one(TickerInput)
        ticker_input.focus()

    def action_clear_or_close(self) -> None:
        """Clear input or close overlays when Escape is pressed."""
        # Get the ticker input widget
        ticker_input = self.query_one(TickerInput)

        # If input has text, clear it
        if ticker_input.value:
            ticker_input.value = ""
            ticker_input.remove_class("error")
        # Otherwise, could close overlays in the future (for VPR-015)

    def action_show_help(self) -> None:
        """Show the help screen."""
        self.push_screen(HelpScreen(is_welcome=False))

    def action_toggle_info(self) -> None:
        """Toggle the info panel visibility."""
        info_container = self.query_one("#info-container")
        quote_container = self.query_one("#quote-container")
        chart_container = self.query_one("#chart-container")

        # Toggle visibility
        if self._info_panel_visible:
            # Hide info panel, show quote panel
            info_container.styles.display = "none"
            quote_container.styles.display = "block"
            self._info_panel_visible = False
        else:
            # Hide chart panel if visible
            if self._chart_panel_visible:
                chart_container.styles.display = "none"
                self._chart_panel_visible = False

            # Show info panel, hide quote panel
            quote_container.styles.display = "none"
            info_container.styles.display = "block"
            self._info_panel_visible = True

            # If we have a current ticker, fetch and display info
            if self._current_ticker:
                self.run_worker(self._fetch_and_display_info(self._current_ticker))

    def action_toggle_chart(self) -> None:
        """Toggle the chart panel visibility."""
        chart_container = self.query_one("#chart-container")
        quote_container = self.query_one("#quote-container")
        info_container = self.query_one("#info-container")

        # Toggle visibility
        if self._chart_panel_visible:
            # Hide chart panel, show quote panel
            chart_container.styles.display = "none"
            quote_container.styles.display = "block"
            self._chart_panel_visible = False
        else:
            # Hide info panel if visible
            if self._info_panel_visible:
                info_container.styles.display = "none"
                self._info_panel_visible = False

            # Show chart panel, hide quote panel
            quote_container.styles.display = "none"
            chart_container.styles.display = "block"
            self._chart_panel_visible = True

            # If we have a current ticker, fetch and display chart
            if self._current_ticker:
                chart_panel = self.query_one(ChartPanel)
                self.run_worker(chart_panel.load_chart(self._current_ticker, "1M"))

    def _change_chart_timeframe(self, key: str) -> None:
        """Change the chart timeframe if chart panel is visible.

        Args:
            key: The number key pressed (1-7)
        """
        # Only change timeframe if chart panel is visible
        if self._chart_panel_visible:
            chart_panel = self.query_one(ChartPanel)
            period = chart_panel.get_timeframe_for_key(key)
            if period:
                self.run_worker(chart_panel.change_timeframe(period))

    def action_timeframe_1(self) -> None:
        """Change chart timeframe to 1W."""
        self._change_chart_timeframe("1")

    def action_timeframe_2(self) -> None:
        """Change chart timeframe to 1M."""
        self._change_chart_timeframe("2")

    def action_timeframe_3(self) -> None:
        """Change chart timeframe to 3M."""
        self._change_chart_timeframe("3")

    def action_timeframe_4(self) -> None:
        """Change chart timeframe to 6M."""
        self._change_chart_timeframe("4")

    def action_timeframe_5(self) -> None:
        """Change chart timeframe to 1Y."""
        self._change_chart_timeframe("5")

    def action_timeframe_6(self) -> None:
        """Change chart timeframe to 5Y."""
        self._change_chart_timeframe("6")

    def action_timeframe_7(self) -> None:
        """Change chart timeframe to MAX."""
        self._change_chart_timeframe("7")

    async def on_watchlist_panel_ticker_selected(
        self, event: WatchlistPanel.TickerSelected
    ) -> None:
        """Handle ticker selection from watchlist.

        Args:
            event: The ticker selected event from the watchlist panel.
        """
        # Trigger a quote lookup for the selected ticker
        await self._fetch_and_display_quote(event.ticker)

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
        await self._fetch_and_display_quote(ticker)

    async def _fetch_and_display_quote(self, ticker: str) -> None:
        """Fetch and display a quote for the given ticker.

        Args:
            ticker: The ticker symbol to fetch.
        """
        # Get the quote panel and status bar
        quote_panel = self.query_one(QuotePanel)
        status_bar = self.query_one(StatusBar)

        # Show loading state
        quote_panel.show_loading()

        try:
            # Fetch the quote using unified service (auto-detects stock vs crypto)
            result = await fetch_quote(ticker)

            # Display result based on type
            if isinstance(result, (StockQuote, CryptoQuote)):
                quote_panel.show_quote(result)
                # Store current ticker for info panel
                self._current_ticker = ticker
                # Update status bar
                status_bar.set_online()
                status_bar.update_last_refresh()
                # Log successful fetch
                self.logger.info(f"Successfully fetched quote for {ticker}")
            elif isinstance(result, (StockError, CryptoError)):
                # Format error message for display
                formatted_error = format_error_message(result)
                # Create a new error with the formatted message
                display_error: StockError | CryptoError
                if isinstance(result, StockError):
                    display_error = StockError(result.ticker, formatted_error)
                else:
                    display_error = CryptoError(result.symbol, formatted_error)

                quote_panel.show_error(display_error)
                self._current_ticker = None

                # Update status bar based on error type
                if is_network_error(result):
                    status_bar.set_offline()
                else:
                    status_bar.set_online()

                # Log the error
                self.logger.error(f"Error fetching quote for {ticker}: {result.error_message}")

        except Exception as e:
            # Handle unexpected errors
            formatted_error = format_error_message(e)
            error = StockError(ticker, formatted_error)
            quote_panel.show_error(error)
            self._current_ticker = None

            # Update status bar
            if is_network_error(e):
                status_bar.set_offline()
            else:
                status_bar.set_online()

            # Log the exception
            self.logger.exception(f"Unexpected error fetching quote for {ticker}: {e}")

    async def _fetch_and_display_info(self, ticker: str) -> None:
        """Fetch and display extended info for the given ticker.

        Args:
            ticker: The ticker symbol to fetch info for.
        """
        # Get the info panel
        info_panel = self.query_one(InfoPanel)

        try:
            # Fetch the quote first to determine asset type
            quote_result = await fetch_quote(ticker)

            # Determine if it's crypto or stock and fetch appropriate info
            if isinstance(quote_result, CryptoQuote):
                # Fetch crypto info
                crypto_info_result = await fetch_crypto_info(ticker)
                if isinstance(crypto_info_result, CryptoInfo):
                    info_panel.show_crypto_info(quote_result, crypto_info_result.info)
                    self.logger.info(f"Successfully fetched crypto info for {ticker}")
                else:
                    # Error - show empty state
                    info_panel.show_empty()
                    self.logger.error(
                        f"Error fetching crypto info for {ticker}: {crypto_info_result.error_message}"
                    )
            elif isinstance(quote_result, StockQuote):
                # Fetch stock info
                stock_info_result = await fetch_stock_info(ticker)
                if isinstance(stock_info_result, StockInfo):
                    info_panel.show_stock_info(quote_result, stock_info_result.info)
                    self.logger.info(f"Successfully fetched stock info for {ticker}")
                else:
                    # Error - show empty state
                    info_panel.show_empty()
                    self.logger.error(
                        f"Error fetching stock info for {ticker}: {stock_info_result.error_message}"
                    )
            else:
                # Error fetching quote - show empty state
                info_panel.show_empty()
                self.logger.error(f"Error fetching quote for info panel for {ticker}")

        except Exception as e:
            # Handle unexpected errors
            info_panel.show_empty()
            self.logger.exception(f"Unexpected error fetching info for {ticker}: {e}")
