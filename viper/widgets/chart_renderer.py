"""Chart rendering engine with Braille and block character support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, TypeVar, cast, overload

if TYPE_CHECKING:
    from viper.widgets.chart_context import ChartContext


class ChartStyle(Enum):
    """Chart rendering style options."""

    BRAILLE = "braille"  # High-resolution using Braille patterns (2x4 dots per char)
    BLOCK = "block"  # Simple block characters (▁▂▃▄▅▆▇█)


@dataclass
class OverlayData:
    """Data for a single overlay line on the chart."""

    values: list[float | None]  # Overlay values (same length as prices), None = no render
    color: str  # Rich markup color name (e.g., "cyan", "magenta")
    name: str  # Display name for legend (e.g., "SMA20")


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
    interpolated_count: int = 0  # Number of data points after interpolation (0 = no interpolation)


class ChartRenderer:
    """Base class for chart renderers."""

    def __init__(self, style: ChartStyle = ChartStyle.BRAILLE) -> None:
        """Initialize chart renderer.

        Args:
            style: Rendering style (BRAILLE or BLOCK)
        """
        self.style = style

    @overload
    def render(
        self,
        prices: list[float],
        dates: list[datetime] | None = None,
        dimensions: ChartDimensions | None = None,
        volumes: list[int] | None = None,
        opens: list[float] | None = None,
        period: str | None = None,
        overlays: list[OverlayData] | None = None,
        *,
        context: None = None,
    ) -> RenderedChart: ...

    @overload
    def render(
        self,
        prices: None = None,
        dates: None = None,
        dimensions: None = None,
        volumes: None = None,
        opens: None = None,
        period: None = None,
        overlays: list[OverlayData] | None = None,
        *,
        context: ChartContext,
    ) -> RenderedChart: ...

    def render(
        self,
        prices: list[float] | None = None,
        dates: list[datetime] | None = None,
        dimensions: ChartDimensions | None = None,
        volumes: list[int] | None = None,
        opens: list[float] | None = None,
        period: str | None = None,
        overlays: list[OverlayData] | None = None,
        *,
        context: ChartContext | None = None,
    ) -> RenderedChart:
        """Render price data as a chart.

        This method supports two calling styles:
        1. Legacy: Pass individual parameters (prices, dates, dimensions, etc.)
        2. Modern: Pass ChartContext via context= parameter (recommended)

        Args:
            prices: List of price values to render (legacy)
            dates: Optional list of datetime objects (legacy)
            dimensions: Chart dimensions (legacy, default: 80x20 with axes)
            volumes: Optional list of volume values (legacy)
            opens: Optional list of open prices (legacy)
            period: Optional time period for date formatting (legacy)
            overlays: Optional list of overlay data (e.g., moving averages)
            context: ChartContext with all data and dimensions (modern, recommended)

        Returns:
            RenderedChart with lines ready for display
        """
        # Modern path: use ChartContext
        if context is not None:
            prices = context.prices
            dates = context.dates
            dimensions = ChartDimensions(
                width=context.total_width,
                height=context.total_height,
                include_y_axis=True,
                include_x_axis=False,  # X-axis rendered separately via render_x_axis()
                y_axis_width=context.y_axis_width,
            )
            period = context.period
            # Note: volumes and opens not used in render(), but stored in context

        # Legacy path: use individual parameters
        if not prices:
            return RenderedChart(lines=["No data"], width=7, height=1, min_value=0.0, max_value=0.0)

        if dimensions is None:
            dimensions = ChartDimensions(width=80, height=20)

        # Delegate to specific renderer
        if self.style == ChartStyle.BRAILLE:
            return self._render_braille(prices, dates, dimensions, volumes, opens, period, overlays)
        else:
            return self._render_block(prices, dates, dimensions, volumes, opens, period, overlays)

    def _render_braille(
        self,
        prices: list[float],
        dates: list[datetime] | None,
        dimensions: ChartDimensions,
        volumes: list[int] | None = None,
        opens: list[float] | None = None,
        period: str | None = None,
        overlays: list[OverlayData] | None = None,
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

        # Track if we interpolated (for volume alignment)
        interpolated_count = 0

        # If we have significantly fewer data points, we need to upsample
        # to distribute them across the full chart width
        if len(prices) < max_data_points * 0.6:  # Less than 60% of target
            # Upsample by linearly interpolating between existing points
            upsampled_prices = []
            for i in range(max_data_points):
                # Map this output index to input space
                input_idx = (i / max_data_points) * len(prices)
                # Find the two surrounding data points
                idx_low = int(input_idx)
                idx_high = min(idx_low + 1, len(prices) - 1)
                # Linear interpolation weight
                weight = input_idx - idx_low
                # Interpolate
                value = prices[idx_low] * (1 - weight) + prices[idx_high] * weight
                upsampled_prices.append(value)
            downsampled_prices = upsampled_prices
            interpolated_count = max_data_points  # Signal that we interpolated

            # Also upsample dates if present
            if dates:
                upsampled_dates = []
                for i in range(max_data_points):
                    input_idx = (i / max_data_points) * len(dates)
                    idx_low = int(input_idx)
                    idx_high = min(idx_low + 1, len(dates) - 1)
                    # For dates, just use the lower index (no interpolation)
                    upsampled_dates.append(dates[idx_low])
                downsampled_dates = upsampled_dates
            else:
                downsampled_dates = None
        else:
            # Normal downsampling for sufficient data
            downsampled_prices_raw = self._downsample(prices, max_data_points)
            # Type narrowing
            assert isinstance(downsampled_prices_raw, list) and (
                not downsampled_prices_raw or isinstance(downsampled_prices_raw[0], (int, float))
            )
            downsampled_prices = downsampled_prices_raw

            downsampled_dates_raw = self._downsample(dates, max_data_points) if dates else None
            downsampled_dates = downsampled_dates_raw if downsampled_dates_raw else None

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
        chart_lines = self._render_braille_line(scaled, chart_height, chart_width)

        # Apply overlays if provided
        if overlays:
            chart_lines = self._apply_overlays_braille(
                chart_lines,
                overlays,
                downsampled_prices,
                min_price,
                max_price,
                chart_height,
                chart_width,
                max_data_points,
                interpolated_count,
            )

        # Add Y-axis labels
        if dimensions.include_y_axis:
            chart_lines = self._add_y_axis(chart_lines, min_price, max_price, dimensions.y_axis_width)

        # Add X-axis labels
        if dimensions.include_x_axis:
            x_axis_lines = self._create_x_axis(downsampled_dates, chart_width, dimensions.y_axis_width, period)
            # X-axis returns multiple lines separated by \n
            chart_lines.extend(x_axis_lines.split("\n"))

        return RenderedChart(
            lines=chart_lines,
            width=len(chart_lines[0]) if chart_lines else 0,
            height=len(chart_lines),
            min_value=min_price,
            max_value=max_price,
            interpolated_count=interpolated_count,
        )

    def _render_braille_line(self, scaled_values: list[int], height: int, target_width: int) -> list[str]:
        """Convert scaled values to braille characters.

        Args:
            scaled_values: Values scaled to vertical positions (0 to height*4-1)
            height: Chart height in characters
            target_width: Exact width in characters to render

        Returns:
            List of strings representing chart lines
        """
        if not scaled_values:
            return [" " * target_width for _ in range(height)]

        # Now we always have chart_width * 2 data points (either downsampled or upsampled)
        # So always render to target_width
        num_chars = target_width
        actual_data_points = len(scaled_values)
        
        # Initialize grid
        lines = [[" " for _ in range(num_chars)] for _ in range(height)]

        # Process data points sequentially
        for i in range(0, min(actual_data_points, num_chars * 2), 2):
            char_idx = i // 2
            if char_idx >= num_chars:
                break
                
            left_val = scaled_values[i]
            right_val = scaled_values[i + 1] if i + 1 < actual_data_points else left_val

            # Determine which row this belongs to (from bottom)
            left_row = height - 1 - (left_val // 4)
            right_row = height - 1 - (right_val // 4)

            # Determine dot positions within the row (0-3)
            left_dot = left_val % 4
            right_dot = right_val % 4

            # Calculate braille pattern
            braille_char = self._get_braille_char(left_row, left_dot, right_row, right_dot, height)

            # Place character in the correct row
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
        volumes: list[int] | None = None,
        opens: list[float] | None = None,
        period: str | None = None,
        overlays: list[OverlayData] | None = None,
    ) -> RenderedChart:
        """Render chart using block characters (▁▂▃▄▅▆▇█).

        This is a simpler fallback that provides lower resolution
        but better terminal compatibility.

        Note: Overlays are not supported in block style (ignored).
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
            x_axis_lines = self._create_x_axis(downsampled_dates, chart_width, dimensions.y_axis_width, period)
            # X-axis returns multiple lines separated by \n
            chart_lines.extend(x_axis_lines.split("\n"))

        return RenderedChart(
            lines=chart_lines,
            width=len(chart_lines[0]) if chart_lines else 0,
            height=len(chart_lines),
            min_value=min_price,
            max_value=max_price,
            interpolated_count=0,  # Block style doesn't interpolate
        )

    @overload
    def _upsample(self, data: list[float], target_size: int) -> list[float]: ...

    @overload
    def _upsample(self, data: list[int], target_size: int) -> list[int]: ...

    def _upsample(self, data: list[float] | list[int], target_size: int) -> list[float] | list[int]:
        """Upsample data using linear interpolation to reach target size.

        Uses the same algorithm as the price chart interpolation.

        Args:
            data: Data to upsample
            target_size: Target number of points

        Returns:
            Upsampled data
        """
        if len(data) >= target_size:
            return data

        is_int = isinstance(data[0], int)
        upsampled_int: list[int] = []
        upsampled_float: list[float] = []
        for i in range(target_size):
            # Map this output index to input space
            input_idx = (i / target_size) * len(data)
            # Find the two surrounding data points
            idx_low = int(input_idx)
            idx_high = min(idx_low + 1, len(data) - 1)
            # Linear interpolation weight
            weight = input_idx - idx_low
            # Interpolate
            value = data[idx_low] * (1 - weight) + data[idx_high] * weight
            if is_int:
                upsampled_int.append(int(value))
            else:
                upsampled_float.append(value)

        if is_int:
            return upsampled_int
        else:
            return upsampled_float

    @overload
    def _downsample(self, data: list[float], target_size: int) -> list[float]: ...

    @overload
    def _downsample(self, data: list[int], target_size: int) -> list[int]: ...

    @overload
    def _downsample(self, data: list[datetime], target_size: int) -> list[datetime]: ...

    @overload
    def _downsample(self, data: None, target_size: int) -> list[float]: ...

    def _downsample(
        self, data: list[float] | list[int] | list[datetime] | None, target_size: int
    ) -> list[float] | list[int] | list[datetime]:
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
        if isinstance(data[0], datetime):
            return cast(list[datetime], result)
        elif isinstance(data[0], int):
            return cast(list[int], result)
        else:
            return cast(list[float], result)

    def _apply_overlays_braille(
        self,
        chart_lines: list[str],
        overlays: list[OverlayData],
        downsampled_prices: list[float],
        min_price: float,
        max_price: float,
        chart_height: int,
        chart_width: int,
        max_data_points: int,
        interpolated_count: int,
    ) -> list[str]:
        """Apply overlay lines to rendered braille chart.

        Args:
            chart_lines: Existing chart lines (without Y-axis)
            overlays: List of overlay data to render
            downsampled_prices: Downsampled price data (for reference, not used but kept for consistency)
            min_price: Minimum price value (for scaling)
            max_price: Maximum price value (for scaling)
            chart_height: Chart height in characters
            chart_width: Chart width in characters
            max_data_points: Maximum data points (width * 2 for braille)
            interpolated_count: If > 0, indicates interpolation was applied

        Returns:
            Chart lines with overlays applied
        """
        # Convert chart lines to a mutable 2D grid
        grid = [list(line) for line in chart_lines]

        # Process each overlay
        for overlay in overlays:
            overlay_values = overlay.values
            # Use Rich markup for Textual compatibility
            color_open = f"[{overlay.color}]"
            color_close = f"[/{overlay.color}]"

            # Apply same interpolation/downsampling as main chart
            if interpolated_count > 0:
                # Upsample overlay to match interpolated data
                upsampled_overlay: list[float | None] = []
                for i in range(max_data_points):
                    input_idx = (i / max_data_points) * len(overlay_values)
                    idx_low = int(input_idx)
                    idx_high = min(idx_low + 1, len(overlay_values) - 1)

                    # Handle None values - don't interpolate across Nones
                    if overlay_values[idx_low] is None or overlay_values[idx_high] is None:
                        upsampled_overlay.append(None)
                    else:
                        weight = input_idx - idx_low
                        # Type narrowing: we know both values are not None
                        val_low = overlay_values[idx_low]
                        val_high = overlay_values[idx_high]
                        assert val_low is not None and val_high is not None
                        value = val_low * (1 - weight) + val_high * weight
                        upsampled_overlay.append(value)
                downsampled_overlay = upsampled_overlay
            else:
                # Normal downsampling
                downsampled_overlay = self._downsample_overlay(overlay_values, max_data_points)

            # Normalize and scale overlay values
            price_range = max_price - min_price
            if price_range == 0:
                continue  # Can't render overlay on flat chart

            # Scale to chart height (4 dots per row)
            vertical_positions = chart_height * 4
            scaled_overlay: list[int | None] = []
            for val in downsampled_overlay:
                if val is None:
                    scaled_overlay.append(None)
                else:
                    normalized = (val - min_price) / price_range
                    scaled_overlay.append(int(normalized * (vertical_positions - 1)))

            # Render overlay as dots/markers on the grid
            for i in range(0, min(len(scaled_overlay), chart_width * 2), 2):
                char_idx = i // 2
                if char_idx >= chart_width:
                    break

                left_val = scaled_overlay[i]
                right_val = scaled_overlay[i + 1] if i + 1 < len(scaled_overlay) else None

                # Skip None values
                if left_val is None and right_val is None:
                    continue

                # Determine positions
                if left_val is not None:
                    left_row = chart_height - 1 - (left_val // 4)
                    left_dot = left_val % 4
                else:
                    left_row = None
                    left_dot = None

                if right_val is not None:
                    right_row = chart_height - 1 - (right_val // 4)
                    right_dot = right_val % 4
                else:
                    right_row = None
                    right_dot = None

                # Get overlay character
                if left_row is not None or right_row is not None:
                    overlay_char = self._get_overlay_braille_char(
                        left_row, left_dot, right_row, right_dot, chart_height
                    )

                    # Determine target row (use whichever is available)
                    if left_row is not None and right_row is not None:
                        target_row = min(left_row, right_row)
                    elif left_row is not None:
                        target_row = left_row
                    elif right_row is not None:
                        target_row = right_row
                    else:
                        continue  # Both None, skip this iteration

                    # Apply colored overlay character with Rich markup
                    if 0 <= target_row < chart_height and 0 <= char_idx < chart_width:
                        grid[target_row][char_idx] = f"{color_open}{overlay_char}{color_close}"

        # Convert grid back to strings
        return ["".join(line) for line in grid]

    def _get_overlay_braille_char(
        self, left_row: int | None, left_dot: int | None, right_row: int | None, right_dot: int | None, height: int
    ) -> str:
        """Get braille character for overlay dots.

        Uses smaller dots to distinguish from main chart.

        Args:
            left_row: Row index for left column (or None)
            left_dot: Dot position within row for left column (0-3) (or None)
            right_row: Row index for right column (or None)
            right_dot: Dot position within row for right column (0-3) (or None)
            height: Total chart height

        Returns:
            Braille Unicode character
        """
        dots = 0

        # For overlays, use single dots rather than full vertical lines
        # This creates a more subtle marker effect
        if left_row is not None and left_dot is not None:
            # Just use dot 7 (bottom of left column) as marker
            dots |= 0x40  # dot 7

        if right_row is not None and right_dot is not None:
            # Just use dot 8 (bottom of right column) as marker
            dots |= 0x80  # dot 8

        return chr(0x2800 + dots)

    def _downsample_overlay(self, values: list[float | None], target_size: int) -> list[float | None]:
        """Downsample overlay data, preserving None values.

        Args:
            values: Overlay values with potential None entries
            target_size: Target number of points

        Returns:
            Downsampled overlay data
        """
        if len(values) <= target_size:
            return values

        # Calculate step size
        step = len(values) / target_size
        return [values[int(i * step)] for i in range(target_size)]

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
        # Distribute labels evenly from row 0 (top) to row len-1 (bottom)
        # so that min/max labels align with the actual data range
        if num_labels > 1:
            labels_at_rows = [i * (len(chart_lines) - 1) // (num_labels - 1) for i in range(num_labels)]
        else:
            labels_at_rows = [0]

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

    def _create_x_axis(
        self, dates: list[datetime] | None, chart_width: int, y_axis_width: int, period: str | None = None
    ) -> str:
        """Create X-axis with date labels.

        Args:
            dates: List of datetime objects (or None for empty axis)
            chart_width: Width of chart area
            y_axis_width: Width of Y-axis (for alignment)
            period: Time period for formatting (1W, 1M, 1Y, 5Y, MAX, etc.)

        Returns:
            X-axis line with date labels (includes newline separator)
        """
        # Create axis line
        y_padding = " " * (y_axis_width - 2) + " └"
        axis_line = "─" * chart_width

        if not dates:
            # No dates - just return empty axis
            return f"{y_padding}{axis_line}\n{' ' * (y_axis_width + chart_width)}"

        # Determine date format based on period
        # Short periods: MM/DD
        # Medium periods (1Y): MMM 'YY
        # Long periods (2Y+, MAX): YYYY
        if period in ("2Y", "5Y", "MAX"):
            # Multi-year: show year
            first_label = dates[0].strftime("%Y")
            last_label = dates[-1].strftime("%Y")
        elif period in ("1Y",):
            # 1 year: show month and abbreviated year
            first_label = dates[0].strftime("%b '%y")
            last_label = dates[-1].strftime("%b '%y")
        elif period in ("3M", "6M"):
            # Multi-month: show month/day/year abbreviated
            first_label = dates[0].strftime("%m/%d/%y")
            last_label = dates[-1].strftime("%m/%d/%y")
        else:
            # Short periods (1W, 1M): show MM/DD
            first_label = dates[0].strftime("%m/%d")
            last_label = dates[-1].strftime("%m/%d")

        # Place labels
        total_width = chart_width
        if total_width >= len(first_label) + len(last_label) + 2:
            # Enough space for both labels
            padding = total_width - len(first_label) - len(last_label)
            labels = f"{first_label}{' ' * padding}{last_label}"
        else:
            # Not enough space - just show first date
            labels = first_label.ljust(total_width)

        return f"{y_padding}{axis_line}\n{' ' * y_axis_width}{labels}"

    def render_volume_bars(
        self,
        volumes: list[int],
        opens: list[float],
        closes: list[float],
        width: int,
        height: int = 3,
        y_axis_width: int = 12,
        style: ChartStyle | None = None,
        interpolated_count: int = 0,
    ) -> list[str]:
        """Render volume bars below the price chart.

        Args:
            volumes: List of volume values
            opens: List of open prices (for color determination)
            closes: List of close prices (for color determination)
            width: Width of chart area in characters
            height: Height in characters for volume bars (default: 3)
            y_axis_width: Width of Y-axis for alignment
            style: Chart style (BRAILLE or BLOCK) - if BRAILLE, each char represents 2 data points
            interpolated_count: If > 0, price chart was upsampled to this many points. Apply same upsampling.

        Returns:
            List of strings representing volume bar lines with ANSI color codes
        """
        if not volumes or not opens or not closes:
            return []

        # For braille charts, each character represents 2 data points
        # So we need to downsample to width * 2 points, then compress to width chars
        if style == ChartStyle.BRAILLE:
            target_data_points = width * 2
        else:
            target_data_points = width

        # If price chart was interpolated, apply same interpolation to volume data
        if interpolated_count > 0:
            # Upsample volumes/opens/closes to match interpolated price data
            volumes = self._upsample(volumes, interpolated_count)
            opens = self._upsample(opens, interpolated_count)
            closes = self._upsample(closes, interpolated_count)

        # Downsample to target data points
        downsampled_volumes_raw = self._downsample(volumes, target_data_points)
        downsampled_opens_raw = self._downsample(opens, target_data_points)
        downsampled_closes_raw = self._downsample(closes, target_data_points)

        # Type narrowing
        assert isinstance(downsampled_volumes_raw, list) and (
            not downsampled_volumes_raw or isinstance(downsampled_volumes_raw[0], (int, float))
        )
        assert isinstance(downsampled_opens_raw, list) and (
            not downsampled_opens_raw or isinstance(downsampled_opens_raw[0], (int, float))
        )
        assert isinstance(downsampled_closes_raw, list) and (
            not downsampled_closes_raw or isinstance(downsampled_closes_raw[0], (int, float))
        )

        downsampled_volumes: list[int] = [int(v) for v in downsampled_volumes_raw]
        downsampled_opens: list[float] = downsampled_opens_raw
        downsampled_closes: list[float] = downsampled_closes_raw

        # If braille style, compress pairs of data points into single characters
        if style == ChartStyle.BRAILLE:
            # Average pairs of volumes for each displayed character
            compressed_volumes = []
            compressed_opens = []
            compressed_closes = []
            for i in range(0, len(downsampled_volumes), 2):
                if i + 1 < len(downsampled_volumes):
                    # Average two consecutive volumes
                    compressed_volumes.append((downsampled_volumes[i] + downsampled_volumes[i + 1]) // 2)
                    compressed_opens.append((downsampled_opens[i] + downsampled_opens[i + 1]) / 2)
                    compressed_closes.append((downsampled_closes[i] + downsampled_closes[i + 1]) / 2)
                else:
                    # Odd number - use last value as-is
                    compressed_volumes.append(downsampled_volumes[i])
                    compressed_opens.append(downsampled_opens[i])
                    compressed_closes.append(downsampled_closes[i])
            
            downsampled_volumes = compressed_volumes
            downsampled_opens = compressed_opens
            downsampled_closes = compressed_closes

        # Normalize volumes to 0-1 range
        max_volume = max(downsampled_volumes) if downsampled_volumes else 1
        if max_volume == 0:
            max_volume = 1

        # Block characters for volume (8 levels)
        block_chars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        # Build volume bar string with Rich markup colors
        # Use Rich markup tags instead of ANSI codes for Textual compatibility
        volume_bars = []
        for i, vol in enumerate(downsampled_volumes):
            # Normalize to 0-1
            normalized = vol / max_volume
            # Map to block character (0-8)
            block_idx = min(int(normalized * 8), 8)
            block_char = block_chars[block_idx]

            # Determine color: green if close > open, red otherwise
            if i < len(downsampled_closes) and i < len(downsampled_opens):
                if downsampled_closes[i] > downsampled_opens[i]:
                    volume_bars.append(f"[green]{block_char}[/green]")
                else:
                    volume_bars.append(f"[red]{block_char}[/red]")
            else:
                volume_bars.append(block_char)

        # Create volume bar line
        volume_line = "".join(volume_bars)

        # Create result with Y-axis padding for alignment
        y_padding = " " * y_axis_width
        result_lines = []

        # Add spacing line before volume bars
        result_lines.append(y_padding + " " * width)

        # Add volume label
        result_lines.append(y_padding + volume_line)

        # Add spacing lines to reach target height
        for _ in range(height - 2):
            result_lines.append(y_padding + " " * width)

        return result_lines


def render_x_axis(context: ChartContext) -> list[str]:
    """Render X-axis with date labels as a standalone component.

    This function extracts X-axis rendering to be rendered once at the bottom
    of the chart layout, shared by price chart and all indicator panels.

    Args:
        context: ChartContext with dates, period, and dimension information

    Returns:
        List of strings representing X-axis lines (typically 2 lines: border + labels)

    Example:
        >>> context = ChartContext.from_historical_data(data, width=80, height=20)
        >>> x_axis_lines = render_x_axis(context)
        >>> for line in x_axis_lines:
        ...     print(line)
    """
    # Use ChartContext to extract all needed information
    dates = context.dates
    chart_width = context.chart_area_width
    y_axis_width = context.y_axis_width
    period = context.period

    # Create axis line
    y_padding = " " * (y_axis_width - 2) + " └"
    axis_line = "─" * chart_width

    if not dates:
        # No dates - just return empty axis
        return [
            f"{y_padding}{axis_line}",
            f"{' ' * (y_axis_width + chart_width)}"
        ]

    # Determine date format based on period
    # Short periods: MM/DD
    # Medium periods (1Y): MMM 'YY
    # Long periods (2Y+, MAX): YYYY
    if period in ("2Y", "5Y", "MAX"):
        # Multi-year: show year
        first_label = dates[0].strftime("%Y")
        last_label = dates[-1].strftime("%Y")
    elif period in ("1Y",):
        # 1 year: show month and abbreviated year
        first_label = dates[0].strftime("%b '%y")
        last_label = dates[-1].strftime("%b '%y")
    elif period in ("3M", "6M"):
        # Multi-month: show month/day/year abbreviated
        first_label = dates[0].strftime("%m/%d/%y")
        last_label = dates[-1].strftime("%m/%d/%y")
    else:
        # Short periods (1W, 1M): show MM/DD
        first_label = dates[0].strftime("%m/%d")
        last_label = dates[-1].strftime("%m/%d")

    # Place labels
    total_width = chart_width
    if total_width >= len(first_label) + len(last_label) + 2:
        # Enough space for both labels
        padding = total_width - len(first_label) - len(last_label)
        labels = f"{first_label}{' ' * padding}{last_label}"
    else:
        # Not enough space - just show first date
        labels = first_label.ljust(total_width)

    return [
        f"{y_padding}{axis_line}",
        f"{' ' * y_axis_width}{labels}"
    ]


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
