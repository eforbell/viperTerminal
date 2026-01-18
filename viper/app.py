"""Main Textual application for Viper Terminal."""

from textual.app import App, ComposeResult
from textual.binding import Binding
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
from viper.widgets import ArticleReaderPanel, ChartPanel, HelpScreen, InfoPanel, NewsPanel, OptionsChainPanel, QuotePanel, StatusBar, TickerInput, WatchlistPanel


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

    #news-container {
        width: 70%;
        border: solid $accent;
        padding: 0;
        display: none;
    }

    #news-container:focus-within {
        border: double $accent;
    }

    #article-reader-container {
        width: 70%;
        border: solid $accent;
        padding: 0;
        display: none;
    }

    #article-reader-container:focus-within {
        border: double $accent;
    }

    #options-container {
        width: 70%;
        border: solid $accent;
        padding: 0;
        display: none;
    }

    #options-container:focus-within {
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
        ("n", "toggle_news", "Toggle News"),
        Binding("o", "toggle_options", "Options", show=False),
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
        self._news_panel_visible = False
        self._article_reader_visible = False
        self._options_panel_visible = False
        self._current_ticker: str | None = None
        self._technical_prefix_active = False

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
                with Container(id="news-container"):
                    yield NewsPanel()
                with Container(id="article-reader-container"):
                    yield ArticleReaderPanel()
                with Container(id="options-container"):
                    yield OptionsChainPanel()
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
        # Clear technical prefix if active
        if self._technical_prefix_active:
            self._technical_prefix_active = False
            status_bar = self.query_one(StatusBar)
            status_bar.set_message("")
            return

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
        news_container = self.query_one("#news-container")

        # Toggle visibility
        if self._info_panel_visible:
            # Hide info panel, show quote panel
            info_container.styles.display = "none"
            quote_container.styles.display = "block"
            self._info_panel_visible = False
        else:
            # Hide other panels if visible
            if self._chart_panel_visible:
                chart_container.styles.display = "none"
                self._chart_panel_visible = False
            if self._news_panel_visible:
                news_container.styles.display = "none"
                self._news_panel_visible = False

            # Show info panel, hide quote panel
            quote_container.styles.display = "none"
            info_container.styles.display = "block"
            self._info_panel_visible = True

            # Set focus to info panel
            info_panel = self.query_one(InfoPanel)
            info_panel.focus()

            # If we have a current ticker, fetch and display info
            if self._current_ticker:
                self.run_worker(self._fetch_and_display_info(self._current_ticker))

    def action_toggle_chart(self) -> None:
        """Toggle the chart panel visibility."""
        chart_container = self.query_one("#chart-container")
        quote_container = self.query_one("#quote-container")
        info_container = self.query_one("#info-container")
        news_container = self.query_one("#news-container")

        # Toggle visibility
        if self._chart_panel_visible:
            # Hide chart panel, show quote panel
            chart_container.styles.display = "none"
            quote_container.styles.display = "block"
            self._chart_panel_visible = False
        else:
            # Hide other panels if visible
            if self._info_panel_visible:
                info_container.styles.display = "none"
                self._info_panel_visible = False
            if self._news_panel_visible:
                news_container.styles.display = "none"
                self._news_panel_visible = False

            # Show chart panel, hide quote panel
            quote_container.styles.display = "none"
            chart_container.styles.display = "block"
            self._chart_panel_visible = True

            # Set focus to chart panel
            chart_panel = self.query_one(ChartPanel)
            chart_panel.focus()

            # If we have a current ticker, fetch and display chart
            if self._current_ticker:
                self.run_worker(chart_panel.load_chart(self._current_ticker, "1M"))

    def action_toggle_news(self) -> None:
        """Toggle the news panel visibility."""
        news_container = self.query_one("#news-container")
        quote_container = self.query_one("#quote-container")
        info_container = self.query_one("#info-container")
        chart_container = self.query_one("#chart-container")

        # Toggle visibility
        if self._news_panel_visible:
            # Hide news panel, show quote panel
            news_container.styles.display = "none"
            quote_container.styles.display = "block"
            self._news_panel_visible = False
        else:
            # Hide other panels if visible
            if self._info_panel_visible:
                info_container.styles.display = "none"
                self._info_panel_visible = False
            if self._chart_panel_visible:
                chart_container.styles.display = "none"
                self._chart_panel_visible = False

            # Show news panel, hide quote panel
            quote_container.styles.display = "none"
            news_container.styles.display = "block"
            self._news_panel_visible = True

            # Set focus to news panel
            news_panel = self.query_one(NewsPanel)
            news_panel.focus()

            # If we have a current ticker, fetch and display news
            if self._current_ticker:
                self.run_worker(news_panel.load_news(self._current_ticker))

    def action_toggle_options(self) -> None:
        """Toggle the options panel visibility."""
        options_container = self.query_one("#options-container")
        quote_container = self.query_one("#quote-container")
        info_container = self.query_one("#info-container")
        chart_container = self.query_one("#chart-container")
        news_container = self.query_one("#news-container")

        # Toggle visibility
        if self._options_panel_visible:
            # Hide options panel, show quote panel
            options_container.styles.display = "none"
            quote_container.styles.display = "block"
            self._options_panel_visible = False
        else:
            # Hide other panels if visible
            if self._info_panel_visible:
                info_container.styles.display = "none"
                self._info_panel_visible = False
            if self._chart_panel_visible:
                chart_container.styles.display = "none"
                self._chart_panel_visible = False
            if self._news_panel_visible:
                news_container.styles.display = "none"
                self._news_panel_visible = False

            # Show options panel, hide quote panel
            quote_container.styles.display = "none"
            options_container.styles.display = "block"
            self._options_panel_visible = True

            # Set focus to options panel
            options_panel = self.query_one(OptionsChainPanel)
            options_panel.focus()

            # If we have a current ticker, fetch and display options
            if self._current_ticker:
                current_price = self._get_current_price()
                self.run_worker(options_panel.load_options(self._current_ticker, current_price))
            else:
                # Show empty state when no ticker selected
                options_panel.show_empty()

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


    def action_cycle_ma(self) -> None:
        """Cycle through moving average display modes on the chart panel."""
        # Only cycle MA when chart panel is visible
        if self._chart_panel_visible:
            chart_panel = self.query_one("#chart-container ChartPanel", ChartPanel)
            chart_panel.cycle_ma_display()

    def action_toggle_rsi(self) -> None:
        """Toggle RSI indicator panel on the chart panel."""
        # Only toggle RSI when chart panel is visible
        if self._chart_panel_visible:
            chart_panel = self.query_one("#chart-container ChartPanel", ChartPanel)
            chart_panel.toggle_rsi()

    def action_toggle_macd(self) -> None:
        """Toggle MACD indicator panel on the chart panel."""
        # Only toggle MACD when chart panel is visible
        if self._chart_panel_visible:
            chart_panel = self.query_one("#chart-container ChartPanel", ChartPanel)
            chart_panel.toggle_macd()

    def on_key(self, event: object) -> None:
        """Handle key presses for prefix system routing.

        Args:
            event: The key event from Textual.
        """
        # Import Key type for type checking
        from textual.events import Key

        # Type guard
        if not isinstance(event, Key):
            return

        # Handle 't' key to activate prefix (when not already active)
        if event.key == "t" and not self._technical_prefix_active:
            self._technical_prefix_active = True
            try:
                status_bar = self.query_one(StatusBar)
                status_bar.set_message("Technical: r=RSI, m=MACD, a=MA")
            except Exception:
                # StatusBar not yet mounted, but prefix is still active
                pass
            event.prevent_default()
            event.stop()
            return

        # If technical prefix is active, route to appropriate indicator action
        if self._technical_prefix_active:
            # Clear prefix state
            self._technical_prefix_active = False
            try:
                status_bar = self.query_one(StatusBar)
                status_bar.set_message("")
            except Exception:
                pass

            # Route based on second key
            if event.key == "r":
                # t-r: Toggle RSI
                self.action_toggle_rsi()
                event.prevent_default()
                event.stop()
            elif event.key == "m":
                # t-m: Toggle MACD
                self.action_toggle_macd()
                event.prevent_default()
                event.stop()
            elif event.key == "a":
                # t-a: Cycle MA
                self.action_cycle_ma()
                event.prevent_default()
                event.stop()
            # Any other key: prefix is cleared (no action)

    def on_news_panel_browser_opening(self, event: NewsPanel.BrowserOpening) -> None:
        """Handle browser opening event from news panel.

        Args:
            event: The browser opening event with URL.
        """
        status_bar = self.query_one(StatusBar)
        status_bar.set_message("Opening in browser...")
        self.logger.info(f"Opening news URL: {event.url}")

    async def on_news_panel_article_open_requested(
        self, event: NewsPanel.ArticleOpenRequested
    ) -> None:
        """Handle article open request from news panel.

        Args:
            event: The article open requested event with NewsItem.
        """
        # Hide news panel, show article reader
        news_container = self.query_one("#news-container")
        reader_container = self.query_one("#article-reader-container")

        news_container.display = False
        self._news_panel_visible = False

        reader_container.display = True
        self._article_reader_visible = True

        # Get the article reader panel and show the article
        reader_panel = self.query_one(ArticleReaderPanel)
        await reader_panel.show_article(event.news_item.url)

        # Focus the article reader panel so keybindings work (j/k scroll, Escape to close)
        reader_panel.focus()

        # Update status
        status_bar = self.query_one(StatusBar)
        status_bar.set_message(f"Loading article: {event.news_item.title[:50]}...")
        self.logger.info(f"Opening article reader for: {event.news_item.url}")

    def on_article_reader_panel_close_requested(
        self, event: ArticleReaderPanel.CloseRequested
    ) -> None:
        """Handle close request from article reader panel.

        Args:
            event: The close requested event.
        """
        # Hide article reader, show news panel
        reader_container = self.query_one("#article-reader-container")
        news_container = self.query_one("#news-container")

        reader_container.display = False
        self._article_reader_visible = False

        news_container.display = True
        self._news_panel_visible = True

        # Restore focus to news panel so j/k navigation works
        news_panel = self.query_one(NewsPanel)
        news_panel.focus()

        # Update status
        status_bar = self.query_one(StatusBar)
        status_bar.set_message("Returned to news")
        self.logger.info("Closed article reader")

    def on_article_reader_panel_browser_opening(
        self, event: ArticleReaderPanel.BrowserOpening
    ) -> None:
        """Handle browser opening from article reader panel.

        Args:
            event: The browser opening event with URL.
        """
        status_bar = self.query_one(StatusBar)
        status_bar.set_message("Opening in browser...")
        self.logger.info(f"Opening article URL in browser: {event.url}")

    async def on_watchlist_panel_ticker_selected(
        self, event: WatchlistPanel.TickerSelected
    ) -> None:
        """Handle ticker selection from watchlist.

        Args:
            event: The ticker selected event from the watchlist panel.
        """
        # Trigger a quote lookup for the selected ticker
        await self._fetch_and_display_quote(event.ticker)

        # Also refresh the currently visible panel (chart, news, or options)
        if self._chart_panel_visible and self._current_ticker:
            chart_panel = self.query_one(ChartPanel)
            self.run_worker(chart_panel.load_chart(self._current_ticker, chart_panel._current_period))
        elif self._news_panel_visible and self._current_ticker:
            news_panel = self.query_one(NewsPanel)
            self.run_worker(news_panel.load_news(self._current_ticker))
        elif self._options_panel_visible and self._current_ticker:
            options_panel = self.query_one(OptionsChainPanel)
            current_price = self._get_current_price()
            self.run_worker(options_panel.load_options(self._current_ticker, current_price))

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

        # Also refresh the currently visible panel (chart, news, or options)
        if self._chart_panel_visible and self._current_ticker:
            chart_panel = self.query_one(ChartPanel)
            self.run_worker(chart_panel.load_chart(self._current_ticker, chart_panel._current_period))
        elif self._news_panel_visible and self._current_ticker:
            news_panel = self.query_one(NewsPanel)
            self.run_worker(news_panel.load_news(self._current_ticker))
        elif self._options_panel_visible and self._current_ticker:
            options_panel = self.query_one(OptionsChainPanel)
            current_price = self._get_current_price()
            self.run_worker(options_panel.load_options(self._current_ticker, current_price))

    def _get_current_price(self) -> float | None:
        """Get the current price from the quote panel.

        Returns:
            The current price if available, None otherwise.
        """
        quote_panel = self.query_one(QuotePanel)
        if quote_panel._state != "success" or not quote_panel._quote:
            return None

        # Extract price based on quote type (StockQuote or CryptoQuote)
        if isinstance(quote_panel._quote, StockQuote):
            return quote_panel._quote.price
        elif isinstance(quote_panel._quote, CryptoQuote):
            return quote_panel._quote.price_usd
        else:
            return None

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
