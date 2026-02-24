"""Tests for MCP get_scan tool."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from viper.mcp.tools.scan import get_scan
from viper.services.history_data import HistoricalData, HistoricalDataError


def _make_historical_data(symbol: str, prices: list[float]) -> HistoricalData:
    """Create HistoricalData fixture."""
    points = len(prices)
    return HistoricalData(
        ticker=symbol,
        dates=[datetime(2024, 1, 1, tzinfo=timezone.utc)] * points,
        prices=prices,
        volumes=[1000000] * points,
        highs=[p + 1 for p in prices],
        lows=[p - 1 for p in prices],
        opens=[p - 0.5 for p in prices],
        period="3M",
        interval="1d",
    )


class TestGetScan:
    """Tests for indicator-based scanning."""

    @pytest.mark.asyncio
    async def test_matches_price_rule(self) -> None:
        """Should return only symbols matching a simple price threshold."""
        async def _fetch(symbol: str, period: str) -> HistoricalData:
            if symbol == "AAPL":
                return _make_historical_data("AAPL", [10.0, 11.0, 12.0])
            return _make_historical_data("TSLA", [90.0, 100.0, 110.0])

        with patch("viper.mcp.tools.scan.fetch_historical_data", new_callable=AsyncMock) as mock:
            mock.side_effect = _fetch
            result = await get_scan("AAPL,TSLA", "price > 50", period="3M")

            assert result["matched_count"] == 1
            matches = result["matches"]
            assert isinstance(matches, list)
            assert matches[0]["symbol"] == "TSLA"

    @pytest.mark.asyncio
    async def test_matches_sma_rule(self) -> None:
        """Should evaluate SMA period rules like sma20 > 20."""
        with patch(
            "viper.mcp.tools.scan.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            # SMA20 for range(1..30) is average of 11..30 = 20.5
            mock.return_value = _make_historical_data(
                "AAPL", [float(i) for i in range(1, 31)]
            )

            result = await get_scan("AAPL", "sma20 > 20", period="3M")

            assert result["matched_count"] == 1
            matches = result["matches"]
            assert isinstance(matches, list)
            metrics = matches[0]["metrics"]
            assert isinstance(metrics, dict)
            assert metrics["sma20"] is not None

    @pytest.mark.asyncio
    async def test_invalid_rule_returns_error(self) -> None:
        """Should return parse error for invalid rule format."""
        result = await get_scan("AAPL", "not a valid rule")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_collects_symbol_errors(self) -> None:
        """Should continue scan and capture per-symbol fetch errors."""
        async def _fetch(symbol: str, period: str) -> HistoricalData | HistoricalDataError:
            if symbol == "BAD":
                return HistoricalDataError(ticker="BAD", error_message="Invalid ticker")
            return _make_historical_data("AAPL", [100.0, 101.0, 102.0])

        with patch("viper.mcp.tools.scan.fetch_historical_data", new_callable=AsyncMock) as mock:
            mock.side_effect = _fetch
            result = await get_scan("AAPL,BAD", "price > 50", period="3M")

            errors = result["errors"]
            assert isinstance(errors, list)
            assert len(errors) == 1
            assert errors[0]["symbol"] == "BAD"

    @pytest.mark.asyncio
    async def test_watchlist_symbol_source(self) -> None:
        """Should resolve symbols from watchlist when requested."""
        with (
            patch("viper.mcp.tools.scan.WatchlistManager") as mock_manager_cls,
            patch(
                "viper.mcp.tools.scan.fetch_historical_data",
                new_callable=AsyncMock,
            ) as mock_fetch,
        ):
            mock_manager = mock_manager_cls.return_value
            mock_manager.get_all.return_value = ["AAPL"]
            mock_fetch.return_value = _make_historical_data("AAPL", [100.0, 101.0, 102.0])

            result = await get_scan("watchlist", "price > 50", period="3M")

            assert result["symbols_requested"] == 1
            assert result["matched_count"] == 1
