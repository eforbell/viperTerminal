"""Historical price data service using yfinance."""

import asyncio
from dataclasses import dataclass
from datetime import datetime

import yfinance as yf  # type: ignore[import-untyped]


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


async def fetch_historical_data(
    ticker: str, period: str = "1M", timeout: float = 10.0
) -> HistoricalResult:
    """
    Fetch historical price data for the given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        period: Time period ('1W', '1M', '3M', '6M', '1Y', '2Y', '5Y', 'MAX')
        timeout: Maximum time to wait for response in seconds

    Returns:
        HistoricalData on success, HistoricalDataError on failure

    Note:
        This function uses run_in_executor to not block the UI event loop.
        All network calls are performed in a thread pool.
    """
    ticker = ticker.upper().strip()
    period = period.upper().strip()

    # Validate period
    if period not in PERIOD_MAP:
        return HistoricalDataError(
            ticker=ticker,
            error_message=f"Invalid period: {period}. Must be one of {list(PERIOD_MAP.keys())}",
        )

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
