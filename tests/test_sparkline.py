"""Tests for sparkline widget."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from viper.widgets.sparkline import SparklineWidget


class SparklineTestApp(App[None]):
    """Test app for SparklineWidget."""

    def __init__(self, sparkline: SparklineWidget):
        """Initialize with a sparkline widget."""
        super().__init__()
        self.sparkline = sparkline

    def compose(self) -> ComposeResult:
        """Compose test app."""
        yield self.sparkline


@pytest.mark.asyncio
async def test_sparkline_with_data():
    """Test sparkline renders with price data."""
    prices = [100.0, 105.0, 102.0, 110.0, 108.0]
    sparkline = SparklineWidget(prices=prices, label="Test Chart", width=60)
    app = SparklineTestApp(sparkline)

    async with app.run_test():
        # Should have label and chart
        labels = sparkline.query(Label)
        assert len(labels) == 2

        # First label is the chart label
        label_text = str(labels[0].render())
        assert "Test Chart" in label_text

        # Second label is the chart itself
        chart_text = str(labels[1].render())
        # Chart should be non-empty
        assert len(chart_text) > 0
        # Chart should use block characters
        assert any(char in chart_text for char in ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"])


@pytest.mark.asyncio
async def test_sparkline_no_data():
    """Test sparkline renders 'No data' when prices is None."""
    sparkline = SparklineWidget(prices=None, label="Test Chart", width=60)
    app = SparklineTestApp(sparkline)

    async with app.run_test():
        labels = sparkline.query(Label)
        assert len(labels) == 2

        # Should show label
        label_text = str(labels[0].render())
        assert "Test Chart" in label_text

        # Should show "No data"
        no_data_text = str(labels[1].render())
        assert "No data" in no_data_text


@pytest.mark.asyncio
async def test_sparkline_empty_list():
    """Test sparkline renders 'No data' when prices is empty list."""
    sparkline = SparklineWidget(prices=[], label="Empty", width=60)
    app = SparklineTestApp(sparkline)

    async with app.run_test():
        labels = sparkline.query(Label)

        # Should show "No data"
        no_data_text = str(labels[1].render())
        assert "No data" in no_data_text


@pytest.mark.asyncio
async def test_sparkline_no_label():
    """Test sparkline without label text."""
    prices = [100.0, 101.0, 102.0]
    sparkline = SparklineWidget(prices=prices, label="", width=60)
    app = SparklineTestApp(sparkline)

    async with app.run_test():
        labels = sparkline.query(Label)
        # Should only have chart label (no separate label widget)
        assert len(labels) == 1

        # Should show chart
        chart_text = str(labels[0].render())
        assert len(chart_text) > 0


@pytest.mark.asyncio
async def test_sparkline_update_data():
    """Test updating sparkline data dynamically."""
    prices = [100.0, 101.0]
    sparkline = SparklineWidget(prices=prices, label="Original", width=60)
    app = SparklineTestApp(sparkline)

    async with app.run_test() as pilot:
        # Verify initial state
        labels = sparkline.query(Label)
        assert len(labels) == 2
        assert "Original" in str(labels[0].render())

        # Update with new data
        new_prices = [200.0, 205.0, 210.0]
        sparkline.update_data(new_prices, label="Updated")

        # Wait for UI update to complete
        await pilot.pause()

        # After update, should have 2 labels (old ones replaced)
        labels = sparkline.query(Label)
        assert len(labels) == 2

        # Should show updated label
        label_text = str(labels[0].render())
        assert "Updated" in label_text


@pytest.mark.asyncio
async def test_sparkline_update_to_no_data():
    """Test updating sparkline to no data state."""
    prices = [100.0, 101.0, 102.0]
    sparkline = SparklineWidget(prices=prices, label="Has Data", width=60)
    app = SparklineTestApp(sparkline)

    async with app.run_test() as pilot:
        # Update to no data
        sparkline.update_data(None, label="No Data")

        # Wait for UI update to complete
        await pilot.pause()

        labels = sparkline.query(Label)

        # Should show "No data"
        found_no_data = False
        for label in labels:
            text = str(label.render())
            if "No data" in text:
                found_no_data = True
        assert found_no_data


def test_render_sparkline_basic():
    """Test basic sparkline rendering logic."""
    sparkline = SparklineWidget()

    prices = [100.0, 110.0, 105.0, 115.0, 120.0]
    chart = sparkline._render_sparkline(prices, width=60)

    # Should return a string
    assert isinstance(chart, str)
    # Should have one character per price
    assert len(chart) == 5
    # Should use block characters
    assert all(char in "▁▂▃▄▅▆▇█" for char in chart)


def test_render_sparkline_upward_trend():
    """Test sparkline with upward trend."""
    sparkline = SparklineWidget()

    prices = [100.0, 110.0, 120.0, 130.0, 140.0]
    chart = sparkline._render_sparkline(prices, width=60)

    # First char should be lowest block, last should be highest
    assert chart[0] == "▁"
    assert chart[-1] == "█"


def test_render_sparkline_flat():
    """Test sparkline with flat prices (all same)."""
    sparkline = SparklineWidget()

    prices = [100.0, 100.0, 100.0, 100.0]
    chart = sparkline._render_sparkline(prices, width=60)

    # Should be a flat line (all dashes)
    assert chart == "─" * 4


def test_render_sparkline_empty():
    """Test rendering empty price list."""
    sparkline = SparklineWidget()

    chart = sparkline._render_sparkline([], width=60)
    assert chart == ""


def test_render_sparkline_single_price():
    """Test rendering with single price."""
    sparkline = SparklineWidget()

    chart = sparkline._render_sparkline([100.0], width=60)
    # Single price is flat
    assert chart == "─"


def test_render_sparkline_downsampling():
    """Test downsampling when prices exceed width."""
    sparkline = SparklineWidget()

    # 100 prices but width is 50
    prices = [float(i) for i in range(100)]
    chart = sparkline._render_sparkline(prices, width=50)

    # Should downsample to 50 characters
    assert len(chart) == 50
    # Should still use block characters
    assert all(char in "▁▂▃▄▅▆▇█" for char in chart)


def test_render_sparkline_normalization():
    """Test price normalization to 8 levels."""
    sparkline = SparklineWidget()

    # Prices ranging from 100 to 200
    prices = [100.0, 125.0, 150.0, 175.0, 200.0]
    chart = sparkline._render_sparkline(prices, width=60)

    # Min should map to lowest block, max to highest
    assert chart[0] == "▁"  # 100.0 is min
    assert chart[-1] == "█"  # 200.0 is max


def test_render_sparkline_two_prices():
    """Test rendering with exactly two prices."""
    sparkline = SparklineWidget()

    chart = sparkline._render_sparkline([100.0, 200.0], width=60)

    # Should have min and max blocks
    assert len(chart) == 2
    assert chart[0] == "▁"
    assert chart[1] == "█"


def test_render_sparkline_negative_prices():
    """Test handling negative prices (should work normally)."""
    sparkline = SparklineWidget()

    prices = [-10.0, -5.0, 0.0, 5.0, 10.0]
    chart = sparkline._render_sparkline(prices, width=60)

    # Should normalize correctly
    assert len(chart) == 5
    assert chart[0] == "▁"  # -10.0 is min
    assert chart[-1] == "█"  # 10.0 is max


def test_render_sparkline_precise_width():
    """Test that downsampling respects exact width."""
    sparkline = SparklineWidget()

    prices = [float(i) for i in range(200)]

    for width in [10, 25, 50, 75]:
        chart = sparkline._render_sparkline(prices, width=width)
        assert len(chart) == width
