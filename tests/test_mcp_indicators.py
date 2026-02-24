"""Tests for MCP get_technical_indicators tool."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from viper.mcp.tools.indicators import get_technical_indicators
from viper.services.history_data import HistoricalData, HistoricalDataError


def _make_historical_data(num_points: int = 50) -> HistoricalData:
    """Create a HistoricalData fixture with enough data for indicators."""
    base_price = 100.0
    prices = [base_price + i * 0.5 for i in range(num_points)]
    return HistoricalData(
        ticker="AAPL",
        dates=[datetime(2024, 1, 1, tzinfo=timezone.utc)] * num_points,
        prices=prices,
        volumes=[1000000] * num_points,
        highs=[p + 1 for p in prices],
        lows=[p - 1 for p in prices],
        opens=[p - 0.5 for p in prices],
        period="3M",
        interval="1d",
    )


class TestGetTechnicalIndicators:
    """Tests for the get_technical_indicators MCP tool."""

    @pytest.mark.asyncio
    async def test_all_indicators(self) -> None:
        """Should return all indicator values when all requested."""
        with patch(
            "viper.mcp.tools.indicators.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = _make_historical_data()

            result = await get_technical_indicators("AAPL")

            assert result["symbol"] == "AAPL"
            assert result["current_price"] is not None
            assert "sma" in result
            assert "ema" in result
            assert "rsi" in result
            assert "macd" in result

            # Check SMA structure
            sma = result["sma"]
            assert isinstance(sma, dict)
            assert sma["period"] == 20
            assert sma["value"] is not None

            # Check MACD structure
            macd = result["macd"]
            assert isinstance(macd, dict)
            assert "macd_line" in macd
            assert "signal_line" in macd
            assert "histogram" in macd

    @pytest.mark.asyncio
    async def test_subset_indicators(self) -> None:
        """Should return only requested indicators."""
        with patch(
            "viper.mcp.tools.indicators.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = _make_historical_data()

            result = await get_technical_indicators("AAPL", indicators="sma,rsi")

            assert "sma" in result
            assert "rsi" in result
            assert "ema" not in result
            assert "macd" not in result

    @pytest.mark.asyncio
    async def test_custom_periods(self) -> None:
        """Should use custom periods for indicators."""
        with patch(
            "viper.mcp.tools.indicators.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = _make_historical_data()

            result = await get_technical_indicators(
                "AAPL", indicators="sma,ema", sma_period=50, ema_period=12
            )

            sma = result["sma"]
            assert isinstance(sma, dict)
            assert sma["period"] == 50

            ema = result["ema"]
            assert isinstance(ema, dict)
            assert ema["period"] == 12

    @pytest.mark.asyncio
    async def test_invalid_indicator(self) -> None:
        """Should return error for invalid indicator names."""
        result = await get_technical_indicators("AAPL", indicators="sma,bogus")

        assert "error" in result
        assert "bogus" in str(result["error"])

    @pytest.mark.asyncio
    async def test_historical_data_error(self) -> None:
        """Should return error when historical data fetch fails."""
        with patch(
            "viper.mcp.tools.indicators.fetch_historical_data",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = HistoricalDataError(
                ticker="INVALID", error_message="Invalid ticker symbol"
            )

            result = await get_technical_indicators("INVALID")

            assert result["error"] == "Invalid ticker symbol"
            assert result["symbol"] == "INVALID"
