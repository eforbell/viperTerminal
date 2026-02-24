"""Tests for MCP info tools."""

from unittest.mock import AsyncMock, patch

import pytest

from viper.mcp.tools.info import get_crypto_info, get_stock_info
from viper.services.crypto import CryptoInfo, CryptoInfoError
from viper.services.stock import StockInfo, StockInfoError


class TestGetStockInfo:
    """Tests for the get_stock_info MCP tool."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Should return stock info on success."""
        with patch(
            "viper.mcp.tools.info.fetch_stock_info", new_callable=AsyncMock
        ) as mock:
            mock.return_value = StockInfo(
                ticker="AAPL",
                info={
                    "sector": "Technology",
                    "industry": "Consumer Electronics",
                    "longBusinessSummary": "Apple Inc. designs...",
                },
            )

            result = await get_stock_info("AAPL")

            assert result["symbol"] == "AAPL"
            info = result["info"]
            assert isinstance(info, dict)
            assert info["sector"] == "Technology"

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        """Should return error dict on failure."""
        with patch(
            "viper.mcp.tools.info.fetch_stock_info", new_callable=AsyncMock
        ) as mock:
            mock.return_value = StockInfoError(
                ticker="INVALID", error_message="Invalid ticker symbol"
            )

            result = await get_stock_info("INVALID")

            assert result["error"] == "Invalid ticker symbol"
            assert result["symbol"] == "INVALID"


class TestGetCryptoInfo:
    """Tests for the get_crypto_info MCP tool."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Should return crypto info on success."""
        with patch(
            "viper.mcp.tools.info.fetch_crypto_info", new_callable=AsyncMock
        ) as mock:
            mock.return_value = CryptoInfo(
                symbol="BTC",
                info={
                    "name": "Bitcoin",
                    "description": "Bitcoin is a decentralized...",
                },
            )

            result = await get_crypto_info("BTC")

            assert result["symbol"] == "BTC"
            info = result["info"]
            assert isinstance(info, dict)
            assert info["name"] == "Bitcoin"

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        """Should return error dict on failure."""
        with patch(
            "viper.mcp.tools.info.fetch_crypto_info", new_callable=AsyncMock
        ) as mock:
            mock.return_value = CryptoInfoError(
                symbol="UNKNOWN", error_message="Unknown crypto symbol: UNKNOWN"
            )

            result = await get_crypto_info("UNKNOWN")

            assert result["error"] == "Unknown crypto symbol: UNKNOWN"
            assert result["symbol"] == "UNKNOWN"
