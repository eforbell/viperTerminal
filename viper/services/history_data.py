"""Historical price data service using yfinance and CoinGecko."""

import asyncio
from dataclasses import dataclass
from datetime import datetime

import httpx
import yfinance as yf  # type: ignore[import-untyped]

from viper.services.crypto import SYMBOL_TO_ID


@dataclass
class HistoricalData:
    """Historical price data with full OHLCV."""

    ticker: str
    dates: list[datetime]
    prices: list[float]  # Closing prices
    volumes: list[int]
    highs: list[float]
    lows: list[float]
    opens: list[float]
    period: str  # e.g., "1W", "1M", etc.
    interval: str  # e.g., "1d", "1h"


@dataclass
class HistoricalStats:
    """Aggregated statistics for a historical period."""

    period_high: float
    period_low: float
    change_percent: float  # From start to end of period
    avg_volume: float
    num_data_points: int


@dataclass
class HistoricalDataError:
    """Error result from historical data fetch."""

    ticker: str
    error_message: str


# Type alias for result
HistoricalResult = HistoricalData | HistoricalDataError


# Period mapping: user-facing period -> yfinance period string
PERIOD_MAP: dict[str, str] = {
    "1W": "5d",  # yfinance doesn't have 1W, use 5d
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "2Y": "2y",
    "5Y": "5y",
    "MAX": "max",
}

# Interval selection based on period
INTERVAL_MAP: dict[str, str] = {
    "1W": "1d",
    "1M": "1d",
    "3M": "1d",
    "6M": "1d",
    "1Y": "1d",
    "2Y": "1wk",
    "5Y": "1wk",
    "MAX": "1mo",
}

# CoinGecko period mapping: user period -> days parameter
COINGECKO_DAYS_MAP: dict[str, str] = {
    "1W": "7",
    "1M": "30",
    "3M": "90",
    "6M": "180",
    "1Y": "365",
    "2Y": "730",
    "5Y": "1825",
    "MAX": "max",
}


def _is_crypto_ticker(ticker: str) -> bool:
    """
    Determine if ticker is a cryptocurrency symbol.

    Args:
        ticker: Ticker symbol to check

    Returns:
        True if ticker is in SYMBOL_TO_ID mapping, False otherwise
    """
    return ticker.upper() in SYMBOL_TO_ID


async def fetch_historical_data(
    ticker: str, period: str = "1M", timeout: float = 10.0, max_retries: int = 3
) -> HistoricalResult:
    """
    Fetch historical price data for the given ticker symbol.

    Auto-detects whether ticker is a stock or cryptocurrency and uses
    appropriate data source (yfinance for stocks, CoinGecko for crypto).

    Args:
        ticker: Ticker symbol (e.g., 'AAPL', 'BTC', 'ETH')
        period: Time period ('1W', '1M', '3M', '6M', '1Y', '2Y', '5Y', 'MAX')
        timeout: Maximum time to wait for response in seconds
        max_retries: Maximum number of retries on rate limit (for crypto)

    Returns:
        HistoricalData on success, HistoricalDataError on failure

    Note:
        - Uses yfinance for stock data (blocking call via executor)
        - Uses CoinGecko API for crypto data (async HTTP)
        - Handles rate limiting with exponential backoff for crypto
    """
    ticker = ticker.upper().strip()
    period = period.upper().strip()

    # Validate period
    if period not in PERIOD_MAP:
        return HistoricalDataError(
            ticker=ticker,
            error_message=f"Invalid period: {period}. Must be one of {list(PERIOD_MAP.keys())}",
        )

    # Auto-detect asset type and route to appropriate data source
    if _is_crypto_ticker(ticker):
        return await _fetch_crypto_historical(ticker, period, timeout, max_retries)
    else:
        return await _fetch_stock_historical(ticker, period, timeout)


async def _fetch_stock_historical(
    ticker: str, period: str, timeout: float
) -> HistoricalResult:
    """
    Fetch stock historical data via yfinance.

    Args:
        ticker: Stock ticker symbol
        period: Normalized period (e.g., '1M', '1Y')
        timeout: Request timeout

    Returns:
        HistoricalData on success, HistoricalDataError on failure
    """
    try:
        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_sync, ticker, period), timeout=timeout
        )
    except TimeoutError:
        return HistoricalDataError(
            ticker=ticker, error_message=f"Request timed out after {timeout}s"
        )
    except Exception as e:
        return HistoricalDataError(ticker=ticker, error_message=f"Unexpected error: {str(e)}")


def _fetch_sync(ticker: str, period: str) -> HistoricalResult:
    """
    Synchronous fetch operation. Called from executor.

    Args:
        ticker: Stock ticker symbol
        period: Normalized period (e.g., '1M', '1Y')

    Returns:
        HistoricalData on success, HistoricalDataError on failure
    """
    try:
        stock = yf.Ticker(ticker)

        # Map user period to yfinance period
        yf_period = PERIOD_MAP[period]
        interval = INTERVAL_MAP[period]

        # Fetch historical data
        hist = stock.history(period=yf_period, interval=interval)

        # Check if we got any data
        if hist is None or hist.empty:
            # This could be a new IPO, delisted stock, or invalid ticker
            return HistoricalDataError(
                ticker=ticker, error_message=f"No historical data available for period {period}"
            )

        # Extract OHLCV data
        dates = [ts.to_pydatetime() for ts in hist.index]
        prices = hist["Close"].tolist()
        volumes = [int(v) for v in hist["Volume"].tolist()]
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        opens = hist["Open"].tolist()

        # Validate we got data
        if not dates or not prices:
            return HistoricalDataError(
                ticker=ticker, error_message=f"No historical data available for period {period}"
            )

        return HistoricalData(
            ticker=ticker,
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=highs,
            lows=lows,
            opens=opens,
            period=period,
            interval=interval,
        )

    except Exception as e:
        # Handle all errors gracefully - return error result, not exception
        error_msg = str(e)
        if "404" in error_msg or "No data found" in error_msg:
            return HistoricalDataError(ticker=ticker, error_message="Invalid ticker symbol")
        if "Connection" in error_msg or "Network" in error_msg:
            return HistoricalDataError(
                ticker=ticker, error_message="Network error - check connection"
            )
        return HistoricalDataError(
            ticker=ticker, error_message=f"Failed to fetch historical data: {error_msg}"
        )


async def _fetch_crypto_historical(
    ticker: str, period: str, timeout: float, max_retries: int
) -> HistoricalResult:
    """
    Fetch crypto historical data via CoinGecko market_chart endpoint.

    Args:
        ticker: Crypto symbol (e.g., 'BTC', 'ETH')
        period: Normalized period (e.g., '1M', '1Y')
        timeout: Request timeout
        max_retries: Maximum number of retries on rate limit

    Returns:
        HistoricalData on success, HistoricalDataError on failure

    Note:
        Uses CoinGecko /coins/{id}/market_chart endpoint with exponential
        backoff on rate limit errors (429).
    """
    # Get CoinGecko coin ID
    coin_id = SYMBOL_TO_ID.get(ticker)
    if coin_id is None:
        return HistoricalDataError(
            ticker=ticker, error_message=f"Unknown crypto symbol: {ticker}"
        )

    # Get days parameter for CoinGecko
    days = COINGECKO_DAYS_MAP[period]

    # Retry loop for rate limiting
    last_error: HistoricalDataError | None = None
    for attempt in range(max_retries):
        try:
            result = await _fetch_crypto_with_timeout(coin_id, ticker, period, days, timeout)

            # Check if we got a rate limit error
            if isinstance(result, HistoricalDataError) and "rate limit" in result.error_message.lower():
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
            return HistoricalDataError(ticker=ticker, error_message=f"Unexpected error: {str(e)}")

    # If we exhausted retries on rate limit
    if last_error:
        return HistoricalDataError(
            ticker=ticker, error_message=f"Rate limit exceeded after {max_retries} retries"
        )
    # Shouldn't reach here, but satisfy type checker
    return HistoricalDataError(ticker=ticker, error_message="Unknown error")  # pragma: no cover


async def _fetch_crypto_with_timeout(
    coin_id: str, ticker: str, period: str, days: str, timeout: float
) -> HistoricalResult:
    """
    Fetch crypto market chart data with timeout handling.

    Args:
        coin_id: CoinGecko coin ID
        ticker: Original ticker symbol for error messages
        period: User-facing period (e.g., '1M')
        days: Days parameter for CoinGecko API
        timeout: Request timeout

    Returns:
        HistoricalData on success, HistoricalDataError on failure
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await asyncio.wait_for(
                client.get(
                    f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
                    params={"vs_currency": "usd", "days": days},
                ),
                timeout=timeout,
            )

            # Handle rate limiting
            if response.status_code == 429:
                return HistoricalDataError(
                    ticker=ticker, error_message="Rate limit exceeded - too many requests"
                )

            # Handle other HTTP errors
            if response.status_code != 200:
                return HistoricalDataError(
                    ticker=ticker,
                    error_message=f"HTTP {response.status_code}: {response.reason_phrase}",
                )

            # Parse JSON response
            data = response.json()
            return _parse_coingecko_chart(data, ticker, period)

    except TimeoutError:
        return HistoricalDataError(ticker=ticker, error_message=f"Request timed out after {timeout}s")
    except httpx.ConnectError:
        return HistoricalDataError(ticker=ticker, error_message="Network error - check connection")
    except httpx.RequestError as e:
        return HistoricalDataError(ticker=ticker, error_message=f"Request failed: {str(e)}")
    except Exception as e:
        return HistoricalDataError(ticker=ticker, error_message=f"Failed to fetch chart: {str(e)}")


def _parse_coingecko_chart(data: dict[str, object], ticker: str, period: str) -> HistoricalResult:
    """
    Parse CoinGecko market_chart API response into HistoricalData.

    Args:
        data: JSON response from CoinGecko market_chart endpoint
        ticker: Ticker symbol
        period: User-facing period (e.g., '1M')

    Returns:
        HistoricalData on success, HistoricalDataError on failure

    Note:
        CoinGecko returns: {"prices": [[timestamp_ms, price], ...], "total_volumes": [...]}
        We extract timestamps, prices, and volumes. For OHLC, we use price for all fields
        since market_chart doesn't provide separate OHLC data.
    """
    try:
        # Extract prices array
        prices_data = data.get("prices")
        if not isinstance(prices_data, list) or not prices_data:
            return HistoricalDataError(ticker=ticker, error_message="No price data in response")

        # Extract volumes array
        volumes_data = data.get("total_volumes")
        if not isinstance(volumes_data, list):
            volumes_data = []

        # Parse timestamps and prices
        dates: list[datetime] = []
        prices: list[float] = []
        for item in prices_data:
            if isinstance(item, list) and len(item) >= 2:
                timestamp_ms = item[0]
                price = item[1]
                # Convert millisecond timestamp to datetime
                dates.append(datetime.fromtimestamp(timestamp_ms / 1000))
                prices.append(float(price))

        # Parse volumes (aligned by timestamp)
        volumes: list[int] = []
        for item in volumes_data:
            if isinstance(item, list) and len(item) >= 2:
                volume = item[1]
                volumes.append(int(volume))

        # Pad volumes if we got fewer volume points than price points
        while len(volumes) < len(prices):
            volumes.append(0)

        # Validate we got data
        if not dates or not prices:
            return HistoricalDataError(
                ticker=ticker, error_message=f"No historical data available for period {period}"
            )

        # For crypto, we don't have separate OHLC, so we use price for all
        # This is acceptable for charting purposes
        highs = prices.copy()
        lows = prices.copy()
        opens = prices.copy()

        # Determine interval based on data density
        # CoinGecko returns different granularities based on days parameter
        if len(dates) > 1:
            time_diff = (dates[-1] - dates[0]).total_seconds()
            avg_interval_seconds = time_diff / len(dates)
            # Rough heuristic for interval label
            if avg_interval_seconds < 3600:
                interval = "5m"
            elif avg_interval_seconds < 86400:
                interval = "1h"
            else:
                interval = "1d"
        else:
            interval = "1d"

        return HistoricalData(
            ticker=ticker,
            dates=dates,
            prices=prices,
            volumes=volumes,
            highs=highs,
            lows=lows,
            opens=opens,
            period=period,
            interval=interval,
        )

    except (KeyError, ValueError, TypeError) as e:
        return HistoricalDataError(ticker=ticker, error_message=f"Failed to parse response: {str(e)}")


def calculate_stats(data: HistoricalData) -> HistoricalStats:
    """
    Calculate aggregated statistics for historical data.

    Args:
        data: HistoricalData object

    Returns:
        HistoricalStats with computed metrics
    """
    period_high = max(data.highs)
    period_low = min(data.lows)

    # Calculate percent change from first to last price
    if len(data.prices) >= 2:
        first_price = data.prices[0]
        last_price = data.prices[-1]
        change_percent = ((last_price - first_price) / first_price) * 100 if first_price != 0 else 0.0
    else:
        change_percent = 0.0

    # Calculate average volume
    avg_volume = sum(data.volumes) / len(data.volumes) if data.volumes else 0.0

    return HistoricalStats(
        period_high=period_high,
        period_low=period_low,
        change_percent=change_percent,
        avg_volume=avg_volume,
        num_data_points=len(data.prices),
    )
