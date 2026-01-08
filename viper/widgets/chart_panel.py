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

    ChartPanel .timeframe-bar {
        margin-top: 0;
        margin-bottom: 1;
    }

    ChartPanel .timeframe-button {
        color: #666666;
    }

    ChartPanel .timeframe-active {
        color: $accent;
        text-style: bold;
    }
    """

    def __init__(self, style: ChartStyle = ChartStyle.BRAILLE, volume_enabled: bool = True) -> None:
        """Initialize the chart panel.

        Args:
            style: Chart rendering style (BRAILLE or BLOCK)
            volume_enabled: Whether volume bars are shown by default
        """
        super().__init__()
        self._state: str = "empty"
        self._data: HistoricalData | HistoricalDataError | None = None
        self._stats: HistoricalStats | None = None
        self._current_ticker: str | None = None
        self._current_period: str = "1M"  # Default period
        self._renderer = ChartRenderer(style=style)
        self._volume_enabled: bool = volume_enabled  # Volume bars toggle state
        # Timeframe mappings
        self._timeframes = {
            "1": "1W",
            "2": "1M",
            "3": "3M",
            "4": "6M",
            "5": "1Y",
            "6": "5Y",
            "7": "MAX",
        }

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
        volume_status = "Vol: ON" if self._volume_enabled else "Vol: OFF"
        header_text = f"{data.ticker} - {data.period} Chart  [{volume_status}]"
        container.mount(Label(header_text, classes="chart-header"))

        # Timeframe selector bar with active indicator
        timeframe_parts = []
        for key, period in self._timeframes.items():
            if period == self._current_period:
                # Active timeframe - highlighted
                timeframe_parts.append(f"[b][cyan]\\[{key}] {period}[/cyan][/b]")
            else:
                # Inactive timeframe
                timeframe_parts.append(f"[dim] {key}  {period}[/dim]")

        timeframe_markup = "  ".join(timeframe_parts)
        container.mount(Label(timeframe_markup, classes="timeframe-bar"))

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

            # Add volume stats if volume is enabled
            if self._volume_enabled and len(data.volumes) > 0:
                avg_volume_str = self._format_number(stats.avg_volume, 0)
                last_volume = data.volumes[-1]
                last_volume_str = self._format_number(last_volume, 0)

                # Calculate volume vs average
                volume_ratio = (last_volume / stats.avg_volume * 100) if stats.avg_volume > 0 else 0
                volume_vs_avg = f"{volume_ratio:.0f}%"

                stats_line += f"  Avg Vol: {avg_volume_str}  Last: {last_volume_str} ({volume_vs_avg})"

            container.mount(Label(stats_line, classes=change_class))

            # Spacing
            container.mount(Label("", classes="stats-row"))

        # Calculate available dimensions for chart
        # Reserve space for header (2 lines), timeframe bar (1 line), stats (2 lines), and padding
        # If volume is enabled, reserve additional 3 lines for volume bars
        volume_height = 3 if self._volume_enabled else 0
        available_height = self.size.height - 7 - volume_height
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
            period=self._current_period,
        )

        # Mount each line of the chart
        for line in rendered.lines:
            container.mount(Label(line, classes="chart-line", markup=False))

        # Render volume bars if enabled
        if self._volume_enabled and len(data.volumes) > 0:
            # Calculate chart area width (must match the price chart area)
            chart_area_width = available_width - dimensions.y_axis_width
            volume_lines = self._renderer.render_volume_bars(
                volumes=data.volumes,
                opens=data.opens,
                closes=data.prices,
                width=chart_area_width,
                height=volume_height,
                y_axis_width=dimensions.y_axis_width,
                style=self._renderer.style,  # Pass the chart style for proper alignment
                interpolated_count=rendered.interpolated_count,  # Pass interpolation info for alignment
            )
            for line in volume_lines:
                # Volume lines use Rich markup for colors, so markup=True (default)
                container.mount(Label(line, classes="chart-line"))

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

    async def change_timeframe(self, period: str) -> None:
        """Change the timeframe for the current chart.

        Args:
            period: Time period (1W, 1M, 3M, 6M, 1Y, 2Y, 5Y, MAX)
        """
        # Only change if we have a ticker and it's different from current
        if self._current_ticker and period != self._current_period:
            await self.load_chart(self._current_ticker, period)

    def get_timeframe_for_key(self, key: str) -> str | None:
        """Get the timeframe period for a given key.

        Args:
            key: The number key pressed (1-7)

        Returns:
            The timeframe period, or None if key is invalid
        """
        return self._timeframes.get(key)

    def toggle_volume(self) -> None:
        """Toggle volume bars display."""
        self._volume_enabled = not self._volume_enabled
        # Re-render to show/hide volume bars
        self._render_content()

    def is_volume_enabled(self) -> bool:
        """Check if volume bars are currently enabled.

        Returns:
            True if volume is enabled, False otherwise
        """
        return self._volume_enabled
