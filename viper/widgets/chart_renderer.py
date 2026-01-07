"""Chart rendering engine with Braille and block character support."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TypeVar, cast, overload


class ChartStyle(Enum):
    """Chart rendering style options."""

    BRAILLE = "braille"  # High-resolution using Braille patterns (2x4 dots per char)
    BLOCK = "block"  # Simple block characters (▁▂▃▄▅▆▇█)


@dataclass
class ChartDimensions:
    """Chart rendering dimensions."""

    width: int  # Width in characters
    height: int  # Height in characters
    include_y_axis: bool = True  # Whether to reserve space for Y-axis labels
    include_x_axis: bool = True  # Whether to reserve space for X-axis labels
    y_axis_width: int = 12  # Width reserved for Y-axis price labels
    x_axis_height: int = 1  # Height reserved for X-axis date labels


@dataclass
class RenderedChart:
    """Result of chart rendering."""

    lines: list[str]  # Rendered chart lines (ANSI color codes included)
    width: int  # Actual width of rendered chart
    height: int  # Actual height of rendered chart
    min_value: float  # Data minimum
    max_value: float  # Data maximum


class ChartRenderer:
    """Base class for chart renderers."""

    def __init__(self, style: ChartStyle = ChartStyle.BRAILLE) -> None:
        """Initialize chart renderer.

        Args:
            style: Rendering style (BRAILLE or BLOCK)
        """
        self.style = style

    def render(
        self,
        prices: list[float],
        dates: list[datetime] | None = None,
        dimensions: ChartDimensions | None = None,
    ) -> RenderedChart:
        """Render price data as a chart.

        Args:
            prices: List of price values to render
            dates: Optional list of datetime objects (same length as prices)
            dimensions: Chart dimensions (default: 80x20 with axes)

        Returns:
            RenderedChart with lines ready for display
        """
        if not prices:
            return RenderedChart(lines=["No data"], width=7, height=1, min_value=0.0, max_value=0.0)

        if dimensions is None:
            dimensions = ChartDimensions(width=80, height=20)

        # Delegate to specific renderer
        if self.style == ChartStyle.BRAILLE:
            return self._render_braille(prices, dates, dimensions)
        else:
            return self._render_block(prices, dates, dimensions)

    def _render_braille(
        self,
        prices: list[float],
        dates: list[datetime] | None,
        dimensions: ChartDimensions,
    ) -> RenderedChart:
        """Render chart using Braille patterns (2x4 dots per character).

        Braille Unicode range: U+2800 to U+28FF (256 patterns)
        Each character has 2 columns x 4 rows of dots:
            Dot positions:  1 4
                           2 5
                           3 6
                           7 8

        Unicode value = 0x2800 + (dot1 + dot2*2 + dot3*4 + dot4*8 + dot5*16 + dot6*32 + dot7*64 + dot8*128)
        """
        # Calculate available space for chart
        chart_width = dimensions.width
        chart_height = dimensions.height

        if dimensions.include_y_axis:
            chart_width -= dimensions.y_axis_width
        if dimensions.include_x_axis:
            chart_height -= dimensions.x_axis_height

        # Use original prices for min/max to avoid losing extremes during downsampling
        min_price = min(prices)
        max_price = max(prices)

        # Downsample data to fit chart width
        # Each braille char represents 2 horizontal data points
        max_data_points = chart_width * 2
        downsampled_prices_raw = self._downsample(prices, max_data_points)
        # Type narrowing: we know prices is list[float], so result is list[float]
        assert isinstance(downsampled_prices_raw, list) and (
            not downsampled_prices_raw or isinstance(downsampled_prices_raw[0], (int, float))
        )
        downsampled_prices: list[float] = downsampled_prices_raw

        downsampled_dates_raw = self._downsample(dates, max_data_points) if dates else None
        downsampled_dates: list[datetime] | None = downsampled_dates_raw if downsampled_dates_raw else None

        # Normalize prices to fit chart height (using original min/max)
        price_range = max_price - min_price

        if price_range == 0:
            # Flat line - all prices the same
            normalized = [0.5] * len(downsampled_prices)
        else:
            normalized = [(p - min_price) / price_range for p in downsampled_prices]

        # Scale to chart height (4 dots per row, so height * 4 vertical positions)
        vertical_positions = chart_height * 4
        scaled = [int(n * (vertical_positions - 1)) for n in normalized]

        # Render braille characters
        chart_lines = self._render_braille_line(scaled, chart_height)

        # Add Y-axis labels
        if dimensions.include_y_axis:
            chart_lines = self._add_y_axis(chart_lines, min_price, max_price, dimensions.y_axis_width)

        # Add X-axis labels
        if dimensions.include_x_axis:
            x_axis_lines = self._create_x_axis(downsampled_dates, chart_width, dimensions.y_axis_width)
            # X-axis returns multiple lines separated by \n
            chart_lines.extend(x_axis_lines.split("\n"))

        return RenderedChart(
            lines=chart_lines,
            width=len(chart_lines[0]) if chart_lines else 0,
            height=len(chart_lines),
            min_value=min_price,
            max_value=max_price,
        )

    def _render_braille_line(self, scaled_values: list[int], height: int) -> list[str]:
        """Convert scaled values to braille characters.

        Args:
            scaled_values: Values scaled to vertical positions (0 to height*4-1)
            height: Chart height in characters

        Returns:
            List of strings representing chart lines
        """
        if not scaled_values:
            return []

        # Initialize grid: height rows, each with width//2 characters (2 cols per char)
        # Braille works with 2 columns per character
        num_chars = (len(scaled_values) + 1) // 2
        lines = [[" " for _ in range(num_chars)] for _ in range(height)]

        # Process pairs of values (2 columns per braille character)
        for i in range(0, len(scaled_values), 2):
            char_idx = i // 2
            left_val = scaled_values[i]
            right_val = scaled_values[i + 1] if i + 1 < len(scaled_values) else left_val

            # Determine which row this belongs to (from bottom)
            # Higher values are at the top, so invert
            left_row = height - 1 - (left_val // 4)
            right_row = height - 1 - (right_val // 4)

            # Determine dot positions within the row (0-3)
            left_dot = left_val % 4
            right_dot = right_val % 4

            # Calculate braille pattern
            braille_char = self._get_braille_char(left_row, left_dot, right_row, right_dot, height)

            # Place character in the correct row
            # Use the topmost row that needs rendering
            target_row = min(left_row, right_row)
            if 0 <= target_row < height:
                lines[target_row][char_idx] = braille_char

        # Convert grid to strings
        return ["".join(line) for line in lines]

    def _get_braille_char(
        self, left_row: int, left_dot: int, right_row: int, right_dot: int, height: int
    ) -> str:
        """Get braille character for two adjacent columns.

        Args:
            left_row: Row index for left column
            left_dot: Dot position within row for left column (0-3)
            right_row: Row index for right column
            right_dot: Dot position within row for right column (0-3)
            height: Total chart height

        Returns:
            Braille Unicode character
        """
        # Braille dot mapping:
        #   1 4    (dots 1-3 are left column, dots 4-6 are right column)
        #   2 5
        #   3 6
        #   7 8    (dots 7-8 are bottom row)

        # For now, use a simplified approach: draw dots at the specified positions
        # This creates a line effect by filling dots vertically
        dots = 0

        # Left column (dots 1, 2, 3, 7)
        if left_dot >= 3:
            dots |= 0x01  # dot 1
        if left_dot >= 2:
            dots |= 0x02  # dot 2
        if left_dot >= 1:
            dots |= 0x04  # dot 3
        if left_dot >= 0:
            dots |= 0x40  # dot 7

        # Right column (dots 4, 5, 6, 8)
        if right_dot >= 3:
            dots |= 0x08  # dot 4
        if right_dot >= 2:
            dots |= 0x10  # dot 5
        if right_dot >= 1:
            dots |= 0x20  # dot 6
        if right_dot >= 0:
            dots |= 0x80  # dot 8

        # Convert to Unicode braille character
        return chr(0x2800 + dots)

    def _render_block(
        self,
        prices: list[float],
        dates: list[datetime] | None,
        dimensions: ChartDimensions,
    ) -> RenderedChart:
        """Render chart using block characters (▁▂▃▄▅▆▇█).

        This is a simpler fallback that provides lower resolution
        but better terminal compatibility.
        """
        # Calculate available space
        chart_width = dimensions.width
        chart_height = dimensions.height

        if dimensions.include_y_axis:
            chart_width -= dimensions.y_axis_width
        if dimensions.include_x_axis:
            chart_height -= dimensions.x_axis_height

        # Use original prices for min/max to avoid losing extremes during downsampling
        min_price = min(prices)
        max_price = max(prices)

        # Downsample data to fit width
        downsampled_prices_raw = self._downsample(prices, chart_width)
        # Type narrowing: we know prices is list[float], so result is list[float]
        assert isinstance(downsampled_prices_raw, list) and (
            not downsampled_prices_raw or isinstance(downsampled_prices_raw[0], (int, float))
        )
        downsampled_prices: list[float] = downsampled_prices_raw

        downsampled_dates_raw = self._downsample(dates, chart_width) if dates else None
        downsampled_dates: list[datetime] | None = downsampled_dates_raw if downsampled_dates_raw else None

        # Normalize prices (using original min/max)
        price_range = max_price - min_price

        if price_range == 0:
            # Flat line
            blocks = ["▄"] * len(downsampled_prices)
        else:
            # Map each price to a block character (8 levels)
            blocks_chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
            blocks = []
            for price in downsampled_prices:
                normalized = (price - min_price) / price_range
                block_idx = min(int(normalized * 8), 7)
                blocks.append(blocks_chars[block_idx])

        # For block rendering, we show a single line of blocks
        # If height > 1, center the blocks vertically
        chart_lines = []
        padding_top = (chart_height - 1) // 2
        padding_bottom = chart_height - 1 - padding_top

        for _ in range(padding_top):
            chart_lines.append(" " * len(blocks))

        chart_lines.append("".join(blocks))

        for _ in range(padding_bottom):
            chart_lines.append(" " * len(blocks))

        # Add Y-axis labels
        if dimensions.include_y_axis:
            chart_lines = self._add_y_axis(chart_lines, min_price, max_price, dimensions.y_axis_width)

        # Add X-axis labels
        if dimensions.include_x_axis:
            x_axis_lines = self._create_x_axis(downsampled_dates, chart_width, dimensions.y_axis_width)
            # X-axis returns multiple lines separated by \n
            chart_lines.extend(x_axis_lines.split("\n"))

        return RenderedChart(
            lines=chart_lines,
            width=len(chart_lines[0]) if chart_lines else 0,
            height=len(chart_lines),
            min_value=min_price,
            max_value=max_price,
        )

    @overload
    def _downsample(self, data: list[float], target_size: int) -> list[float]: ...

    @overload
    def _downsample(self, data: list[datetime], target_size: int) -> list[datetime]: ...

    @overload
    def _downsample(self, data: None, target_size: int) -> list[float]: ...

    def _downsample(
        self, data: list[float] | list[datetime] | None, target_size: int
    ) -> list[float] | list[datetime]:
        """Downsample data to fit target size.

        Uses simple even-spaced sampling.

        Args:
            data: Data to downsample
            target_size: Target number of points

        Returns:
            Downsampled data
        """
        if data is None:
            return cast(list[float], [])

        if len(data) <= target_size:
            return data

        # Calculate step size
        step = len(data) / target_size
        # Mypy can't infer the type of the list comprehension
        # Cast to help it understand the result type matches input type
        result = [data[int(i * step)] for i in range(target_size)]
        return cast(list[float], result) if isinstance(data[0], (int, float)) else cast(list[datetime], result)

    def _add_y_axis(self, chart_lines: list[str], min_value: float, max_value: float, axis_width: int) -> list[str]:
        """Add Y-axis with price labels to the left of chart.

        Args:
            chart_lines: Chart lines without Y-axis
            min_value: Minimum price
            max_value: Maximum price
            axis_width: Width to reserve for Y-axis

        Returns:
            Chart lines with Y-axis prepended
        """
        num_labels = min(len(chart_lines), 5)  # Show up to 5 price labels
        labels_at_rows = [i * len(chart_lines) // num_labels for i in range(num_labels)]

        result_lines = []
        for row_idx, line in enumerate(chart_lines):
            if row_idx in labels_at_rows:
                # Calculate price for this row (inverted - top is max, bottom is min)
                label_idx = labels_at_rows.index(row_idx)
                fraction = 1.0 - (label_idx / (num_labels - 1)) if num_labels > 1 else 0.5
                price = min_value + (max_value - min_value) * fraction
                label = f"${price:,.2f}".rjust(axis_width - 2)
                result_lines.append(f"{label} │{line}")
            else:
                # Empty label with axis line
                result_lines.append(f"{' ' * (axis_width - 2)} │{line}")

        return result_lines

    def _create_x_axis(self, dates: list[datetime] | None, chart_width: int, y_axis_width: int) -> str:
        """Create X-axis with date labels.

        Args:
            dates: List of datetime objects (or None for empty axis)
            chart_width: Width of chart area
            y_axis_width: Width of Y-axis (for alignment)

        Returns:
            X-axis line with date labels
        """
        # Create axis line
        y_padding = " " * (y_axis_width - 2) + " └"
        axis_line = "─" * chart_width

        if not dates:
            # No dates - just return empty axis
            return f"{y_padding}{axis_line}\n{' ' * (y_axis_width + chart_width)}"

        # Show first and last dates
        first_date = dates[0].strftime("%m/%d")
        last_date = dates[-1].strftime("%m/%d")

        # Place labels
        # Format: "MM/DD" + spaces + "MM/DD"
        total_width = chart_width
        if total_width >= len(first_date) + len(last_date) + 2:
            # Enough space for both labels
            padding = total_width - len(first_date) - len(last_date)
            labels = f"{first_date}{' ' * padding}{last_date}"
        else:
            # Not enough space - just show first date
            labels = first_date.ljust(total_width)

        return f"{y_padding}{axis_line}\n{' ' * y_axis_width}{labels}"


def create_chart(
    prices: list[float],
    dates: list[datetime] | None = None,
    width: int = 80,
    height: int = 20,
    style: ChartStyle = ChartStyle.BRAILLE,
    include_axes: bool = True,
) -> RenderedChart:
    """Convenience function to create a chart.

    Args:
        prices: List of price values
        dates: Optional list of dates
        width: Chart width in characters
        height: Chart height in characters
        style: Rendering style (BRAILLE or BLOCK)
        include_axes: Whether to include axis labels

    Returns:
        RenderedChart ready for display
    """
    renderer = ChartRenderer(style=style)
    dimensions = ChartDimensions(
        width=width,
        height=height,
        include_y_axis=include_axes,
        include_x_axis=include_axes,
    )
    return renderer.render(prices, dates, dimensions)
