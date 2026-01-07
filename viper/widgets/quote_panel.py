"""Quote panel widget for displaying stock quote information."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator

from viper.services.stock import StockError, StockQuote


class QuotePanel(Widget):
    """Panel for displaying stock quote data with loading and error states."""

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
        self._quote: StockQuote | StockError | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Container(id="quote-content")

    def show_loading(self) -> None:
        """Display loading state with spinner."""
        self._state = "loading"
        self._render_content()

    def show_quote(self, quote: StockQuote) -> None:
        """Display a successful stock quote.

        Args:
            quote: The stock quote data to display.
        """
        self._state = "success"
        self._quote = quote
        self._render_content()

    def show_error(self, error: StockError) -> None:
        """Display an error state.

        Args:
            error: The error information to display.
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
        elif self._state == "error" and isinstance(self._quote, StockError):
            container.mount(
                Label(f"Error: {self._quote.error_message}", classes="error-state")
            )
        elif self._state == "success" and isinstance(self._quote, StockQuote):
            self._render_quote(container, self._quote)

    def _render_quote(self, container: Container, quote: StockQuote) -> None:
        """Render a successful quote display.

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
