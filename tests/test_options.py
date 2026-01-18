"""Tests for options data fetching service."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from viper.services.options import OptionsError, fetch_option_expirations


class MockFastInfoInvalid:
    """Mock fast_info that raises AttributeError on last_price access."""

    @property
    def last_price(self) -> float:
        """Raise AttributeError to simulate invalid ticker."""
        raise AttributeError("No data")


class TestOptionsError:
    """Tests for OptionsError dataclass."""

    def test_options_error_creation(self) -> None:
        """Test OptionsError dataclass instantiation."""
        error = OptionsError(ticker="INVALID", error_message="Invalid ticker symbol")
        assert error.ticker == "INVALID"
        assert error.error_message == "Invalid ticker symbol"


class TestFetchOptionExpirations:
    """Tests for fetch_option_expirations async function."""

    @pytest.mark.asyncio
    async def test_fetch_valid_ticker_with_options(self) -> None:
        """Test fetching a valid ticker with options returns list of dates."""
        # Mock yfinance Ticker with options
        mock_ticker = MagicMock()
        mock_ticker.options = ("2024-01-19", "2024-02-16", "2024-03-15")

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_expirations("AAPL")

        assert isinstance(result, list)
        assert len(result) == 3
        assert result == ["2024-01-19", "2024-02-16", "2024-03-15"]

    @pytest.mark.asyncio
    async def test_fetch_ticker_uppercase_normalization(self) -> None:
        """Test ticker is normalized to uppercase."""
        mock_ticker = MagicMock()
        mock_ticker.options = ("2024-01-19",)

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_option_expirations("aapl")

        assert isinstance(result, list)
        # Verify yfinance was called with uppercase ticker
        mock_yf.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_fetch_ticker_with_whitespace(self) -> None:
        """Test ticker whitespace is stripped."""
        mock_ticker = MagicMock()
        mock_ticker.options = ("2024-01-19",)

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_option_expirations("  tsla  ")

        assert isinstance(result, list)
        mock_yf.assert_called_once_with("TSLA")

    @pytest.mark.asyncio
    async def test_fetch_valid_ticker_without_options(self) -> None:
        """Test valid ticker that has no options returns OptionsError."""
        # Mock ticker with no options but valid fast_info
        mock_ticker = MagicMock()
        mock_ticker.options = ()  # Empty tuple means no options
        mock_fast_info = MagicMock()
        mock_fast_info.last_price = 100.0
        mock_ticker.fast_info = mock_fast_info

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_expirations("SPY")

        assert isinstance(result, OptionsError)
        assert result.ticker == "SPY"
        assert "no options available" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_invalid_ticker(self) -> None:
        """Test fetching an invalid ticker returns OptionsError."""
        # Mock ticker with no options and no fast_info data
        mock_ticker = MagicMock()
        mock_ticker.options = ()
        # Simulate invalid ticker by using custom class that raises AttributeError
        mock_ticker.fast_info = MockFastInfoInvalid()

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_expirations("INVALID")

        assert isinstance(result, OptionsError)
        assert result.ticker == "INVALID"
        assert "invalid ticker" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_none_options(self) -> None:
        """Test handling when options property returns None."""
        mock_ticker = MagicMock()
        mock_ticker.options = None
        # Simulate invalid ticker by using custom class that raises AttributeError
        mock_ticker.fast_info = MockFastInfoInvalid()

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_expirations("TEST")

        assert isinstance(result, OptionsError)
        assert "invalid ticker" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_network_error(self) -> None:
        """Test handling network errors."""
        with patch(
            "viper.services.options.yf.Ticker",
            side_effect=Exception("Connection error: Failed to connect"),
        ):
            result = await fetch_option_expirations("AAPL")

        assert isinstance(result, OptionsError)
        assert result.ticker == "AAPL"
        assert "network error" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_404_error(self) -> None:
        """Test handling 404 errors (invalid ticker from API)."""
        with patch(
            "viper.services.options.yf.Ticker",
            side_effect=Exception("404 Client Error: Not Found"),
        ):
            result = await fetch_option_expirations("NOTREAL")

        assert isinstance(result, OptionsError)
        assert result.ticker == "NOTREAL"
        assert "invalid ticker" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_timeout(self) -> None:
        """Test handling request timeout."""

        def slow_ticker(*args: object, **kwargs: object) -> Mock:
            import time

            time.sleep(2)
            return Mock()

        with patch("viper.services.options.yf.Ticker", side_effect=slow_ticker):
            result = await fetch_option_expirations("AAPL", timeout=0.1)

        assert isinstance(result, OptionsError)
        assert result.ticker == "AAPL"
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_with_custom_timeout(self) -> None:
        """Test fetch with custom timeout value."""
        mock_ticker = MagicMock()
        mock_ticker.options = ("2024-01-19",)

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_expirations("AAPL", timeout=5.0)

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_fetch_many_expirations(self) -> None:
        """Test fetching ticker with many expiration dates."""
        # Simulate a ticker with many expiration dates (like SPY)
        expirations = tuple(f"2024-{month:02d}-15" for month in range(1, 13))
        mock_ticker = MagicMock()
        mock_ticker.options = expirations

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_expirations("SPY")

        assert isinstance(result, list)
        assert len(result) == 12
        assert result[0] == "2024-01-15"
        assert result[-1] == "2024-12-15"

    @pytest.mark.asyncio
    async def test_fetch_generic_exception(self) -> None:
        """Test handling generic exceptions."""
        with patch(
            "viper.services.options.yf.Ticker",
            side_effect=Exception("Unexpected error occurred"),
        ):
            result = await fetch_option_expirations("AAPL")

        assert isinstance(result, OptionsError)
        assert result.ticker == "AAPL"
        assert "failed to fetch options" in result.error_message.lower()
