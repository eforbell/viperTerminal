"""MCP tool for fetching historical price data."""

from viper.mcp.serializers import serialize_datetime
from viper.mcp.server import mcp
from viper.services.history_data import (
    HistoricalData,
    HistoricalDataError,
    calculate_stats,
    fetch_historical_data,
)


@mcp.tool()
async def get_price_history(
    symbol: str, period: str = "1M"
) -> dict[str, object]:
    """Get historical OHLCV price data for a stock or cryptocurrency.

    Args:
        symbol: Ticker symbol, e.g. "AAPL", "BTC"
        period: Time period - "1W", "1M", "3M", "6M", "1Y", "2Y", "5Y", or "MAX"

    Returns:
        OHLCV data with dates, summary statistics, and period metadata.
    """
    result = await fetch_historical_data(symbol, period=period)

    if isinstance(result, HistoricalDataError):
        return {"error": result.error_message, "symbol": result.ticker}

    assert isinstance(result, HistoricalData)
    stats = calculate_stats(result)

    return {
        "symbol": result.ticker,
        "period": result.period,
        "interval": result.interval,
        "data_points": len(result.prices),
        "dates": [serialize_datetime(d) for d in result.dates],
        "opens": result.opens,
        "highs": result.highs,
        "lows": result.lows,
        "closes": result.prices,
        "volumes": result.volumes,
        "stats": {
            "period_high": stats.period_high,
            "period_low": stats.period_low,
            "change_percent": stats.change_percent,
            "avg_volume": stats.avg_volume,
            "num_data_points": stats.num_data_points,
        },
    }
