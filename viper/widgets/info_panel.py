"""Info panel widget for displaying extended asset metadata."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label, Static

from viper.services.crypto import CryptoQuote
from viper.services.stock import StockQuote


class InfoPanel(Static):
    """Panel displaying extended metadata about stocks or crypto assets."""

    can_focus = True

    def __init__(self) -> None:
        """Initialize the InfoPanel."""
        super().__init__()
        self._current_quote: StockQuote | CryptoQuote | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the panel."""
        # Use VerticalScroll for scrollable content
        with VerticalScroll(id="info-scroll"):
            yield Label("No asset selected", id="info-content")

    def show_stock_info(self, quote: StockQuote, info: dict[str, object]) -> None:
        """
        Display extended information for a stock.

        Args:
            quote: The stock quote data
            info: Extended metadata dictionary from yfinance
        """
        self._current_quote = quote

        # Extract metadata with safe defaults
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        description = info.get("longBusinessSummary", "No description available")
        website = info.get("website", "N/A")
        employees = info.get("fullTimeEmployees", "N/A")

        # Format employees with commas if it's a number
        if isinstance(employees, int):
            employees_str = f"{employees:,}"
        else:
            employees_str = str(employees)

        # Build info text
        content = f"""[bold]{quote.name or quote.ticker}[/bold]
[dim]Ticker:[/dim] {quote.ticker}

[dim]Sector:[/dim] {sector}
[dim]Industry:[/dim] {industry}
[dim]Employees:[/dim] {employees_str}
[dim]Website:[/dim] {website}

[dim]Description:[/dim]
{description}
"""

        # Update the content
        self._update_content(content)

    def show_crypto_info(self, quote: CryptoQuote, info: dict[str, object]) -> None:
        """
        Display extended information for a crypto asset.

        Args:
            quote: The crypto quote data
            info: Extended metadata dictionary from CoinGecko
        """
        self._current_quote = quote

        # Extract metadata with safe defaults
        description_dict = info.get("description", {})
        if isinstance(description_dict, dict):
            description = description_dict.get("en", "No description available")
        else:
            description = "No description available"

        links = info.get("links", {})
        if isinstance(links, dict):
            homepage = links.get("homepage", [])
            if isinstance(homepage, list) and homepage:
                website = homepage[0] if homepage[0] else "N/A"
            else:
                website = "N/A"
        else:
            website = "N/A"

        genesis_date = info.get("genesis_date", "N/A")

        # Build info text
        content = f"""[bold]{quote.name or quote.symbol}[/bold]
[dim]Symbol:[/dim] {quote.symbol}

[dim]Genesis Date:[/dim] {genesis_date}
[dim]Website:[/dim] {website}

[dim]Description:[/dim]
{description}
"""

        # Update the content
        self._update_content(content)

    def show_empty(self) -> None:
        """Display empty state when no asset is selected."""
        self._current_quote = None
        self._update_content("No asset selected")

    def _update_content(self, text: str) -> None:
        """
        Update the panel content.

        Args:
            text: The text content to display
        """
        try:
            scroll = self.query_one("#info-scroll", VerticalScroll)
            scroll.remove_children()
            scroll.mount(Label(text, id="info-content"))
        except Exception:
            # Panel not yet mounted
            pass
