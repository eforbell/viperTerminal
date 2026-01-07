"""Crypto quote fetching service using yfinance."""

import asyncio
from dataclasses import dataclass

import yfinance as yf  # type: ignore[import-untyped]


@dataclass
class CryptoQuote:
    """Crypto quote data."""

    symbol: str
    price_usd: float
    change_24h_percent: float
    market_cap_usd: int
    volume_24h_usd: float
    name: str | None = None


@dataclass
class CryptoError:
    """Error result from crypto fetch."""

    symbol: str
    error_message: str


@dataclass
class CryptoInfo:
    """Extended crypto information."""

    symbol: str
    info: dict[str, object]


@dataclass
class CryptoInfoError:
    """Error result from crypto info fetch."""

    symbol: str
    error_message: str


# Type alias for result
CryptoResult = CryptoQuote | CryptoError
CryptoInfoResult = CryptoInfo | CryptoInfoError


# Mapping of common crypto symbols to yfinance ticker pairs (SYMBOL-USD format)
SYMBOL_TO_PAIR: dict[str, str] = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "USDT": "USDT-USD",
    "BNB": "BNB-USD",
    "SOL": "SOL-USD",
    "USDC": "USDC-USD",
    "XRP": "XRP-USD",
    "ADA": "ADA-USD",
    "DOGE": "DOGE-USD",
    "TRX": "TRX-USD",
    "DOT": "DOT-USD",
    "MATIC": "MATIC-USD",
    "LTC": "LTC-USD",
    "SHIB": "SHIB-USD",
    "AVAX": "AVAX-USD",
    "LINK": "LINK-USD",
    "UNI": "UNI-USD",
    "ATOM": "ATOM-USD",
    "XLM": "XLM-USD",
    "ETC": "ETC-USD",
}

# Legacy alias for backward compatibility
SYMBOL_TO_ID = SYMBOL_TO_PAIR


async def fetch_crypto_quote(
    symbol: str, timeout: float = 10.0, max_retries: int = 3
) -> CryptoResult:
    """
    Fetch crypto quote data for the given symbol using yfinance.

    Args:
        symbol: Crypto symbol (e.g., 'BTC', 'ETH') or full pair (e.g., 'BTC-USD')
        timeout: Maximum time to wait for response in seconds (unused but kept for compatibility)
        max_retries: Maximum number of retries on error (unused but kept for compatibility)

    Returns:
        CryptoQuote on success, CryptoError on failure

    Note:
        Auto-converts common symbols: BTC→BTC-USD, ETH→ETH-USD, etc.
        Supports explicit -USD suffix for direct usage.
        Uses yfinance for data fetching - no rate limits like CoinGecko.
    """
    symbol = symbol.upper().strip()

    # Auto-convert to SYMBOL-USD format if needed
    if "-USD" not in symbol:
        pair = SYMBOL_TO_PAIR.get(symbol)
        if pair is None:
            return CryptoError(symbol=symbol, error_message=f"Unknown crypto symbol: {symbol}")
    else:
        # Use symbol as-is if it already has -USD suffix
        pair = symbol
        # Extract base symbol for result
        symbol = symbol.replace("-USD", "")

    # Fetch data from yfinance
    try:
        result = await asyncio.to_thread(_fetch_yfinance_crypto, pair, symbol)
        return result
    except Exception as e:
        return CryptoError(symbol=symbol, error_message=f"Unexpected error: {str(e)}")


def _fetch_yfinance_crypto(pair: str, symbol: str) -> CryptoResult:
    """
    Fetch crypto data using yfinance (synchronous, called via asyncio.to_thread).

    Args:
        pair: yfinance ticker pair (e.g., 'BTC-USD')
        symbol: Original symbol for result (e.g., 'BTC')

    Returns:
        CryptoQuote on success, CryptoError on failure
    """
    try:
        ticker = yf.Ticker(pair)

        # Get fast_info for quote data
        info = ticker.fast_info

        # Extract current price
        price_usd = info.get("last_price")
        if price_usd is None:
            # Fallback: try regular price from .info
            full_info = ticker.info
            price_usd = full_info.get("regularMarketPrice") or full_info.get("currentPrice")
            if price_usd is None:
                return CryptoError(symbol=symbol, error_message="Missing price data in response")

        # Get 1-day history for 24h change calculation
        hist = ticker.history(period="2d")
        if hist.empty or len(hist) < 2:
            # No historical data - use 0% change
            change_24h_percent = 0.0
        else:
            # Calculate 24h change percentage
            previous_close = float(hist.iloc[-2]["Close"])
            current_price = float(hist.iloc[-1]["Close"])
            if previous_close > 0:
                change_24h_percent = ((current_price - previous_close) / previous_close) * 100
            else:
                change_24h_percent = 0.0

        # Extract market cap (may not be available for all crypto)
        full_info = ticker.info
        market_cap_usd = full_info.get("marketCap", 0)
        if market_cap_usd is None:
            market_cap_usd = 0

        # Extract 24h volume
        volume_24h_usd = full_info.get("volume24Hr", 0.0) or full_info.get("regularMarketVolume", 0.0)
        if volume_24h_usd is None:
            volume_24h_usd = 0.0

        # Extract name
        name = full_info.get("longName") or full_info.get("name")

        return CryptoQuote(
            symbol=symbol,
            price_usd=float(price_usd),
            change_24h_percent=float(change_24h_percent),
            market_cap_usd=int(market_cap_usd),
            volume_24h_usd=float(volume_24h_usd),
            name=name,
        )

    except Exception as e:
        return CryptoError(symbol=symbol, error_message=f"Failed to fetch quote: {str(e)}")


async def fetch_crypto_info(
    symbol: str, timeout: float = 10.0, max_retries: int = 3
) -> CryptoInfoResult:
    """
    Fetch extended crypto information for the info panel using yfinance.

    Args:
        symbol: Crypto symbol (e.g., 'BTC', 'ETH') or full pair (e.g., 'BTC-USD')
        timeout: Maximum time to wait for response in seconds (unused but kept for compatibility)
        max_retries: Maximum number of retries on error (unused but kept for compatibility)

    Returns:
        CryptoInfo on success, CryptoInfoError on failure

    Note:
        Returns full info dict from yfinance with description, website, etc.
        Auto-converts common symbols: BTC→BTC-USD, ETH→ETH-USD, etc.
    """
    symbol = symbol.upper().strip()

    # Auto-convert to SYMBOL-USD format if needed
    if "-USD" not in symbol:
        pair = SYMBOL_TO_PAIR.get(symbol)
        if pair is None:
            return CryptoInfoError(symbol=symbol, error_message=f"Unknown crypto symbol: {symbol}")
    else:
        # Use symbol as-is if it already has -USD suffix
        pair = symbol
        # Extract base symbol for result
        symbol = symbol.replace("-USD", "")

    # Fetch info from yfinance
    try:
        result = await asyncio.to_thread(_fetch_yfinance_info, pair, symbol)
        return result
    except Exception as e:
        return CryptoInfoError(symbol=symbol, error_message=f"Unexpected error: {str(e)}")


def _fetch_yfinance_info(pair: str, symbol: str) -> CryptoInfoResult:
    """
    Fetch crypto info using yfinance (synchronous, called via asyncio.to_thread).

    Args:
        pair: yfinance ticker pair (e.g., 'BTC-USD')
        symbol: Original symbol for result (e.g., 'BTC')

    Returns:
        CryptoInfo on success, CryptoInfoError on failure
    """
    try:
        ticker = yf.Ticker(pair)

        # Get full info dict
        info = ticker.info

        # Validate we got data
        if not isinstance(info, dict) or not info:
            return CryptoInfoError(symbol=symbol, error_message="Invalid response format")

        # Return the full info dict
        return CryptoInfo(symbol=symbol, info=info)

    except Exception as e:
        return CryptoInfoError(symbol=symbol, error_message=f"Failed to fetch info: {str(e)}")
