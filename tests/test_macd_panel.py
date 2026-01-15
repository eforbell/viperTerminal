"""Tests for the MACDPanel widget."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from viper.widgets.macd_panel import MACDPanel


class MACDPanelTestApp(App[None]):
    """Test app for MACDPanel widget."""

    def compose(self) -> ComposeResult:
        """Compose test app."""
        yield MACDPanel()


@pytest.mark.asyncio
async def test_macd_panel_initialization() -> None:
    """Test that the MACD panel initializes with correct MACD-specific configuration."""
    app = MACDPanelTestApp()
    async with app.run_test():
        panel = app.query_one(MACDPanel)

        # Check MACD-specific configuration
        assert panel.get_name() == "MACD"
        assert panel._height == 7  # More height than RSI (needs space for histogram)
        assert panel._min_value == -10.0  # MACD uses centered scale
        assert panel._max_value == 10.0
        # MACD should have 1 reference line (zero line)
        assert len(panel._reference_lines) == 1
        assert panel._reference_lines[0].value == 0.0
        assert panel._reference_lines[0].label == "0"
        assert panel._reference_lines[0].style == "solid"
        assert panel._reference_lines[0].color == "white"  # Rich markup color name


@pytest.mark.asyncio
async def test_macd_panel_starts_visible() -> None:
    """Test that the MACD panel starts in visible state (for standalone test)."""
    app = MACDPanelTestApp()
    async with app.run_test():
        panel = app.query_one(MACDPanel)

        # Panel should start visible in standalone test
        assert panel.is_visible() is True
        assert panel.styles.display == "block"


@pytest.mark.asyncio
async def test_macd_panel_toggle_visibility() -> None:
    """Test that the MACD panel visibility can be toggled."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Panel starts visible in standalone test
        assert panel.is_visible() is True

        # Hide panel
        panel.hide()
        await pilot.pause()
        assert panel.is_visible() is False
        assert panel.styles.display == "none"

        # Show panel again
        panel.show()
        await pilot.pause()
        assert panel.is_visible() is True
        assert panel.styles.display == "block"

        # Toggle visibility
        panel.toggle_visibility()
        await pilot.pause()
        assert panel.is_visible() is False

        panel.toggle_visibility()
        await pilot.pause()
        assert panel.is_visible() is True


@pytest.mark.asyncio
async def test_macd_panel_display_positive_values() -> None:
    """Test that the MACD panel displays positive MACD values (bullish signal)."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Create positive MACD values (bullish)
        macd_line = [None] * 33 + [0.5, 1.0, 1.5, 2.0, 2.5, 2.0, 1.5, 1.0]
        signal_line = [None] * 33 + [0.3, 0.7, 1.2, 1.7, 2.1, 1.9, 1.6, 1.2]
        histogram = [None] * 33 + [0.2, 0.3, 0.3, 0.3, 0.4, 0.1, -0.1, -0.2]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Check that values are stored
        assert panel._macd_line == macd_line
        assert panel._signal_line == signal_line
        assert panel._histogram == histogram

        # Check header displays all three components
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        assert len(header_labels) == 1
        header_text = str(header_labels[0].render())
        assert "MACD" in header_text
        assert "Signal" in header_text
        assert "Hist" in header_text
        # Check current values (last non-None values)
        assert "1.00" in header_text  # MACD current
        assert "1.20" in header_text  # Signal current
        assert "-0.20" in header_text or "0.20" in header_text  # Histogram current


@pytest.mark.asyncio
async def test_macd_panel_display_negative_values() -> None:
    """Test that the MACD panel displays negative MACD values (bearish signal)."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Create negative MACD values (bearish)
        macd_line = [None] * 33 + [-2.5, -2.0, -1.5, -1.0, -0.5, -1.0, -1.5, -2.0]
        signal_line = [None] * 33 + [-2.1, -1.8, -1.4, -1.1, -0.7, -0.9, -1.3, -1.7]
        histogram = [None] * 33 + [-0.4, -0.2, -0.1, 0.1, 0.2, -0.1, -0.2, -0.3]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Check header displays negative values
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "-2.00" in header_text  # MACD current
        assert "-1.70" in header_text  # Signal current
        assert "-0.30" in header_text or "0.30" in header_text  # Histogram current


@pytest.mark.asyncio
async def test_macd_panel_display_crossover() -> None:
    """Test that the MACD panel displays MACD/Signal crossover (buy/sell signal)."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # MACD crossing above Signal (bullish crossover)
        macd_line = [None] * 33 + [-0.5, -0.2, 0.0, 0.3, 0.5, 0.7, 0.9, 1.0]
        signal_line = [None] * 33 + [0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        histogram = [
            None if m is None or s is None else m - s
            for m, s in zip(macd_line, signal_line)
        ]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_macd_panel_with_all_none_values() -> None:
    """Test that the MACD panel handles all None values (insufficient data)."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # All None values (insufficient data for MACD calculation)
        macd_line: list[float | None] = [None] * 40
        signal_line: list[float | None] = [None] * 40
        histogram: list[float | None] = [None] * 40

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Should display "No data" message
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "No data" in header_text


@pytest.mark.asyncio
async def test_macd_panel_with_partial_none_values() -> None:
    """Test that the MACD panel filters out None values correctly."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # MACD typically has first 33 values as None, then valid values
        macd_line: list[float | None] = [None] * 33 + [
            0.5, 0.8, 1.0, 1.2, 1.5, 1.3, 1.0, 0.8, 0.5, 0.3
        ]
        signal_line: list[float | None] = [None] * 33 + [
            0.3, 0.5, 0.7, 0.9, 1.1, 1.2, 1.1, 0.9, 0.6, 0.4
        ]
        histogram: list[float | None] = [None] * 33 + [
            0.2, 0.3, 0.3, 0.3, 0.4, 0.1, -0.1, -0.1, -0.1, -0.1
        ]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Should render successfully, filtering out Nones
        labels = panel.query(Label)
        # Should have header + chart lines
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_macd_panel_zero_crossing() -> None:
    """Test that the MACD panel handles MACD crossing zero line (trend change)."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # MACD crossing zero from negative to positive (bearish to bullish)
        macd_line = [None] * 33 + [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
        signal_line = [None] * 33 + [-1.2, -0.9, -0.6, -0.2, 0.2, 0.6, 1.0, 1.4]
        histogram = [
            None if m is None or s is None else m - s
            for m, s in zip(macd_line, signal_line)
        ]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_macd_panel_extreme_values() -> None:
    """Test that the MACD panel handles extreme MACD values (near min/max)."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # MACD at extremes (near -10 and +10 limits)
        macd_line = [None] * 33 + [-9.0, -5.0, 0.0, 5.0, 9.0, 0.0]
        signal_line = [None] * 33 + [-8.0, -4.5, 0.5, 4.5, 8.0, 0.5]
        histogram = [
            None if m is None or s is None else m - s
            for m, s in zip(macd_line, signal_line)
        ]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_macd_panel_reference_lines_rendered() -> None:
    """Test that MACD reference line (zero line) is configured."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Show some MACD data
        macd_line = [None] * 33 + [1.0] * 20
        signal_line = [None] * 33 + [0.8] * 20
        histogram = [None] * 33 + [0.2] * 20

        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Reference line should be configured (verified in initialization test)
        # Rendering happens in panel, just verify panel renders without errors
        labels = panel.query(Label)
        assert len(labels) > 0


@pytest.mark.asyncio
async def test_macd_panel_large_dataset() -> None:
    """Test that the MACD panel handles large datasets with downsampling."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Create large MACD dataset (more than 140 points = 70 chars * 2 points per char)
        macd_line: list[float | None] = [None] * 33 + [
            float(2.0 * (i % 10 / 5.0 - 1.0)) for i in range(200)
        ]
        signal_line: list[float | None] = [None] * 33 + [
            float(1.5 * (i % 10 / 5.0 - 1.0)) for i in range(200)
        ]
        histogram: list[float | None] = [
            None if m is None or s is None else m - s
            for m, s in zip(macd_line, signal_line)
        ]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Should render without errors (downsampling applied)
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_macd_panel_realistic_values() -> None:
    """Test the MACD panel with realistic MACD values from a typical stock."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Realistic MACD values showing a bullish trend
        macd_line: list[float | None] = [None] * 33 + [
            -1.2, -0.8, -0.4, 0.0, 0.5, 1.0, 1.5, 2.0,
            2.3, 2.5, 2.4, 2.2, 1.9, 1.5, 1.0, 0.5,
            0.0, -0.3, -0.5, -0.7, -0.8, -0.9, -1.0
        ]
        signal_line: list[float | None] = [None] * 33 + [
            -1.0, -0.7, -0.3, 0.1, 0.4, 0.8, 1.2, 1.6,
            1.9, 2.1, 2.2, 2.2, 2.1, 1.8, 1.4, 1.0,
            0.5, 0.1, -0.2, -0.4, -0.5, -0.6, -0.7
        ]
        histogram: list[float | None] = [
            None if m is None or s is None else m - s
            for m, s in zip(macd_line, signal_line)
        ]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Check that current values are displayed
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "-1.00" in header_text  # MACD current
        assert "-0.70" in header_text  # Signal current
        assert "-0.30" in header_text or "0.30" in header_text  # Histogram current


@pytest.mark.asyncio
async def test_macd_panel_empty_data() -> None:
    """Test that the MACD panel handles empty data gracefully."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Show MACD with empty lists
        panel.show_macd([], [], [])
        await pilot.pause()

        # Should display "No data" message
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "No data" in header_text


@pytest.mark.asyncio
async def test_macd_panel_hidden_no_render() -> None:
    """Test that hidden MACD panel stores data when updated while hidden."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Hide panel first
        panel.hide()
        await pilot.pause()

        # Update data while hidden
        macd_line = [None] * 33 + [1.0] * 10
        signal_line = [None] * 33 + [0.8] * 10
        histogram = [None] * 33 + [0.2] * 10

        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Data should be stored but panel should remain hidden
        assert panel._macd_line == macd_line
        assert panel._signal_line == signal_line
        assert panel._histogram == histogram
        assert panel.is_visible() is False


@pytest.mark.asyncio
async def test_macd_panel_divergence_pattern() -> None:
    """Test MACD panel with divergence pattern (price vs MACD direction mismatch)."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # MACD showing bearish divergence (MACD making lower highs while price makes higher highs)
        # Represented here as MACD declining from high to lower high
        macd_line: list[float | None] = [None] * 33 + [
            1.0, 1.5, 2.0, 2.5, 3.0,  # First peak
            2.5, 2.0, 1.5, 1.0, 0.5,  # Decline
            1.0, 1.5, 2.0, 2.3, 2.5,  # Lower peak (divergence)
        ]
        signal_line: list[float | None] = [None] * 33 + [
            0.8, 1.2, 1.6, 2.0, 2.4,
            2.3, 2.0, 1.6, 1.2, 0.8,
            1.0, 1.3, 1.7, 2.0, 2.2,
        ]
        histogram: list[float | None] = [
            None if m is None or s is None else m - s
            for m, s in zip(macd_line, signal_line)
        ]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Should render successfully
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_macd_panel_histogram_color_transition() -> None:
    """Test that histogram transitions from positive (green) to negative (red)."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Histogram transitioning from positive to negative
        macd_line = [None] * 33 + [1.0, 0.8, 0.5, 0.2, 0.0, -0.2, -0.5, -0.8]
        signal_line = [None] * 33 + [0.5, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, -0.1]
        histogram = [
            None if m is None or s is None else m - s
            for m, s in zip(macd_line, signal_line)
        ]

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Histogram should transition from positive to negative
        # (green bars to red bars - visual verification only)
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_macd_panel_get_last_value_helper() -> None:
    """Test the _get_last_value helper method."""
    app = MACDPanelTestApp()
    async with app.run_test():
        panel = app.query_one(MACDPanel)

        # Test with mixed None and float values
        values: list[float | None] = [None, None, 1.0, 2.0, None, 3.0, None]
        assert panel._get_last_value(values) == 3.0

        # Test with all None values
        all_none: list[float | None] = [None, None, None]
        assert panel._get_last_value(all_none) is None

        # Test with no None values
        no_none: list[float | None] = [1.0, 2.0, 3.0, 4.0]
        assert panel._get_last_value(no_none) == 4.0

        # Test with empty list
        empty: list[float | None] = []
        assert panel._get_last_value(empty) is None


@pytest.mark.asyncio
async def test_macd_panel_flat_values() -> None:
    """Test MACD panel with flat (constant) values."""
    app = MACDPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(MACDPanel)

        # Flat MACD values (no trend)
        macd_line = [None] * 33 + [0.0] * 20
        signal_line = [None] * 33 + [0.0] * 20
        histogram = [None] * 33 + [0.0] * 20

        # Show MACD data
        panel.show_macd(macd_line, signal_line, histogram)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "0.00" in header_text
