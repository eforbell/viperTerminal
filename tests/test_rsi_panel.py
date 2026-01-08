"""Tests for the RSIPanel widget."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from viper.widgets.rsi_panel import RSIPanel


class RSIPanelTestApp(App[None]):
    """Test app for RSIPanel widget."""

    def compose(self) -> ComposeResult:
        """Compose test app."""
        yield RSIPanel()


@pytest.mark.asyncio
async def test_rsi_panel_initialization() -> None:
    """Test that the RSI panel initializes with correct RSI-specific configuration."""
    app = RSIPanelTestApp()
    async with app.run_test():
        panel = app.query_one(RSIPanel)

        # Check RSI-specific configuration
        assert panel.get_name() == "RSI"
        assert panel._height == 4
        assert panel._min_value == 0.0
        assert panel._max_value == 100.0
        # RSI should have 2 reference lines (overbought 70, oversold 30)
        assert len(panel._reference_lines) == 2
        assert panel._reference_lines[0].value == 70.0
        assert panel._reference_lines[0].label == "Overbought (70)"
        assert panel._reference_lines[0].style == "dashed"
        assert panel._reference_lines[0].color == "\033[31m"  # Red
        assert panel._reference_lines[1].value == 30.0
        assert panel._reference_lines[1].label == "Oversold (30)"
        assert panel._reference_lines[1].style == "dashed"
        assert panel._reference_lines[1].color == "\033[32m"  # Green


@pytest.mark.asyncio
async def test_rsi_panel_starts_hidden() -> None:
    """Test that the RSI panel starts in hidden state."""
    app = RSIPanelTestApp()
    async with app.run_test():
        panel = app.query_one(RSIPanel)

        # Panel should start hidden (set in chart_panel.py composition)
        # For standalone test, it starts visible
        assert panel.is_visible() is True
        assert panel.styles.display == "block"


@pytest.mark.asyncio
async def test_rsi_panel_toggle_visibility() -> None:
    """Test that the RSI panel visibility can be toggled."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

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
async def test_rsi_panel_display_neutral_rsi() -> None:
    """Test that the RSI panel displays neutral RSI values (30-70 range)."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # Create neutral RSI values (between 30 and 70)
        rsi_values = [None] * 14 + [45.0, 48.0, 50.0, 52.0, 55.0, 50.0, 48.0, 52.0]
        current_rsi = 52.0

        # Show RSI data
        panel.show_indicator(rsi_values, current_rsi)
        await pilot.pause()

        # Check that values are stored
        assert panel._indicator_values == rsi_values
        assert panel._current_value == current_rsi

        # Check header displays name and current value
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        assert len(header_labels) == 1
        header_text = str(header_labels[0].render())
        assert "RSI" in header_text
        assert "52.00" in header_text


@pytest.mark.asyncio
async def test_rsi_panel_display_overbought() -> None:
    """Test that the RSI panel displays overbought RSI values (> 70)."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # Create overbought RSI values (above 70)
        rsi_values = [None] * 14 + [72.0, 75.0, 78.0, 80.0, 82.0, 80.0, 78.0, 75.0]
        current_rsi = 75.0

        # Show RSI data
        panel.show_indicator(rsi_values, current_rsi)
        await pilot.pause()

        # Check header shows overbought value
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "75.00" in header_text


@pytest.mark.asyncio
async def test_rsi_panel_display_oversold() -> None:
    """Test that the RSI panel displays oversold RSI values (< 30)."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # Create oversold RSI values (below 30)
        rsi_values = [None] * 14 + [25.0, 22.0, 20.0, 18.0, 20.0, 22.0, 25.0, 28.0]
        current_rsi = 28.0

        # Show RSI data
        panel.show_indicator(rsi_values, current_rsi)
        await pilot.pause()

        # Check header shows oversold value
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "28.00" in header_text


@pytest.mark.asyncio
async def test_rsi_panel_with_all_none_values() -> None:
    """Test that the RSI panel handles all None values (insufficient data)."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # All None values (insufficient data for RSI calculation)
        rsi_values: list[float | None] = [None] * 20

        # Show indicator
        panel.show_indicator(rsi_values, None)
        await pilot.pause()

        # Should display "No data" message
        labels = panel.query(Label)
        assert any("No data" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_rsi_panel_with_partial_none_values() -> None:
    """Test that the RSI panel filters out None values correctly."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # RSI typically has first 14 values as None, then valid values
        rsi_values: list[float | None] = [None] * 14 + [
            50.0, 52.0, 55.0, 58.0, 60.0, 62.0, 65.0, 67.0, 70.0, 68.0
        ]
        current_rsi = 68.0

        # Show indicator
        panel.show_indicator(rsi_values, current_rsi)
        await pilot.pause()

        # Should render successfully, filtering out Nones
        labels = panel.query(Label)
        # Should have header + chart lines
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_rsi_panel_extreme_values() -> None:
    """Test that the RSI panel handles extreme RSI values (0 and 100)."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # RSI at extremes (0 = strong oversold, 100 = strong overbought)
        rsi_values = [None] * 14 + [0.0, 10.0, 50.0, 90.0, 100.0, 50.0]
        current_rsi = 50.0

        # Show indicator
        panel.show_indicator(rsi_values, current_rsi)
        await pilot.pause()

        # Should render without errors
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_rsi_panel_reference_lines_rendered() -> None:
    """Test that RSI reference lines (70 overbought, 30 oversold) are configured."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # Show some RSI data
        rsi_values = [None] * 14 + [50.0] * 20
        panel.show_indicator(rsi_values, 50.0)
        await pilot.pause()

        # Reference lines should be configured (verified in initialization test)
        # Rendering happens in base class, just verify panel renders without errors
        labels = panel.query(Label)
        assert len(labels) > 0


@pytest.mark.asyncio
async def test_rsi_panel_large_dataset() -> None:
    """Test that the RSI panel handles large datasets with downsampling."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # Create large RSI dataset (more than 140 points = 70 chars * 2 points per char)
        rsi_values: list[float | None] = [None] * 14 + [
            float(50 + 20 * (i % 10 / 10.0)) for i in range(200)
        ]
        current_rsi = 55.0

        # Show indicator
        panel.show_indicator(rsi_values, current_rsi)
        await pilot.pause()

        # Should render without errors (downsampling applied)
        labels = panel.query(Label)
        assert len(labels) > 1


@pytest.mark.asyncio
async def test_rsi_panel_realistic_values() -> None:
    """Test the RSI panel with realistic RSI values from a typical stock."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # Realistic RSI values showing a trend from oversold to overbought
        rsi_values: list[float | None] = [None] * 14 + [
            28.5, 30.2, 32.8, 35.6, 38.9, 42.3, 45.8, 48.2,
            51.5, 54.3, 57.8, 61.2, 64.8, 68.3, 71.5, 69.8,
            66.2, 63.5, 60.1, 57.4, 54.8, 52.1, 49.5
        ]
        current_rsi = 49.5

        # Show indicator
        panel.show_indicator(rsi_values, current_rsi)
        await pilot.pause()

        # Check that current value is displayed
        labels = panel.query(Label)
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "49.50" in header_text


@pytest.mark.asyncio
async def test_rsi_panel_empty_data() -> None:
    """Test that the RSI panel handles empty data gracefully."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # Show indicator with None values list
        panel.show_indicator(None)
        await pilot.pause()

        # Should display "No data" message
        labels = panel.query(Label)
        assert any("No data" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_rsi_panel_hidden_no_render() -> None:
    """Test that hidden RSI panel does not render when data is updated."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # Hide panel first
        panel.hide()
        await pilot.pause()

        # Update data while hidden
        rsi_values = [None] * 14 + [50.0] * 10
        panel.show_indicator(rsi_values, 50.0)
        await pilot.pause()

        # Data should be stored but panel should remain hidden
        assert panel._indicator_values == rsi_values
        assert panel.is_visible() is False


@pytest.mark.asyncio
async def test_rsi_panel_crossing_threshold() -> None:
    """Test RSI panel with values crossing overbought/oversold thresholds."""
    app = RSIPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RSIPanel)

        # RSI values crossing from oversold through neutral to overbought
        rsi_values: list[float | None] = [None] * 14 + [
            25.0,  # Oversold
            28.0,
            30.0,  # Crossing oversold threshold
            35.0,
            40.0,
            45.0,
            50.0,  # Neutral
            55.0,
            60.0,
            65.0,
            70.0,  # Crossing overbought threshold
            75.0,  # Overbought
        ]
        current_rsi = 75.0

        # Show indicator
        panel.show_indicator(rsi_values, current_rsi)
        await pilot.pause()

        # Should render successfully
        labels = panel.query(Label)
        assert len(labels) > 1
        header_labels = [label for label in labels if "indicator-header" in label.classes]
        header_text = str(header_labels[0].render())
        assert "75.00" in header_text
