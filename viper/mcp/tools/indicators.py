"""MCP tool for calculating technical indicators."""

from viper.mcp.server import mcp
from viper.services.history_data import (
    HistoricalData,
    HistoricalDataError,
    fetch_historical_data,
)
from viper.services.indicators import (
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)

VALID_INDICATORS = {"sma", "ema", "rsi", "macd"}


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value from a list."""
    for v in reversed(values):
        if v is not None:
            return v
    return None


@mcp.tool()
async def get_technical_indicators(
    symbol: str,
    period: str = "3M",
    indicators: str = "sma,ema,rsi,macd",
    sma_period: int = 20,
    ema_period: int = 20,
    rsi_period: int = 14,
) -> dict[str, object]:
    """Calculate technical indicators for a stock or cryptocurrency.

    Returns the current (most recent) value for each requested indicator.

    Args:
        symbol: Ticker symbol, e.g. "AAPL", "BTC"
        period: Historical data period - "1W", "1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"
        indicators: Comma-separated list of indicators: "sma", "ema", "rsi", "macd"
        sma_period: Period for SMA calculation (default 20)
        ema_period: Period for EMA calculation (default 20)
        rsi_period: Period for RSI calculation (default 14)

    Returns:
        Current values for each requested indicator.
    """
    requested = {i.strip().lower() for i in indicators.split(",")}
    invalid = requested - VALID_INDICATORS
    if invalid:
        return {
            "error": f"Invalid indicators: {', '.join(sorted(invalid))}. "
            f"Valid: {', '.join(sorted(VALID_INDICATORS))}",
            "symbol": symbol,
        }

    result = await fetch_historical_data(symbol, period=period)

    if isinstance(result, HistoricalDataError):
        return {"error": result.error_message, "symbol": result.ticker}

    assert isinstance(result, HistoricalData)
    prices = result.prices

    response: dict[str, object] = {
        "symbol": result.ticker,
        "period": result.period,
        "data_points": len(prices),
        "current_price": prices[-1] if prices else None,
    }

    if "sma" in requested:
        sma_values = calculate_sma(prices, sma_period)
        response["sma"] = {
            "period": sma_period,
            "value": _last_valid(sma_values),
        }

    if "ema" in requested:
        ema_values = calculate_ema(prices, ema_period)
        response["ema"] = {
            "period": ema_period,
            "value": _last_valid(ema_values),
        }

    if "rsi" in requested:
        rsi_values = calculate_rsi(prices, rsi_period)
        response["rsi"] = {
            "period": rsi_period,
            "value": _last_valid(rsi_values),
        }

    if "macd" in requested:
        macd_line, signal_line, histogram = calculate_macd(prices)
        response["macd"] = {
            "macd_line": _last_valid(macd_line),
            "signal_line": _last_valid(signal_line),
            "histogram": _last_valid(histogram),
        }

    return response
