"""Tests for chart rendering engine."""

from datetime import datetime, timedelta

import pytest

from viper.services.history_data import HistoricalData
from viper.widgets.chart_context import ChartContext
from viper.widgets.chart_renderer import (
    ChartDimensions,
    ChartRenderer,
    ChartStyle,
    OverlayData,
    RenderedChart,
    create_chart,
    render_x_axis,
)


class TestChartRenderer:
    """Test suite for ChartRenderer."""

    def test_empty_data(self) -> None:
        """Test rendering with empty price data."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        result = renderer.render(prices=[], dates=None)

        assert result.lines == ["No data"]
        assert result.width == 7
        assert result.height == 1
        assert result.min_value == 0.0
        assert result.max_value == 0.0

    def test_single_price(self) -> None:
        """Test rendering with a single price point."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=20, height=10, include_y_axis=False, include_x_axis=False)
        result = renderer.render(prices=[100.0], dates=None, dimensions=dimensions)

        assert result.height == 10
        assert result.min_value == 100.0
        assert result.max_value == 100.0
        # Should render something (not crash)
        assert len(result.lines) > 0

    def test_flat_line(self) -> None:
        """Test rendering when all prices are the same."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=20, height=10, include_y_axis=False, include_x_axis=False)
        prices = [100.0] * 50

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        assert result.min_value == 100.0
        assert result.max_value == 100.0
        assert result.height == 10
        # Flat line should render successfully
        assert len(result.lines) == 10

    def test_ascending_prices(self) -> None:
        """Test rendering with ascending price data."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [float(i) for i in range(1, 101)]  # 1 to 100

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        assert result.min_value == 1.0
        assert result.max_value == 100.0
        assert result.height == 10
        assert len(result.lines) == 10
        # Check that we got valid output
        for line in result.lines:
            assert isinstance(line, str)

    def test_descending_prices(self) -> None:
        """Test rendering with descending price data."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [float(i) for i in range(100, 0, -1)]  # 100 to 1

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        assert result.min_value == 1.0
        assert result.max_value == 100.0
        assert result.height == 10
        assert len(result.lines) == 10

    def test_volatile_prices(self) -> None:
        """Test rendering with volatile (zigzag) price data."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        # Create zigzag pattern
        prices = [100.0 + (50.0 if i % 2 == 0 else -50.0) for i in range(50)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        assert result.min_value == 50.0
        assert result.max_value == 150.0
        assert result.height == 10

    def test_downsampling(self) -> None:
        """Test that large datasets are downsampled to fit width."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        # Create 1000 data points
        prices = [float(i) for i in range(1000)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should be downsampled to fit in 40 chars (80 data points for braille)
        assert result.height == 10
        assert len(result.lines) == 10

    def test_braille_style(self) -> None:
        """Test rendering with BRAILLE style."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [float(i) for i in range(1, 51)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Braille characters should be in Unicode range U+2800 to U+28FF
        for line in result.lines:
            for char in line:
                if char != " ":
                    # Allow space or braille characters
                    assert char == " " or (0x2800 <= ord(char) <= 0x28FF)

    def test_block_style(self) -> None:
        """Test rendering with BLOCK style."""
        renderer = ChartRenderer(style=ChartStyle.BLOCK)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [float(i) for i in range(1, 51)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Block characters: ▁▂▃▄▅▆▇█
        blocks = "▁▂▃▄▅▆▇█"
        # At least one line should contain block characters
        has_blocks = any(any(c in blocks for c in line) for line in result.lines)
        assert has_blocks

    def test_y_axis_labels(self) -> None:
        """Test that Y-axis labels are added correctly."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=True, include_x_axis=False, y_axis_width=12)
        prices = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Y-axis should be present
        assert result.height == 10
        # Check that at least some lines have the Y-axis character │
        has_axis = any("│" in line for line in result.lines)
        assert has_axis
        # Check that price labels are present (should have $ sign)
        has_price = any("$" in line for line in result.lines)
        assert has_price

    def test_x_axis_labels(self) -> None:
        """Test that X-axis labels are added correctly."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=False, include_x_axis=True, x_axis_height=1)

        # Create dates
        start_date = datetime(2024, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(30)]
        prices = [100.0 + i for i in range(30)]

        result = renderer.render(prices=prices, dates=dates, dimensions=dimensions)

        # X-axis should be present (height should include axis)
        assert result.height == 11  # 10 chart + 1 axis
        # Last line should contain date format (MM/DD)
        last_line = result.lines[-1]
        # Should have date-like strings
        assert any(char.isdigit() for char in last_line)

    def test_both_axes(self) -> None:
        """Test rendering with both X and Y axes."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=True, include_x_axis=True)

        start_date = datetime(2024, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(30)]
        prices = [100.0 + i * 2 for i in range(30)]

        result = renderer.render(prices=prices, dates=dates, dimensions=dimensions)

        # Should have both axes
        assert result.height == 11  # 10 chart + 1 x-axis
        # Check for Y-axis
        has_y_axis = any("│" in line for line in result.lines[:-1])  # Exclude last line (x-axis)
        assert has_y_axis
        # Check for X-axis
        has_x_axis = "─" in result.lines[-1] or any(char.isdigit() for char in result.lines[-1])
        assert has_x_axis

    def test_dimensions_respected(self) -> None:
        """Test that specified dimensions are respected."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)

        # Test various dimensions
        dimensions_list = [
            ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False),
            ChartDimensions(width=80, height=20, include_y_axis=False, include_x_axis=False),
            ChartDimensions(width=20, height=5, include_y_axis=False, include_x_axis=False),
        ]

        prices = [float(i) for i in range(1, 51)]

        for dims in dimensions_list:
            result = renderer.render(prices=prices, dates=None, dimensions=dims)
            assert result.height == dims.height

    def test_realistic_stock_data(self) -> None:
        """Test with realistic stock price data."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=80, height=20, include_y_axis=True, include_x_axis=True)

        # Simulate 1 month of daily stock prices
        start_date = datetime(2024, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(30)]
        # Simulate stock going from $150 to $165
        prices = [150.0 + i * 0.5 + (i % 3) * 2 for i in range(30)]

        result = renderer.render(prices=prices, dates=dates, dimensions=dimensions)

        assert result.min_value >= 150.0
        assert result.max_value <= 200.0
        assert result.height == 21  # 20 chart + 1 x-axis
        assert len(result.lines) == 21

    def test_small_terminal(self) -> None:
        """Test rendering in a small terminal (80x24)."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=80, height=10, include_y_axis=True, include_x_axis=True)

        start_date = datetime(2024, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(7)]
        prices = [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0]

        result = renderer.render(prices=prices, dates=dates, dimensions=dimensions)

        # Should render without issues
        assert result.height == 11  # 10 chart + 1 axis
        assert len(result.lines) > 0

    def test_very_small_chart(self) -> None:
        """Test rendering in a very small space."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=20, height=5, include_y_axis=True, include_x_axis=False)
        prices = [100.0, 105.0, 110.0]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should render without crashing
        assert result.height == 5
        assert len(result.lines) > 0


class TestConvenienceFunction:
    """Test suite for create_chart convenience function."""

    def test_create_chart_default(self) -> None:
        """Test create_chart with default parameters."""
        prices = [float(i) for i in range(1, 51)]
        result = create_chart(prices)

        # Should use default dimensions (80x20) with axes
        assert result.height == 21  # 20 chart + 1 x-axis
        assert result.min_value == 1.0
        assert result.max_value == 50.0

    def test_create_chart_custom_dimensions(self) -> None:
        """Test create_chart with custom dimensions."""
        prices = [float(i) for i in range(1, 51)]
        result = create_chart(prices, width=60, height=15)

        assert result.height == 16  # 15 chart + 1 x-axis

    def test_create_chart_with_dates(self) -> None:
        """Test create_chart with dates."""
        start_date = datetime(2024, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(30)]
        prices = [100.0 + i for i in range(30)]

        result = create_chart(prices, dates=dates)

        assert result.height == 21  # 20 chart + 1 x-axis
        # Should have date labels
        assert any(char.isdigit() for char in result.lines[-1])

    def test_create_chart_block_style(self) -> None:
        """Test create_chart with BLOCK style."""
        prices = [float(i) for i in range(1, 51)]
        result = create_chart(prices, style=ChartStyle.BLOCK)

        blocks = "▁▂▃▄▅▆▇█"
        has_blocks = any(any(c in blocks for c in line) for line in result.lines)
        assert has_blocks

    def test_create_chart_no_axes(self) -> None:
        """Test create_chart without axes."""
        prices = [float(i) for i in range(1, 51)]
        result = create_chart(prices, include_axes=False, width=40, height=10)

        # Without axes, height should match specified height
        assert result.height == 10


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_single_data_point_block_style(self) -> None:
        """Test BLOCK style with single data point."""
        renderer = ChartRenderer(style=ChartStyle.BLOCK)
        dimensions = ChartDimensions(width=20, height=10, include_y_axis=False, include_x_axis=False)
        result = renderer.render(prices=[100.0], dates=None, dimensions=dimensions)

        assert result.min_value == 100.0
        assert result.max_value == 100.0

    def test_two_identical_prices(self) -> None:
        """Test with two identical prices."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=20, height=10, include_y_axis=False, include_x_axis=False)
        result = renderer.render(prices=[100.0, 100.0], dates=None, dimensions=dimensions)

        assert result.min_value == 100.0
        assert result.max_value == 100.0

    def test_very_small_price_range(self) -> None:
        """Test with very small price variations."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        # Prices vary by only 0.01
        prices = [100.00, 100.01, 100.00, 100.01, 100.00]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Use a slightly larger epsilon for floating point comparison
        assert abs(result.max_value - result.min_value) <= 0.011

    def test_very_large_prices(self) -> None:
        """Test with very large price values."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=True, include_x_axis=False)
        prices = [10000.0 + i * 100 for i in range(50)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        assert result.min_value >= 10000.0
        assert result.max_value <= 15000.0

    def test_negative_prices(self) -> None:
        """Test with negative prices (e.g., futures)."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [-10.0, -5.0, 0.0, 5.0, 10.0]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        assert result.min_value == -10.0
        assert result.max_value == 10.0

    def test_mismatched_dates_length(self) -> None:
        """Test when dates list length doesn't match prices."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=True)

        # More prices than dates
        prices = [100.0 + i for i in range(30)]
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(10)]

        # Should handle gracefully (downsample dates too)
        result = renderer.render(prices=prices, dates=dates, dimensions=dimensions)

        # Should still render successfully
        assert len(result.lines) > 0

    def test_none_dates(self) -> None:
        """Test with None dates when X-axis is requested."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=True)
        prices = [100.0 + i for i in range(30)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should render chart without X-axis labels (just the line)
        assert len(result.lines) > 0

    def test_chart_wider_than_data(self) -> None:
        """Test when chart width is much larger than data points."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=200, height=10, include_y_axis=False, include_x_axis=False)
        prices = [100.0, 110.0, 120.0]  # Only 3 points

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should render without issues (no upsampling, just spread out)
        assert result.height == 10


class TestVolumeRendering:
    """Test suite for volume bar rendering."""

    def test_render_volume_bars_basic(self) -> None:
        """Test basic volume bar rendering."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        volumes = [1000000, 2000000, 1500000, 3000000, 2500000]
        opens = [100.0, 105.0, 103.0, 108.0, 110.0]
        closes = [105.0, 103.0, 108.0, 110.0, 112.0]

        result = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=50,
            height=3,
            y_axis_width=12,
        )

        # Should return 3 lines (height=3)
        assert len(result) == 3
        # Each line should have y-axis padding
        for line in result:
            assert line.startswith(" " * 12)

    def test_render_volume_bars_empty(self) -> None:
        """Test volume bar rendering with empty data."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)

        result = renderer.render_volume_bars(
            volumes=[],
            opens=[],
            closes=[],
            width=50,
            height=3,
            y_axis_width=12,
        )

        # Should return empty list for empty data
        assert result == []

    def test_render_volume_bars_color_logic(self) -> None:
        """Test that volume bars use correct colors based on close vs open."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        # Setup: close > open = green, close < open = red
        volumes = [1000000, 2000000, 1500000]
        opens = [100.0, 105.0, 103.0]
        closes = [105.0, 103.0, 108.0]  # up, down, up

        result = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=10,
            height=3,
            y_axis_width=12,
        )

        # Check that Rich markup color tags are present
        volume_line = result[1]  # Middle line has the volume bars
        assert "[green]" in volume_line or "[red]" in volume_line  # Rich markup tags

    def test_render_volume_bars_normalization(self) -> None:
        """Test that volume bars are normalized to max volume."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        # Max volume should get tallest bar (█)
        volumes = [1000000, 5000000, 2000000]  # Middle is max
        opens = [100.0, 100.0, 100.0]
        closes = [101.0, 101.0, 101.0]  # All green

        result = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=10,
            height=3,
            y_axis_width=12,
        )

        # Volume line should contain block characters
        volume_line = result[1]
        # Check for block characters
        block_chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        has_block = any(char in volume_line for char in block_chars)
        assert has_block

    def test_render_volume_bars_downsampling(self) -> None:
        """Test that volume bars downsample when data exceeds width."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        # 100 data points but only 20 width
        volumes = [i * 10000 for i in range(100)]
        opens = [100.0 + i for i in range(100)]
        closes = [101.0 + i for i in range(100)]

        result = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=20,
            height=3,
            y_axis_width=12,
        )

        # Should still render successfully
        assert len(result) == 3
        # Volume line should have reasonable length
        volume_line = result[1]
        assert len(volume_line) > 0

    def test_render_volume_bars_zero_volumes(self) -> None:
        """Test volume bars with all zero volumes."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        volumes = [0, 0, 0, 0, 0]
        opens = [100.0, 100.0, 100.0, 100.0, 100.0]
        closes = [101.0, 101.0, 101.0, 101.0, 101.0]

        result = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=10,
            height=3,
            y_axis_width=12,
        )

        # Should handle zero volumes gracefully
        assert len(result) == 3

    def test_interpolated_count_returned(self) -> None:
        """Test that interpolated_count is returned when data is upsampled."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=False, include_x_axis=False)

        # Small dataset that will trigger upsampling (< 60% of max_data_points)
        # max_data_points = 60 * 2 = 120, so < 72 points triggers upsampling
        prices = [100.0, 110.0, 105.0, 115.0, 120.0]  # Only 5 points

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should have been interpolated to 120 data points
        assert result.interpolated_count == 120

    def test_no_interpolation_with_sufficient_data(self) -> None:
        """Test that interpolated_count is 0 when no upsampling occurs."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=False, include_x_axis=False)

        # Enough data points (>= 60% of max_data_points)
        # max_data_points = 120, so >= 72 points means no upsampling
        prices = [100.0 + i for i in range(100)]  # 100 points

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should NOT have been interpolated
        assert result.interpolated_count == 0

    def test_volume_alignment_with_interpolation(self) -> None:
        """Test that volume bars align with price chart when interpolation occurs."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=False, include_x_axis=False)

        # Small dataset that will trigger upsampling
        prices = [100.0, 110.0, 105.0, 115.0, 120.0]  # 5 points
        volumes = [1000000, 2000000, 1500000, 3000000, 2500000]  # 5 points
        opens = [100.0, 108.0, 105.0, 112.0, 118.0]
        closes = prices

        # Render price chart (will trigger interpolation)
        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Now render volume bars with interpolation info
        volume_lines = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=60,
            height=3,
            y_axis_width=12,
            style=ChartStyle.BRAILLE,
            interpolated_count=result.interpolated_count,
        )

        # Volume bars should render successfully with same alignment
        assert len(volume_lines) == 3

    def test_volume_alignment_without_interpolation(self) -> None:
        """Test that volume bars work normally when no interpolation occurs."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)

        # Enough data points (no interpolation)
        prices = [100.0 + i for i in range(100)]
        volumes = [1000000 + i * 10000 for i in range(100)]
        opens = [100.0 + i for i in range(100)]
        closes = prices

        # Render with no interpolation
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)
        assert result.interpolated_count == 0

        # Volume bars should work the same as before
        volume_lines = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=40,
            height=3,
            y_axis_width=12,
            style=ChartStyle.BRAILLE,
            interpolated_count=0,
        )

        assert len(volume_lines) == 3

    def test_volume_upsampling_edge_cases(self) -> None:
        """Test volume bar upsampling with various edge case data sizes."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)

        # Test with single data point
        volumes = [1000000]
        opens = [100.0]
        closes = [105.0]

        volume_lines = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=20,
            height=3,
            y_axis_width=12,
            style=ChartStyle.BRAILLE,
            interpolated_count=40,  # Simulate interpolation to 40 points
        )

        # Should handle upsampling from 1 point
        assert len(volume_lines) == 3

        # Test with exactly 2 points
        volumes = [1000000, 2000000]
        opens = [100.0, 105.0]
        closes = [105.0, 110.0]

        volume_lines = renderer.render_volume_bars(
            volumes=volumes,
            opens=opens,
            closes=closes,
            width=30,
            height=3,
            y_axis_width=12,
            style=ChartStyle.BRAILLE,
            interpolated_count=60,  # Simulate interpolation to 60 points
        )

        # Should handle upsampling from 2 points
        assert len(volume_lines) == 3


class TestOverlayRendering:
    """Test suite for overlay line rendering."""

    def test_single_overlay_basic(self) -> None:
        """Test rendering with a single overlay."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        # Create price data
        prices = [100.0 + i for i in range(50)]

        # Create overlay (e.g., moving average)
        overlay_values = [None] * 10 + [105.0 + i for i in range(40)]  # First 10 are None
        overlay = OverlayData(
            values=overlay_values,
            color="cyan",  # Rich cyan markup
            name="SMA20"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should render successfully
        assert result.height == 10
        assert len(result.lines) == 10
        # Should contain ANSI color codes from overlay
        chart_text = "".join(result.lines)
        assert "[cyan]" in chart_text  # Rich cyan markup

    def test_multiple_overlays(self) -> None:
        """Test rendering with multiple overlays."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        prices = [100.0 + i * 0.5 for i in range(50)]

        # Two overlays with different colors
        overlay1 = OverlayData(
            values=[None] * 10 + [102.0 + i * 0.5 for i in range(40)],
            color="cyan",  # Rich cyan markup
            name="SMA20"
        )
        overlay2 = OverlayData(
            values=[None] * 20 + [104.0 + i * 0.5 for i in range(30)],
            color="magenta",  # Rich magenta markup
            name="SMA50"
        )

        result = renderer.render(
            prices=prices,
            dates=None,
            dimensions=dimensions,
            overlays=[overlay1, overlay2]
        )

        # Should contain both color codes
        chart_text = "".join(result.lines)
        assert "[cyan]" in chart_text  # Rich cyan markup
        assert "[magenta]" in chart_text  # Rich magenta markup

    def test_overlay_with_all_none_values(self) -> None:
        """Test overlay where all values are None."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        prices = [100.0 + i for i in range(50)]
        overlay = OverlayData(
            values=[None] * 50,  # All None
            color="cyan",
            name="Empty"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should render without errors, but overlay won't be visible
        assert result.height == 10
        assert len(result.lines) == 10

    def test_overlay_none_handling(self) -> None:
        """Test that None values in overlay are not rendered."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        prices = [100.0 + i for i in range(50)]
        # Overlay with gaps (None values in middle)
        overlay_values = [105.0 + i for i in range(20)] + [None] * 10 + [115.0 + i for i in range(20)]
        overlay = OverlayData(
            values=overlay_values,
            color="\033[33m",  # Yellow
            name="Gapped"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should render successfully (gaps won't cause errors)
        assert result.height == 10

    def test_overlay_alignment_with_interpolation(self) -> None:
        """Test that overlays align correctly when price chart is interpolated."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=False, include_x_axis=False)

        # Small dataset that triggers interpolation (< 60% of max_data_points)
        prices = [100.0, 110.0, 105.0, 115.0, 120.0]  # 5 points
        overlay_values = [None, 108.0, 107.0, 113.0, 118.0]  # 5 points, first is None

        overlay = OverlayData(
            values=overlay_values,
            color="cyan",
            name="MA"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should have been interpolated
        assert result.interpolated_count == 120  # 60 * 2
        # Should render successfully with overlay aligned
        assert len(result.lines) == 10

    def test_overlay_downsampling(self) -> None:
        """Test that overlays are downsampled correctly for large datasets."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        # Large dataset (more than chart can display)
        prices = [100.0 + i * 0.1 for i in range(200)]
        overlay_values = [102.0 + i * 0.1 for i in range(200)]

        overlay = OverlayData(
            values=overlay_values,
            color="cyan",
            name="SMA"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should render successfully with downsampling
        assert result.height == 10
        assert len(result.lines) == 10

    def test_overlay_flat_price_chart(self) -> None:
        """Test overlay on a flat (zero range) price chart."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        # All prices the same
        prices = [100.0] * 50
        overlay_values = [100.0] * 50  # Also flat

        overlay = OverlayData(
            values=overlay_values,
            color="cyan",
            name="Flat"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should render (overlay won't be visible on flat chart due to price_range == 0 check)
        assert result.height == 10

    def test_overlay_with_empty_overlays_list(self) -> None:
        """Test that empty overlays list works correctly."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        prices = [100.0 + i for i in range(50)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[])

        # Should render normally without overlays
        assert result.height == 10
        assert len(result.lines) == 10

    def test_overlay_no_overlays_parameter(self) -> None:
        """Test backward compatibility when overlays parameter is not provided."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        prices = [100.0 + i for i in range(50)]

        # Don't pass overlays parameter at all
        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should render normally
        assert result.height == 10
        assert len(result.lines) == 10

    def test_overlay_block_style_ignores_overlays(self) -> None:
        """Test that block style ignores overlays (not supported)."""
        renderer = ChartRenderer(style=ChartStyle.BLOCK)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        prices = [100.0 + i for i in range(50)]
        overlay = OverlayData(
            values=[105.0 + i for i in range(50)],
            color="cyan",
            name="SMA"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should render successfully (overlay ignored)
        assert result.height == 10

    def test_overlay_with_y_axis(self) -> None:
        """Test overlay rendering with Y-axis enabled."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=True, include_x_axis=False)

        prices = [100.0 + i for i in range(50)]
        overlay = OverlayData(
            values=[None] * 10 + [105.0 + i for i in range(40)],
            color="cyan",
            name="SMA20"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should render with Y-axis (overlay applied before Y-axis is added)
        assert result.height == 10
        # Check for Y-axis markers
        assert any("│" in line for line in result.lines)

    def test_overlay_values_outside_price_range(self) -> None:
        """Test overlay with values outside the main price range."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)

        # Price range: 100-150
        prices = [100.0 + i for i in range(50)]
        # Overlay extends beyond price range
        overlay_values = [90.0 + i for i in range(50)]  # Starts below price range

        overlay = OverlayData(
            values=overlay_values,
            color="cyan",
            name="BelowRange"
        )

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions, overlays=[overlay])

        # Should still render (overlay will be clipped or scaled appropriately)
        assert result.height == 10


class TestCandlestickStyle:
    """Test suite for candlestick chart style (VPR-088)."""

    def test_candlestick_enum_exists(self) -> None:
        """Test that CANDLESTICK enum value exists and is usable."""
        # Verify the enum value exists
        assert hasattr(ChartStyle, "CANDLESTICK")
        assert ChartStyle.CANDLESTICK.value == "candlestick"

    def test_candlestick_renderer_basic(self) -> None:
        """Test basic rendering with CANDLESTICK style."""
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [float(i) for i in range(1, 51)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should render successfully (stub delegates to braille)
        assert result.height == 10
        assert len(result.lines) == 10
        assert result.min_value == 1.0
        assert result.max_value == 50.0

    def test_candlestick_style_dispatch(self) -> None:
        """Test that style dispatch correctly routes to _render_candlestick."""
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [100.0, 110.0, 120.0, 130.0, 140.0]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Verify it produces output (stub should delegate to braille)
        assert result.height == 10
        assert len(result.lines) > 0

    def test_braille_unchanged_after_candlestick_addition(self) -> None:
        """Test that existing BRAILLE style produces identical output as before."""
        # This regression test ensures adding CANDLESTICK didn't break BRAILLE
        renderer_braille = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [100.0 + i for i in range(50)]

        result = renderer_braille.render(prices=prices, dates=None, dimensions=dimensions)

        # Should still render with braille characters
        for line in result.lines:
            for char in line:
                if char != " ":
                    assert char == " " or (0x2800 <= ord(char) <= 0x28FF)

    def test_block_unchanged_after_candlestick_addition(self) -> None:
        """Test that existing BLOCK style produces identical output as before."""
        # This regression test ensures adding CANDLESTICK didn't break BLOCK
        renderer_block = ChartRenderer(style=ChartStyle.BLOCK)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        prices = [100.0 + i for i in range(50)]

        result = renderer_block.render(prices=prices, dates=None, dimensions=dimensions)

        # Should still render with block characters
        blocks = "▁▂▃▄▅▆▇█"
        has_blocks = any(any(c in blocks for c in line) for line in result.lines)
        assert has_blocks

    def test_candlestick_with_empty_data(self) -> None:
        """Test candlestick rendering with empty data."""
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        result = renderer.render(prices=[], dates=None)

        # Should handle empty data gracefully
        assert result.lines == ["No data"]
        assert result.width == 7
        assert result.height == 1

    def test_candlestick_with_y_axis(self) -> None:
        """Test candlestick rendering with Y-axis enabled."""
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        dimensions = ChartDimensions(width=60, height=10, include_y_axis=True, include_x_axis=False)
        prices = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should include Y-axis markers
        assert result.height == 10
        assert any("│" in line for line in result.lines)

    def test_candlestick_style_initialization(self) -> None:
        """Test that ChartRenderer can be initialized with CANDLESTICK style."""
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        assert renderer.style == ChartStyle.CANDLESTICK

    def test_candlestick_with_ohlc_data(self) -> None:
        """Test candlestick rendering with full OHLC data via ChartContext."""
        # Create realistic OHLC data
        dates = [datetime.now() + timedelta(days=i) for i in range(10)]
        opens = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0, 104.0, 106.0, 105.0, 107.0]
        closes = [102.0, 101.0, 103.0, 102.0, 105.0, 104.0, 106.0, 105.0, 107.0, 108.0]
        highs = [103.0, 103.0, 104.0, 104.0, 106.0, 106.0, 107.0, 107.0, 108.0, 109.0]
        lows = [99.0, 100.0, 100.0, 101.0, 101.0, 103.0, 103.0, 104.0, 104.0, 106.0]
        volumes = [1000000] * 10

        data = HistoricalData(
            ticker="TEST",
            period="1M",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=60, height=15)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        result = renderer.render(context=context)

        # Should render successfully
        assert result.height == 15
        assert result.min_value == min(lows)
        assert result.max_value == max(highs)
        # Should have some content
        assert len(result.lines) > 0

    def test_candlestick_bullish_candle(self) -> None:
        """Test that bullish candles (close > open) are rendered."""
        dates = [datetime.now() + timedelta(days=i) for i in range(3)]
        opens = [100.0, 100.0, 100.0]
        closes = [110.0, 110.0, 110.0]  # All bullish
        highs = [115.0, 115.0, 115.0]
        lows = [95.0, 95.0, 95.0]
        volumes = [1000000] * 3

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=10)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        result = renderer.render(context=context)

        # Check that green color markup exists (bullish)
        chart_content = "".join(result.lines)
        assert "[green]" in chart_content

    def test_candlestick_bearish_candle(self) -> None:
        """Test that bearish candles (close < open) are rendered."""
        dates = [datetime.now() + timedelta(days=i) for i in range(3)]
        opens = [110.0, 110.0, 110.0]
        closes = [100.0, 100.0, 100.0]  # All bearish
        highs = [115.0, 115.0, 115.0]
        lows = [95.0, 95.0, 95.0]
        volumes = [1000000] * 3

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=10)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        result = renderer.render(context=context)

        # Check that red color markup exists (bearish)
        chart_content = "".join(result.lines)
        assert "[red]" in chart_content

    def test_candlestick_doji_candle(self) -> None:
        """Test that doji candles (close == open) are rendered."""
        dates = [datetime.now() + timedelta(days=i) for i in range(3)]
        opens = [100.0, 100.0, 100.0]
        closes = [100.0, 100.0, 100.0]  # All doji
        highs = [105.0, 105.0, 105.0]
        lows = [95.0, 95.0, 95.0]
        volumes = [1000000] * 3

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=10)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        result = renderer.render(context=context)

        # Doji should render as horizontal line
        chart_content = "".join(result.lines)
        assert "─" in chart_content

    def test_candlestick_y_axis_uses_high_low_range(self) -> None:
        """Test that Y-axis scaling uses high-low range, not just close prices."""
        dates = [datetime.now() + timedelta(days=i) for i in range(5)]
        opens = [100.0, 100.0, 100.0, 100.0, 100.0]
        closes = [102.0, 102.0, 102.0, 102.0, 102.0]
        # Wicks extend significantly beyond body
        highs = [120.0, 120.0, 120.0, 120.0, 120.0]
        lows = [80.0, 80.0, 80.0, 80.0, 80.0]
        volumes = [1000000] * 5

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=10)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        result = renderer.render(context=context)

        # Min/max should reflect high-low range, not open-close
        assert result.min_value == 80.0
        assert result.max_value == 120.0

    def test_candlestick_ohlc_downsampling(self) -> None:
        """Test that OHLC downsampling preserves price structure."""
        # Create 100 data points with known OHLC pattern
        dates = [datetime.now() + timedelta(days=i) for i in range(100)]
        opens = [100.0 + i for i in range(100)]
        closes = [102.0 + i for i in range(100)]
        highs = [105.0 + i for i in range(100)]
        lows = [95.0 + i for i in range(100)]
        volumes = [1000000] * 100

        data = HistoricalData(
            ticker="TEST",
            period="3M",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        # Render to narrow width to force downsampling
        context = ChartContext.from_historical_data(data, width=30, height=10)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        result = renderer.render(context=context)

        # Should use full high-low range from original data
        assert result.min_value == 95.0  # First low
        assert result.max_value == 204.0  # Last high (105 + 99)

    def test_candlestick_flat_prices(self) -> None:
        """Test candlestick rendering when all prices are identical."""
        dates = [datetime.now() + timedelta(days=i) for i in range(5)]
        opens = [100.0] * 5
        closes = [100.0] * 5
        highs = [100.0] * 5
        lows = [100.0] * 5
        volumes = [1000000] * 5

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=10)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        result = renderer.render(context=context)

        # Should render successfully without crashing
        assert result.height == 10
        assert result.min_value == 100.0
        assert result.max_value == 100.0

    def test_candlestick_with_sma_overlay(self) -> None:
        """Test SMA overlay renders correctly on candlestick chart."""
        dates = [datetime.now() + timedelta(days=i) for i in range(10)]
        opens = [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 109.0]
        closes = [102.0, 103.0, 102.0, 105.0, 106.0, 105.0, 108.0, 109.0, 108.0, 111.0]
        highs = [103.0, 104.0, 103.0, 106.0, 107.0, 106.0, 109.0, 110.0, 109.0, 112.0]
        lows = [99.0, 101.0, 100.0, 102.0, 104.0, 103.0, 105.0, 107.0, 106.0, 108.0]
        volumes = [1000000] * 10

        # Simple SMA with some None values at the start
        sma_values: list[float | None] = [None, None, None, 102.0, 103.5, 104.0, 105.5, 107.0, 108.0, 109.0]

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=15)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)

        # Create overlay
        overlay = OverlayData(values=sma_values, color="cyan", name="SMA5")

        result = renderer.render(context=context, overlays=[overlay])

        # Should render successfully
        assert result.height == 15
        assert len(result.lines) == 15

        # Check that overlay color appears in output
        chart_str = "\n".join(result.lines)
        assert "[cyan]" in chart_str  # Overlay color markup should be present
        assert "·" in chart_str  # Overlay dot marker should be present

    def test_candlestick_with_multiple_overlays(self) -> None:
        """Test multiple overlays (SMA20, SMA50) render correctly on candlestick chart."""
        dates = [datetime.now() + timedelta(days=i) for i in range(10)]
        opens = [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 109.0]
        closes = [102.0, 103.0, 102.0, 105.0, 106.0, 105.0, 108.0, 109.0, 108.0, 111.0]
        highs = [103.0, 104.0, 103.0, 106.0, 107.0, 106.0, 109.0, 110.0, 109.0, 112.0]
        lows = [99.0, 101.0, 100.0, 102.0, 104.0, 103.0, 105.0, 107.0, 106.0, 108.0]
        volumes = [1000000] * 10

        sma20_values: list[float | None] = [None, None, None, 102.0, 103.5, 104.0, 105.5, 107.0, 108.0, 109.0]
        sma50_values: list[float | None] = [None, None, None, None, None, 103.0, 104.0, 105.0, 106.0, 107.0]

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=15)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)

        # Create overlays with distinct colors
        overlay1 = OverlayData(values=sma20_values, color="cyan", name="SMA20")
        overlay2 = OverlayData(values=sma50_values, color="magenta", name="SMA50")

        result = renderer.render(context=context, overlays=[overlay1, overlay2])

        # Should render successfully
        assert result.height == 15
        assert len(result.lines) == 15

        # Check that both overlay colors appear
        chart_str = "\n".join(result.lines)
        assert "[cyan]" in chart_str  # SMA20 color
        assert "[magenta]" in chart_str  # SMA50 color
        assert "·" in chart_str  # Overlay markers

    def test_candlestick_overlay_colors_distinct(self) -> None:
        """Test overlay colors (cyan, magenta) are distinct from candle colors (green, red)."""
        dates = [datetime.now() + timedelta(days=i) for i in range(5)]
        opens = [100.0, 102.0, 104.0, 103.0, 105.0]
        closes = [102.0, 104.0, 103.0, 105.0, 107.0]  # Mixed bullish/bearish
        highs = [103.0, 105.0, 105.0, 106.0, 108.0]
        lows = [99.0, 101.0, 102.0, 102.0, 104.0]
        volumes = [1000000] * 5

        sma_values: list[float | None] = [None, 101.0, 103.0, 104.0, 106.0]

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=15)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        overlay = OverlayData(values=sma_values, color="cyan", name="SMA")

        result = renderer.render(context=context, overlays=[overlay])
        chart_str = "\n".join(result.lines)

        # All four colors should be present
        assert "[green]" in chart_str  # Bullish candles
        assert "[red]" in chart_str  # Bearish candles
        assert "[cyan]" in chart_str  # Overlay
        # Verify overlay uses dot marker, not candle characters
        assert "·" in chart_str

    def test_candlestick_overlay_y_axis_scaling(self) -> None:
        """Test overlays use same Y-axis scaling as candlesticks (high-low range)."""
        dates = [datetime.now() + timedelta(days=i) for i in range(5)]
        opens = [100.0, 102.0, 101.0, 103.0, 105.0]
        closes = [102.0, 103.0, 102.0, 105.0, 106.0]
        highs = [105.0, 106.0, 105.0, 108.0, 110.0]  # High range
        lows = [95.0, 98.0, 97.0, 99.0, 101.0]  # Low range
        volumes = [1000000] * 5

        # SMA in middle of high-low range
        sma_values: list[float | None] = [None, 100.0, 101.0, 102.0, 103.0]

        data = HistoricalData(
            ticker="TEST",
            period="1W",
            interval="1d",
            dates=dates,
            prices=closes,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
        )

        context = ChartContext.from_historical_data(data, width=40, height=15)
        renderer = ChartRenderer(style=ChartStyle.CANDLESTICK)
        overlay = OverlayData(values=sma_values, color="cyan", name="SMA")

        result = renderer.render(context=context, overlays=[overlay])

        # Y-axis should use high-low range (95-110), not close range (102-106)
        assert result.min_value == 95.0
        assert result.max_value == 110.0

        # Overlay should render successfully
        chart_str = "\n".join(result.lines)
        assert "[cyan]" in chart_str
