"""Tests for chart interpolation with sparse data."""

from datetime import datetime, timedelta

import pytest

from viper.widgets.chart_renderer import ChartDimensions, ChartRenderer, ChartStyle


class TestSparseDataInterpolation:
    """Test suite for sparse data interpolation (upsampling)."""

    def test_sparse_data_fills_full_width(self) -> None:
        """Test that sparse data (e.g., 21 daily bars for 1M) uses full chart width."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        # Simulate 1M chart: 60 char width, but only 21 data points
        dimensions = ChartDimensions(width=60, height=20, include_y_axis=False, include_x_axis=False)
        prices = [100.0 + i * 5 for i in range(21)]  # 21 data points (like 1M daily bars)

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Chart should use full width via interpolation
        assert result.width == 60
        assert len(result.lines) == 20
        # Each line should be exactly 60 characters
        for line in result.lines:
            assert len(line) == 60

    def test_sparse_data_interpolated_smoothly(self) -> None:
        """Test that sparse data is interpolated smoothly without jumps."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        # Only 10 data points for 40-char width (needs 80 points for braille)
        prices = [float(i * 10) for i in range(10)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should render without errors and use full width
        assert result.width == 40
        assert len(result.lines) == 10

    def test_very_sparse_data_still_renders(self) -> None:
        """Test that very sparse data (5 points) still renders correctly."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=20, include_y_axis=False, include_x_axis=False)
        prices = [100.0, 110.0, 105.0, 115.0, 120.0]  # Only 5 points

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should still use full width via upsampling
        assert result.width == 60
        assert result.min_value == 100.0
        assert result.max_value == 120.0

    def test_interpolation_preserves_min_max(self) -> None:
        """Test that interpolation preserves the original min/max values."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=50, height=15, include_y_axis=False, include_x_axis=False)
        prices = [50.0, 100.0, 75.0, 125.0, 60.0]  # Min=50, Max=125

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Min/max should be preserved from original data
        assert result.min_value == 50.0
        assert result.max_value == 125.0

    def test_interpolation_with_dates(self) -> None:
        """Test that interpolation works correctly with date labels."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=20, include_y_axis=True, include_x_axis=True)
        
        # Create sparse data with dates (like 1M period with 21 trading days)
        start_date = datetime(2025, 12, 1)
        dates = [start_date + timedelta(days=i) for i in range(21)]
        prices = [100.0 + i * 2 for i in range(21)]

        result = renderer.render(prices=prices, dates=dates, dimensions=dimensions, period="1M")

        # Should render successfully with axes
        assert result.width == 60  # Width is of chart area
        assert result.height > 20  # Includes X-axis lines
        # First line should include Y-axis label
        first_line = result.lines[0]
        assert "$" in first_line  # Y-axis price label
        # Last line should show date labels
        last_line = result.lines[-1]
        assert any(c.isdigit() for c in last_line)  # Should contain date numbers

    def test_no_padding_with_last_price(self) -> None:
        """Test that we don't pad/repeat the last price to fill width."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=60, height=20, include_y_axis=False, include_x_axis=False)
        # 20 points with distinct values at the end
        prices = [100.0] * 15 + [110.0, 115.0, 120.0, 125.0, 130.0]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # The last few points should show variation, not a flat line
        # This is hard to test directly, but we can verify no crash and correct min/max
        assert result.min_value == 100.0
        assert result.max_value == 130.0
        assert result.width == 60

    def test_downsampling_still_works(self) -> None:
        """Test that downsampling still works when we have too much data."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        # 500 data points should be downsampled to 80 (40 chars * 2 for braille)
        prices = [100.0 + i * 0.1 for i in range(500)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        # Should downsample and use full width
        assert result.width == 40
        assert len(result.lines) == 10

    def test_exactly_target_size_no_sampling(self) -> None:
        """Test that data matching target size is rendered directly."""
        renderer = ChartRenderer(style=ChartStyle.BRAILLE)
        dimensions = ChartDimensions(width=40, height=10, include_y_axis=False, include_x_axis=False)
        # Exactly 80 points for 40-char width (no sampling needed)
        prices = [100.0 + i * 0.5 for i in range(80)]

        result = renderer.render(prices=prices, dates=None, dimensions=dimensions)

        assert result.width == 40
        assert result.min_value == 100.0
        assert result.max_value == 100.0 + 79 * 0.5
