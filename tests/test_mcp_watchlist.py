"""Tests for MCP watchlist tools."""

import pytest

import viper.mcp.tools.watchlist as watchlist_module
from viper.mcp.tools.watchlist import (
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist,
)


@pytest.fixture(autouse=True)
def reset_watchlist_singleton() -> None:
    """Reset the lazy singleton before each test."""
    watchlist_module._manager = None


class TestWatchlistTools:
    """Tests for watchlist MCP tools."""

    @pytest.mark.asyncio
    async def test_empty_watchlist(self) -> None:
        """Should return empty list when watchlist has no items."""
        result = await get_watchlist()

        assert result["tickers"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_add_to_watchlist(self) -> None:
        """Should add a ticker and return updated list."""
        result = await add_to_watchlist("AAPL")

        assert result["added"] == "AAPL"
        assert "AAPL" in result["tickers"]
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_add_multiple(self) -> None:
        """Should add multiple tickers."""
        await add_to_watchlist("AAPL")
        result = await add_to_watchlist("TSLA")

        assert result["count"] == 2
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert "AAPL" in tickers
        assert "TSLA" in tickers

    @pytest.mark.asyncio
    async def test_remove_from_watchlist(self) -> None:
        """Should remove a ticker and confirm removal."""
        await add_to_watchlist("AAPL")
        result = await remove_from_watchlist("AAPL")

        assert result["removed"] == "AAPL"
        assert result["was_present"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self) -> None:
        """Should indicate ticker was not present."""
        result = await remove_from_watchlist("NOTHERE")

        assert result["was_present"] is False

    @pytest.mark.asyncio
    async def test_round_trip(self) -> None:
        """Should support add, get, remove round-trip."""
        await add_to_watchlist("AAPL")
        await add_to_watchlist("BTC")

        get_result = await get_watchlist()
        assert get_result["count"] == 2

        await remove_from_watchlist("AAPL")

        get_result = await get_watchlist()
        assert get_result["count"] == 1
        tickers = get_result["tickers"]
        assert isinstance(tickers, list)
        assert "BTC" in tickers
        assert "AAPL" not in tickers

    @pytest.mark.asyncio
    async def test_normalizes_ticker(self) -> None:
        """Should normalize ticker to uppercase."""
        result = await add_to_watchlist("aapl")

        assert result["added"] == "AAPL"
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert "AAPL" in tickers
