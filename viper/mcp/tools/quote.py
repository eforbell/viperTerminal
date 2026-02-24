"""MCP tool for fetching stock and crypto quotes."""

from dataclasses import asdict

from viper.mcp.server import mcp
from viper.services.crypto import CryptoError, CryptoQuote
from viper.services.quote import fetch_quote
from viper.services.stock import StockError, StockQuote


@mcp.tool()
async def get_quote(symbol: str, timeout_seconds: float = 20.0) -> dict[str, object]:
    """Get a real-time quote for a stock or cryptocurrency.

    Supports auto-detection (AAPL, BTC) or explicit prefixes (AAPL:STOCK, BTC:CRYPTO).

    Args:
        symbol: Ticker symbol, e.g. "AAPL", "BTC", "TSLA:STOCK", "ETH:CRYPTO"
        timeout_seconds: Quote fetch timeout in seconds (default: 20.0)

    Returns:
        Quote data including price, change, volume, and market cap.
    """
    result = await fetch_quote(symbol, timeout=timeout_seconds)

    if isinstance(result, (StockError, CryptoError)):
        if isinstance(result, StockError):
            return {"error": result.error_message, "symbol": result.ticker}
        return {"error": result.error_message, "symbol": result.symbol}

    if isinstance(result, StockQuote):
        return {
            "type": "stock",
            "ticker": result.ticker,
            "name": result.name,
            "price": result.price,
            "change": result.change,
            "change_percent": result.change_percent,
            "volume": result.volume,
            "market_cap": result.market_cap,
            "high_52w": result.high_52w,
            "low_52w": result.low_52w,
        }

    # CryptoQuote
    assert isinstance(result, CryptoQuote)
    return {
        "type": "crypto",
        "symbol": result.symbol,
        "name": result.name,
        "price_usd": result.price_usd,
        "change_24h_percent": result.change_24h_percent,
        "market_cap_usd": result.market_cap_usd,
        "volume_24h_usd": result.volume_24h_usd,
    }
