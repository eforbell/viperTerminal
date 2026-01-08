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
from viper.services.indicators import calculate_rsi, calculate_sma
from viper.widgets.chart_renderer import (
    ChartDimensions,
    ChartRenderer,
    ChartStyle,
    OverlayData,
)
from viper.widgets.rsi_panel import RSIPanel


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
        # Moving average display state
        self._ma_mode: str = "off"  # Cycle: off -> sma20 -> sma50 -> both -> off
        self._sma20: list[float | None] | None = None  # Cached SMA20 values
        self._sma50: list[float | None] | None = None  # Cached SMA50 values
        # RSI indicator state
        self._rsi_values: list[float | None] | None = None  # Cached RSI values
        self._rsi_panel: RSIPanel | None = None  # RSI panel widget

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Container(id="chart-content")
        # RSI panel starts hidden
        self._rsi_panel = RSIPanel()
        self._rsi_panel.hide()
        yield self._rsi_panel

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
        # Calculate moving averages when chart loads (cache for toggles)
        self._calculate_moving_averages(data.prices)
        # Calculate RSI when chart loads (cache for toggles)
        self._calculate_rsi(data.prices)
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

        # Add MA legend if MAs are displayed
        if self._ma_mode != "off":
            ma_legend_parts = []
            if self._ma_mode in ("sma20", "both") and self._sma20:
                # Get last non-None value from SMA20
                sma20_value = next((v for v in reversed(self._sma20) if v is not None), None)
                if sma20_value:
                    ma_legend_parts.append(f"SMA20: ${sma20_value:.2f}")
            if self._ma_mode in ("sma50", "both") and self._sma50:
                # Get last non-None value from SMA50
                sma50_value = next((v for v in reversed(self._sma50) if v is not None), None)
                if sma50_value:
                    ma_legend_parts.append(f"SMA50: ${sma50_value:.2f}")
            if ma_legend_parts:
                header_text += "  " + "  ".join(ma_legend_parts)

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

        # Build overlay list based on MA mode
        overlays: list[OverlayData] = []
        if self._ma_mode in ("sma20", "both") and self._sma20:
            overlays.append(OverlayData(
                values=self._sma20,
                color="cyan",  # Cyan for SMA20
                name="SMA20"
            ))
        if self._ma_mode in ("sma50", "both") and self._sma50:
            overlays.append(OverlayData(
                values=self._sma50,
                color="magenta",  # Magenta for SMA50
                name="SMA50"
            ))

        rendered = self._renderer.render(
            prices=data.prices,
            dates=data.dates,
            dimensions=dimensions,
            period=self._current_period,
            overlays=overlays if overlays else None,
        )

        # Mount each line of the chart
        # Enable markup when overlays are present (they use Rich markup for colors)
        has_overlays = bool(overlays)
        for line in rendered.lines:
            container.mount(Label(line, classes="chart-line", markup=has_overlays))

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

    def _calculate_moving_averages(self, prices: list[float]) -> None:
        """Calculate and cache moving averages for the current chart data.

        Args:
            prices: List of price values
        """
        # Calculate SMA20 and SMA50 for overlay display
        self._sma20 = calculate_sma(prices, 20) if len(prices) >= 20 else None
        self._sma50 = calculate_sma(prices, 50) if len(prices) >= 50 else None

    def _calculate_rsi(self, prices: list[float]) -> None:
        """Calculate and cache RSI for the current chart data.

        Args:
            prices: List of price values
        """
        # Calculate RSI (requires at least 15 prices: 14 for period + 1 for first calculation)
        self._rsi_values = calculate_rsi(prices, 14) if len(prices) >= 15 else None

        # Update RSI panel if visible
        if self._rsi_panel and self._rsi_values:
            # Get latest non-None RSI value
            current_rsi = next((v for v in reversed(self._rsi_values) if v is not None), None)
            self._rsi_panel.show_indicator(self._rsi_values, current_rsi)

    def cycle_ma_display(self) -> None:
        """Cycle through moving average display modes: off -> sma20 -> sma50 -> both -> off."""
        # Define cycle order
        cycle_order = ["off", "sma20", "sma50", "both"]
        current_idx = cycle_order.index(self._ma_mode)
        next_idx = (current_idx + 1) % len(cycle_order)
        self._ma_mode = cycle_order[next_idx]
        # Re-render to show/hide MAs
        self._render_content()

    def get_ma_mode(self) -> str:
        """Get current MA display mode.

        Returns:
            Current mode: 'off', 'sma20', 'sma50', or 'both'
        """
        return self._ma_mode

    def toggle_rsi(self) -> None:
        """Toggle RSI indicator panel visibility."""
        if self._rsi_panel:
            self._rsi_panel.toggle_visibility()
            # If panel is now visible and we have RSI data, update it
            if self._rsi_panel.is_visible() and self._rsi_values:
                current_rsi = next((v for v in reversed(self._rsi_values) if v is not None), None)
                self._rsi_panel.show_indicator(self._rsi_values, current_rsi)

    def is_rsi_visible(self) -> bool:
        """Check if RSI panel is currently visible.

        Returns:
            True if RSI is visible, False otherwise
        """
        return self._rsi_panel.is_visible() if self._rsi_panel else False
