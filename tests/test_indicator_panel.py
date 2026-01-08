"""Tests for the IndicatorPanel base widget."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from viper.widgets.indicator_panel import HorizontalLine, IndicatorPanel


class IndicatorPanelTestApp(App[None]):
    """Test app for IndicatorPanel widget."""

    def compose(self) -> ComposeResult:
        """Compose test app."""
        yield IndicatorPanel(name="RSI", height=4, min_value=0.0, max_value=100.0)


@pytest.mark.asyncio
async def test_indicator_panel_initialization() -> None:
    """Test that the indicator panel initializes with correct defaults."""
    app = IndicatorPanelTestApp()
    async with app.run_test():
        panel = app.query_one(IndicatorPanel)

        # Check initial state
        assert panel.get_name() == "RSI"
        assert panel._height == 4
        assert panel._min_value == 0.0
        assert panel._max_value == 100.0
        assert panel.is_visible() is True
        assert panel._indicator_values is None
        assert panel._current_value is None


@pytest.mark.asyncio
async def test_indicator_panel_empty_state() -> None:
    """Test that the indicator panel displays empty state when no data."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Show indicator with None values
        panel.show_indicator(None)
        await pilot.pause()

        # Should display empty message
        labels = panel.query(Label)
        assert any("No data" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_indicator_panel_show_values() -> None:
    """Test that the indicator panel displays indicator values."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Create sample RSI values (0-100 range)
        rsi_values = [50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 70.0, 65.0, 60.0, 55.0]
        current_value = 55.0

        # Show indicator
        panel.show_indicator(rsi_values, current_value)
        await pilot.pause()

        # Check that values are stored
        assert panel._indicator_values == rsi_values
        assert panel._current_value == current_value

        # Check header displays name and current value
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        assert len(header_labels) == 1
        header_text = str(header_labels[0].render())
        assert "RSI" in header_text
        assert "55.00" in header_text


@pytest.mark.asyncio
async def test_indicator_panel_hide_show() -> None:
    """Test that the indicator panel can be hidden and shown."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Panel starts visible
        assert panel.is_visible() is True
        assert panel.styles.display == "block"

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


@pytest.mark.asyncio
async def test_indicator_panel_toggle_visibility() -> None:
    """Test that the indicator panel visibility can be toggled."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Panel starts visible
        assert panel.is_visible() is True

        # Toggle to hidden
        panel.toggle_visibility()
        await pilot.pause()
        assert panel.is_visible() is False

        # Toggle back to visible
        panel.toggle_visibility()
        await pilot.pause()
        assert panel.is_visible() is True


@pytest.mark.asyncio
async def test_indicator_panel_with_reference_lines() -> None:
    """Test that the indicator panel can display horizontal reference lines."""

    class RSIPanelApp(App[None]):
        """Test app with RSI-style reference lines."""

        def compose(self) -> ComposeResult:
            """Compose test app."""
            reference_lines = [
                HorizontalLine(
                    value=70.0, label="Overbought", style="dashed", color="\033[31m"
                ),
                HorizontalLine(
                    value=30.0, label="Oversold", style="dashed", color="\033[32m"
                ),
            ]
            yield IndicatorPanel(
                name="RSI",
                height=4,
                min_value=0.0,
                max_value=100.0,
                reference_lines=reference_lines,
            )

    app = RSIPanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Check reference lines are configured
        assert len(panel._reference_lines) == 2
        assert panel._reference_lines[0].value == 70.0
        assert panel._reference_lines[0].label == "Overbought"
        assert panel._reference_lines[1].value == 30.0
        assert panel._reference_lines[1].label == "Oversold"

        # Show some data
        rsi_values = [50.0] * 20
        panel.show_indicator(rsi_values, 50.0)
        await pilot.pause()

        # Panel should render without errors
        labels = panel.query(Label)
        assert len(labels) > 0


@pytest.mark.asyncio
async def test_indicator_panel_with_none_values() -> None:
    """Test that the indicator panel handles None values in data (initial values)."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Create RSI-like data with initial None values (first 14 values)
        rsi_values: list[float | None] = [None] * 14 + [50.0, 55.0, 60.0, 65.0, 70.0]
        current_value = 70.0

        # Show indicator
        panel.show_indicator(rsi_values, current_value)
        await pilot.pause()

        # Should render successfully, filtering out Nones
        labels = panel.query(Label)
        # Should have header + chart lines
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_indicator_panel_all_none_values() -> None:
    """Test that the indicator panel handles all None values gracefully."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # All None values (insufficient data)
        rsi_values: list[float | None] = [None] * 20

        # Show indicator
        panel.show_indicator(rsi_values, None)
        await pilot.pause()

        # Should display "No data" message
        labels = panel.query(Label)
        assert any("No data" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_indicator_panel_downsampling() -> None:
    """Test that the indicator panel downsamples large datasets."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Create large dataset (more than 140 points = 70 chars * 2 points per char)
        large_dataset = [float(i % 100) for i in range(200)]

        # Show indicator
        panel.show_indicator(large_dataset, 50.0)
        await pilot.pause()

        # Should render without errors (downsampling applied)
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_indicator_panel_flat_values() -> None:
    """Test that the indicator panel handles flat values (no variation)."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # All same value (flat line)
        flat_values = [50.0] * 30

        # Show indicator
        panel.show_indicator(flat_values, 50.0)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_indicator_panel_extreme_values() -> None:
    """Test that the indicator panel handles values at min/max boundaries."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # RSI at boundaries (0 and 100)
        extreme_values = [0.0, 100.0, 0.0, 100.0, 50.0]

        # Show indicator
        panel.show_indicator(extreme_values, 50.0)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_indicator_panel_custom_height() -> None:
    """Test that the indicator panel respects custom height."""

    class CustomHeightApp(App[None]):
        """Test app with custom panel height."""

        def compose(self) -> ComposeResult:
            """Compose test app."""
            yield IndicatorPanel(name="MACD", height=5, min_value=-10.0, max_value=10.0)

    app = CustomHeightApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Check height is set correctly
        assert panel._height == 5

        # Show some data
        values = [0.0, 2.0, 4.0, 2.0, 0.0, -2.0, -4.0, -2.0, 0.0]
        panel.show_indicator(values, 0.0)
        await pilot.pause()

        # Should render with custom height
        labels = panel.query(Label)
        # Should have header + 5 chart lines
        chart_lines = [label for label in labels if "indicator-line" in label.classes]
        assert len(chart_lines) == 5


@pytest.mark.asyncio
async def test_indicator_panel_custom_range() -> None:
    """Test that the indicator panel works with custom min/max range."""

    class CustomRangeApp(App[None]):
        """Test app with custom value range."""

        def compose(self) -> ComposeResult:
            """Compose test app."""
            # MACD-like range (-10 to +10)
            yield IndicatorPanel(name="MACD", height=4, min_value=-10.0, max_value=10.0)

    app = CustomRangeApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Check range is set correctly
        assert panel._min_value == -10.0
        assert panel._max_value == 10.0

        # Show data in custom range
        values = [-8.0, -4.0, 0.0, 4.0, 8.0, 4.0, 0.0, -4.0]
        panel.show_indicator(values, -4.0)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_indicator_panel_hidden_no_render() -> None:
    """Test that hidden panel does not render when data is updated."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Hide panel first
        panel.hide()
        await pilot.pause()

        # Update data while hidden
        values = [50.0] * 10
        panel.show_indicator(values, 50.0)
        await pilot.pause()

        # Data should be stored but not rendered (panel still hidden)
        assert panel._indicator_values == values
        assert panel.is_visible() is False


@pytest.mark.asyncio
async def test_indicator_panel_downsample_preserves_data() -> None:
    """Test that downsampling preserves general shape of data."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Create data with clear pattern (sine-wave like)
        values = [50.0 + 30.0 * (i % 20 / 20.0) for i in range(200)]

        # Downsample
        downsampled = panel._downsample(values, 50)

        # Should have target count
        assert len(downsampled) == 50

        # Should preserve approximate range
        assert min(downsampled) >= min(values) - 5.0
        assert max(downsampled) <= max(values) + 5.0


@pytest.mark.asyncio
async def test_indicator_panel_downsample_no_op() -> None:
    """Test that downsampling is a no-op when data is smaller than target."""
    app = IndicatorPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Small dataset
        values = [50.0, 60.0, 70.0, 60.0, 50.0]

        # Downsample to larger target
        downsampled = panel._downsample(values, 100)

        # Should return original values
        assert downsampled == values


@pytest.mark.asyncio
async def test_indicator_panel_reference_line_styles() -> None:
    """Test that different reference line styles are configured correctly."""

    class MultiStyleApp(App[None]):
        """Test app with multiple line styles."""

        def compose(self) -> ComposeResult:
            """Compose test app."""
            reference_lines = [
                HorizontalLine(value=80.0, label="High", style="solid", color="\033[31m"),
                HorizontalLine(value=50.0, label="Mid", style="dashed", color="\033[33m"),
                HorizontalLine(value=20.0, label="Low", style="dotted", color="\033[32m"),
            ]
            yield IndicatorPanel(
                name="Custom",
                height=4,
                min_value=0.0,
                max_value=100.0,
                reference_lines=reference_lines,
            )

    app = MultiStyleApp()
    async with app.run_test() as pilot:
        panel = app.query_one(IndicatorPanel)

        # Check all reference lines are configured
        assert len(panel._reference_lines) == 3
        assert panel._reference_lines[0].style == "solid"
        assert panel._reference_lines[1].style == "dashed"
        assert panel._reference_lines[2].style == "dotted"

        # Show data
        values = [50.0] * 20
        panel.show_indicator(values, 50.0)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1
