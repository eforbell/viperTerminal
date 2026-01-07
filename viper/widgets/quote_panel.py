"""Quote panel widget for displaying stock and crypto quote information."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator

from viper.services.crypto import CryptoError, CryptoQuote
from viper.services.stock import StockError, StockQuote

# Union types for all possible quotes
Quote = StockQuote | CryptoQuote
QuoteError = StockError | CryptoError


class QuotePanel(Widget):
    """Panel for displaying stock quote data with loading and error states."""

    # Make the panel focusable
    can_focus = True

    DEFAULT_CSS = """
    QuotePanel {
        height: 100%;
        width: 100%;
        padding: 1 2;
    }

    QuotePanel Label {
        width: 100%;
    }

    QuotePanel .ticker-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    QuotePanel .price {
        text-style: bold;
        margin-bottom: 1;
    }

    QuotePanel .positive {
        color: #00ff00;
    }

    QuotePanel .negative {
        color: #ff0000;
    }

    QuotePanel .neutral {
        color: $accent;
    }

    QuotePanel .data-row {
        margin-top: 0;
        margin-bottom: 0;
    }

    QuotePanel .empty-state {
        color: #666666;
        text-align: center;
        margin-top: 3;
    }

    QuotePanel .error-state {
        color: #ff0000;
        text-align: center;
        margin-top: 3;
    }

    QuotePanel .loading-container {
        align: center middle;
        height: 100%;
    }
    """

    def __init__(self) -> None:
        """Initialize the quote panel."""
        super().__init__()
        self._state: str = "empty"
        self._quote: Quote | QuoteError | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Container(id="quote-content")

    def show_loading(self) -> None:
        """Display loading state with spinner."""
        self._state = "loading"
        self._render_content()

    def show_quote(self, quote: Quote) -> None:
        """Display a successful quote (stock or crypto).

        Args:
            quote: The quote data to display (StockQuote or CryptoQuote).
        """
        self._state = "success"
        self._quote = quote
        self._render_content()

    def show_error(self, error: QuoteError) -> None:
        """Display an error state.

        Args:
            error: The error information to display (StockError or CryptoError).
        """
        self._state = "error"
        self._quote = error
        self._render_content()

    def show_empty(self) -> None:
        """Display empty state when no ticker is selected."""
        self._state = "empty"
        self._quote = None
        self._render_content()

    def _render_content(self) -> None:
        """Render the appropriate content based on current state."""
        container = self.query_one("#quote-content", Container)
        container.remove_children()

        if self._state == "empty":
            container.mount(Label("No ticker selected", classes="empty-state"))
        elif self._state == "loading":
            # Create loading container with widgets to mount
            loading_indicator = LoadingIndicator()
            loading_label = Label("Loading...")
            loading_container = Container(
                loading_indicator, loading_label, classes="loading-container"
            )
            container.mount(loading_container)
        elif self._state == "error" and isinstance(self._quote, (StockError, CryptoError)):
            container.mount(
                Label(f"Error: {self._quote.error_message}", classes="error-state")
            )
        elif self._state == "success":
            if isinstance(self._quote, StockQuote):
                self._render_stock_quote(container, self._quote)
            elif isinstance(self._quote, CryptoQuote):
                self._render_crypto_quote(container, self._quote)

    def _render_stock_quote(self, container: Container, quote: StockQuote) -> None:
        """Render a successful stock quote display.

        Args:
            container: The container to mount widgets into.
            quote: The stock quote to display.
        """
        # Determine color based on change
        if quote.change > 0:
            price_class = "price positive"
            change_sign = "+"
        elif quote.change < 0:
            price_class = "price negative"
            change_sign = ""  # Negative sign is already in the number
        else:
            price_class = "price neutral"
            change_sign = ""

        # Format numbers with proper decimals and commas
        price_str = f"${self._format_number(quote.price, 2)}"
        change_str = f"{change_sign}${self._format_number(abs(quote.change), 2)}"
        change_pct_str = f"({change_sign}{self._format_number(abs(quote.change_percent), 2)}%)"

        # Ticker header with name if available
        header_text = f"{quote.ticker} - {quote.name}" if quote.name else quote.ticker
        container.mount(Label(header_text, classes="ticker-header"))

        # Price with change
        price_line = f"{price_str}  {change_str} {change_pct_str}"
        price_label = Label(price_line, classes=price_class)
        container.mount(price_label)

        # Additional data rows
        container.mount(Label("", classes="data-row"))  # Spacing

        # Volume
        volume_str = self._format_number(quote.volume, 0)
        container.mount(Label(f"Volume: {volume_str}", classes="data-row"))

        # Market cap
        market_cap_str = self._format_number(quote.market_cap, 0)
        container.mount(Label(f"Market Cap: ${market_cap_str}", classes="data-row"))

        # 52-week range
        high_52w_str = f"${self._format_number(quote.high_52w, 2)}"
        low_52w_str = f"${self._format_number(quote.low_52w, 2)}"
        container.mount(
            Label(f"52W Range: {low_52w_str} - {high_52w_str}", classes="data-row")
        )

    def _render_crypto_quote(self, container: Container, quote: CryptoQuote) -> None:
        """Render a successful crypto quote display.

        Args:
            container: The container to mount widgets into.
            quote: The crypto quote to display.
        """
        # Determine color based on 24h change
        if quote.change_24h_percent > 0:
            price_class = "price positive"
            change_sign = "+"
        elif quote.change_24h_percent < 0:
            price_class = "price negative"
            change_sign = ""  # Negative sign is already in the number
        else:
            price_class = "price neutral"
            change_sign = ""

        # Format price and change percentage
        price_str = f"${self._format_number(quote.price_usd, 2)}"
        change_pct_str = (
            f"({change_sign}{self._format_number(abs(quote.change_24h_percent), 2)}%)"
        )

        # Header with name if available
        header_text = f"{quote.symbol} - {quote.name}" if quote.name else quote.symbol
        container.mount(Label(header_text, classes="ticker-header"))

        # Price with 24h change
        price_line = f"{price_str}  24h {change_pct_str}"
        price_label = Label(price_line, classes=price_class)
        container.mount(price_label)

        # Additional data rows
        container.mount(Label("", classes="data-row"))  # Spacing

        # 24h Volume
        volume_str = self._format_number(quote.volume_24h_usd, 0)
        container.mount(Label(f"24h Volume: ${volume_str}", classes="data-row"))

        # Market cap
        market_cap_str = self._format_number(quote.market_cap_usd, 0)
        container.mount(Label(f"Market Cap: ${market_cap_str}", classes="data-row"))

    def _format_number(self, value: float, decimals: int) -> str:
        """Format a number with commas and specified decimal places.

        Args:
            value: The number to format.
            decimals: Number of decimal places.

        Returns:
            Formatted number string with commas for thousands.
        """
        if decimals == 0:
            return f"{int(value):,}"
        return f"{value:,.{decimals}f}"
