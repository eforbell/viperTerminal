"""Tests for MCP options tools."""

from unittest.mock import AsyncMock, patch

import pytest

from viper.mcp.tools.options import get_option_expirations, get_options_chain
from viper.services.options import OptionContract, OptionsChain, OptionsError


class TestGetOptionExpirations:
    """Tests for the get_option_expirations MCP tool."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Should return expiration dates on success."""
        with patch(
            "viper.mcp.tools.options.fetch_option_expirations",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = ["2024-01-19", "2024-02-16", "2024-03-15"]

            result = await get_option_expirations("AAPL")

            assert result["symbol"] == "AAPL"
            assert result["count"] == 3
            assert result["expirations"] == ["2024-01-19", "2024-02-16", "2024-03-15"]

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        """Should return error dict on failure."""
        with patch(
            "viper.mcp.tools.options.fetch_option_expirations",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = OptionsError(
                ticker="INVALID", error_message="Invalid ticker symbol"
            )

            result = await get_option_expirations("INVALID")

            assert result["error"] == "Invalid ticker symbol"
            assert result["symbol"] == "INVALID"


class TestGetOptionsChain:
    """Tests for the get_options_chain MCP tool."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Should return calls and puts on success."""
        call = OptionContract(
            strike=150.0,
            bid=5.0,
            ask=5.5,
            last_price=5.25,
            volume=100,
            open_interest=500,
            implied_volatility=0.3,
            in_the_money=True,
        )
        put = OptionContract(
            strike=150.0,
            bid=3.0,
            ask=3.5,
            last_price=3.25,
            volume=80,
            open_interest=400,
            implied_volatility=0.28,
            in_the_money=False,
        )
        with patch(
            "viper.mcp.tools.options.fetch_option_chain",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = OptionsChain(
                ticker="AAPL",
                expiration="2024-01-19",
                calls=[call],
                puts=[put],
            )

            result = await get_options_chain("AAPL", "2024-01-19")

            assert result["symbol"] == "AAPL"
            assert result["expiration"] == "2024-01-19"
            assert result["num_calls"] == 1
            assert result["num_puts"] == 1

            calls = result["calls"]
            assert isinstance(calls, list)
            assert calls[0]["strike"] == 150.0
            assert calls[0]["in_the_money"] is True

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        """Should return error dict on failure."""
        with patch(
            "viper.mcp.tools.options.fetch_option_chain",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = OptionsError(
                ticker="AAPL",
                error_message="Invalid expiration date: 2099-01-01",
            )

            result = await get_options_chain("AAPL", "2099-01-01")

            assert "error" in result
            assert "2099-01-01" in str(result["error"])
