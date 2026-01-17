"""Base indicator panel widget for displaying technical indicators.

This module provides a framework for displaying oscillator-type indicators
(like RSI, MACD, Stochastic) in a sub-panel below the price chart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Label

if TYPE_CHECKING:
    from viper.widgets.chart_context import ChartContext


@dataclass
class HorizontalLine:
    """Configuration for a horizontal reference line (e.g., RSI overbought/oversold levels)."""

    value: float  # Y-axis value where line should be drawn
    label: str  # Label for the line (e.g., "Overbought (70)")
    style: str  # Line style: "solid", "dashed", or "dotted"
    color: str  # Rich markup color name (e.g., "yellow", "red")


class IndicatorPanel(Widget):
    """Base panel for displaying technical indicators below the price chart.

    This panel provides a framework for rendering oscillator indicators that
    don't overlay on the price chart. It supports:
    - Configurable height (3-5 lines)
    - Horizontal reference lines (e.g., RSI 30/70 levels)
    - Panel header with indicator name and current value
    - Show/hide toggle capability
    """

    # Make the panel focusable
    can_focus = False  # Indicators are display-only, no interaction needed

    DEFAULT_CSS = """
    IndicatorPanel {
        height: 7;
        width: 100%;
        padding: 0;
        margin-top: 1;
        margin-bottom: 0;
    }

    IndicatorPanel .indicator-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 0;
    }

    IndicatorPanel .indicator-line {
        margin: 0;
        padding: 0;
    }

    IndicatorPanel .empty-state {
        color: #666666;
        text-align: center;
    }
    """

    def __init__(
        self,
        name: str,
        height: int = 4,
        min_value: float = 0.0,
        max_value: float = 100.0,
        reference_lines: list[HorizontalLine] | None = None,
    ) -> None:
        """Initialize the indicator panel.

        Args:
            name: Display name for the indicator (e.g., "RSI", "MACD")
            height: Height of the indicator chart in lines (default 4)
            min_value: Minimum value on the Y-axis (default 0.0)
            max_value: Maximum value on the Y-axis (default 100.0)
            reference_lines: Optional horizontal reference lines to display
        """
        super().__init__()
        self._name: str = name
        self._height: int = height
        self._min_value: float = min_value
        self._max_value: float = max_value
        self._reference_lines: list[HorizontalLine] = reference_lines or []
        self._visible: bool = True
        self._indicator_values: list[float | None] | None = None
        self._current_value: float | None = None
        self._chart_width: int = 70  # Default, updated by show_indicator()
        self._y_axis_width: int = 12  # Default, updated by show_indicator() with ChartContext

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Container(id="indicator-content")

    def show_indicator(
        self,
        values: list[float | None],
        current_value: float | None = None,
        chart_width: int | None = None,
        context: ChartContext | None = None,
    ) -> None:
        """Display indicator values.

        Supports two calling styles:
        1. Legacy: Pass chart_width directly
        2. Modern: Pass ChartContext via context= parameter (recommended)

        Args:
            values: List of indicator values to display (None = no data at that point)
            current_value: Optional current/latest value for header display
            chart_width: Width of the chart area in characters (legacy)
            context: ChartContext with dimensions and data (modern, recommended)
        """
        self._indicator_values = values
        self._current_value = current_value

        # Modern path: extract dimensions from ChartContext
        if context is not None:
            self._chart_width = context.chart_area_width
            self._y_axis_width = context.y_axis_width
        # Legacy path: use chart_width parameter
        elif chart_width is not None:
            self._chart_width = chart_width
            # Keep existing y_axis_width (default 12)

        # Always re-render content when data changes (even if hidden, so it's ready when toggled visible)
        self._rebuild_content()

    def hide(self) -> None:
        """Hide the indicator panel."""
        self._visible = False
        self.styles.display = "none"

    def show(self) -> None:
        """Show the indicator panel."""
        self._visible = True
        self.styles.display = "block"
        self._rebuild_content()

    def toggle_visibility(self) -> None:
        """Toggle indicator panel visibility."""
        if self._visible:
            self.hide()
        else:
            self.show()

    def is_visible(self) -> bool:
        """Check if panel is currently visible.

        Returns:
            True if panel is visible, False otherwise
        """
        return self._visible

    def get_name(self) -> str:
        """Get the indicator name.

        Returns:
            The indicator name
        """
        return self._name

    def _rebuild_content(self) -> None:
        """Render the indicator panel content."""
        container = self.query_one("#indicator-content", Container)
        container.remove_children()

        if self._indicator_values is None:
            container.mount(Label("No data", classes="empty-state"))
            return

        # Y-axis padding to align with price chart (from ChartContext or default)
        y_axis_padding = " " * self._y_axis_width

        # Build header text with current value if available
        header_text = self._name
        if self._current_value is not None:
            header_text += f": {self._current_value:.2f}"
        container.mount(Label(y_axis_padding + header_text, classes="indicator-header"))

        # Render the indicator chart
        chart_lines = self._render_indicator_chart()
        for line in chart_lines:
            container.mount(Label(line, classes="indicator-line", markup=True))

    def _render_indicator_chart(self) -> list[str]:
        """Render the indicator chart with braille characters.

        Returns:
            List of chart lines ready for display
        """
        if not self._indicator_values:
            return ["No data"]

        # Filter out None values to get actual data points
        data_points = [v for v in self._indicator_values if v is not None]
        if not data_points:
            return ["No data"]

        # Use the chart width passed from the parent (matches price chart)
        chart_width = self._chart_width

        # Calculate target data points (2 per character for braille)
        target_data_points = chart_width * 2

        # Downsample or upsample to match chart width exactly
        if len(data_points) > target_data_points:
            data_points = self._downsample(data_points, target_data_points)
        elif len(data_points) < target_data_points:
            # Upsample using linear interpolation to fill chart width
            data_points = self._upsample(data_points, target_data_points)

        # Create braille chart
        chart_lines = self._render_braille_chart(data_points, chart_width)

        return chart_lines

    def _downsample(self, values: list[float], target_count: int) -> list[float]:
        """Downsample data to target count using averaging.

        Args:
            values: List of values to downsample
            target_count: Target number of data points

        Returns:
            Downsampled list of values
        """
        if len(values) <= target_count:
            return values

        chunk_size = len(values) / target_count
        downsampled = []

        for i in range(target_count):
            start_idx = int(i * chunk_size)
            end_idx = int((i + 1) * chunk_size)
            chunk = values[start_idx:end_idx]
            if chunk:
                downsampled.append(sum(chunk) / len(chunk))

        return downsampled

    def _upsample(self, values: list[float], target_count: int) -> list[float]:
        """Upsample data to target count using linear interpolation.

        Args:
            values: List of values to upsample
            target_count: Target number of data points

        Returns:
            Upsampled list of values
        """
        if len(values) >= target_count or len(values) < 2:
            return values

        upsampled: list[float] = []
        step = (len(values) - 1) / (target_count - 1)

        for i in range(target_count):
            pos = i * step
            lower_idx = int(pos)
            upper_idx = min(lower_idx + 1, len(values) - 1)
            fraction = pos - lower_idx

            # Linear interpolation
            value = values[lower_idx] + (values[upper_idx] - values[lower_idx]) * fraction
            upsampled.append(value)

        return upsampled

    def _render_braille_chart(self, values: list[float], width: int) -> list[str]:
        """Render indicator values as a braille chart.

        Args:
            values: List of indicator values to render
            width: Chart width in characters

        Returns:
            List of chart lines
        """
        if not values:
            return ["No data"]

        # Calculate vertical positions (use 4 dots per character row in braille)
        value_range = self._max_value - self._min_value
        if value_range == 0:
            # Flat line at middle
            vertical_positions = [self._height * 4 // 2] * len(values)
        else:
            vertical_positions = [
                int(((v - self._min_value) / value_range) * (self._height * 4 - 1))
                for v in values
            ]

        # Initialize chart grid with spaces
        chart_lines: list[str] = [" " * width for _ in range(self._height)]
        grid = [[" " for _ in range(width)] for _ in range(self._height)]

        # Braille dot patterns (8 dots per character)
        # Using dots 7 and 8 for simple line (bottom half)
        braille_base = 0x2800
        dot_7 = 0x40  # Bottom-left dot
        dot_8 = 0x80  # Bottom-right dot

        # Plot reference lines first (so data line draws over them)
        for ref_line in self._reference_lines:
            if self._min_value <= ref_line.value <= self._max_value:
                self._draw_reference_line(grid, ref_line, value_range)

        # Plot data points (2 per character for braille)
        for i in range(0, len(vertical_positions) - 1, 2):
            char_idx = i // 2
            if char_idx >= width:
                break

            left_pos = vertical_positions[i]
            right_pos = vertical_positions[i + 1] if i + 1 < len(vertical_positions) else left_pos

            # Clamp to valid range
            left_pos = max(0, min(self._height * 4 - 1, left_pos))
            right_pos = max(0, min(self._height * 4 - 1, right_pos))

            # Convert to row (invert for display - top of terminal = high values)
            left_row = (self._height * 4 - 1 - left_pos) // 4
            right_row = (self._height * 4 - 1 - right_pos) // 4

            # Use the higher row (closer to top = higher value)
            target_row = min(left_row, right_row)
            if 0 <= target_row < self._height:
                # Simple braille character for indicator line
                braille_char = chr(braille_base + dot_7 + dot_8)
                grid[target_row][char_idx] = f"[cyan]{braille_char}[/cyan]"

        # Convert grid to strings with Y-axis padding for alignment with price chart
        # Y-axis width from ChartContext (via show_indicator) or default 12
        y_axis_padding = " " * self._y_axis_width
        chart_lines = [y_axis_padding + "".join(line) for line in grid]

        return chart_lines

    def _draw_reference_line(
        self, grid: list[list[str]], ref_line: HorizontalLine, value_range: float
    ) -> None:
        """Draw a horizontal reference line on the grid.

        Args:
            grid: 2D character grid to draw on
            ref_line: Reference line configuration
            value_range: Total range of values (max - min)
        """
        if value_range == 0:
            return

        # Calculate row position for reference line
        normalized = (ref_line.value - self._min_value) / value_range
        row_pos = int(normalized * (self._height * 4 - 1))
        row = (self._height * 4 - 1 - row_pos) // 4

        if 0 <= row < self._height:
            # Choose character based on line style
            if ref_line.style == "dashed":
                char = "┄"  # Dashed horizontal line
            elif ref_line.style == "dotted":
                char = "┈"  # Dotted horizontal line
            else:  # solid
                char = "─"  # Solid horizontal line

            # Draw line across entire width
            width = len(grid[row])
            colored_char = f"[{ref_line.color}]{char}[/{ref_line.color}]"
            for col in range(width):
                # Only draw if space (don't overwrite data)
                if grid[row][col] == " ":
                    grid[row][col] = colored_char
