"""MACD (Moving Average Convergence Divergence) indicator panel widget.

This module provides a MACD indicator panel that displays:
- MACD line (cyan): 12-period EMA - 26-period EMA
- Signal line (yellow): 9-period EMA of MACD line
- Histogram (green/red): MACD line - Signal line
- Zero reference line (white): Indicates trend direction
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from viper.widgets.indicator_panel import HorizontalLine, IndicatorPanel

if TYPE_CHECKING:
    from viper.widgets.chart_context import ChartContext


class MACDPanel(IndicatorPanel):
    """Panel for displaying the MACD (Moving Average Convergence Divergence) indicator.

    MACD is a trend-following momentum indicator that shows the relationship between
    two moving averages of a security's price. It consists of:
    - MACD line: Fast (12-period EMA) - Slow (26-period EMA)
    - Signal line: 9-period EMA of MACD line (trigger line)
    - Histogram: MACD line - Signal line (visual divergence)

    Interpretation:
    - MACD crosses above Signal: Bullish signal (potential buy)
    - MACD crosses below Signal: Bearish signal (potential sell)
    - MACD crosses zero: Trend direction change
    - Divergence: Price makes new high/low but MACD doesn't (reversal warning)
    """

    def __init__(self) -> None:
        """Initialize the MACD panel with standard MACD configuration."""
        # Define MACD reference line: zero line (trend direction)
        # Use Rich markup color names (NOT ANSI codes!)
        reference_lines = [
            HorizontalLine(
                value=0.0,
                label="0",
                style="solid",
                color="white"  # White for zero line
            ),
        ]

        # Initialize with MACD-specific configuration
        super().__init__(
            name="MACD",
            height=7,  # 7 lines for MACD (needs more height for histogram + 2 lines)
            min_value=-10.0,  # Typical MACD range is around -10 to +10
            max_value=10.0,
            reference_lines=reference_lines
        )

        # Store MACD component data
        self._macd_line: list[float | None] | None = None
        self._signal_line: list[float | None] | None = None
        self._histogram: list[float | None] | None = None

    def show_macd(
        self,
        macd_line: list[float | None],
        signal_line: list[float | None],
        histogram: list[float | None],
        context: ChartContext | None = None,
    ) -> None:
        """Display MACD indicator values.

        Args:
            macd_line: MACD line values (12-EMA - 26-EMA)
            signal_line: Signal line values (9-EMA of MACD)
            histogram: Histogram values (MACD - Signal)
            context: ChartContext with dimensions for alignment (recommended)
        """
        # Store all three components
        self._macd_line = macd_line
        self._signal_line = signal_line
        self._histogram = histogram

        # Extract current values (last non-None value from each series)
        macd_current = self._get_last_value(macd_line)
        signal_current = self._get_last_value(signal_line)
        hist_current = self._get_last_value(histogram)

        # Use MACD line for base indicator display
        # We'll override the rendering to show all three components
        self.show_indicator(
            values=macd_line,
            current_value=macd_current,
            context=context,
        )

    def _get_last_value(self, values: list[float | None]) -> float | None:
        """Extract the last non-None value from a list.

        Args:
            values: List of values to search

        Returns:
            Last non-None value, or None if all values are None
        """
        for value in reversed(values):
            if value is not None:
                return value
        return None

    def _render_content(self) -> None:
        """Render the MACD panel content with custom header format.

        Overrides the base class to show MACD, Signal, and Histogram values
        in the header.
        """
        from textual.containers import Container
        from textual.widgets import Label

        container = self.query_one("#indicator-content", Container)
        container.remove_children()

        # Check if we have data
        if self._macd_line is None or self._signal_line is None or self._histogram is None:
            container.mount(Label("No data", classes="empty-state"))
            return

        # Y-axis padding to align with price chart
        y_axis_padding = " " * self._y_axis_width

        # Build header text with all three component values
        macd_current = self._get_last_value(self._macd_line)
        signal_current = self._get_last_value(self._signal_line)
        hist_current = self._get_last_value(self._histogram)

        if macd_current is None and signal_current is None and hist_current is None:
            header_text = "MACD: No data"
        else:
            macd_str = f"{macd_current:.2f}" if macd_current is not None else "N/A"
            signal_str = f"{signal_current:.2f}" if signal_current is not None else "N/A"
            hist_str = f"{hist_current:.2f}" if hist_current is not None else "N/A"
            header_text = f"MACD: {macd_str}  Signal: {signal_str}  Hist: {hist_str}"

        container.mount(Label(y_axis_padding + header_text, classes="indicator-header"))

        # Render the MACD chart with all three components
        chart_lines = self._render_macd_chart()
        for line in chart_lines:
            container.mount(Label(line, classes="indicator-line", markup=True))

    def _render_macd_chart(self) -> list[str]:
        """Render the MACD chart with MACD line, Signal line, and Histogram.

        Returns:
            List of chart lines ready for display
        """
        if not self._macd_line or not self._signal_line or not self._histogram:
            return ["No data"]

        # Filter out None values to get actual data points for each series
        macd_data = [v for v in self._macd_line if v is not None]
        signal_data = [v for v in self._signal_line if v is not None]
        hist_data = [v for v in self._histogram if v is not None]

        if not macd_data and not signal_data and not hist_data:
            return ["No data"]

        # Use the chart width passed from the parent
        chart_width = self._chart_width

        # Calculate target data points (2 per character for braille)
        target_data_points = chart_width * 2

        # Prepare all three data series for rendering
        # We'll render histogram first (background), then MACD and Signal lines
        macd_points = self._prepare_data_series(self._macd_line, target_data_points)
        signal_points = self._prepare_data_series(self._signal_line, target_data_points)
        hist_points = self._prepare_data_series(self._histogram, target_data_points)

        # Create the chart
        chart_lines = self._render_macd_components(
            macd_points, signal_points, hist_points, chart_width
        )

        return chart_lines

    def _prepare_data_series(
        self, values: list[float | None], target_count: int
    ) -> list[float]:
        """Prepare a data series for rendering (filter None, resample).

        Args:
            values: Raw data series with possible None values
            target_count: Target number of data points after resampling

        Returns:
            Prepared data series ready for rendering
        """
        # Filter out None values
        data_points = [v for v in values if v is not None]
        if not data_points:
            return []

        # Resample to match chart width
        if len(data_points) > target_count:
            data_points = self._downsample(data_points, target_count)
        elif len(data_points) < target_count:
            data_points = self._upsample(data_points, target_count)

        return data_points

    def _render_macd_components(
        self,
        macd_points: list[float],
        signal_points: list[float],
        hist_points: list[float],
        width: int,
    ) -> list[str]:
        """Render MACD, Signal line, and Histogram on the chart.

        Args:
            macd_points: Prepared MACD line data
            signal_points: Prepared Signal line data
            hist_points: Prepared Histogram data
            width: Chart width in characters

        Returns:
            List of chart lines with all three components rendered
        """
        if not macd_points and not signal_points and not hist_points:
            return ["No data"]

        # Initialize chart grid with spaces
        grid = [[" " for _ in range(width)] for _ in range(self._height)]

        # Calculate value range
        value_range = self._max_value - self._min_value

        # Draw reference lines first (zero line)
        for ref_line in self._reference_lines:
            if self._min_value <= ref_line.value <= self._max_value:
                self._draw_reference_line(grid, ref_line, value_range)

        # Render histogram bars first (background layer)
        if hist_points:
            self._render_histogram_bars(grid, hist_points, value_range)

        # Render MACD line (cyan)
        if macd_points:
            self._render_line(grid, macd_points, value_range, "cyan")

        # Render Signal line (yellow)
        if signal_points:
            self._render_line(grid, signal_points, value_range, "yellow")

        # Convert grid to strings with Y-axis padding
        y_axis_padding = " " * self._y_axis_width
        chart_lines = [y_axis_padding + "".join(line) for line in grid]

        return chart_lines

    def _render_histogram_bars(
        self, grid: list[list[str]], values: list[float], value_range: float
    ) -> None:
        """Render histogram bars centered at zero line.

        Args:
            grid: 2D character grid to draw on
            values: Histogram values
            value_range: Total range of values (max - min)
        """
        if value_range == 0:
            return

        # Calculate zero line row position
        zero_normalized = (0.0 - self._min_value) / value_range
        zero_row_pos = int(zero_normalized * (self._height * 4 - 1))
        zero_row = (self._height * 4 - 1 - zero_row_pos) // 4

        # Block characters for histogram (vertical bars)
        blocks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        for i, value in enumerate(values):
            char_idx = i // 2  # 2 data points per character
            if char_idx >= len(grid[0]):
                break

            # Calculate bar height in rows
            normalized = (value - self._min_value) / value_range
            value_row_pos = int(normalized * (self._height * 4 - 1))
            value_row = (self._height * 4 - 1 - value_row_pos) // 4

            # Determine bar direction and color
            if value >= 0:
                # Positive: green bar extending upward from zero line
                color = "green"
                start_row = min(value_row, zero_row)
                end_row = zero_row
            else:
                # Negative: red bar extending downward from zero line
                color = "red"
                start_row = zero_row
                end_row = max(value_row, zero_row)

            # Draw vertical bar
            bar_height = abs(end_row - start_row) + 1
            if bar_height > 0:
                # Choose block character based on bar height
                block_idx = min(bar_height - 1, len(blocks) - 1)
                block_char = blocks[block_idx]

                # Draw at the appropriate row (closer to zero line)
                target_row = start_row if value >= 0 else end_row
                if 0 <= target_row < self._height:
                    # Only draw if space (don't overwrite reference lines)
                    if grid[target_row][char_idx] == " ":
                        grid[target_row][char_idx] = f"[{color}]{block_char}[/{color}]"

    def _render_line(
        self, grid: list[list[str]], values: list[float], value_range: float, color: str
    ) -> None:
        """Render a line on the chart grid using braille characters.

        Args:
            grid: 2D character grid to draw on
            values: Data values to plot
            value_range: Total range of values (max - min)
            color: Rich markup color name for the line
        """
        if value_range == 0:
            return

        # Braille dot patterns (using dots 7+8 for simple line)
        braille_base = 0x2800
        dot_7 = 0x40
        dot_8 = 0x80

        # Calculate vertical positions
        vertical_positions = [
            int(((v - self._min_value) / value_range) * (self._height * 4 - 1))
            for v in values
        ]

        # Plot data points (2 per character for braille)
        for i in range(0, len(vertical_positions) - 1, 2):
            char_idx = i // 2
            if char_idx >= len(grid[0]):
                break

            left_pos = vertical_positions[i]
            right_pos = vertical_positions[i + 1] if i + 1 < len(vertical_positions) else left_pos

            # Clamp to valid range
            left_pos = max(0, min(self._height * 4 - 1, left_pos))
            right_pos = max(0, min(self._height * 4 - 1, right_pos))

            # Convert to row (invert for display)
            left_row = (self._height * 4 - 1 - left_pos) // 4
            right_row = (self._height * 4 - 1 - right_pos) // 4

            # Use the higher row (closer to top = higher value)
            target_row = min(left_row, right_row)
            if 0 <= target_row < self._height:
                # Create braille character
                braille_char = chr(braille_base + dot_7 + dot_8)
                # Overwrite existing content (lines draw over histogram)
                grid[target_row][char_idx] = f"[{color}]{braille_char}[/{color}]"
