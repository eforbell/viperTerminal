"""Tests for chart rendering engine."""

from datetime import datetime, timedelta

import pytest

from viper.widgets.chart_renderer import (
    ChartDimensions,
    ChartRenderer,
    ChartStyle,
    RenderedChart,
    create_chart,
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

        # Check that ANSI color codes are present
        volume_line = result[1]  # Middle line has the volume bars
        assert "\033[32m" in volume_line or "\033[31m" in volume_line  # Green or red color code

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
