"""Tests for historical price data service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from viper.services.history_data import (
    HistoricalData,
    HistoricalDataError,
    HistoricalStats,
    calculate_stats,
    fetch_historical_data,
)


def create_mock_history_df(num_points: int = 10, start_price: float = 100.0) -> pd.DataFrame:
    """Create a mock historical data DataFrame."""
    dates = pd.date_range(start="2024-01-01", periods=num_points, freq="D")
    data = {
        "Open": [start_price + i * 0.5 for i in range(num_points)],
        "High": [start_price + i * 0.5 + 2.0 for i in range(num_points)],
        "Low": [start_price + i * 0.5 - 1.0 for i in range(num_points)],
        "Close": [start_price + i for i in range(num_points)],
        "Volume": [1000000 + i * 10000 for i in range(num_points)],
    }
    return pd.DataFrame(data, index=dates)


class TestHistoricalData:
    """Tests for HistoricalData dataclass."""

    def test_historical_data_creation(self) -> None:
        """Test HistoricalData dataclass instantiation."""
        dates = [datetime(2024, 1, i + 1) for i in range(5)]
        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=[100.0, 101.0, 102.0, 103.0, 104.0],
            volumes=[1000000, 1100000, 1200000, 1300000, 1400000],
            highs=[101.0, 102.0, 103.0, 104.0, 105.0],
            lows=[99.0, 100.0, 101.0, 102.0, 103.0],
            opens=[99.5, 100.5, 101.5, 102.5, 103.5],
            period="1M",
            interval="1d",
        )
        assert data.ticker == "AAPL"
        assert len(data.dates) == 5
        assert len(data.prices) == 5
        assert len(data.volumes) == 5
        assert data.period == "1M"
        assert data.interval == "1d"


class TestHistoricalDataError:
    """Tests for HistoricalDataError dataclass."""

    def test_historical_data_error_creation(self) -> None:
        """Test HistoricalDataError dataclass instantiation."""
        error = HistoricalDataError(
            ticker="INVALID", error_message="No historical data available"
        )
        assert error.ticker == "INVALID"
        assert error.error_message == "No historical data available"


class TestHistoricalStats:
    """Tests for HistoricalStats dataclass."""

    def test_historical_stats_creation(self) -> None:
        """Test HistoricalStats dataclass instantiation."""
        stats = HistoricalStats(
            period_high=110.0,
            period_low=90.0,
            change_percent=10.0,
            avg_volume=1250000.0,
            num_data_points=30,
        )
        assert stats.period_high == 110.0
        assert stats.period_low == 90.0
        assert stats.change_percent == 10.0
        assert stats.avg_volume == 1250000.0
        assert stats.num_data_points == 30


class TestCalculateStats:
    """Tests for calculate_stats function."""

    def test_calculate_stats_basic(self) -> None:
        """Test stats calculation with normal data."""
        dates = [datetime(2024, 1, i + 1) for i in range(5)]
        data = HistoricalData(
            ticker="AAPL",
            dates=dates,
            prices=[100.0, 102.0, 101.0, 103.0, 105.0],
            volumes=[1000000, 1100000, 1200000, 1300000, 1400000],
            highs=[102.0, 104.0, 103.0, 105.0, 107.0],
            lows=[99.0, 101.0, 100.0, 102.0, 104.0],
            opens=[99.5, 101.5, 100.5, 102.5, 104.5],
            period="1M",
            interval="1d",
        )
        stats = calculate_stats(data)

        assert stats.period_high == 107.0
        assert stats.period_low == 99.0
        assert stats.change_percent == pytest.approx(5.0, rel=1e-3)  # (105-100)/100 * 100
        assert stats.avg_volume == 1200000.0
        assert stats.num_data_points == 5

    def test_calculate_stats_negative_change(self) -> None:
        """Test stats calculation with declining prices."""
        dates = [datetime(2024, 1, i + 1) for i in range(3)]
        data = HistoricalData(
            ticker="TEST",
            dates=dates,
            prices=[100.0, 95.0, 90.0],
            volumes=[1000000, 1000000, 1000000],
            highs=[101.0, 96.0, 91.0],
            lows=[99.0, 94.0, 89.0],
            opens=[100.0, 95.0, 90.0],
            period="1W",
            interval="1d",
        )
        stats = calculate_stats(data)

        assert stats.change_percent == pytest.approx(-10.0, rel=1e-3)  # (90-100)/100 * 100

    def test_calculate_stats_single_point(self) -> None:
        """Test stats calculation with single data point."""
        dates = [datetime(2024, 1, 1)]
        data = HistoricalData(
            ticker="TEST",
            dates=dates,
            prices=[100.0],
            volumes=[1000000],
            highs=[101.0],
            lows=[99.0],
            opens=[100.0],
            period="1W",
            interval="1d",
        )
        stats = calculate_stats(data)

        assert stats.period_high == 101.0
        assert stats.period_low == 99.0
        assert stats.change_percent == 0.0  # Single point = no change
        assert stats.avg_volume == 1000000.0
        assert stats.num_data_points == 1


class TestFetchHistoricalData:
    """Tests for fetch_historical_data async function."""

    @pytest.mark.asyncio
    async def test_fetch_valid_ticker_1m_period(self) -> None:
        """Test fetching valid ticker with 1M period returns HistoricalData."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_history_df(num_points=30)

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
            result = await fetch_historical_data("AAPL", period="1M")

        assert isinstance(result, HistoricalData)
        assert result.ticker == "AAPL"
        assert result.period == "1M"
        assert result.interval == "1d"
        assert len(result.prices) == 30
        assert len(result.dates) == 30
        assert len(result.volumes) == 30
        assert len(result.highs) == 30
        assert len(result.lows) == 30
        assert len(result.opens) == 30
        # Verify yfinance was called with correct parameters
        mock_ticker.history.assert_called_once_with(period="1mo", interval="1d")

    @pytest.mark.asyncio
    async def test_fetch_all_periods(self) -> None:
        """Test all supported periods map correctly."""
        periods_to_test = ["1W", "1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"]
        expected_yf_periods = ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]

        for user_period, yf_period in zip(periods_to_test, expected_yf_periods):
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = create_mock_history_df(num_points=10)

            with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
                result = await fetch_historical_data("AAPL", period=user_period)

            assert isinstance(result, HistoricalData)
            assert result.period == user_period
            # Verify correct yfinance period was used
            mock_ticker.history.assert_called_once()
            call_args = mock_ticker.history.call_args
            assert call_args.kwargs["period"] == yf_period

    @pytest.mark.asyncio
    async def test_fetch_ticker_uppercase_normalization(self) -> None:
        """Test ticker is normalized to uppercase."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_history_df()

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_historical_data("aapl", period="1M")

        assert isinstance(result, HistoricalData)
        assert result.ticker == "AAPL"
        mock_yf.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_fetch_ticker_with_whitespace(self) -> None:
        """Test ticker whitespace is stripped."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_history_df()

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_historical_data("  TSLA  ", period="1M")

        assert isinstance(result, HistoricalData)
        assert result.ticker == "TSLA"
        mock_yf.assert_called_once_with("TSLA")

    @pytest.mark.asyncio
    async def test_fetch_invalid_period(self) -> None:
        """Test invalid period returns error."""
        result = await fetch_historical_data("AAPL", period="INVALID")

        assert isinstance(result, HistoricalDataError)
        assert result.ticker == "AAPL"
        assert "Invalid period" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_empty_data(self) -> None:
        """Test empty data returns error (e.g., new IPO, delisted stock)."""
        mock_ticker = MagicMock()
        # Empty DataFrame
        mock_ticker.history.return_value = pd.DataFrame()

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
            result = await fetch_historical_data("NEWIPO", period="1Y")

        assert isinstance(result, HistoricalDataError)
        assert result.ticker == "NEWIPO"
        assert "No historical data available" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_none_data(self) -> None:
        """Test None data returns error."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = None

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
            result = await fetch_historical_data("TEST", period="1M")

        assert isinstance(result, HistoricalDataError)
        assert "No historical data available" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_invalid_ticker(self) -> None:
        """Test invalid ticker returns error."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("404 Not Found")

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
            result = await fetch_historical_data("INVALID123", period="1M")

        assert isinstance(result, HistoricalDataError)
        assert result.ticker == "INVALID123"
        assert "Invalid ticker symbol" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_network_error(self) -> None:
        """Test network error handling."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("Connection timeout")

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
            result = await fetch_historical_data("AAPL", period="1M")

        assert isinstance(result, HistoricalDataError)
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_timeout(self) -> None:
        """Test timeout handling."""
        mock_ticker = MagicMock()
        # Simulate a slow response by sleeping longer than timeout
        import asyncio

        async def slow_fetch() -> None:
            await asyncio.sleep(10)

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
            with patch(
                "asyncio.get_event_loop"
            ) as mock_loop:
                mock_loop.return_value.run_in_executor.return_value = slow_fetch()
                result = await fetch_historical_data("AAPL", period="1M", timeout=0.1)

        assert isinstance(result, HistoricalDataError)
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_generic_error(self) -> None:
        """Test generic error handling."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("Something went wrong")

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
            result = await fetch_historical_data("AAPL", period="1M")

        assert isinstance(result, HistoricalDataError)
        assert "Failed to fetch historical data" in result.error_message

    @pytest.mark.asyncio
    async def test_volumes_converted_to_int(self) -> None:
        """Test that volumes are properly converted to integers."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_history_df(num_points=5)

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker):
            result = await fetch_historical_data("AAPL", period="1M")

        assert isinstance(result, HistoricalData)
        # Check that all volumes are integers
        for volume in result.volumes:
            assert isinstance(volume, int)
