"""Tests for crypto quote fetching service using yfinance."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from viper.services.crypto import (
    SYMBOL_TO_PAIR,
    CryptoError,
    CryptoInfo,
    CryptoInfoError,
    CryptoQuote,
    fetch_crypto_info,
    fetch_crypto_quote,
)


class TestCryptoQuote:
    """Tests for CryptoQuote dataclass."""

    def test_crypto_quote_creation(self) -> None:
        """Test CryptoQuote dataclass instantiation."""
        quote = CryptoQuote(
            symbol="BTC",
            price_usd=45000.50,
            change_24h_percent=2.5,
            market_cap_usd=900000000000,
            volume_24h_usd=25000000000.0,
            name="Bitcoin",
        )
        assert quote.symbol == "BTC"
        assert quote.price_usd == 45000.50
        assert quote.change_24h_percent == 2.5
        assert quote.market_cap_usd == 900000000000
        assert quote.volume_24h_usd == 25000000000.0
        assert quote.name == "Bitcoin"

    def test_crypto_quote_optional_name(self) -> None:
        """Test CryptoQuote with optional name field."""
        quote = CryptoQuote(
            symbol="BTC",
            price_usd=45000.0,
            change_24h_percent=0.0,
            market_cap_usd=900000000000,
            volume_24h_usd=25000000000.0,
        )
        assert quote.name is None


class TestCryptoError:
    """Tests for CryptoError dataclass."""

    def test_crypto_error_creation(self) -> None:
        """Test CryptoError dataclass instantiation."""
        error = CryptoError(symbol="INVALID", error_message="Unknown crypto symbol: INVALID")
        assert error.symbol == "INVALID"
        assert error.error_message == "Unknown crypto symbol: INVALID"


class TestSymbolMapping:
    """Tests for symbol to pair mapping."""

    def test_symbol_to_pair_mapping_exists(self) -> None:
        """Test that common crypto symbols have pair mappings."""
        assert SYMBOL_TO_PAIR["BTC"] == "BTC-USD"
        assert SYMBOL_TO_PAIR["ETH"] == "ETH-USD"
        assert SYMBOL_TO_PAIR["DOGE"] == "DOGE-USD"
        assert SYMBOL_TO_PAIR["SOL"] == "SOL-USD"

    def test_symbol_to_pair_has_reasonable_coverage(self) -> None:
        """Test that we have a decent number of symbols mapped."""
        assert len(SYMBOL_TO_PAIR) >= 20  # Should cover top cryptos


class TestFetchCryptoQuote:
    """Tests for fetch_crypto_quote async function."""

    @pytest.mark.asyncio
    async def test_fetch_valid_symbol(self) -> None:
        """Test fetching a valid crypto symbol returns CryptoQuote."""
        # Mock yfinance Ticker
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 45000.50}
        mock_ticker.info = {
            "marketCap": 900000000000,
            "regularMarketVolume": 25000000000.0,
            "longName": "Bitcoin USD",
        }

        # Mock historical data for 24h change calculation
        hist_data = pd.DataFrame(
            {"Close": [44000.0, 45000.50]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.symbol == "BTC"
        assert result.price_usd == 45000.50
        # Expected: (45000.50 - 44000.0) / 44000.0 * 100 = 2.2738...
        assert abs(result.change_24h_percent - 2.2738636363636367) < 0.001
        assert result.market_cap_usd == 900000000000
        assert result.volume_24h_usd == 25000000000.0
        assert result.name == "Bitcoin USD"

    @pytest.mark.asyncio
    async def test_fetch_symbol_uppercase_normalization(self) -> None:
        """Test symbol is normalized to uppercase."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 3000.0}
        mock_ticker.info = {
            "marketCap": 360000000000,
            "regularMarketVolume": 15000000000.0,
            "longName": "Ethereum USD",
        }

        hist_data = pd.DataFrame(
            {"Close": [2950.0, 3000.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("eth")

        assert isinstance(result, CryptoQuote)
        assert result.symbol == "ETH"

    @pytest.mark.asyncio
    async def test_fetch_symbol_with_whitespace(self) -> None:
        """Test symbol whitespace is stripped."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 100.0}
        mock_ticker.info = {
            "marketCap": 50000000000,
            "regularMarketVolume": 2000000000.0,
            "longName": "Solana USD",
        }

        hist_data = pd.DataFrame(
            {"Close": [100.0, 100.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("  sol  ")

        assert isinstance(result, CryptoQuote)
        assert result.symbol == "SOL"

    @pytest.mark.asyncio
    async def test_fetch_unknown_symbol(self) -> None:
        """Test fetching an unknown symbol returns CryptoError."""
        result = await fetch_crypto_quote("NOTACRYPTO")

        assert isinstance(result, CryptoError)
        assert result.symbol == "NOTACRYPTO"
        assert "Unknown crypto symbol" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_with_usd_suffix(self) -> None:
        """Test fetching with explicit -USD suffix."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 45000.0}
        mock_ticker.info = {
            "marketCap": 900000000000,
            "regularMarketVolume": 25000000000.0,
            "longName": "Bitcoin USD",
        }

        hist_data = pd.DataFrame(
            {"Close": [44000.0, 45000.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_crypto_quote("BTC-USD")

        assert isinstance(result, CryptoQuote)
        assert result.symbol == "BTC"
        # Verify yfinance was called with the full pair
        mock_yf.assert_called_once_with("BTC-USD")

    @pytest.mark.asyncio
    async def test_fetch_missing_price_data(self) -> None:
        """Test handling response with missing price data."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {}  # No last_price
        mock_ticker.info = {}  # No fallback prices

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert "Missing price data" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_with_missing_optional_fields(self) -> None:
        """Test handling when optional fields are missing."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 45000.0}
        mock_ticker.info = {}  # Missing market cap, volume, name

        hist_data = pd.DataFrame(
            {"Close": [44000.0, 45000.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.price_usd == 45000.0
        assert result.market_cap_usd == 0  # Default
        assert result.volume_24h_usd == 0.0  # Default
        assert result.name is None  # Default

    @pytest.mark.asyncio
    async def test_fetch_with_no_historical_data(self) -> None:
        """Test handling when historical data is unavailable."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 45000.0}
        mock_ticker.info = {
            "marketCap": 900000000000,
            "regularMarketVolume": 25000000000.0,
            "longName": "Bitcoin USD",
        }

        # Empty historical data
        hist_data = pd.DataFrame()
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.change_24h_percent == 0.0  # Default when no history

    @pytest.mark.asyncio
    async def test_fetch_with_single_historical_point(self) -> None:
        """Test handling when only one historical data point exists."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 45000.0}
        mock_ticker.info = {
            "marketCap": 900000000000,
            "regularMarketVolume": 25000000000.0,
            "longName": "Bitcoin USD",
        }

        # Only one data point
        hist_data = pd.DataFrame({"Close": [45000.0]}, index=pd.date_range("2024-01-01", periods=1))
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.change_24h_percent == 0.0  # Default when insufficient history

    @pytest.mark.asyncio
    async def test_fetch_positive_change(self) -> None:
        """Test with positive 24h change."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 46000.0}
        mock_ticker.info = {
            "marketCap": 900000000000,
            "regularMarketVolume": 25000000000.0,
            "longName": "Bitcoin USD",
        }

        hist_data = pd.DataFrame(
            {"Close": [44000.0, 46000.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        # Expected: (46000 - 44000) / 44000 * 100 = 4.545...
        assert result.change_24h_percent > 0

    @pytest.mark.asyncio
    async def test_fetch_negative_change(self) -> None:
        """Test with negative 24h change."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 43000.0}
        mock_ticker.info = {
            "marketCap": 900000000000,
            "regularMarketVolume": 25000000000.0,
            "longName": "Bitcoin USD",
        }

        hist_data = pd.DataFrame(
            {"Close": [44000.0, 43000.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        # Expected: (43000 - 44000) / 44000 * 100 = -2.27...
        assert result.change_24h_percent < 0

    @pytest.mark.asyncio
    async def test_fetch_zero_previous_close(self) -> None:
        """Test handling when previous close is zero (edge case)."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 45000.0}
        mock_ticker.info = {
            "marketCap": 900000000000,
            "regularMarketVolume": 25000000000.0,
            "longName": "Bitcoin USD",
        }

        hist_data = pd.DataFrame(
            {"Close": [0.0, 45000.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.change_24h_percent == 0.0  # Should handle division by zero

    @pytest.mark.asyncio
    async def test_fetch_fallback_to_info_price(self) -> None:
        """Test fallback to .info price when fast_info doesn't have last_price."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {}  # No last_price
        mock_ticker.info = {"regularMarketPrice": 45000.0}

        hist_data = pd.DataFrame(
            {"Close": [44000.0, 45000.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.price_usd == 45000.0

    @pytest.mark.asyncio
    async def test_fetch_exception_handling(self) -> None:
        """Test handling exceptions during yfinance call."""

        def raise_exception(pair: str) -> None:
            raise RuntimeError("Network error")

        with patch("yfinance.Ticker", side_effect=raise_exception):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "Failed to fetch quote" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_all_major_cryptos(self) -> None:
        """Test fetching quotes for all major crypto pairs."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"last_price": 100.0}
        mock_ticker.info = {
            "marketCap": 100000000,
            "regularMarketVolume": 1000000.0,
            "longName": "Test Crypto",
        }

        hist_data = pd.DataFrame(
            {"Close": [100.0, 100.0]}, index=pd.date_range("2024-01-01", periods=2)
        )
        mock_ticker.history.return_value = hist_data

        # Test a few major cryptos
        symbols = ["BTC", "ETH", "SOL", "ADA", "DOGE"]

        with patch("yfinance.Ticker", return_value=mock_ticker):
            for symbol in symbols:
                result = await fetch_crypto_quote(symbol)
                assert isinstance(result, CryptoQuote)
                assert result.symbol == symbol


class TestFetchCryptoInfo:
    """Tests for fetch_crypto_info async function."""

    @pytest.mark.asyncio
    async def test_fetch_valid_info(self) -> None:
        """Test fetching valid crypto info."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Bitcoin USD",
            "description": "Bitcoin is a cryptocurrency",
            "website": "https://bitcoin.org",
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_info("BTC")

        assert isinstance(result, CryptoInfo)
        assert result.symbol == "BTC"
        assert isinstance(result.info, dict)
        assert result.info["longName"] == "Bitcoin USD"

    @pytest.mark.asyncio
    async def test_fetch_info_unknown_symbol(self) -> None:
        """Test fetching info for unknown symbol."""
        result = await fetch_crypto_info("NOTACRYPTO")

        assert isinstance(result, CryptoInfoError)
        assert result.symbol == "NOTACRYPTO"
        assert "Unknown crypto symbol" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_info_with_usd_suffix(self) -> None:
        """Test fetching info with explicit -USD suffix."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"longName": "Bitcoin USD"}

        with patch("yfinance.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_crypto_info("BTC-USD")

        assert isinstance(result, CryptoInfo)
        assert result.symbol == "BTC"
        mock_yf.assert_called_once_with("BTC-USD")

    @pytest.mark.asyncio
    async def test_fetch_info_empty_response(self) -> None:
        """Test handling empty info response."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await fetch_crypto_info("BTC")

        # Empty dict should return error
        assert isinstance(result, CryptoInfoError)
        assert "Invalid response format" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_info_exception_handling(self) -> None:
        """Test handling exceptions during info fetch."""

        def raise_exception(pair: str) -> None:
            raise RuntimeError("Network error")

        with patch("yfinance.Ticker", side_effect=raise_exception):
            result = await fetch_crypto_info("BTC")

        assert isinstance(result, CryptoInfoError)
        assert result.symbol == "BTC"
        assert "Failed to fetch info" in result.error_message
