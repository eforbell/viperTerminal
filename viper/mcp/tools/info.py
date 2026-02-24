"""MCP tools for fetching stock and crypto information."""

from viper.mcp.server import mcp
from viper.services.crypto import CryptoInfo, CryptoInfoError, fetch_crypto_info
from viper.services.stock import StockInfo, StockInfoError, fetch_stock_info


@mcp.tool()
async def get_stock_info(ticker: str) -> dict[str, object]:
    """Get extended information for a stock (sector, industry, description, etc.).

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL", "TSLA"

    Returns:
        Detailed stock information including sector, industry, website, and description.
    """
    result = await fetch_stock_info(ticker)

    if isinstance(result, StockInfoError):
        return {"error": result.error_message, "symbol": result.ticker}

    assert isinstance(result, StockInfo)
    return {
        "symbol": result.ticker,
        "info": result.info,
    }


@mcp.tool()
async def get_crypto_info(symbol: str) -> dict[str, object]:
    """Get extended information for a cryptocurrency.

    Args:
        symbol: Crypto symbol, e.g. "BTC", "ETH"

    Returns:
        Detailed crypto information including description, website, and market data.
    """
    result = await fetch_crypto_info(symbol)

    if isinstance(result, CryptoInfoError):
        return {"error": result.error_message, "symbol": result.symbol}

    assert isinstance(result, CryptoInfo)
    return {
        "symbol": result.symbol,
        "info": result.info,
    }
