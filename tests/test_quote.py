"""Tests for unified quote service."""

from unittest.mock import AsyncMock, patch

import pytest

from viper.services.crypto import CryptoError, CryptoQuote
from viper.services.quote import (
    AssetType,
    _auto_detect_and_fetch,
    _parse_symbol_input,
    fetch_quote,
    is_crypto_quote,
    is_stock_quote,
)
from viper.services.stock import StockError, StockQuote


class TestParseSymbolInput:
    """Tests for symbol input parsing."""

    def test_parse_explicit_crypto_prefix(self) -> None:
        """Should parse :CRYPTO prefix."""
        symbol, asset_type = _parse_symbol_input("BTC:CRYPTO")
        assert symbol == "BTC"
        assert asset_type == AssetType.CRYPTO

    def test_parse_explicit_stock_prefix(self) -> None:
        """Should parse :STOCK prefix."""
        symbol, asset_type = _parse_symbol_input("AAPL:STOCK")
        assert symbol == "AAPL"
        assert asset_type == AssetType.STOCK

    def test_parse_no_prefix(self) -> None:
        """Should return None asset type when no prefix."""
        symbol, asset_type = _parse_symbol_input("TSLA")
        assert symbol == "TSLA"
        assert asset_type is None

    def test_parse_normalizes_case(self) -> None:
        """Should normalize to uppercase."""
        symbol, asset_type = _parse_symbol_input("btc:crypto")
        assert symbol == "BTC"
        assert asset_type == AssetType.CRYPTO

    def test_parse_strips_whitespace(self) -> None:
        """Should strip whitespace."""
        symbol, asset_type = _parse_symbol_input("  ETH:CRYPTO  ")
        assert symbol == "ETH"
        assert asset_type == AssetType.CRYPTO

    def test_parse_with_whitespace_around_colon(self) -> None:
        """Should handle whitespace around colon."""
        symbol, asset_type = _parse_symbol_input("AAPL :STOCK")
        assert symbol == "AAPL"
        assert asset_type == AssetType.STOCK


class TestAutoDetectAndFetch:
    """Tests for auto-detection logic."""

    @pytest.mark.asyncio
    async def test_known_crypto_symbol_fetches_crypto(self) -> None:
        """Should fetch from crypto service for known crypto symbols."""
        with patch(
            "viper.services.quote.fetch_crypto_quote", new_callable=AsyncMock
        ) as mock_crypto:
            mock_crypto.return_value = CryptoQuote(
                symbol="BTC",
                price_usd=50000.0,
                change_24h_percent=2.5,
                market_cap_usd=1000000000,
                volume_24h_usd=50000000,
                name="Bitcoin",
            )

            result = await _auto_detect_and_fetch("BTC", timeout=10.0)

            assert isinstance(result, CryptoQuote)
            assert result.symbol == "BTC"
            mock_crypto.assert_awaited_once_with("BTC", timeout=10.0)

    @pytest.mark.asyncio
    async def test_unknown_symbol_fetches_stock(self) -> None:
        """Should fetch from stock service for unknown symbols."""
        with patch("viper.services.quote.fetch_stock_quote", new_callable=AsyncMock) as mock_stock:
            mock_stock.return_value = StockQuote(
                ticker="AAPL",
                price=150.0,
                change=2.5,
                change_percent=1.7,
                volume=1000000,
                market_cap=2500000000,
                high_52w=180.0,
                low_52w=120.0,
                name="Apple Inc.",
            )

            result = await _auto_detect_and_fetch("AAPL", timeout=10.0)

            assert isinstance(result, StockQuote)
            assert result.ticker == "AAPL"
            mock_stock.assert_awaited_once_with("AAPL", timeout=10.0)

    @pytest.mark.asyncio
    async def test_normalizes_symbol_before_detection(self) -> None:
        """Should normalize symbol case before checking crypto list."""
        with patch(
            "viper.services.quote.fetch_crypto_quote", new_callable=AsyncMock
        ) as mock_crypto:
            mock_crypto.return_value = CryptoQuote(
                symbol="ETH",
                price_usd=3000.0,
                change_24h_percent=-1.5,
                market_cap_usd=400000000,
                volume_24h_usd=20000000,
            )

            result = await _auto_detect_and_fetch("eth", timeout=10.0)

            assert isinstance(result, CryptoQuote)
            mock_crypto.assert_awaited_once_with("ETH", timeout=10.0)

    @pytest.mark.asyncio
    async def test_known_crypto_usd_pair_fetches_crypto(self) -> None:
        """Should treat known -USD crypto pairs as crypto."""
        with patch(
            "viper.services.quote.fetch_crypto_quote", new_callable=AsyncMock
        ) as mock_crypto:
            mock_crypto.return_value = CryptoQuote(
                symbol="BTC",
                price_usd=50000.0,
                change_24h_percent=1.0,
                market_cap_usd=1000000000,
                volume_24h_usd=20000000,
            )

            result = await _auto_detect_and_fetch("BTC-USD", timeout=10.0)

            assert isinstance(result, CryptoQuote)
            mock_crypto.assert_awaited_once_with("BTC-USD", timeout=10.0)


class TestFetchQuote:
    """Tests for unified fetch_quote function."""

    @pytest.mark.asyncio
    async def test_explicit_crypto_prefix(self) -> None:
        """Should fetch crypto when :CRYPTO prefix is used."""
        with patch(
            "viper.services.quote.fetch_crypto_quote", new_callable=AsyncMock
        ) as mock_crypto:
            mock_crypto.return_value = CryptoQuote(
                symbol="BTC",
                price_usd=50000.0,
                change_24h_percent=2.5,
                market_cap_usd=1000000000,
                volume_24h_usd=50000000,
            )

            result = await fetch_quote("BTC:CRYPTO")

            assert isinstance(result, CryptoQuote)
            mock_crypto.assert_awaited_once_with("BTC", timeout=10.0)

    @pytest.mark.asyncio
    async def test_explicit_stock_prefix(self) -> None:
        """Should fetch stock when :STOCK prefix is used."""
        with patch("viper.services.quote.fetch_stock_quote", new_callable=AsyncMock) as mock_stock:
            mock_stock.return_value = StockQuote(
                ticker="AAPL",
                price=150.0,
                change=2.5,
                change_percent=1.7,
                volume=1000000,
                market_cap=2500000000,
                high_52w=180.0,
                low_52w=120.0,
            )

            result = await fetch_quote("AAPL:STOCK")

            assert isinstance(result, StockQuote)
            mock_stock.assert_awaited_once_with("AAPL", timeout=10.0)

    @pytest.mark.asyncio
    async def test_auto_detect_crypto(self) -> None:
        """Should auto-detect and fetch crypto for known symbols."""
        with patch(
            "viper.services.quote.fetch_crypto_quote", new_callable=AsyncMock
        ) as mock_crypto:
            mock_crypto.return_value = CryptoQuote(
                symbol="ETH",
                price_usd=3000.0,
                change_24h_percent=-1.5,
                market_cap_usd=400000000,
                volume_24h_usd=20000000,
            )

            result = await fetch_quote("ETH")

            assert isinstance(result, CryptoQuote)
            mock_crypto.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auto_detect_stock(self) -> None:
        """Should auto-detect and fetch stock for non-crypto symbols."""
        with patch("viper.services.quote.fetch_stock_quote", new_callable=AsyncMock) as mock_stock:
            mock_stock.return_value = StockQuote(
                ticker="TSLA",
                price=250.0,
                change=-5.0,
                change_percent=-2.0,
                volume=2000000,
                market_cap=800000000,
                high_52w=300.0,
                low_52w=150.0,
            )

            result = await fetch_quote("TSLA")

            assert isinstance(result, StockQuote)
            mock_stock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_custom_timeout(self) -> None:
        """Should pass custom timeout to fetch functions."""
        with patch(
            "viper.services.quote.fetch_crypto_quote", new_callable=AsyncMock
        ) as mock_crypto:
            mock_crypto.return_value = CryptoQuote(
                symbol="BTC",
                price_usd=50000.0,
                change_24h_percent=2.5,
                market_cap_usd=1000000000,
                volume_24h_usd=50000000,
            )

            await fetch_quote("BTC:CRYPTO", timeout=5.0)

            mock_crypto.assert_awaited_once_with("BTC", timeout=5.0)

    @pytest.mark.asyncio
    async def test_returns_crypto_error(self) -> None:
        """Should return CryptoError on crypto fetch failure."""
        with patch(
            "viper.services.quote.fetch_crypto_quote", new_callable=AsyncMock
        ) as mock_crypto:
            mock_crypto.return_value = CryptoError(
                symbol="UNKNOWN", error_message="Unknown crypto symbol: UNKNOWN"
            )

            result = await fetch_quote("UNKNOWN:CRYPTO")

            assert isinstance(result, CryptoError)
            assert result.error_message == "Unknown crypto symbol: UNKNOWN"

    @pytest.mark.asyncio
    async def test_returns_stock_error(self) -> None:
        """Should return StockError on stock fetch failure."""
        with patch(
            "viper.services.quote.fetch_stock_quote", new_callable=AsyncMock
        ) as mock_stock:
            mock_stock.return_value = StockError(
                ticker="INVALID", error_message="Invalid ticker symbol"
            )

            result = await fetch_quote("INVALID:STOCK")

            assert isinstance(result, StockError)
            assert result.error_message == "Invalid ticker symbol"


class TestTypeHelpers:
    """Tests for type checking helper functions."""

    def test_is_crypto_quote_with_crypto_quote(self) -> None:
        """Should return True for CryptoQuote."""
        quote = CryptoQuote(
            symbol="BTC",
            price_usd=50000.0,
            change_24h_percent=2.5,
            market_cap_usd=1000000000,
            volume_24h_usd=50000000,
        )
        assert is_crypto_quote(quote) is True

    def test_is_crypto_quote_with_crypto_error(self) -> None:
        """Should return True for CryptoError."""
        error = CryptoError(symbol="BTC", error_message="Test error")
        assert is_crypto_quote(error) is True

    def test_is_crypto_quote_with_stock_quote(self) -> None:
        """Should return False for StockQuote."""
        quote = StockQuote(
            ticker="AAPL",
            price=150.0,
            change=2.5,
            change_percent=1.7,
            volume=1000000,
            market_cap=2500000000,
            high_52w=180.0,
            low_52w=120.0,
        )
        assert is_crypto_quote(quote) is False

    def test_is_stock_quote_with_stock_quote(self) -> None:
        """Should return True for StockQuote."""
        quote = StockQuote(
            ticker="AAPL",
            price=150.0,
            change=2.5,
            change_percent=1.7,
            volume=1000000,
            market_cap=2500000000,
            high_52w=180.0,
            low_52w=120.0,
        )
        assert is_stock_quote(quote) is True

    def test_is_stock_quote_with_stock_error(self) -> None:
        """Should return True for StockError."""
        error = StockError(ticker="AAPL", error_message="Test error")
        assert is_stock_quote(error) is True

    def test_is_stock_quote_with_crypto_quote(self) -> None:
        """Should return False for CryptoQuote."""
        quote = CryptoQuote(
            symbol="BTC",
            price_usd=50000.0,
            change_24h_percent=2.5,
            market_cap_usd=1000000000,
            volume_24h_usd=50000000,
        )
        assert is_stock_quote(quote) is False
