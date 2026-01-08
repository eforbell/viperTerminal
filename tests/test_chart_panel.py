"""Tests for the ChartPanel widget."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label, LoadingIndicator

from viper.services.history_data import (
    HistoricalData,
    HistoricalDataError,
    HistoricalStats,
)
from viper.widgets import ChartPanel
from viper.widgets.chart_renderer import ChartStyle


class ChartPanelTestApp(App[None]):
    """Test app for ChartPanel widget."""

    def compose(self) -> ComposeResult:
        """Compose test app."""
        yield ChartPanel()


@pytest.mark.asyncio
async def test_chart_panel_empty_state() -> None:
    """Test that the chart panel displays empty state by default."""
    app = ChartPanelTestApp()
    async with app.run_test():
        panel = app.query_one(ChartPanel)

        # Should start in empty state
        assert panel._state == "empty"

        # Should display empty message
        labels = panel.query(Label)
        assert len(labels) > 0
        assert any("No ticker selected" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_chart_panel_loading_state() -> None:
    """Test that the chart panel displays loading state correctly."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Show loading state
        panel.show_loading("AAPL", "1M")

        # Wait for UI to update
        await pilot.pause()

        # Should update state
        assert panel._state == "loading"
        assert panel._current_ticker == "AAPL"
        assert panel._current_period == "1M"

        # Should display loading indicator
        loading_indicators = panel.query(LoadingIndicator)
        assert len(loading_indicators) == 1

        # Should display loading message with ticker and period
        labels = panel.query(Label)
        assert any("Loading chart for AAPL (1M)" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_chart_panel_error_state() -> None:
    """Test that the chart panel displays error state correctly."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create error
        error = HistoricalDataError(
            ticker="INVALID",
            error_message="Invalid ticker symbol",
        )

        # Show error
        panel.show_error(error)

        # Wait for UI to update
        await pilot.pause()

        # Should update state
        assert panel._state == "error"
        assert panel._current_ticker == "INVALID"

        # Should display error message
        labels = panel.query(Label)
        assert any("Error: Invalid ticker symbol" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_chart_panel_success_state_positive_change() -> None:
    """Test displaying a successful chart with positive price change."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock historical data with positive change
        dates = [datetime.now() - timedelta(days=30-i) for i in range(30)]
        prices = [100.0 + i * 2.0 for i in range(30)]  # Increasing prices
        volumes = [1000000 + i * 10000 for i in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 5.0 for p in prices],
            lows=[p - 5.0 for p in prices],
            opens=[p - 1.0 for p in prices],
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=58.0,  # Positive change
            avg_volume=sum(volumes) / len(volumes),
            num_data_points=len(prices),
        )

        # Show chart
        panel.show_chart(data, stats)

        # Wait for UI to update
        await pilot.pause()

        # Should update state
        assert panel._state == "success"
        assert panel._current_ticker == "AAPL"
        assert panel._current_period == "1M"

        # Should display header with ticker and period
        labels = panel.query(Label)
        header_labels = [label for label in labels if "AAPL - 1M Chart" in str(label.render())]
        assert len(header_labels) > 0

        # Should display stats with positive change (green)
        stats_labels = [label for label in labels if "Change:" in str(label.render())]
        assert len(stats_labels) > 0


@pytest.mark.asyncio
async def test_chart_panel_success_state_negative_change() -> None:
    """Test displaying a successful chart with negative price change."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock historical data with negative change
        dates = [datetime.now() - timedelta(days=30-i) for i in range(30)]
        prices = [200.0 - i * 2.0 for i in range(30)]  # Decreasing prices
        volumes = [2000000 for _ in range(30)]

        data = HistoricalData(
            ticker="TSLA",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 3.0 for p in prices],
            lows=[p - 3.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=-29.0,  # Negative change
            avg_volume=2000000.0,
            num_data_points=len(prices),
        )

        # Show chart
        panel.show_chart(data, stats)

        # Wait for UI to update
        await pilot.pause()

        # Should update state
        assert panel._state == "success"
        assert panel._current_ticker == "TSLA"

        # Should display stats with negative change (red)
        labels = panel.query(Label)
        stats_labels = [label for label in labels if "Change:" in str(label.render())]
        assert len(stats_labels) > 0


@pytest.mark.asyncio
async def test_chart_panel_show_empty() -> None:
    """Test that show_empty resets the panel state."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # First show a chart
        dates = [datetime.now() - timedelta(days=i) for i in range(10)]
        prices = [100.0 + i for i in range(10)]
        volumes = [1000000 for _ in range(10)]

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 5.0 for p in prices],
            lows=[p - 5.0 for p in prices],
            opens=prices,
            period="1W",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=9.0,
            avg_volume=1000000.0,
            num_data_points=10,
        )

        panel.show_chart(data, stats)
        await pilot.pause()

        # Now show empty
        panel.show_empty()
        await pilot.pause()

        # Should reset to empty state
        assert panel._state == "empty"
        assert panel._data is None
        assert panel._stats is None
        assert panel._current_ticker is None

        # Should display empty message
        labels = panel.query(Label)
        assert any("No ticker selected" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_chart_panel_load_chart_success() -> None:
    """Test the load_chart method with successful data fetch."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Mock the fetch_historical_data function
        dates = [datetime.now() - timedelta(days=90-i) for i in range(90)]
        prices = [150.0 + i * 0.5 for i in range(90)]
        volumes = [3000000 for _ in range(90)]

        mock_data = HistoricalData(
            ticker="MSFT",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 2.0 for p in prices],
            lows=[p - 2.0 for p in prices],
            opens=prices,
            period="3M",
            interval="1d",
        )

        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data

            # Load chart
            await panel.load_chart("MSFT", "3M")
            await pilot.pause()

            # Should have called fetch
            mock_fetch.assert_called_once_with("MSFT", "3M")

            # Should be in success state
            assert panel._state == "success"
            assert panel._current_ticker == "MSFT"
            assert panel._current_period == "3M"


@pytest.mark.asyncio
async def test_chart_panel_load_chart_error() -> None:
    """Test the load_chart method with error from data fetch."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Mock the fetch_historical_data function to return error
        mock_error = HistoricalDataError(
            ticker="BADTICKER",
            error_message="Failed to fetch data",
        )

        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_error

            # Load chart
            await panel.load_chart("BADTICKER", "1M")
            await pilot.pause()

            # Should have called fetch
            mock_fetch.assert_called_once_with("BADTICKER", "1M")

            # Should be in error state
            assert panel._state == "error"
            assert panel._current_ticker == "BADTICKER"


@pytest.mark.asyncio
async def test_chart_panel_ticker_changed_during_fetch() -> None:
    """Test that chart ignores data if ticker changed during fetch."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Mock data
        dates = [datetime.now() - timedelta(days=i) for i in range(30)]
        prices = [100.0 for _ in range(30)]
        volumes = [1000000 for _ in range(30)]

        mock_data_aapl = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=prices,
            lows=prices,
            opens=prices,
            period="1M",
            interval="1d",
        )

        mock_data_msft = HistoricalData(
            ticker="MSFT",
            dates=dates,
            prices=[p * 2 for p in prices],
            volumes=volumes,
            highs=[p * 2 for p in prices],
            lows=[p * 2 for p in prices],
            opens=[p * 2 for p in prices],
            period="1M",
            interval="1d",
        )

        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            # First call returns AAPL data
            mock_fetch.side_effect = [mock_data_aapl, mock_data_msft]

            # Load chart for AAPL (don't await, so it's async)
            task_aapl = panel.load_chart("AAPL", "1M")

            # Immediately load chart for MSFT (simulating ticker change)
            task_msft = panel.load_chart("MSFT", "1M")

            # Wait for both to complete
            await task_aapl
            await task_msft
            await pilot.pause()

            # Panel should show MSFT data (most recent call)
            assert panel._current_ticker == "MSFT"
            assert panel._state == "success"


@pytest.mark.asyncio
async def test_chart_panel_different_periods() -> None:
    """Test that the panel handles different time periods correctly."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        periods = ["1W", "1M", "3M", "6M", "1Y", "5Y", "MAX"]

        for period in periods:
            # Show loading for each period
            panel.show_loading("AAPL", period)
            await pilot.pause()

            # Verify period is stored
            assert panel._current_period == period

            # Verify loading message includes period
            labels = panel.query(Label)
            assert any(f"({period})" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_chart_panel_braille_style() -> None:
    """Test chart panel with Braille rendering style."""
    app_braille = type("BrailleChartPanelTestApp", (App,), {
        "compose": lambda self: (yield ChartPanel(style=ChartStyle.BRAILLE))
    })()

    async with app_braille.run_test() as pilot:
        panel = app_braille.query_one(ChartPanel)

        # Verify renderer uses Braille style
        assert panel._renderer.style == ChartStyle.BRAILLE


@pytest.mark.asyncio
async def test_chart_panel_block_style() -> None:
    """Test chart panel with Block rendering style."""
    app_block = type("BlockChartPanelTestApp", (App,), {
        "compose": lambda self: (yield ChartPanel(style=ChartStyle.BLOCK))
    })()

    async with app_block.run_test() as pilot:
        panel = app_block.query_one(ChartPanel)

        # Verify renderer uses Block style
        assert panel._renderer.style == ChartStyle.BLOCK


@pytest.mark.asyncio
async def test_chart_panel_responsive_sizing() -> None:
    """Test that chart panel adjusts chart size to terminal dimensions."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        dates = [datetime.now() - timedelta(days=i) for i in range(30)]
        prices = [100.0 + i for i in range(30)]
        volumes = [1000000 for _ in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 5.0 for p in prices],
            lows=[p - 5.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=29.0,
            avg_volume=1000000.0,
            num_data_points=30,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # Chart should render without errors
        # The actual rendering is tested in test_chart_renderer.py
        assert panel._state == "success"


@pytest.mark.asyncio
async def test_chart_panel_format_number() -> None:
    """Test the number formatting helper method."""
    app = ChartPanelTestApp()
    async with app.run_test():
        panel = app.query_one(ChartPanel)

        # Test integer formatting
        assert panel._format_number(1234567, 0) == "1,234,567"

        # Test float with 2 decimals
        assert panel._format_number(1234.56, 2) == "1,234.56"

        # Test float with 0 decimals (converted to int)
        assert panel._format_number(1234.99, 0) == "1,234"


@pytest.mark.asyncio
async def test_chart_panel_get_timeframe_for_key() -> None:
    """Test getting timeframe period for number keys."""
    app = ChartPanelTestApp()
    async with app.run_test():
        panel = app.query_one(ChartPanel)

        # Test valid keys
        assert panel.get_timeframe_for_key("1") == "1W"
        assert panel.get_timeframe_for_key("2") == "1M"
        assert panel.get_timeframe_for_key("3") == "3M"
        assert panel.get_timeframe_for_key("4") == "6M"
        assert panel.get_timeframe_for_key("5") == "1Y"
        assert panel.get_timeframe_for_key("6") == "5Y"
        assert panel.get_timeframe_for_key("7") == "MAX"

        # Test invalid keys
        assert panel.get_timeframe_for_key("0") is None
        assert panel.get_timeframe_for_key("8") is None
        assert panel.get_timeframe_for_key("a") is None


@pytest.mark.asyncio
async def test_chart_panel_change_timeframe() -> None:
    """Test changing timeframe reloads chart with new period."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Mock data for different timeframes
        dates = [datetime.now() - timedelta(days=i) for i in range(30)]
        prices_1m = [100.0 + i for i in range(30)]
        prices_3m = [150.0 + i * 2 for i in range(30)]
        volumes = [1000000 for _ in range(30)]

        mock_data_1m = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices_1m,
            volumes=volumes,
            highs=[p + 5.0 for p in prices_1m],
            lows=[p - 5.0 for p in prices_1m],
            opens=prices_1m,
            period="1M",
            interval="1d",
        )

        mock_data_3m = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices_3m,
            volumes=volumes,
            highs=[p + 5.0 for p in prices_3m],
            lows=[p - 5.0 for p in prices_3m],
            opens=prices_3m,
            period="3M",
            interval="1d",
        )

        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            # First call returns 1M data, second returns 3M data
            mock_fetch.side_effect = [mock_data_1m, mock_data_3m]

            # Load initial chart with 1M
            await panel.load_chart("AAPL", "1M")
            await pilot.pause()

            assert panel._current_period == "1M"
            assert panel._state == "success"

            # Change timeframe to 3M
            await panel.change_timeframe("3M")
            await pilot.pause()

            # Should have reloaded with 3M period
            assert mock_fetch.call_count == 2
            mock_fetch.assert_called_with("AAPL", "3M")
            assert panel._current_period == "3M"
            assert panel._state == "success"


@pytest.mark.asyncio
async def test_chart_panel_change_timeframe_no_ticker() -> None:
    """Test that change_timeframe does nothing when no ticker is set."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Ensure no ticker is set (empty state)
        assert panel._current_ticker is None

        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            # Try to change timeframe
            await panel.change_timeframe("3M")
            await pilot.pause()

            # Should not have fetched anything
            mock_fetch.assert_not_called()
            assert panel._state == "empty"


@pytest.mark.asyncio
async def test_chart_panel_change_timeframe_same_period() -> None:
    """Test that change_timeframe does nothing when period is already current."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Mock data
        dates = [datetime.now() - timedelta(days=i) for i in range(30)]
        prices = [100.0 + i for i in range(30)]
        volumes = [1000000 for _ in range(30)]

        mock_data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 5.0 for p in prices],
            lows=[p - 5.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data

            # Load initial chart with 1M
            await panel.load_chart("AAPL", "1M")
            await pilot.pause()

            assert mock_fetch.call_count == 1
            assert panel._current_period == "1M"

            # Try to change to same period
            await panel.change_timeframe("1M")
            await pilot.pause()

            # Should not have fetched again
            assert mock_fetch.call_count == 1


@pytest.mark.asyncio
async def test_chart_panel_timeframe_bar_display() -> None:
    """Test that timeframe selector bar is displayed with active indicator."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data with 1M period
        dates = [datetime.now() - timedelta(days=i) for i in range(30)]
        prices = [100.0 + i for i in range(30)]
        volumes = [1000000 for _ in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 5.0 for p in prices],
            lows=[p - 5.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=29.0,
            avg_volume=1000000.0,
            num_data_points=30,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # Check that timeframe bar is displayed
        labels = panel.query(Label)
        timeframe_labels = [label for label in labels if any(
            period in str(label.render()) for period in ["1W", "1M", "3M", "6M", "1Y", "5Y", "MAX"]
        )]

        # Should have at least one label with timeframe info
        assert len(timeframe_labels) > 0

        # Should show all number keys (1-7)
        label_text = " ".join([str(label.render()) for label in labels])
        for key in ["1", "2", "3", "4", "5", "6", "7"]:
            assert key in label_text


@pytest.mark.asyncio
async def test_chart_panel_timeframe_persistence() -> None:
    """Test that timeframe persists across chart reloads for same ticker."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Mock data for 3M timeframe
        dates = [datetime.now() - timedelta(days=i) for i in range(90)]
        prices = [150.0 + i for i in range(90)]
        volumes = [2000000 for _ in range(90)]

        mock_data_3m = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 5.0 for p in prices],
            lows=[p - 5.0 for p in prices],
            opens=prices,
            period="3M",
            interval="1d",
        )

        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data_3m

            # Load chart with 3M timeframe
            await panel.load_chart("AAPL", "3M")
            await pilot.pause()

            # Verify timeframe is set to 3M
            assert panel._current_period == "3M"
            assert panel._current_ticker == "AAPL"

            # The timeframe should persist until explicitly changed
            # (This is tested indirectly - _current_period stays 3M until change_timeframe is called)


@pytest.mark.asyncio
async def test_chart_panel_default_timeframe() -> None:
    """Test that default timeframe is 1M for new charts."""
    app = ChartPanelTestApp()
    async with app.run_test():
        panel = app.query_one(ChartPanel)

        # Check default period
        assert panel._current_period == "1M"


@pytest.mark.asyncio
async def test_chart_panel_all_timeframes() -> None:
    """Test loading chart with all supported timeframes."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        timeframes = ["1W", "1M", "3M", "6M", "1Y", "5Y", "MAX"]

        for period in timeframes:
            # Create mock data for each timeframe
            dates = [datetime.now() - timedelta(days=i) for i in range(30)]
            prices = [100.0 + i for i in range(30)]
            volumes = [1000000 for _ in range(30)]

            mock_data = HistoricalData(
                ticker="AAPL",
                dates=dates,
                prices=prices,
                volumes=volumes,
                highs=[p + 5.0 for p in prices],
                lows=[p - 5.0 for p in prices],
                opens=prices,
                period=period,
                interval="1d",
            )

            with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = mock_data

                # Load chart with timeframe
                await panel.load_chart("AAPL", period)
                await pilot.pause()

                # Verify timeframe is set correctly
                assert panel._current_period == period
                mock_fetch.assert_called_once_with("AAPL", period)


@pytest.mark.asyncio
async def test_chart_panel_volume_toggle() -> None:
    """Test that volume can be toggled on and off."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Volume should be enabled by default
        assert panel.is_volume_enabled() is True
        assert panel._volume_enabled is True

        # Toggle volume off
        panel.toggle_volume()
        await pilot.pause()
        assert panel.is_volume_enabled() is False
        assert panel._volume_enabled is False

        # Toggle volume on
        panel.toggle_volume()
        await pilot.pause()
        assert panel.is_volume_enabled() is True
        assert panel._volume_enabled is True


@pytest.mark.asyncio
async def test_chart_panel_volume_bars_displayed() -> None:
    """Test that volume bars are displayed when volume is enabled."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data with volumes
        mock_data = HistoricalData(
            ticker="AAPL",
            dates=[datetime.now() - timedelta(days=i) for i in range(10)],
            prices=[150.0 + i for i in range(10)],
            volumes=[1000000 + i * 100000 for i in range(10)],
            highs=[155.0 + i for i in range(10)],
            lows=[145.0 + i for i in range(10)],
            opens=[148.0 + i for i in range(10)],
            period="1M",
            interval="1d",
        )

        mock_stats = HistoricalStats(
            period_high=160.0,
            period_low=145.0,
            change_percent=5.5,
            avg_volume=1500000.0,
            num_data_points=10,
        )

        # Load chart with volume (enabled by default)
        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            await panel.load_chart("AAPL", "1M")
            await pilot.pause()

            # Verify chart is shown
            assert panel._state == "success"
            assert panel._volume_enabled is True

            # Toggle volume off
            panel.toggle_volume()
            await pilot.pause()

            # Verify volume is disabled and display is updated
            assert panel._volume_enabled is False
            # Volume bars should not be rendered when disabled


@pytest.mark.asyncio
async def test_chart_panel_volume_stats_displayed() -> None:
    """Test that volume statistics are displayed when volume is enabled."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        mock_data = HistoricalData(
            ticker="AAPL",
            dates=[datetime.now() - timedelta(days=i) for i in range(5)],
            prices=[150.0, 152.0, 151.0, 153.0, 155.0],
            volumes=[1000000, 1200000, 1100000, 1500000, 1300000],
            highs=[151.0, 153.0, 152.0, 154.0, 156.0],
            lows=[149.0, 151.0, 150.0, 152.0, 154.0],
            opens=[150.0, 151.0, 152.0, 151.0, 153.0],
            period="1W",
            interval="1d",
        )

        mock_stats = HistoricalStats(
            period_high=156.0,
            period_low=149.0,
            change_percent=3.33,
            avg_volume=1220000.0,
            num_data_points=5,
        )

        # Volume is already enabled by default, just load chart
        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            await panel.load_chart("AAPL", "1W")
            await pilot.pause()

            # Verify volume stats are included in display
            # The _render_chart method should include volume stats in the stats line
            assert panel._volume_enabled is True
            assert len(panel._data.volumes) > 0  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_chart_panel_volume_empty_data() -> None:
    """Test volume toggle with empty volume data."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data with empty volumes
        mock_data = HistoricalData(
            ticker="NEWIPO",
            dates=[datetime.now()],
            prices=[100.0],
            volumes=[],  # Empty volumes
            highs=[101.0],
            lows=[99.0],
            opens=[100.0],
            period="1W",
            interval="1d",
        )

        # Volume is already enabled by default, just load chart
        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            await panel.load_chart("NEWIPO", "1W")
            await pilot.pause()

            # Should handle empty volumes gracefully
            assert panel._state == "success"
            assert panel._volume_enabled is True


@pytest.mark.asyncio
async def test_chart_panel_volume_disabled_via_config() -> None:
    """Test that volume can be disabled via config parameter."""
    class DisabledVolumeApp(App[None]):
        """Test app with volume disabled."""

        def compose(self) -> ComposeResult:
            """Compose test app."""
            yield ChartPanel(volume_enabled=False)

    app = DisabledVolumeApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Volume should be disabled when passed False
        assert panel.is_volume_enabled() is False
        assert panel._volume_enabled is False

        # Toggle volume on
        panel.toggle_volume()
        await pilot.pause()
        assert panel.is_volume_enabled() is True
        assert panel._volume_enabled is True


@pytest.mark.asyncio
async def test_chart_panel_volume_status_indicator() -> None:
    """Test that volume status is shown in chart header."""
    from datetime import datetime, timedelta

    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        mock_data = HistoricalData(
            ticker="AAPL",
            dates=[datetime.now() - timedelta(days=i) for i in range(5)],
            prices=[150.0, 152.0, 151.0, 153.0, 155.0],
            volumes=[1000000, 1200000, 1100000, 1500000, 1300000],
            highs=[151.0, 153.0, 152.0, 154.0, 156.0],
            lows=[149.0, 151.0, 150.0, 152.0, 154.0],
            opens=[150.0, 151.0, 152.0, 151.0, 153.0],
            period="1M",
            interval="1d",
        )

        mock_stats = HistoricalStats(
            period_high=156.0,
            period_low=149.0,
            change_percent=3.33,
            avg_volume=1220000.0,
            num_data_points=5,
        )

        # Load chart with volume enabled (default)
        with patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            await panel.load_chart("AAPL", "1M")
            await pilot.pause()

            # Check that "Vol: ON" appears in header
            labels = panel.query(Label)
            header_labels = [label for label in labels if "Chart" in str(label.render())]
            assert len(header_labels) > 0
            assert any("[Vol: ON]" in str(label.render()) for label in header_labels)

            # Toggle volume off
            panel.toggle_volume()
            await pilot.pause()

            # Check that "Vol: OFF" appears in header
            labels = panel.query(Label)
            header_labels = [label for label in labels if "Chart" in str(label.render())]
            assert len(header_labels) > 0
            assert any("[Vol: OFF]" in str(label.render()) for label in header_labels)


@pytest.mark.asyncio
async def test_chart_panel_ma_cycle_off_to_sma20() -> None:
    """Test cycling MA display from off to SMA20."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data with enough points for SMA20
        dates = [datetime.now() - timedelta(days=50-i) for i in range(50)]
        prices = [100.0 + i * 0.5 for i in range(50)]
        volumes = [1000000] * 50

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 2.0 for p in prices],
            lows=[p - 2.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=24.5,
            avg_volume=1000000,
            num_data_points=50,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # Should start with MA off
        assert panel.get_ma_mode() == "off"
        labels = panel.query(Label)
        header_labels = [label for label in labels if "Chart" in str(label.render())]
        # Should not have SMA in header
        assert not any("SMA20" in str(label.render()) for label in header_labels)

        # Cycle to SMA20
        panel.cycle_ma_display()
        await pilot.pause()

        # Should now be in sma20 mode
        assert panel.get_ma_mode() == "sma20"
        # Should have SMA20 in header
        labels = panel.query(Label)
        header_labels = [label for label in labels if "Chart" in str(label.render())]
        assert any("SMA20" in str(label.render()) for label in header_labels)


@pytest.mark.asyncio
async def test_chart_panel_ma_cycle_full_cycle() -> None:
    """Test full MA cycle: off -> sma20 -> sma50 -> both -> off."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data with enough points for SMA50
        dates = [datetime.now() - timedelta(days=60-i) for i in range(60)]
        prices = [100.0 + i * 0.5 for i in range(60)]
        volumes = [1000000] * 60

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 2.0 for p in prices],
            lows=[p - 2.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=29.5,
            avg_volume=1000000,
            num_data_points=60,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # Start: off
        assert panel.get_ma_mode() == "off"

        # Cycle to sma20
        panel.cycle_ma_display()
        await pilot.pause()
        assert panel.get_ma_mode() == "sma20"

        # Cycle to sma50
        panel.cycle_ma_display()
        await pilot.pause()
        assert panel.get_ma_mode() == "sma50"

        # Cycle to both
        panel.cycle_ma_display()
        await pilot.pause()
        assert panel.get_ma_mode() == "both"

        # Cycle back to off
        panel.cycle_ma_display()
        await pilot.pause()
        assert panel.get_ma_mode() == "off"


@pytest.mark.asyncio
async def test_chart_panel_ma_legend_display() -> None:
    """Test that MA legend values are displayed correctly in header."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        dates = [datetime.now() - timedelta(days=60-i) for i in range(60)]
        prices = [100.0 + i * 1.0 for i in range(60)]  # Linear increase
        volumes = [1000000] * 60

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 2.0 for p in prices],
            lows=[p - 2.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=59.0,
            avg_volume=1000000,
            num_data_points=60,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # Cycle to SMA20 mode
        panel.cycle_ma_display()
        await pilot.pause()

        # Should show SMA20 value in header
        labels = panel.query(Label)
        header_labels = [label for label in labels if "Chart" in str(label.render())]
        assert any("SMA20:" in str(label.render()) and "$" in str(label.render()) for label in header_labels)

        # Cycle to both mode
        panel.cycle_ma_display()  # sma50
        panel.cycle_ma_display()  # both
        await pilot.pause()

        # Should show both SMA20 and SMA50 values in header
        labels = panel.query(Label)
        header_labels = [label for label in labels if "Chart" in str(label.render())]
        assert any("SMA20:" in str(label.render()) and "SMA50:" in str(label.render()) for label in header_labels)


@pytest.mark.asyncio
async def test_chart_panel_ma_insufficient_data() -> None:
    """Test MA behavior when data is insufficient for calculation."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data with only 15 points (less than SMA20 needs)
        dates = [datetime.now() - timedelta(days=15-i) for i in range(15)]
        prices = [100.0 + i * 1.0 for i in range(15)]
        volumes = [1000000] * 15

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 2.0 for p in prices],
            lows=[p - 2.0 for p in prices],
            opens=prices,
            period="1W",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=14.0,
            avg_volume=1000000,
            num_data_points=15,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # MAs should be None due to insufficient data
        assert panel._sma20 is None
        assert panel._sma50 is None

        # Cycle to SMA20 mode
        panel.cycle_ma_display()
        await pilot.pause()

        # Should not crash, but no MA legend should appear
        labels = panel.query(Label)
        header_labels = [label for label in labels if "Chart" in str(label.render())]
        # Header should exist but not contain SMA values
        assert len(header_labels) > 0
        # Should not have SMA values (either no "SMA" text or no "$" after it)
        sma_in_header = any("SMA20:" in str(label.render()) for label in header_labels)
        # If SMA text is there, it shouldn't have a value
        if sma_in_header:
            assert not any("SMA20: $" in str(label.render()) for label in header_labels)


@pytest.mark.asyncio
async def test_chart_panel_ma_calculation_on_load() -> None:
    """Test that MAs are calculated when chart loads."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        dates = [datetime.now() - timedelta(days=60-i) for i in range(60)]
        prices = [100.0 + i * 1.0 for i in range(60)]
        volumes = [1000000] * 60

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 2.0 for p in prices],
            lows=[p - 2.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=59.0,
            avg_volume=1000000,
            num_data_points=60,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # MAs should be calculated and cached
        assert panel._sma20 is not None
        assert panel._sma50 is not None
        assert len(panel._sma20) == 60
        assert len(panel._sma50) == 60
        # First 19 values should be None for SMA20
        assert all(v is None for v in panel._sma20[:19])
        # Values from index 19 onwards should be floats
        assert all(isinstance(v, float) for v in panel._sma20[19:])


@pytest.mark.asyncio
async def test_chart_panel_ma_render_with_overlays() -> None:
    """Test that MA overlays are passed to chart renderer."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        dates = [datetime.now() - timedelta(days=60-i) for i in range(60)]
        prices = [100.0 + i * 1.0 for i in range(60)]
        volumes = [1000000] * 60

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 2.0 for p in prices],
            lows=[p - 2.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=59.0,
            avg_volume=1000000,
            num_data_points=60,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # Cycle to SMA20 mode
        panel.cycle_ma_display()
        await pilot.pause()

        # Verify that overlays were created (we can't easily mock the renderer,
        # but we can verify the MA values are calculated)
        assert panel._sma20 is not None
        assert panel.get_ma_mode() == "sma20"

        # Cycle to both mode
        panel.cycle_ma_display()  # sma50
        panel.cycle_ma_display()  # both
        await pilot.pause()

        # Verify both MAs available
        assert panel._sma20 is not None
        assert panel._sma50 is not None
        assert panel.get_ma_mode() == "both"


@pytest.mark.asyncio
async def test_chart_panel_ma_toggle_preserves_state() -> None:
    """Test that toggling MA preserves calculated values."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        dates = [datetime.now() - timedelta(days=60-i) for i in range(60)]
        prices = [100.0 + i * 1.0 for i in range(60)]
        volumes = [1000000] * 60

        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=[p + 2.0 for p in prices],
            lows=[p - 2.0 for p in prices],
            opens=prices,
            period="1M",
            interval="1d",
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=59.0,
            avg_volume=1000000,
            num_data_points=60,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # Store initial MA values
        initial_sma20 = panel._sma20
        initial_sma50 = panel._sma50

        # Cycle through modes
        panel.cycle_ma_display()  # sma20
        await pilot.pause()
        panel.cycle_ma_display()  # sma50
        await pilot.pause()
        panel.cycle_ma_display()  # both
        await pilot.pause()
        panel.cycle_ma_display()  # off
        await pilot.pause()

        # MA values should still be cached (not recalculated on toggle)
        assert panel._sma20 is initial_sma20
        assert panel._sma50 is initial_sma50


@pytest.mark.asyncio
async def test_chart_panel_rsi_calculation() -> None:
    """Test that RSI is calculated when chart loads."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data with enough points for RSI (requires 15+ points)
        dates = [datetime(2024, 1, i + 1) for i in range(30)]
        prices = [float(100 + i % 10) for i in range(30)]
        volumes = [int(1000000 + i * 10000) for i in range(30)]
        opens = [float(100 + (i + 0.5) % 10) for i in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            period="1M",
            dates=dates,
            prices=prices,
            volumes=volumes,
            opens=opens,
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=5.0,
            avg_volume=sum(volumes) / len(volumes),
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # RSI should be calculated
        assert panel._rsi_values is not None
        assert len(panel._rsi_values) == len(prices)
        # First 14 values should be None (RSI period)
        assert all(v is None for v in panel._rsi_values[:14])
        # Remaining values should be floats between 0 and 100
        assert all(
            v is None or (isinstance(v, float) and 0 <= v <= 100)
            for v in panel._rsi_values
        )


@pytest.mark.asyncio
async def test_chart_panel_rsi_toggle() -> None:
    """Test that RSI panel can be toggled on and off."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # RSI panel should start hidden
        assert panel._rsi_panel is not None
        assert panel.is_rsi_visible() is False

        # Load chart data
        dates = [datetime(2024, 1, i + 1) for i in range(30)]
        prices = [float(100 + i % 10) for i in range(30)]
        volumes = [int(1000000) for _ in range(30)]
        opens = [float(100) for _ in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            period="1M",
            dates=dates,
            prices=prices,
            volumes=volumes,
            opens=opens,
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=5.0,
            avg_volume=1000000,
        )

        panel.show_chart(data, stats)
        await pilot.pause()

        # Toggle RSI on
        panel.toggle_rsi()
        await pilot.pause()
        assert panel.is_rsi_visible() is True

        # Toggle RSI off
        panel.toggle_rsi()
        await pilot.pause()
        assert panel.is_rsi_visible() is False


@pytest.mark.asyncio
async def test_chart_panel_rsi_insufficient_data() -> None:
    """Test that RSI is not calculated when data is insufficient."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data with too few points for RSI (< 15)
        dates = [datetime(2024, 1, i + 1) for i in range(10)]
        prices = [float(100 + i) for i in range(10)]
        volumes = [int(1000000) for _ in range(10)]
        opens = [float(100) for _ in range(10)]

        data = HistoricalData(
            ticker="AAPL",
            period="1W",
            dates=dates,
            prices=prices,
            volumes=volumes,
            opens=opens,
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=5.0,
            avg_volume=1000000,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # RSI should be None due to insufficient data
        assert panel._rsi_values is None


@pytest.mark.asyncio
async def test_chart_panel_rsi_panel_updates() -> None:
    """Test that RSI panel receives data updates when visible."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        dates = [datetime(2024, 1, i + 1) for i in range(30)]
        prices = [float(100 + i % 10) for i in range(30)]
        volumes = [int(1000000) for _ in range(30)]
        opens = [float(100) for _ in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            period="1M",
            dates=dates,
            prices=prices,
            volumes=volumes,
            opens=opens,
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=5.0,
            avg_volume=1000000,
        )

        # Show chart and toggle RSI on
        panel.show_chart(data, stats)
        await pilot.pause()

        panel.toggle_rsi()
        await pilot.pause()

        # RSI panel should have received the data
        assert panel._rsi_panel is not None
        assert panel._rsi_panel.is_visible() is True
        assert panel._rsi_panel._indicator_values == panel._rsi_values


@pytest.mark.asyncio
async def test_chart_panel_rsi_caching() -> None:
    """Test that RSI values are cached and not recalculated on toggle."""
    app = ChartPanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(ChartPanel)

        # Create mock data
        dates = [datetime(2024, 1, i + 1) for i in range(30)]
        prices = [float(100 + i % 10) for i in range(30)]
        volumes = [int(1000000) for _ in range(30)]
        opens = [float(100) for _ in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            period="1M",
            dates=dates,
            prices=prices,
            volumes=volumes,
            opens=opens,
        )

        stats = HistoricalStats(
            period_high=max(prices),
            period_low=min(prices),
            change_percent=5.0,
            avg_volume=1000000,
        )

        # Show chart
        panel.show_chart(data, stats)
        await pilot.pause()

        # Store initial RSI values
        initial_rsi = panel._rsi_values

        # Toggle RSI on and off
        panel.toggle_rsi()
        await pilot.pause()
        panel.toggle_rsi()
        await pilot.pause()

        # RSI values should still be cached (not recalculated on toggle)
        assert panel._rsi_values is initial_rsi
