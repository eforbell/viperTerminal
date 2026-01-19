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
from viper.services.indicators import calculate_macd, calculate_rsi, calculate_sma
from viper.widgets.chart_context import ChartContext
from viper.widgets.chart_renderer import (
    ChartDimensions,
    ChartRenderer,
    ChartStyle,
    OverlayData,
    render_x_axis,
)
from viper.widgets.macd_panel import MACDPanel
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
        layout: vertical;
    }

    ChartPanel #chart-content {
        height: 1fr;
        width: 100%;
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

    ChartPanel #x-axis-container {
        height: auto;
        width: 100%;
    }
    """

    def __init__(self, style: ChartStyle = ChartStyle.CANDLESTICK, default_period: str = "1Y") -> None:
        """Initialize the chart panel.

        Args:
            style: Chart rendering style (BRAILLE, BLOCK, or CANDLESTICK)
            default_period: Default timeframe for charts (1W, 1M, 3M, 6M, 1Y, 5Y, MAX)
        """
        super().__init__()
        self._state: str = "empty"
        self._data: HistoricalData | HistoricalDataError | None = None
        self._stats: HistoricalStats | None = None
        self._current_ticker: str | None = None
        self._current_period: str = default_period
        self._chart_style: ChartStyle = style  # Current chart style
        self._renderer = ChartRenderer(style=style)
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
        # MACD indicator state
        self._macd_line: list[float | None] | None = None  # Cached MACD line
        self._signal_line: list[float | None] | None = None  # Cached Signal line
        self._histogram: list[float | None] | None = None  # Cached Histogram
        self._macd_panel: MACDPanel | None = None  # MACD panel widget
        self._chart_area_width: int = 70  # Cached for indicator panel updates
        # ChartContext - single source of truth for dimensions and data
        self._chart_context: ChartContext | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Container(id="chart-content")
        # RSI panel starts hidden
        self._rsi_panel = RSIPanel()
        self._rsi_panel.hide()
        yield self._rsi_panel
        # MACD panel starts hidden
        self._macd_panel = MACDPanel()
        self._macd_panel.hide()
        yield self._macd_panel
        # X-axis container - rendered AFTER all indicator panels (at very bottom)
        yield Container(id="x-axis-container")

    def on_mount(self) -> None:
        """Initialize content when mounted."""
        self._rebuild_content()

    def show_loading(self, ticker: str, period: str) -> None:
        """Display loading state with spinner.

        Args:
            ticker: The ticker being loaded
            period: The time period being loaded
        """
        self._state = "loading"
        self._current_ticker = ticker
        self._current_period = period
        self._rebuild_content()

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
        # Calculate MACD when chart loads (cache for toggles)
        self._calculate_macd(data.prices)
        self._rebuild_content()

    def show_error(self, error: HistoricalDataError) -> None:
        """Display an error state.

        Args:
            error: The error information to display
        """
        self._state = "error"
        self._data = error
        self._stats = None
        self._current_ticker = error.ticker
        self._rebuild_content()

    def show_empty(self) -> None:
        """Display empty state when no ticker is selected."""
        self._state = "empty"
        self._data = None
        self._stats = None
        self._current_ticker = None
        self._rebuild_content()

    def _rebuild_content(self) -> None:
        """Render the appropriate content based on current state."""
        container = self.query_one("#chart-content", Container)
        container.remove_children()

        if self._state == "empty":
            container.mount(Label("No ticker selected", classes="empty-state"))
            self._clear_x_axis()
        elif self._state == "loading":
            # Create loading container with widgets to mount
            loading_indicator = LoadingIndicator()
            loading_text = f"Loading chart for {self._current_ticker} ({self._current_period})..."
            loading_label = Label(loading_text)
            loading_container = Container(
                loading_indicator, loading_label, classes="loading-container"
            )
            container.mount(loading_container)
            self._clear_x_axis()
        elif self._state == "error" and isinstance(self._data, HistoricalDataError):
            container.mount(
                Label(f"Error: {self._data.error_message}", classes="error-state")
            )
            self._clear_x_axis()
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

        # Add style and interval info when in candlestick mode
        if self._chart_style == ChartStyle.CANDLESTICK:
            interval_display = self._get_interval_display()
            if interval_display:
                header_text += f" [Candlestick · {interval_display}]"

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

            # Add volume stats
            if len(data.volumes) > 0:
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
        # Reserve space for header (2 lines), timeframe bar (1 line), stats (2 lines), padding (2 lines)
        # Reserve 3 lines for volume bars (always shown)
        # When RSI is visible, it takes 8 lines (7 height + 1 margin-top) from #chart-content's space
        # When MACD is visible, it takes 8 lines (7 height + 1 margin-top) from #chart-content's space
        # We must account for this because self.size.height is ChartPanel's full height,
        # but #chart-content (where we render) gets reduced when indicators are visible
        volume_height = 3
        rsi_overhead = 8 if self.is_rsi_visible() else 0
        macd_overhead = 8 if self.is_macd_visible() else 0
        available_height = self.size.height - 7 - volume_height - rsi_overhead - macd_overhead
        available_width = self.size.width - 4  # Account for padding

        # Ensure minimum dimensions
        if available_height < 10:
            available_height = 10
        if available_width < 40:
            available_width = 40

        # Create ChartContext - single source of truth for dimensions and data
        self._chart_context = ChartContext.from_historical_data(
            data=data,
            width=available_width,
            height=available_height,
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

        # Render using ChartContext (modern path)
        rendered = self._renderer.render(
            overlays=overlays if overlays else None,
            context=self._chart_context,
        )

        # Mount each line of the chart
        # Enable markup when overlays are present OR when using candlestick style
        # (both use Rich markup for colors - overlays use cyan/magenta, candlesticks use green/red)
        needs_markup = bool(overlays) or self._chart_style == ChartStyle.CANDLESTICK
        for line in rendered.lines:
            container.mount(Label(line, classes="chart-line", markup=needs_markup))

        # Cache chart area width for volume and RSI (derived from ChartContext)
        chart_area_width = self._chart_context.chart_area_width
        self._chart_area_width = chart_area_width

        # Render volume bars (always shown)
        if len(data.volumes) > 0:
            volume_lines = self._renderer.render_volume_bars(
                volumes=data.volumes,
                opens=data.opens,
                closes=data.prices,
                width=chart_area_width,
                height=volume_height,
                y_axis_width=self._chart_context.y_axis_width,
                style=self._renderer.style,  # Pass the chart style for proper alignment
                interpolated_count=rendered.interpolated_count,  # Pass interpolation info for alignment
            )
            for line in volume_lines:
                # Volume lines use Rich markup for colors, so markup=True (default)
                container.mount(Label(line, classes="chart-line"))

        # Update RSI panel with ChartContext (even if hidden, so it's ready when toggled)
        if self._rsi_panel and self._rsi_values:
            current_rsi = next((v for v in reversed(self._rsi_values) if v is not None), None)
            self._rsi_panel.show_indicator(
                self._rsi_values, current_rsi, context=self._chart_context
            )

        # Update MACD panel with ChartContext (even if hidden, so it's ready when toggled)
        if self._macd_panel and self._macd_line and self._signal_line and self._histogram:
            self._macd_panel.show_macd(
                self._macd_line, self._signal_line, self._histogram, context=self._chart_context
            )

        # Render X-axis in dedicated container at very bottom (after all indicator panels)
        self._update_x_axis()

    def _update_x_axis(self) -> None:
        """Update the X-axis container with date labels.

        This renders the X-axis in a dedicated container at the very bottom,
        after all indicator panels (RSI, future MACD, etc.).
        """
        x_axis_container = self.query_one("#x-axis-container", Container)
        x_axis_container.remove_children()

        if self._chart_context:
            x_axis_lines = render_x_axis(self._chart_context)
            for line in x_axis_lines:
                x_axis_container.mount(Label(line, classes="chart-line"))

    def _clear_x_axis(self) -> None:
        """Clear the X-axis container when chart is not displayed."""
        x_axis_container = self.query_one("#x-axis-container", Container)
        x_axis_container.remove_children()

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
        # Note: RSI panel is updated in _render_chart() where we have the correct chart width

    def _calculate_macd(self, prices: list[float]) -> None:
        """Calculate and cache MACD for the current chart data.

        Args:
            prices: List of price values
        """
        # Calculate MACD (requires at least 34 prices: 33 None + 1 for first value)
        if len(prices) >= 34:
            macd_line, signal_line, histogram = calculate_macd(prices, 12, 26, 9)
            self._macd_line = macd_line
            self._signal_line = signal_line
            self._histogram = histogram
        else:
            self._macd_line = None
            self._signal_line = None
            self._histogram = None
        # Note: MACD panel is updated in _render_chart() where we have the correct chart width

    def cycle_ma_display(self) -> None:
        """Cycle through moving average display modes: off -> sma20 -> sma50 -> both -> off."""
        # Define cycle order
        cycle_order = ["off", "sma20", "sma50", "both"]
        current_idx = cycle_order.index(self._ma_mode)
        next_idx = (current_idx + 1) % len(cycle_order)
        self._ma_mode = cycle_order[next_idx]
        # Re-render to show/hide MAs
        self._rebuild_content()

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
            # If panel is now visible and we have RSI data and context, update it
            if self._rsi_panel.is_visible() and self._rsi_values and self._chart_context:
                current_rsi = next((v for v in reversed(self._rsi_values) if v is not None), None)
                self._rsi_panel.show_indicator(
                    self._rsi_values, current_rsi, context=self._chart_context
                )
            # Re-render chart to adjust height for RSI panel
            self._rebuild_content()

    def is_rsi_visible(self) -> bool:
        """Check if RSI panel is currently visible.

        Returns:
            True if RSI is visible, False otherwise
        """
        return self._rsi_panel.is_visible() if self._rsi_panel else False

    def toggle_macd(self) -> None:
        """Toggle MACD indicator panel visibility."""
        if self._macd_panel:
            self._macd_panel.toggle_visibility()
            # If panel is now visible and we have MACD data and context, update it
            if (
                self._macd_panel.is_visible()
                and self._macd_line
                and self._signal_line
                and self._histogram
                and self._chart_context
            ):
                self._macd_panel.show_macd(
                    self._macd_line, self._signal_line, self._histogram, context=self._chart_context
                )
            # Re-render chart to adjust height for MACD panel
            self._rebuild_content()

    def is_macd_visible(self) -> bool:
        """Check if MACD panel is currently visible.

        Returns:
            True if MACD is visible, False otherwise
        """
        return self._macd_panel.is_visible() if self._macd_panel else False

    def toggle_chart_style(self) -> None:
        """Toggle between BRAILLE and CANDLESTICK chart styles."""
        # Cycle: BRAILLE -> CANDLESTICK -> BRAILLE
        if self._chart_style == ChartStyle.BRAILLE:
            self._chart_style = ChartStyle.CANDLESTICK
        else:
            self._chart_style = ChartStyle.BRAILLE

        # Update renderer style
        self._renderer.style = self._chart_style

        # Re-render chart with new style (no refetch needed)
        self._rebuild_content()

    def _get_interval_display(self) -> str:
        """Get human-readable interval name for current chart data.

        Returns:
            Human-readable interval (e.g., "Daily", "Weekly", "Monthly")
        """
        if not self._data or not isinstance(self._data, HistoricalData):
            return ""

        # Map interval codes to human-readable names
        interval_map = {
            "1d": "Daily",
            "1wk": "Weekly",
            "1mo": "Monthly",
        }

        return interval_map.get(self._data.interval, self._data.interval)
