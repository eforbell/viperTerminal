"""Tests for MCP get_price_history tool."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from viper.mcp.tools.history import get_price_history
from viper.services.history_data import HistoricalData, HistoricalDataError


class TestGetPriceHistory:
    """Tests for the get_price_history MCP tool."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Should return OHLCV data with stats on success."""
        dates = [
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 2, tzinfo=timezone.utc),
            datetime(2024, 1, 3, tzinfo=timezone.utc),
        ]
        with patch(
            "viper.mcp.tools.history.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = HistoricalData(
                ticker="AAPL",
                dates=dates,
                prices=[150.0, 152.0, 155.0],
                volumes=[1000000, 1100000, 1200000],
                highs=[151.0, 153.0, 156.0],
                lows=[149.0, 151.0, 154.0],
                opens=[150.0, 151.0, 153.0],
                period="1M",
                interval="1d",
            )

            result = await get_price_history("AAPL", period="1M")

            assert result["symbol"] == "AAPL"
            assert result["period"] == "1M"
            assert result["interval"] == "1d"
            assert result["data_points"] == 3
            assert len(result["dates"]) == 3  # type: ignore[arg-type]
            assert result["closes"] == [150.0, 152.0, 155.0]
            assert result["volumes"] == [1000000, 1100000, 1200000]

            # Check stats
            stats = result["stats"]
            assert isinstance(stats, dict)
            assert stats["period_high"] == 156.0
            assert stats["period_low"] == 149.0
            assert stats["num_data_points"] == 3

    @pytest.mark.asyncio
    async def test_datetime_serialization(self) -> None:
        """Should serialize datetimes to ISO format strings."""
        dt = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch(
            "viper.mcp.tools.history.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = HistoricalData(
                ticker="AAPL",
                dates=[dt],
                prices=[150.0],
                volumes=[1000000],
                highs=[151.0],
                lows=[149.0],
                opens=[150.0],
                period="1M",
                interval="1d",
            )

            result = await get_price_history("AAPL")

            dates = result["dates"]
            assert isinstance(dates, list)
            assert dates[0] == "2024-06-15T14:30:00+00:00"

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        """Should return error dict on failure."""
        with patch(
            "viper.mcp.tools.history.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = HistoricalDataError(
                ticker="INVALID", error_message="No historical data available"
            )

            result = await get_price_history("INVALID")

            assert result["error"] == "No historical data available"
            assert result["symbol"] == "INVALID"

    @pytest.mark.asyncio
    async def test_default_period(self) -> None:
        """Should default to 1M period."""
        with patch(
            "viper.mcp.tools.history.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = HistoricalDataError(
                ticker="AAPL", error_message="test"
            )

            await get_price_history("AAPL")

            mock.assert_awaited_once_with("AAPL", period="1M")
