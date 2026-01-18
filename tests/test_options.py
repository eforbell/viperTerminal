"""Tests for options data fetching service."""

from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from viper.services.options import (
    OptionContract,
    OptionsChain,
    OptionsError,
    fetch_option_chain,
    fetch_option_expirations,
)


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


class TestOptionContract:
    """Tests for OptionContract dataclass."""

    def test_option_contract_creation(self) -> None:
        """Test OptionContract dataclass instantiation."""
        contract = OptionContract(
            strike=150.0,
            bid=2.50,
            ask=2.55,
            last_price=2.52,
            volume=1000,
            open_interest=5000,
            implied_volatility=0.25,
            in_the_money=True,
        )
        assert contract.strike == 150.0
        assert contract.bid == 2.50
        assert contract.ask == 2.55
        assert contract.last_price == 2.52
        assert contract.volume == 1000
        assert contract.open_interest == 5000
        assert contract.implied_volatility == 0.25
        assert contract.in_the_money is True


class TestOptionsChain:
    """Tests for OptionsChain dataclass."""

    def test_options_chain_creation(self) -> None:
        """Test OptionsChain dataclass instantiation."""
        call = OptionContract(
            strike=150.0,
            bid=2.50,
            ask=2.55,
            last_price=2.52,
            volume=1000,
            open_interest=5000,
            implied_volatility=0.25,
            in_the_money=True,
        )
        put = OptionContract(
            strike=150.0,
            bid=1.50,
            ask=1.55,
            last_price=1.52,
            volume=500,
            open_interest=2500,
            implied_volatility=0.20,
            in_the_money=False,
        )
        chain = OptionsChain(
            ticker="AAPL", expiration="2024-01-19", calls=[call], puts=[put]
        )
        assert chain.ticker == "AAPL"
        assert chain.expiration == "2024-01-19"
        assert len(chain.calls) == 1
        assert len(chain.puts) == 1
        assert chain.calls[0].strike == 150.0
        assert chain.puts[0].strike == 150.0


class TestFetchOptionChain:
    """Tests for fetch_option_chain async function."""

    def _create_mock_option_chain(self) -> MagicMock:
        """Helper to create mock option chain data."""
        # Create mock DataFrames for calls and puts
        calls_data = {
            "strike": [145.0, 150.0, 155.0],
            "bid": [5.10, 2.50, 0.80],
            "ask": [5.20, 2.55, 0.85],
            "lastPrice": [5.15, 2.52, 0.82],
            "volume": [1000, 1500, 800],
            "openInterest": [5000, 7500, 4000],
            "impliedVolatility": [0.25, 0.26, 0.28],
            "inTheMoney": [True, True, False],
        }
        puts_data = {
            "strike": [145.0, 150.0, 155.0],
            "bid": [0.50, 1.50, 3.50],
            "ask": [0.55, 1.55, 3.60],
            "lastPrice": [0.52, 1.52, 3.55],
            "volume": [500, 1000, 2000],
            "openInterest": [2500, 5000, 10000],
            "impliedVolatility": [0.18, 0.20, 0.22],
            "inTheMoney": [False, False, True],
        }

        calls_df = pd.DataFrame(calls_data)
        puts_df = pd.DataFrame(puts_data)

        mock_chain = MagicMock()
        mock_chain.calls = calls_df
        mock_chain.puts = puts_df

        return mock_chain

    @pytest.mark.asyncio
    async def test_fetch_valid_option_chain(self) -> None:
        """Test fetching a valid option chain returns OptionsChain."""
        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = self._create_mock_option_chain()

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_chain("AAPL", "2024-01-19")

        assert isinstance(result, OptionsChain)
        assert result.ticker == "AAPL"
        assert result.expiration == "2024-01-19"
        assert len(result.calls) == 3
        assert len(result.puts) == 3

        # Verify call data
        assert result.calls[0].strike == 145.0
        assert result.calls[0].bid == 5.10
        assert result.calls[0].in_the_money is True

        # Verify put data
        assert result.puts[2].strike == 155.0
        assert result.puts[2].bid == 3.50
        assert result.puts[2].in_the_money is True

    @pytest.mark.asyncio
    async def test_fetch_ticker_uppercase_normalization_chain(self) -> None:
        """Test ticker is normalized to uppercase in chain fetch."""
        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = self._create_mock_option_chain()

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_option_chain("aapl", "2024-01-19")

        assert isinstance(result, OptionsChain)
        assert result.ticker == "AAPL"
        mock_yf.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_fetch_empty_chain(self) -> None:
        """Test handling empty option chain (no contracts)."""
        # Create empty DataFrames
        empty_df = pd.DataFrame()
        mock_chain = MagicMock()
        mock_chain.calls = empty_df
        mock_chain.puts = empty_df

        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = mock_chain

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_chain("AAPL", "2024-01-19")

        assert isinstance(result, OptionsChain)
        assert len(result.calls) == 0
        assert len(result.puts) == 0

    @pytest.mark.asyncio
    async def test_fetch_chain_with_nan_values(self) -> None:
        """Test handling NaN values in option chain data."""
        # Create DataFrame with NaN values
        import numpy as np

        calls_data = {
            "strike": [150.0],
            "bid": [np.nan],
            "ask": [2.55],
            "lastPrice": [np.nan],
            "volume": [np.nan],
            "openInterest": [5000],
            "impliedVolatility": [np.nan],
            "inTheMoney": [True],
        }
        puts_data = {
            "strike": [150.0],
            "bid": [1.50],
            "ask": [np.nan],
            "lastPrice": [1.52],
            "volume": [500],
            "openInterest": [np.nan],
            "impliedVolatility": [0.20],
            "inTheMoney": [False],
        }

        calls_df = pd.DataFrame(calls_data)
        puts_df = pd.DataFrame(puts_data)

        mock_chain = MagicMock()
        mock_chain.calls = calls_df
        mock_chain.puts = puts_df

        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = mock_chain

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_chain("AAPL", "2024-01-19")

        assert isinstance(result, OptionsChain)
        # NaN values should be converted to 0
        assert result.calls[0].bid == 0.0
        assert result.calls[0].last_price == 0.0
        assert result.calls[0].volume == 0
        assert result.calls[0].implied_volatility == 0.0

        assert result.puts[0].ask == 0.0
        assert result.puts[0].open_interest == 0

    @pytest.mark.asyncio
    async def test_fetch_chain_invalid_expiration(self) -> None:
        """Test handling invalid expiration date."""
        with patch(
            "viper.services.options.yf.Ticker",
            side_effect=Exception("'2099-01-01' not in list"),
        ):
            result = await fetch_option_chain("AAPL", "2099-01-01")

        assert isinstance(result, OptionsError)
        assert result.ticker == "AAPL"
        assert "invalid expiration" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_chain_invalid_ticker(self) -> None:
        """Test handling invalid ticker in chain fetch."""
        with patch(
            "viper.services.options.yf.Ticker",
            side_effect=Exception("404 Client Error: Not Found"),
        ):
            result = await fetch_option_chain("NOTREAL", "2024-01-19")

        assert isinstance(result, OptionsError)
        assert result.ticker == "NOTREAL"
        assert "invalid ticker" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_chain_network_error(self) -> None:
        """Test handling network errors in chain fetch."""
        with patch(
            "viper.services.options.yf.Ticker",
            side_effect=Exception("Connection error: Failed to connect"),
        ):
            result = await fetch_option_chain("AAPL", "2024-01-19")

        assert isinstance(result, OptionsError)
        assert result.ticker == "AAPL"
        assert "network error" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_chain_timeout(self) -> None:
        """Test handling request timeout in chain fetch."""

        def slow_ticker(*args: object, **kwargs: object) -> Mock:
            import time

            time.sleep(2)
            return Mock()

        with patch("viper.services.options.yf.Ticker", side_effect=slow_ticker):
            result = await fetch_option_chain("AAPL", "2024-01-19", timeout=0.1)

        assert isinstance(result, OptionsError)
        assert result.ticker == "AAPL"
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_chain_generic_exception(self) -> None:
        """Test handling generic exceptions in chain fetch."""
        with patch(
            "viper.services.options.yf.Ticker",
            side_effect=Exception("Unexpected error occurred"),
        ):
            result = await fetch_option_chain("AAPL", "2024-01-19")

        assert isinstance(result, OptionsError)
        assert result.ticker == "AAPL"
        assert "failed to fetch option chain" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_chain_with_missing_columns(self) -> None:
        """Test handling DataFrames with missing columns."""
        # Create DataFrame with only some columns
        calls_data = {
            "strike": [150.0],
            "bid": [2.50],
            # Missing: ask, lastPrice, volume, openInterest, impliedVolatility, inTheMoney
        }

        calls_df = pd.DataFrame(calls_data)
        puts_df = pd.DataFrame(calls_data)

        mock_chain = MagicMock()
        mock_chain.calls = calls_df
        mock_chain.puts = puts_df

        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = mock_chain

        with patch("viper.services.options.yf.Ticker", return_value=mock_ticker):
            result = await fetch_option_chain("AAPL", "2024-01-19")

        assert isinstance(result, OptionsChain)
        # Missing columns should default to 0 or False
        assert result.calls[0].strike == 150.0
        assert result.calls[0].bid == 2.50
        assert result.calls[0].ask == 0.0
        assert result.calls[0].last_price == 0.0
        assert result.calls[0].volume == 0
        assert result.calls[0].open_interest == 0
        assert result.calls[0].implied_volatility == 0.0
        assert result.calls[0].in_the_money is False
