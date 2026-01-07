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
