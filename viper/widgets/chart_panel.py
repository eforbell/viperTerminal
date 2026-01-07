"""Chart panel widget for displaying historical price charts."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator

from viper.services.history_data import (
    HistoricalData,
    HistoricalDataError,
    HistoricalStats,
    calculate_stats,
    fetch_historical_data,
)
from viper.widgets.chart_renderer import ChartDimensions, ChartRenderer, ChartStyle


class ChartPanel(Widget):
    """Panel for displaying historical price charts with loading and error states."""

    # Make the panel focusable
    can_focus = True

    DEFAULT_CSS = """
    ChartPanel {
        height: 100%;
        width: 100%;
        padding: 1 2;
    }

    ChartPanel Label {
        width: 100%;
    }

    ChartPanel .chart-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    ChartPanel .stats-row {
        margin-top: 0;
        margin-bottom: 0;
    }

    ChartPanel .positive {
        color: #00ff00;
    }

    ChartPanel .negative {
        color: #ff0000;
    }

    ChartPanel .neutral {
        color: $accent;
    }

    ChartPanel .empty-state {
        color: #666666;
        text-align: center;
        margin-top: 3;
    }

    ChartPanel .error-state {
        color: #ff0000;
        text-align: center;
        margin-top: 3;
    }

    ChartPanel .loading-container {
        align: center middle;
        height: 100%;
    }

    ChartPanel .chart-line {
        margin: 0;
    }
    """

    def __init__(self, style: ChartStyle = ChartStyle.BRAILLE) -> None:
        """Initialize the chart panel.

        Args:
            style: Chart rendering style (BRAILLE or BLOCK)
        """
        super().__init__()
        self._state: str = "empty"
        self._data: HistoricalData | HistoricalDataError | None = None
        self._stats: HistoricalStats | None = None
        self._current_ticker: str | None = None
        self._current_period: str = "1M"  # Default period
        self._renderer = ChartRenderer(style=style)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Container(id="chart-content")

    def show_loading(self, ticker: str, period: str) -> None:
        """Display loading state with spinner.

        Args:
            ticker: The ticker being loaded
            period: The time period being loaded
        """
        self._state = "loading"
        self._current_ticker = ticker
        self._current_period = period
        self._render_content()

    def show_chart(self, data: HistoricalData, stats: HistoricalStats) -> None:
        """Display a historical price chart.

        Args:
            data: The historical data to display
            stats: Calculated statistics for the period
        """
        self._state = "success"
        self._data = data
        self._stats = stats
        self._current_ticker = data.ticker
        self._current_period = data.period
        self._render_content()

    def show_error(self, error: HistoricalDataError) -> None:
        """Display an error state.

        Args:
            error: The error information to display
        """
        self._state = "error"
        self._data = error
        self._stats = None
        self._current_ticker = error.ticker
        self._render_content()

    def show_empty(self) -> None:
        """Display empty state when no ticker is selected."""
        self._state = "empty"
        self._data = None
        self._stats = None
        self._current_ticker = None
        self._render_content()

    def _render_content(self) -> None:
        """Render the appropriate content based on current state."""
        container = self.query_one("#chart-content", Container)
        container.remove_children()

        if self._state == "empty":
            container.mount(Label("No ticker selected", classes="empty-state"))
        elif self._state == "loading":
            # Create loading container with widgets to mount
            loading_indicator = LoadingIndicator()
            loading_text = f"Loading chart for {self._current_ticker} ({self._current_period})..."
            loading_label = Label(loading_text)
            loading_container = Container(
                loading_indicator, loading_label, classes="loading-container"
            )
            container.mount(loading_container)
        elif self._state == "error" and isinstance(self._data, HistoricalDataError):
            container.mount(
                Label(f"Error: {self._data.error_message}", classes="error-state")
            )
        elif self._state == "success" and isinstance(self._data, HistoricalData):
            self._render_chart(container, self._data, self._stats)

    def _render_chart(
        self, container: Container, data: HistoricalData, stats: HistoricalStats | None
    ) -> None:
        """Render a successful chart display.

        Args:
            container: The container to mount widgets into
            data: The historical data to display
            stats: Calculated statistics for the period (optional)
        """
        # Header with ticker and timeframe
        header_text = f"{data.ticker} - {data.period} Chart"
        container.mount(Label(header_text, classes="chart-header"))

        # Stats row if available
        if stats:
            # Determine color based on change
            if stats.change_percent > 0:
                change_class = "stats-row positive"
                change_sign = "+"
            elif stats.change_percent < 0:
                change_class = "stats-row negative"
                change_sign = ""  # Negative sign already in number
            else:
                change_class = "stats-row neutral"
                change_sign = ""

            # Format stats
            high_str = f"${self._format_number(stats.period_high, 2)}"
            low_str = f"${self._format_number(stats.period_low, 2)}"
            change_str = f"{change_sign}{self._format_number(abs(stats.change_percent), 2)}%"

            stats_line = f"High: {high_str}  Low: {low_str}  Change: {change_str}"
            container.mount(Label(stats_line, classes=change_class))

            # Spacing
            container.mount(Label("", classes="stats-row"))

        # Calculate available dimensions for chart
        # Reserve space for header (2 lines), stats (2 lines), and padding
        available_height = self.size.height - 6
        available_width = self.size.width - 4  # Account for padding

        # Ensure minimum dimensions
        if available_height < 10:
            available_height = 10
        if available_width < 40:
            available_width = 40

        # Render the chart
        dimensions = ChartDimensions(
            width=available_width,
            height=available_height,
            include_y_axis=True,
            include_x_axis=True,
        )

        rendered = self._renderer.render(
            prices=data.prices,
            dates=data.dates,
            dimensions=dimensions,
        )

        # Mount each line of the chart
        for line in rendered.lines:
            container.mount(Label(line, classes="chart-line", markup=False))

    def _format_number(self, value: float, decimals: int) -> str:
        """Format a number with commas and specified decimal places.

        Args:
            value: The number to format
            decimals: Number of decimal places

        Returns:
            Formatted number string with commas for thousands
        """
        if decimals == 0:
            return f"{int(value):,}"
        return f"{value:,.{decimals}f}"

    async def load_chart(self, ticker: str, period: str = "1M") -> None:
        """Load and display a chart for the given ticker and period.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1W, 1M, 3M, 6M, 1Y, 2Y, 5Y, MAX)
        """
        # Show loading state
        self.show_loading(ticker, period)

        # Fetch historical data
        result = await fetch_historical_data(ticker, period)

        # Check if ticker hasn't changed during fetch
        if self._current_ticker != ticker:
            return

        # Display result
        if isinstance(result, HistoricalData):
            # Calculate stats
            stats = calculate_stats(result)
            self.show_chart(result, stats)
        elif isinstance(result, HistoricalDataError):
            self.show_error(result)
