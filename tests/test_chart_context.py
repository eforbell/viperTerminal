"""Tests for ChartContext dataclass."""

from datetime import datetime, timedelta

import pytest

from viper.services.history_data import HistoricalData
from viper.widgets.chart_context import ChartContext


class TestChartContextBasics:
    """Test basic ChartContext creation and properties."""

    def test_create_chart_context_with_all_fields(self) -> None:
        """Test creating ChartContext with all required fields."""
        dates = [datetime(2024, 1, i + 1) for i in range(5)]
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        volumes = [1000, 1100, 1200, 1300, 1400]
        opens = [99.0, 100.5, 101.5, 102.5, 103.5]
        closes = [100.0, 101.0, 102.0, 103.0, 104.0]
        highs = [101.0, 102.0, 103.0, 104.0, 105.0]
        lows = [98.0, 99.0, 100.0, 101.0, 102.0]

        context = ChartContext(
            ticker="AAPL",
            period="1W",
            dates=dates,
            prices=prices,
            volumes=volumes,
            opens=opens,
            closes=closes,
            highs=highs,
            lows=lows,
            total_width=100,
            total_height=30,
            y_axis_width=12,
        )

        assert context.ticker == "AAPL"
        assert context.period == "1W"
        assert context.dates == dates
        assert context.prices == prices
        assert context.volumes == volumes
        assert context.opens == opens
        assert context.closes == closes
        assert context.highs == highs
        assert context.lows == lows
        assert context.total_width == 100
        assert context.total_height == 30
        assert context.y_axis_width == 12

    def test_chart_area_width_computed_property(self) -> None:
        """Test chart_area_width computed property calculation."""
        context = ChartContext(
            ticker="AAPL",
            period="1M",
            dates=[datetime(2024, 1, 1)],
            prices=[150.0],
            volumes=[1000],
            opens=[149.0],
            closes=[150.0],
            highs=[151.0],
            lows=[148.0],
            total_width=100,
            total_height=30,
            y_axis_width=12,
        )

        assert context.chart_area_width == 88  # 100 - 12

    def test_chart_area_width_with_custom_y_axis_width(self) -> None:
        """Test chart_area_width with non-default y_axis_width."""
        context = ChartContext(
            ticker="AAPL",
            period="1M",
            dates=[datetime(2024, 1, 1)],
            prices=[150.0],
            volumes=[1000],
            opens=[149.0],
            closes=[150.0],
            highs=[151.0],
            lows=[148.0],
            total_width=100,
            total_height=30,
            y_axis_width=15,  # Custom width
        )

        assert context.chart_area_width == 85  # 100 - 15

    def test_chart_context_is_frozen(self) -> None:
        """Test that ChartContext is immutable (frozen=True)."""
        context = ChartContext(
            ticker="AAPL",
            period="1M",
            dates=[datetime(2024, 1, 1)],
            prices=[150.0],
            volumes=[1000],
            opens=[149.0],
            closes=[150.0],
            highs=[151.0],
            lows=[148.0],
            total_width=100,
            total_height=30,
        )

        # Should raise FrozenInstanceError when trying to modify
        with pytest.raises(AttributeError):
            context.ticker = "MSFT"  # type: ignore[misc]

        with pytest.raises(AttributeError):
            context.total_width = 200  # type: ignore[misc]


class TestChartContextFactory:
    """Test ChartContext.from_historical_data factory method."""

    def test_from_historical_data_basic(self) -> None:
        """Test creating ChartContext from HistoricalData."""
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(5)]
        historical_data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=[100.0, 101.0, 102.0, 103.0, 104.0],
            volumes=[1000, 1100, 1200, 1300, 1400],
            highs=[101.0, 102.0, 103.0, 104.0, 105.0],
            lows=[99.0, 100.0, 101.0, 102.0, 103.0],
            opens=[99.5, 100.5, 101.5, 102.5, 103.5],
            period="1W",
            interval="1d",
        )

        context = ChartContext.from_historical_data(
            historical_data,
            width=100,
            height=30,
        )

        assert context.ticker == "AAPL"
        assert context.period == "1W"
        assert context.dates == dates
        assert context.prices == [100.0, 101.0, 102.0, 103.0, 104.0]
        assert context.volumes == [1000, 1100, 1200, 1300, 1400]
        assert context.opens == [99.5, 100.5, 101.5, 102.5, 103.5]
        assert context.closes == [100.0, 101.0, 102.0, 103.0, 104.0]  # closes = prices
        assert context.highs == [101.0, 102.0, 103.0, 104.0, 105.0]
        assert context.lows == [99.0, 100.0, 101.0, 102.0, 103.0]
        assert context.total_width == 100
        assert context.total_height == 30
        assert context.y_axis_width == 12  # default

    def test_from_historical_data_with_custom_y_axis_width(self) -> None:
        """Test factory method with custom y_axis_width."""
        historical_data = HistoricalData(
            ticker="BTC-USD",
            dates=[datetime(2024, 1, 1)],
            prices=[45000.0],
            volumes=[1000000],
            highs=[46000.0],
            lows=[44000.0],
            opens=[44500.0],
            period="1D",
            interval="1h",
        )

        context = ChartContext.from_historical_data(
            historical_data,
            width=120,
            height=40,
            y_axis_width=15,  # Custom
        )

        assert context.ticker == "BTC-USD"
        assert context.total_width == 120
        assert context.total_height == 40
        assert context.y_axis_width == 15
        assert context.chart_area_width == 105  # 120 - 15

    def test_from_historical_data_crypto(self) -> None:
        """Test factory method with crypto ticker."""
        historical_data = HistoricalData(
            ticker="ETH-USD",
            dates=[datetime(2024, 1, i + 1) for i in range(3)],
            prices=[2500.0, 2550.0, 2600.0],
            volumes=[500000, 510000, 520000],
            highs=[2600.0, 2650.0, 2700.0],
            lows=[2450.0, 2500.0, 2550.0],
            opens=[2480.0, 2520.0, 2570.0],
            period="1W",
            interval="1d",
        )

        context = ChartContext.from_historical_data(
            historical_data,
            width=80,
            height=24,
        )

        assert context.ticker == "ETH-USD"
        assert len(context.prices) == 3
        assert len(context.volumes) == 3
        assert context.chart_area_width == 68  # 80 - 12


class TestChartContextDimensions:
    """Test dimension calculations and edge cases."""

    def test_minimum_terminal_size(self) -> None:
        """Test ChartContext with minimum terminal size (80x24)."""
        historical_data = HistoricalData(
            ticker="AAPL",
            dates=[datetime(2024, 1, 1)],
            prices=[150.0],
            volumes=[1000],
            highs=[151.0],
            lows=[149.0],
            opens=[149.5],
            period="1D",
            interval="1h",
        )

        context = ChartContext.from_historical_data(
            historical_data,
            width=80,
            height=24,
        )

        assert context.total_width == 80
        assert context.total_height == 24
        assert context.chart_area_width == 68  # 80 - 12

    def test_large_terminal_size(self) -> None:
        """Test ChartContext with large terminal size."""
        historical_data = HistoricalData(
            ticker="AAPL",
            dates=[datetime(2024, 1, 1)],
            prices=[150.0],
            volumes=[1000],
            highs=[151.0],
            lows=[149.0],
            opens=[149.5],
            period="1D",
            interval="1h",
        )

        context = ChartContext.from_historical_data(
            historical_data,
            width=200,
            height=60,
        )

        assert context.total_width == 200
        assert context.total_height == 60
        assert context.chart_area_width == 188  # 200 - 12

    def test_zero_y_axis_width_edge_case(self) -> None:
        """Test with y_axis_width=0 (no Y-axis)."""
        context = ChartContext(
            ticker="AAPL",
            period="1M",
            dates=[datetime(2024, 1, 1)],
            prices=[150.0],
            volumes=[1000],
            opens=[149.0],
            closes=[150.0],
            highs=[151.0],
            lows=[148.0],
            total_width=100,
            total_height=30,
            y_axis_width=0,  # No Y-axis
        )

        assert context.chart_area_width == 100  # 100 - 0


class TestChartContextDataLengths:
    """Test data length invariants."""

    def test_all_data_lists_same_length(self) -> None:
        """Test that all data lists have matching lengths."""
        dates = [datetime(2024, 1, i + 1) for i in range(10)]
        prices = [100.0 + i for i in range(10)]
        volumes = [1000 + i * 100 for i in range(10)]
        opens = [99.0 + i for i in range(10)]
        closes = [100.0 + i for i in range(10)]
        highs = [101.0 + i for i in range(10)]
        lows = [98.0 + i for i in range(10)]

        context = ChartContext(
            ticker="AAPL",
            period="1M",
            dates=dates,
            prices=prices,
            volumes=volumes,
            opens=opens,
            closes=closes,
            highs=highs,
            lows=lows,
            total_width=100,
            total_height=30,
        )

        assert len(context.dates) == 10
        assert len(context.prices) == 10
        assert len(context.volumes) == 10
        assert len(context.opens) == 10
        assert len(context.closes) == 10
        assert len(context.highs) == 10
        assert len(context.lows) == 10

    def test_single_data_point(self) -> None:
        """Test ChartContext with single data point."""
        context = ChartContext(
            ticker="AAPL",
            period="1D",
            dates=[datetime(2024, 1, 1)],
            prices=[150.0],
            volumes=[1000],
            opens=[149.0],
            closes=[150.0],
            highs=[151.0],
            lows=[148.0],
            total_width=100,
            total_height=30,
        )

        assert len(context.dates) == 1
        assert len(context.prices) == 1
        assert len(context.volumes) == 1

    def test_large_dataset(self) -> None:
        """Test ChartContext with large dataset (200+ points)."""
        num_points = 250
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(num_points)]
        prices = [100.0 + (i * 0.5) for i in range(num_points)]
        volumes = [1000 + (i * 10) for i in range(num_points)]
        opens = [99.5 + (i * 0.5) for i in range(num_points)]
        closes = prices
        highs = [100.5 + (i * 0.5) for i in range(num_points)]
        lows = [99.0 + (i * 0.5) for i in range(num_points)]

        context = ChartContext(
            ticker="AAPL",
            period="1Y",
            dates=dates,
            prices=prices,
            volumes=volumes,
            opens=opens,
            closes=closes,
            highs=highs,
            lows=lows,
            total_width=100,
            total_height=30,
        )

        assert len(context.dates) == 250
        assert len(context.prices) == 250
        assert len(context.volumes) == 250


class TestChartContextEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_data_lists(self) -> None:
        """Test ChartContext with empty data lists."""
        context = ChartContext(
            ticker="AAPL",
            period="1D",
            dates=[],
            prices=[],
            volumes=[],
            opens=[],
            closes=[],
            highs=[],
            lows=[],
            total_width=100,
            total_height=30,
        )

        assert len(context.dates) == 0
        assert len(context.prices) == 0
        assert len(context.volumes) == 0
        assert context.chart_area_width == 88  # Still calculates correctly

    def test_different_ticker_formats(self) -> None:
        """Test ChartContext with different ticker symbol formats."""
        # Stock ticker
        stock_context = ChartContext(
            ticker="AAPL",
            period="1M",
            dates=[datetime(2024, 1, 1)],
            prices=[150.0],
            volumes=[1000],
            opens=[149.0],
            closes=[150.0],
            highs=[151.0],
            lows=[148.0],
            total_width=100,
            total_height=30,
        )
        assert stock_context.ticker == "AAPL"

        # Crypto ticker
        crypto_context = ChartContext(
            ticker="BTC-USD",
            period="1M",
            dates=[datetime(2024, 1, 1)],
            prices=[45000.0],
            volumes=[1000000],
            opens=[44000.0],
            closes=[45000.0],
            highs=[46000.0],
            lows=[43000.0],
            total_width=100,
            total_height=30,
        )
        assert crypto_context.ticker == "BTC-USD"

    def test_different_periods(self) -> None:
        """Test ChartContext with different period strings."""
        periods = ["1D", "1W", "1M", "3M", "6M", "1Y", "5Y", "MAX"]

        for period in periods:
            context = ChartContext(
                ticker="AAPL",
                period=period,
                dates=[datetime(2024, 1, 1)],
                prices=[150.0],
                volumes=[1000],
                opens=[149.0],
                closes=[150.0],
                highs=[151.0],
                lows=[148.0],
                total_width=100,
                total_height=30,
            )
            assert context.period == period
