"""Unified quote service with asset type detection."""

from dataclasses import dataclass

from viper.services.crypto import SYMBOL_TO_ID, CryptoError, CryptoQuote, fetch_crypto_quote
from viper.services.stock import StockError, StockQuote, fetch_stock_quote

# Union types for all possible quote results
Quote = StockQuote | CryptoQuote
QuoteError = StockError | CryptoError
QuoteResult = Quote | QuoteError


@dataclass
class AssetType:
    """Asset type enumeration."""

    STOCK = "STOCK"
    CRYPTO = "CRYPTO"


async def fetch_quote(symbol_input: str, timeout: float = 10.0) -> QuoteResult:
    """
    Fetch a quote with automatic asset type detection.

    Supports explicit prefixes (e.g., 'BTC:CRYPTO', 'AAPL:STOCK') or auto-detection.
    Auto-detection checks known crypto symbols first, then falls back to stock lookup.

    Args:
        symbol_input: Symbol with optional type prefix (e.g., 'AAPL', 'BTC:CRYPTO')
        timeout: Maximum time to wait for response in seconds

    Returns:
        StockQuote, CryptoQuote, StockError, or CryptoError

    Examples:
        >>> await fetch_quote('AAPL')  # Auto-detects as stock
        >>> await fetch_quote('BTC')   # Auto-detects as crypto
        >>> await fetch_quote('AAPL:STOCK')  # Explicit stock
        >>> await fetch_quote('BTC:CRYPTO')  # Explicit crypto
    """
    # Parse the input for explicit type prefix
    symbol, asset_type = _parse_symbol_input(symbol_input)

    if asset_type == AssetType.CRYPTO:
        # Explicit crypto request
        return await fetch_crypto_quote(symbol, timeout=timeout)
    if asset_type == AssetType.STOCK:
        # Explicit stock request
        return await fetch_stock_quote(symbol, timeout=timeout)
    # Auto-detection: check crypto list first
    return await _auto_detect_and_fetch(symbol, timeout)


def _parse_symbol_input(symbol_input: str) -> tuple[str, str | None]:
    """
    Parse symbol input for explicit type prefix.

    Args:
        symbol_input: Raw input from user (e.g., 'BTC:CRYPTO', 'AAPL', 'TSLA:STOCK')

    Returns:
        Tuple of (symbol, asset_type) where asset_type is None if no prefix
    """
    symbol_input = symbol_input.upper().strip()

    # Check for explicit type prefix
    if ":CRYPTO" in symbol_input:
        symbol = symbol_input.replace(":CRYPTO", "").strip()
        return (symbol, AssetType.CRYPTO)
    if ":STOCK" in symbol_input:
        symbol = symbol_input.replace(":STOCK", "").strip()
        return (symbol, AssetType.STOCK)
    # No prefix - return as-is for auto-detection
    return (symbol_input, None)


async def _auto_detect_and_fetch(symbol: str, timeout: float) -> QuoteResult:
    """
    Auto-detect asset type and fetch quote.

    Checks known crypto symbol list first, then falls back to stock lookup.

    Args:
        symbol: Normalized symbol (no prefix)
        timeout: Request timeout

    Returns:
        Quote result from appropriate service
    """
    symbol = symbol.upper().strip()

    # Check if it's a known crypto symbol
    if symbol in SYMBOL_TO_ID:
        return await fetch_crypto_quote(symbol, timeout=timeout)

    # Check known crypto trading pairs (e.g., BTC-USD, ETH-USD)
    if symbol.endswith("-USD"):
        base_symbol = symbol.removesuffix("-USD")
        if base_symbol in SYMBOL_TO_ID:
            return await fetch_crypto_quote(symbol, timeout=timeout)

    # Fall back to stock lookup
    return await fetch_stock_quote(symbol, timeout=timeout)


def is_crypto_quote(quote: Quote | QuoteError) -> bool:
    """
    Check if a quote result is a crypto quote.

    Args:
        quote: Quote or error result

    Returns:
        True if crypto quote or error, False otherwise
    """
    return isinstance(quote, (CryptoQuote, CryptoError))


def is_stock_quote(quote: Quote | QuoteError) -> bool:
    """
    Check if a quote result is a stock quote.

    Args:
        quote: Quote or error result

    Returns:
        True if stock quote or error, False otherwise
    """
    return isinstance(quote, (StockQuote, StockError))
