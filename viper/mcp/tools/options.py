"""MCP tools for fetching options data."""

from dataclasses import asdict

from viper.mcp.server import mcp
from viper.services.options import (
    OptionsChain,
    OptionsError,
    fetch_option_chain,
    fetch_option_expirations,
)


@mcp.tool()
async def get_option_expirations(ticker: str) -> dict[str, object]:
    """Get available option expiration dates for a stock.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL", "TSLA"

    Returns:
        List of available expiration dates in YYYY-MM-DD format.
    """
    result = await fetch_option_expirations(ticker)

    if isinstance(result, OptionsError):
        return {"error": result.error_message, "symbol": result.ticker}

    return {
        "symbol": ticker.upper().strip(),
        "expirations": result,
        "count": len(result),
    }


@mcp.tool()
async def get_options_chain(ticker: str, expiration: str) -> dict[str, object]:
    """Get the options chain (calls and puts) for a specific expiration date.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL", "TSLA"
        expiration: Expiration date in YYYY-MM-DD format

    Returns:
        Calls and puts with strike, bid, ask, volume, open interest, and IV.
    """
    result = await fetch_option_chain(ticker, expiration)

    if isinstance(result, OptionsError):
        return {"error": result.error_message, "symbol": result.ticker}

    assert isinstance(result, OptionsChain)
    return {
        "symbol": result.ticker,
        "expiration": result.expiration,
        "calls": [asdict(c) for c in result.calls],
        "puts": [asdict(p) for p in result.puts],
        "num_calls": len(result.calls),
        "num_puts": len(result.puts),
    }
