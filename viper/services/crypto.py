"""Crypto quote fetching service using CoinGecko API."""

import asyncio
from dataclasses import dataclass

import httpx


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


# Mapping of common crypto symbols to CoinGecko IDs
SYMBOL_TO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binancecoin",
    "SOL": "solana",
    "USDC": "usd-coin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "TRX": "tron",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "SHIB": "shiba-inu",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XLM": "stellar",
    "ETC": "ethereum-classic",
}


async def fetch_crypto_quote(
    symbol: str, timeout: float = 10.0, max_retries: int = 3
) -> CryptoResult:
    """
    Fetch crypto quote data for the given symbol.

    Args:
        symbol: Crypto symbol (e.g., 'BTC', 'ETH')
        timeout: Maximum time to wait for response in seconds
        max_retries: Maximum number of retries on rate limit (429)

    Returns:
        CryptoQuote on success, CryptoError on failure

    Note:
        Handles rate limiting with exponential backoff.
        All HTTP requests use httpx async client.
    """
    symbol = symbol.upper().strip()

    # Map symbol to CoinGecko ID
    coin_id = SYMBOL_TO_ID.get(symbol)
    if coin_id is None:
        return CryptoError(symbol=symbol, error_message=f"Unknown crypto symbol: {symbol}")

    # Retry loop for rate limiting
    last_error: CryptoError | None = None
    for attempt in range(max_retries):
        try:
            result = await _fetch_with_timeout(coin_id, symbol, timeout)

            # Check if we got a rate limit error
            if isinstance(result, CryptoError) and "rate limit" in result.error_message.lower():
                last_error = result
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s...
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                # Last attempt failed with rate limit
                break
            return result

        except Exception as e:
            return CryptoError(symbol=symbol, error_message=f"Unexpected error: {str(e)}")

    # If we exhausted retries on rate limit
    if last_error:
        return CryptoError(
            symbol=symbol, error_message=f"Rate limit exceeded after {max_retries} retries"
        )
    # Shouldn't reach here, but satisfy type checker
    return CryptoError(symbol=symbol, error_message="Unknown error")  # pragma: no cover


async def _fetch_with_timeout(coin_id: str, symbol: str, timeout: float) -> CryptoResult:
    """
    Fetch crypto data with timeout handling.

    Args:
        coin_id: CoinGecko coin ID
        symbol: Original symbol for error messages
        timeout: Request timeout in seconds

    Returns:
        CryptoQuote on success, CryptoError on failure
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await asyncio.wait_for(
                client.get(
                    f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "market_data": "true",
                        "community_data": "false",
                        "developer_data": "false",
                        "sparkline": "false",
                    },
                ),
                timeout=timeout,
            )

            # Handle rate limiting
            if response.status_code == 429:
                return CryptoError(
                    symbol=symbol, error_message="Rate limit exceeded - too many requests"
                )

            # Handle other HTTP errors
            if response.status_code != 200:
                return CryptoError(
                    symbol=symbol,
                    error_message=f"HTTP {response.status_code}: {response.reason_phrase}",
                )

            # Parse JSON response
            data = response.json()
            return _parse_crypto_data(data, symbol)

    except TimeoutError:
        return CryptoError(symbol=symbol, error_message=f"Request timed out after {timeout}s")
    except httpx.ConnectError:
        return CryptoError(symbol=symbol, error_message="Network error - check connection")
    except httpx.RequestError as e:
        return CryptoError(symbol=symbol, error_message=f"Request failed: {str(e)}")
    except Exception as e:
        return CryptoError(symbol=symbol, error_message=f"Failed to fetch quote: {str(e)}")


def _parse_crypto_data(data: dict[str, object], symbol: str) -> CryptoResult:
    """
    Parse CoinGecko API response into CryptoQuote.

    Args:
        data: JSON response from CoinGecko API
        symbol: Original symbol for error messages

    Returns:
        CryptoQuote on success, CryptoError on failure
    """
    try:
        # Extract market data
        market_data = data.get("market_data")
        if not isinstance(market_data, dict):
            return CryptoError(symbol=symbol, error_message="Missing market data in response")

        # Extract price in USD
        current_price = market_data.get("current_price")
        if not isinstance(current_price, dict):
            return CryptoError(symbol=symbol, error_message="Missing price data in response")

        price_usd = current_price.get("usd")
        if price_usd is None:
            return CryptoError(symbol=symbol, error_message="Missing USD price in response")

        # Extract 24h change percentage
        change_24h = market_data.get("price_change_percentage_24h")
        if change_24h is None:
            change_24h = 0.0

        # Extract market cap
        market_cap = market_data.get("market_cap")
        market_cap_usd = 0
        if isinstance(market_cap, dict):
            market_cap_usd = int(market_cap.get("usd", 0))

        # Extract 24h volume
        volume_24h = market_data.get("total_volume")
        volume_24h_usd = 0.0
        if isinstance(volume_24h, dict):
            volume_24h_usd = float(volume_24h.get("usd", 0.0))

        # Extract name
        name = data.get("name")
        if not isinstance(name, str):
            name = None

        return CryptoQuote(
            symbol=symbol,
            price_usd=float(price_usd),
            change_24h_percent=float(change_24h),
            market_cap_usd=market_cap_usd,
            volume_24h_usd=volume_24h_usd,
            name=name,
        )

    except (KeyError, ValueError, TypeError) as e:
        return CryptoError(symbol=symbol, error_message=f"Failed to parse response: {str(e)}")


async def fetch_crypto_info(
    symbol: str, timeout: float = 10.0, max_retries: int = 3
) -> CryptoInfoResult:
    """
    Fetch extended crypto information for the info panel.

    Args:
        symbol: Crypto symbol (e.g., 'BTC', 'ETH')
        timeout: Maximum time to wait for response in seconds
        max_retries: Maximum number of retries on rate limit (429)

    Returns:
        CryptoInfo on success, CryptoInfoError on failure

    Note:
        Handles rate limiting with exponential backoff.
        Returns full info dict with description, website, genesis date, etc.
    """
    symbol = symbol.upper().strip()

    # Map symbol to CoinGecko ID
    coin_id = SYMBOL_TO_ID.get(symbol)
    if coin_id is None:
        return CryptoInfoError(symbol=symbol, error_message=f"Unknown crypto symbol: {symbol}")

    # Retry loop for rate limiting
    last_error: CryptoInfoError | None = None
    for attempt in range(max_retries):
        try:
            result = await _fetch_info_with_timeout(coin_id, symbol, timeout)

            # Check if we got a rate limit error
            if isinstance(result, CryptoInfoError) and "rate limit" in result.error_message.lower():
                last_error = result
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s...
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                # Last attempt failed with rate limit
                break
            return result

        except Exception as e:
            return CryptoInfoError(symbol=symbol, error_message=f"Unexpected error: {str(e)}")

    # If we exhausted retries on rate limit
    if last_error:
        return CryptoInfoError(
            symbol=symbol, error_message=f"Rate limit exceeded after {max_retries} retries"
        )
    # Shouldn't reach here, but satisfy type checker
    return CryptoInfoError(symbol=symbol, error_message="Unknown error")  # pragma: no cover


async def _fetch_info_with_timeout(coin_id: str, symbol: str, timeout: float) -> CryptoInfoResult:
    """
    Fetch crypto info with timeout handling.

    Args:
        coin_id: CoinGecko coin ID
        symbol: Original symbol for error messages
        timeout: Request timeout in seconds

    Returns:
        CryptoInfo on success, CryptoInfoError on failure
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await asyncio.wait_for(
                client.get(
                    f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                    params={
                        "localization": "true",
                        "tickers": "false",
                        "market_data": "false",
                        "community_data": "false",
                        "developer_data": "false",
                        "sparkline": "false",
                    },
                ),
                timeout=timeout,
            )

            # Handle rate limiting
            if response.status_code == 429:
                return CryptoInfoError(
                    symbol=symbol, error_message="Rate limit exceeded - too many requests"
                )

            # Handle other HTTP errors
            if response.status_code != 200:
                return CryptoInfoError(
                    symbol=symbol,
                    error_message=f"HTTP {response.status_code}: {response.reason_phrase}",
                )

            # Parse JSON response
            data = response.json()

            # Validate we got data
            if not isinstance(data, dict):
                return CryptoInfoError(symbol=symbol, error_message="Invalid response format")

            # Return the full info dict
            return CryptoInfo(symbol=symbol, info=data)

    except TimeoutError:
        return CryptoInfoError(symbol=symbol, error_message=f"Request timed out after {timeout}s")
    except httpx.ConnectError:
        return CryptoInfoError(symbol=symbol, error_message="Network error - check connection")
    except httpx.RequestError as e:
        return CryptoInfoError(symbol=symbol, error_message=f"Request failed: {str(e)}")
    except Exception as e:
        return CryptoInfoError(symbol=symbol, error_message=f"Failed to fetch info: {str(e)}")
