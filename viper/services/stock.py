"""Stock quote fetching service using yfinance."""

import asyncio
from dataclasses import dataclass

import yfinance as yf  # type: ignore[import-untyped]


@dataclass
class StockQuote:
    """Stock quote data."""

    ticker: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: int
    high_52w: float
    low_52w: float
    name: str | None = None


@dataclass
class StockError:
    """Error result from stock fetch."""

    ticker: str
    error_message: str


# Type alias for result
StockResult = StockQuote | StockError


async def fetch_stock_quote(ticker: str, timeout: float = 10.0) -> StockResult:
    """
    Fetch stock quote data for the given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        timeout: Maximum time to wait for response in seconds

    Returns:
        StockQuote on success, StockError on failure

    Note:
        This function uses run_in_executor to not block the UI event loop.
        All network calls are performed in a thread pool.
    """
    ticker = ticker.upper().strip()

    try:
        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_sync, ticker), timeout=timeout
        )
    except TimeoutError:
        return StockError(ticker=ticker, error_message=f"Request timed out after {timeout}s")
    except Exception as e:
        return StockError(ticker=ticker, error_message=f"Unexpected error: {str(e)}")


def _fetch_sync(ticker: str) -> StockResult:
    """
    Synchronous fetch operation. Called from executor.

    Args:
        ticker: Stock ticker symbol

    Returns:
        StockQuote on success, StockError on failure
    """
    try:
        stock = yf.Ticker(ticker)

        # Use fast_info for speed (as per PRD notes)
        info = stock.fast_info

        # Extract required fields
        # fast_info provides: last_price, open, previous_close, currency, market_cap, etc.
        price = info.get("last_price")
        previous_close = info.get("previous_close")

        # Validate we got the essential data
        if price is None or previous_close is None:
            return StockError(ticker=ticker, error_message="Invalid ticker or no data available")

        # Calculate change and change percent
        change = price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close != 0 else 0.0

        # Get additional fields with defaults
        volume = info.get("last_volume", 0)
        market_cap = info.get("market_cap", 0)

        # Get 52-week high/low from regular info (not available in fast_info)
        # We'll try to get it, but fall back to current price if not available
        try:
            regular_info = stock.info
            high_52w = regular_info.get("fiftyTwoWeekHigh", price)
            low_52w = regular_info.get("fiftyTwoWeekLow", price)
            name = regular_info.get("longName")
        except Exception:
            # If regular info fails, use price as fallback for 52w range
            high_52w = price
            low_52w = price
            name = None

        return StockQuote(
            ticker=ticker,
            price=price,
            change=change,
            change_percent=change_percent,
            volume=int(volume),
            market_cap=int(market_cap),
            high_52w=high_52w,
            low_52w=low_52w,
            name=name,
        )

    except Exception as e:
        # Handle all errors gracefully - return error result, not exception
        error_msg = str(e)
        if "404" in error_msg or "No data found" in error_msg:
            return StockError(ticker=ticker, error_message="Invalid ticker symbol")
        if "Connection" in error_msg or "Network" in error_msg:
            return StockError(ticker=ticker, error_message="Network error - check connection")
        return StockError(ticker=ticker, error_message=f"Failed to fetch quote: {error_msg}")
