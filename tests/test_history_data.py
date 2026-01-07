"""Tests for historical price data service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import respx
from httpx import Response

from viper.services.history_data import (
    HistoricalData,
    HistoricalDataError,
    HistoricalStats,
    _is_crypto_ticker,
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


def create_mock_coingecko_response(num_points: int = 10, start_price: float = 50000.0) -> dict[str, list[list[float]]]:
    """Create a mock CoinGecko market_chart API response."""
    import time
    base_timestamp = 1704067200000  # 2024-01-01 in milliseconds

    prices = []
    volumes = []
    for i in range(num_points):
        timestamp = base_timestamp + (i * 86400000)  # +1 day in ms
        price = start_price + (i * 100)
        volume = 10000000000 + (i * 100000000)
        prices.append([timestamp, price])
        volumes.append([timestamp, volume])

    return {
        "prices": prices,
        "market_caps": [[p[0], p[1] * 1000000] for p in prices],  # Not used but in real response
        "total_volumes": volumes,
    }


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


class TestCryptoDetection:
    """Tests for crypto ticker auto-detection."""

    def test_is_crypto_ticker_btc(self) -> None:
        """Test BTC is detected as crypto."""
        assert _is_crypto_ticker("BTC") is True

    def test_is_crypto_ticker_eth(self) -> None:
        """Test ETH is detected as crypto."""
        assert _is_crypto_ticker("ETH") is True

    def test_is_crypto_ticker_lowercase(self) -> None:
        """Test lowercase crypto symbols are detected."""
        assert _is_crypto_ticker("btc") is True
        assert _is_crypto_ticker("eth") is True

    def test_is_crypto_ticker_stock(self) -> None:
        """Test stock tickers are not detected as crypto."""
        assert _is_crypto_ticker("AAPL") is False
        assert _is_crypto_ticker("TSLA") is False
        assert _is_crypto_ticker("MSFT") is False

    def test_is_crypto_ticker_invalid(self) -> None:
        """Test invalid symbols are not detected as crypto."""
        assert _is_crypto_ticker("INVALID123") is False
        assert _is_crypto_ticker("XYZ") is False


class TestFetchCryptoHistoricalData:
    """Tests for fetching crypto historical data via CoinGecko."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_btc_1m(self) -> None:
        """Test fetching BTC historical data for 1M period."""
        mock_data = create_mock_coingecko_response(num_points=30, start_price=50000.0)
        
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart").mock(
            return_value=Response(200, json=mock_data)
        )

        result = await fetch_historical_data("BTC", period="1M")

        assert isinstance(result, HistoricalData)
        assert result.ticker == "BTC"
        assert result.period == "1M"
        assert len(result.prices) == 30
        assert len(result.dates) == 30
        assert len(result.volumes) == 30
        # For crypto, OHLC all use price data
        assert len(result.highs) == 30
        assert len(result.lows) == 30
        assert len(result.opens) == 30
        assert result.prices == result.highs == result.lows == result.opens

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_all_periods(self) -> None:
        """Test all supported periods work for crypto."""
        periods_to_test = ["1W", "1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"]
        expected_days = ["7", "30", "90", "180", "365", "730", "1825", "max"]

        for user_period, expected_day in zip(periods_to_test, expected_days):
            mock_data = create_mock_coingecko_response(num_points=10)
            
            route = respx.get(
                "https://api.coingecko.com/api/v3/coins/ethereum/market_chart",
                params={"vs_currency": "usd", "days": expected_day}
            ).mock(return_value=Response(200, json=mock_data))

            result = await fetch_historical_data("ETH", period=user_period)

            assert isinstance(result, HistoricalData)
            assert result.period == user_period
            assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_rate_limit_retry(self) -> None:
        """Test rate limit handling with retry and exponential backoff."""
        mock_data = create_mock_coingecko_response(num_points=10)
        
        # First two attempts return 429, third succeeds
        route = respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart")
        route.side_effect = [
            Response(429),
            Response(429),
            Response(200, json=mock_data),
        ]

        result = await fetch_historical_data("BTC", period="1M", max_retries=3)

        assert isinstance(result, HistoricalData)
        assert result.ticker == "BTC"
        assert route.call_count == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_rate_limit_exhausted(self) -> None:
        """Test rate limit error after exhausting retries."""
        route = respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart")
        route.mock(return_value=Response(429))

        result = await fetch_historical_data("BTC", period="1M", max_retries=2)

        assert isinstance(result, HistoricalDataError)
        assert result.ticker == "BTC"
        assert "Rate limit exceeded after 2 retries" in result.error_message
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_404_error(self) -> None:
        """Test handling of 404 error (invalid coin ID)."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart").mock(
            return_value=Response(404)
        )

        result = await fetch_historical_data("BTC", period="1M")

        assert isinstance(result, HistoricalDataError)
        assert "HTTP 404" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_empty_data(self) -> None:
        """Test handling of empty price data."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart").mock(
            return_value=Response(200, json={"prices": [], "total_volumes": []})
        )

        result = await fetch_historical_data("BTC", period="1M")

        assert isinstance(result, HistoricalDataError)
        assert "No price data in response" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_malformed_response(self) -> None:
        """Test handling of malformed API response."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart").mock(
            return_value=Response(200, json={"invalid": "data"})
        )

        result = await fetch_historical_data("BTC", period="1M")

        assert isinstance(result, HistoricalDataError)
        assert "No price data in response" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_network_error(self) -> None:
        """Test handling of network errors."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart").mock(
            side_effect=Exception("Network error")
        )

        result = await fetch_historical_data("BTC", period="1M")

        assert isinstance(result, HistoricalDataError)
        assert "Failed to fetch chart" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_volumes_padded(self) -> None:
        """Test that volumes are padded if fewer than prices."""
        mock_data = {
            "prices": [[1704067200000, 50000.0], [1704153600000, 51000.0], [1704240000000, 52000.0]],
            "total_volumes": [[1704067200000, 10000000000]],  # Only one volume
        }
        
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart").mock(
            return_value=Response(200, json=mock_data)
        )

        result = await fetch_historical_data("BTC", period="1W")

        assert isinstance(result, HistoricalData)
        assert len(result.volumes) == 3
        assert result.volumes[0] == 10000000000
        assert result.volumes[1] == 0
        assert result.volumes[2] == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_timestamp_conversion(self) -> None:
        """Test that millisecond timestamps are correctly converted to datetime."""
        mock_data = {
            "prices": [[1704067200000, 50000.0]],  # 2024-01-01 00:00:00 UTC
            "total_volumes": [[1704067200000, 10000000000]],
        }

        respx.get("https://api.coingecko.com/api/v3/coins/ethereum/market_chart").mock(
            return_value=Response(200, json=mock_data)
        )

        result = await fetch_historical_data("ETH", period="1W")

        assert isinstance(result, HistoricalData)
        assert len(result.dates) == 1
        # Check the datetime is reasonable (timestamp 1704067200000 = 2024-01-01 00:00:00 UTC)
        # Depending on timezone, this could be 2023-12-31 or 2024-01-01 local time
        assert result.dates[0].year in (2023, 2024)
        assert result.dates[0].month in (1, 12)

    @pytest.mark.asyncio
    async def test_fetch_crypto_unknown_symbol(self) -> None:
        """Test fetching unknown crypto symbol returns error."""
        result = await fetch_historical_data("UNKNOWNCRYPTO", period="1M")

        # Should be treated as stock (not in SYMBOL_TO_ID) and fail via yfinance
        assert isinstance(result, HistoricalDataError)

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_case_insensitive(self) -> None:
        """Test crypto symbol is case-insensitive."""
        mock_data = create_mock_coingecko_response(num_points=10)
        
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart").mock(
            return_value=Response(200, json=mock_data)
        )

        result = await fetch_historical_data("btc", period="1M")

        assert isinstance(result, HistoricalData)
        assert result.ticker == "BTC"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_crypto_whitespace_stripped(self) -> None:
        """Test crypto symbol whitespace is stripped."""
        mock_data = create_mock_coingecko_response(num_points=10)
        
        respx.get("https://api.coingecko.com/api/v3/coins/ethereum/market_chart").mock(
            return_value=Response(200, json=mock_data)
        )

        result = await fetch_historical_data("  ETH  ", period="1M")

        assert isinstance(result, HistoricalData)
        assert result.ticker == "ETH"


class TestAutoRouting:
    """Tests for automatic routing between stock and crypto data sources."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_auto_route_crypto(self) -> None:
        """Test that crypto tickers are automatically routed to CoinGecko."""
        mock_data = create_mock_coingecko_response(num_points=10)
        
        route = respx.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart")
        route.mock(return_value=Response(200, json=mock_data))

        result = await fetch_historical_data("BTC", period="1M")

        assert isinstance(result, HistoricalData)
        assert route.called

    @pytest.mark.asyncio
    async def test_auto_route_stock(self) -> None:
        """Test that stock tickers are automatically routed to yfinance."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_history_df(num_points=30)

        with patch("viper.services.history_data.yf.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_historical_data("AAPL", period="1M")

        assert isinstance(result, HistoricalData)
        assert mock_yf.called
        mock_ticker.history.assert_called_once()
