"""Tests for MCP get_quote tool."""

from unittest.mock import AsyncMock, patch

import pytest

from viper.mcp.tools.quote import get_quote
from viper.services.crypto import CryptoError, CryptoQuote
from viper.services.stock import StockError, StockQuote


class TestGetQuote:
    """Tests for the get_quote MCP tool."""

    @pytest.mark.asyncio
    async def test_stock_quote_success(self) -> None:
        """Should return stock quote data on success."""
        with patch(
            "viper.mcp.tools.quote.fetch_quote", new_callable=AsyncMock
        ) as mock:
            mock.return_value = StockQuote(
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

            result = await get_quote("AAPL")

            assert result["type"] == "stock"
            assert result["ticker"] == "AAPL"
            assert result["price"] == 150.0
            assert result["change"] == 2.5
            assert result["change_percent"] == 1.7
            assert result["volume"] == 1000000
            assert result["market_cap"] == 2500000000
            assert result["name"] == "Apple Inc."
            mock.assert_awaited_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_crypto_quote_success(self) -> None:
        """Should return crypto quote data on success."""
        with patch(
            "viper.mcp.tools.quote.fetch_quote", new_callable=AsyncMock
        ) as mock:
            mock.return_value = CryptoQuote(
                symbol="BTC",
                price_usd=50000.0,
                change_24h_percent=2.5,
                market_cap_usd=1000000000,
                volume_24h_usd=50000000.0,
                name="Bitcoin",
            )

            result = await get_quote("BTC")

            assert result["type"] == "crypto"
            assert result["symbol"] == "BTC"
            assert result["price_usd"] == 50000.0
            assert result["change_24h_percent"] == 2.5
            assert result["name"] == "Bitcoin"
            mock.assert_awaited_once_with("BTC")

    @pytest.mark.asyncio
    async def test_stock_error(self) -> None:
        """Should return error dict on stock fetch failure."""
        with patch(
            "viper.mcp.tools.quote.fetch_quote", new_callable=AsyncMock
        ) as mock:
            mock.return_value = StockError(
                ticker="INVALID", error_message="Invalid ticker symbol"
            )

            result = await get_quote("INVALID")

            assert result["error"] == "Invalid ticker symbol"
            assert result["symbol"] == "INVALID"

    @pytest.mark.asyncio
    async def test_crypto_error(self) -> None:
        """Should return error dict on crypto fetch failure."""
        with patch(
            "viper.mcp.tools.quote.fetch_quote", new_callable=AsyncMock
        ) as mock:
            mock.return_value = CryptoError(
                symbol="UNKNOWN", error_message="Unknown crypto symbol: UNKNOWN"
            )

            result = await get_quote("UNKNOWN:CRYPTO")

            assert result["error"] == "Unknown crypto symbol: UNKNOWN"
            assert result["symbol"] == "UNKNOWN"
