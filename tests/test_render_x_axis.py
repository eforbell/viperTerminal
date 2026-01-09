"""Tests for render_x_axis() function."""

from datetime import datetime, timedelta

from viper.services.history_data import HistoricalData
from viper.widgets.chart_context import ChartContext
from viper.widgets.chart_renderer import render_x_axis


class TestRenderXAxis:
    """Test suite for render_x_axis() function."""

    def test_render_x_axis_basic(self) -> None:
        """Test basic X-axis rendering with dates."""
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(30)]
        prices = [100.0 + i for i in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            period="1M",
            interval="1d",
            dates=dates,
            prices=prices,
            volumes=[1000000] * 30,
            opens=[99.0 + i for i in range(30)],
            highs=[101.0 + i for i in range(30)],
            lows=[98.0 + i for i in range(30)]
        )

        context = ChartContext.from_historical_data(data, width=80, height=20)
        x_axis_lines = render_x_axis(context)

        # Should return 2 lines: border line and date labels
        assert len(x_axis_lines) == 2
        assert "└" in x_axis_lines[0]
        assert "─" in x_axis_lines[0]
        # Date labels should be present
        assert any(char.isdigit() for char in x_axis_lines[1])

    def test_render_x_axis_no_dates(self) -> None:
        """Test X-axis rendering with no dates."""
        data = HistoricalData(
            ticker="AAPL",
            period="1M",
            interval="1d",
            dates=[],
            prices=[100.0] * 10,
            volumes=[1000000] * 10,
            opens=[99.0] * 10,
            highs=[101.0] * 10,
            lows=[98.0] * 10
        )

        context = ChartContext.from_historical_data(data, width=80, height=20)
        x_axis_lines = render_x_axis(context)

        # Should still return 2 lines (border + empty labels)
        assert len(x_axis_lines) == 2
        assert "└" in x_axis_lines[0]
        assert "─" in x_axis_lines[0]

    def test_render_x_axis_short_period(self) -> None:
        """Test X-axis with short period (1W) - should show MM/DD format."""
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(7)]
        prices = [100.0 + i for i in range(7)]

        data = HistoricalData(
            ticker="AAPL",
            period="1W",
            interval="1d",
            dates=dates,
            prices=prices,
            volumes=[1000000] * 7,
            opens=[99.0 + i for i in range(7)],
            highs=[101.0 + i for i in range(7)],
            lows=[98.0 + i for i in range(7)]
        )

        context = ChartContext.from_historical_data(data, width=80, height=20)
        x_axis_lines = render_x_axis(context)

        # Should use MM/DD format for short periods
        assert len(x_axis_lines) == 2
        assert any(char.isdigit() for char in x_axis_lines[1])

    def test_render_x_axis_long_period(self) -> None:
        """Test X-axis with long period (5Y) - should show YYYY format."""
        dates = [datetime(2019, 1, 1) + timedelta(days=i * 30) for i in range(60)]
        prices = [100.0 + i for i in range(60)]

        data = HistoricalData(
            ticker="AAPL",
            period="5Y",
            interval="1d",
            dates=dates,
            prices=prices,
            volumes=[1000000] * 60,
            opens=[99.0 + i for i in range(60)],
            highs=[101.0 + i for i in range(60)],
            lows=[98.0 + i for i in range(60)]
        )

        context = ChartContext.from_historical_data(data, width=80, height=20)
        x_axis_lines = render_x_axis(context)

        # Should use YYYY format for long periods
        assert len(x_axis_lines) == 2
        assert "2019" in x_axis_lines[1] or "2020" in x_axis_lines[1]

    def test_render_x_axis_alignment_width(self) -> None:
        """Test that X-axis width aligns with chart_area_width from context."""
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(30)]
        prices = [100.0 + i for i in range(30)]

        data = HistoricalData(
            ticker="AAPL",
            period="1M",
            interval="1d",
            dates=dates,
            prices=prices,
            volumes=[1000000] * 30,
            opens=[99.0 + i for i in range(30)],
            highs=[101.0 + i for i in range(30)],
            lows=[98.0 + i for i in range(30)]
        )

        context = ChartContext.from_historical_data(data, width=100, height=20)
        x_axis_lines = render_x_axis(context)

        # X-axis should be width = total_width (includes y_axis_width padding)
        assert len(x_axis_lines[0]) == context.total_width
        assert len(x_axis_lines[1]) == context.total_width

    def test_render_x_axis_crypto_ticker(self) -> None:
        """Test X-axis rendering with crypto ticker."""
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(30)]
        prices = [50000.0 + i * 100 for i in range(30)]

        data = HistoricalData(
            ticker="BTC-USD",
            period="1M",
            interval="1d",
            dates=dates,
            prices=prices,
            volumes=[1000000] * 30,
            opens=[49900.0 + i * 100 for i in range(30)],
            highs=[50100.0 + i * 100 for i in range(30)],
            lows=[49800.0 + i * 100 for i in range(30)]
        )

        context = ChartContext.from_historical_data(data, width=80, height=20)
        x_axis_lines = render_x_axis(context)

        # Should work the same for crypto as stocks
        assert len(x_axis_lines) == 2
        assert "└" in x_axis_lines[0]
        assert "─" in x_axis_lines[0]
