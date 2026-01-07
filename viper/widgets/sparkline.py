"""Sparkline widget for displaying ASCII line charts."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label


class SparklineWidget(Widget):
    """Widget that renders an ASCII sparkline chart from price data."""

    DEFAULT_CSS = """
    SparklineWidget {
        height: auto;
        width: 100%;
        padding: 0;
    }

    SparklineWidget Label {
        width: 100%;
        margin: 0;
    }

    SparklineWidget .sparkline-label {
        color: #666666;
        margin-bottom: 0;
    }

    SparklineWidget .sparkline-chart {
        color: $accent;
        margin-top: 0;
        margin-bottom: 0;
    }

    SparklineWidget .no-data {
        color: #666666;
        margin-top: 0;
    }
    """

    def __init__(
        self, prices: list[float] | None = None, label: str = "", width: int = 60
    ) -> None:
        """Initialize the sparkline widget.

        Args:
            prices: List of price values to render. None shows "No data" state.
            label: Label to display above the chart (e.g., "Intraday (1d, 5m)").
            width: Width of the chart in characters.
        """
        super().__init__()
        self._prices = prices
        self._label = label
        self._width = width

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        if self._label:
            yield Label(self._label, classes="sparkline-label")

        if self._prices is None or len(self._prices) == 0:
            yield Label("No data", classes="no-data")
        else:
            chart = self._render_sparkline(self._prices, self._width)
            yield Label(chart, classes="sparkline-chart")

    def update_data(self, prices: list[float] | None, label: str = "") -> None:
        """Update the sparkline with new data.

        Args:
            prices: New list of price values. None shows "No data" state.
            label: New label text.
        """
        self._prices = prices
        self._label = label
        self._refresh_chart()

    def _refresh_chart(self) -> None:
        """Re-render the chart with current data."""
        # Remove all children and recreate
        self.remove_children()
        if self._label:
            self.mount(Label(self._label, classes="sparkline-label"))

        if self._prices is None or len(self._prices) == 0:
            self.mount(Label("No data", classes="no-data"))
        else:
            chart = self._render_sparkline(self._prices, self._width)
            self.mount(Label(chart, classes="sparkline-chart"))

    def _render_sparkline(self, prices: list[float], width: int) -> str:
        """Render an ASCII sparkline chart from price data.

        Args:
            prices: List of price values to render.
            width: Width of the chart in characters.

        Returns:
            ASCII art string representing the sparkline.
        """
        if not prices or len(prices) == 0:
            return ""

        # If we have more data points than width, downsample
        if len(prices) > width:
            # Simple downsampling: take evenly spaced points
            step = len(prices) / width
            downsampled = [prices[int(i * step)] for i in range(width)]
            prices = downsampled

        # Normalize prices to fit in 8 vertical levels (using Unicode block chars)
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price

        if price_range == 0:
            # All prices are the same - render a flat line
            return "─" * len(prices)

        # Map each price to a vertical position (0-7)
        # Use Unicode block characters for smoother display
        blocks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        chart_chars = []
        for price in prices:
            # Normalize to 0-1 range
            normalized = (price - min_price) / price_range
            # Map to block index (0-7)
            block_index = min(int(normalized * 8), 7)
            chart_chars.append(blocks[block_index])

        return "".join(chart_chars)
