"""Options data fetching service using yfinance."""

import asyncio
from dataclasses import dataclass

import yfinance as yf  # type: ignore[import-untyped]


@dataclass
class OptionsError:
    """Error result from options fetch."""

    ticker: str
    error_message: str


# Type alias for result
OptionsExpirationsResult = list[str] | OptionsError


async def fetch_option_expirations(ticker: str, timeout: float = 10.0) -> OptionsExpirationsResult:
    """
    Fetch available option expiration dates for the given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        timeout: Maximum time to wait for response in seconds

    Returns:
        List of expiration date strings in YYYY-MM-DD format on success,
        OptionsError on failure

    Note:
        This function uses run_in_executor to not block the UI event loop.
        All network calls are performed in a thread pool.
    """
    ticker = ticker.upper().strip()

    try:
        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_expirations_sync, ticker), timeout=timeout
        )
    except TimeoutError:
        return OptionsError(ticker=ticker, error_message=f"Request timed out after {timeout}s")
    except Exception as e:
        return OptionsError(ticker=ticker, error_message=f"Unexpected error: {str(e)}")


def _fetch_expirations_sync(ticker: str) -> OptionsExpirationsResult:
    """
    Synchronous fetch operation for option expirations. Called from executor.

    Args:
        ticker: Stock ticker symbol

    Returns:
        List of expiration date strings on success, OptionsError on failure
    """
    try:
        stock = yf.Ticker(ticker)

        # Get available expiration dates
        # ticker.options returns a tuple of date strings or empty tuple
        expirations = stock.options

        # Check if ticker exists but has no options
        if expirations is None or len(expirations) == 0:
            # Try to verify ticker exists by checking fast_info
            try:
                _ = stock.fast_info.last_price
                # Ticker exists but has no options
                return OptionsError(
                    ticker=ticker, error_message="Ticker has no options available"
                )
            except (AttributeError, KeyError):
                # Ticker doesn't exist
                return OptionsError(ticker=ticker, error_message="Invalid ticker symbol")

        # Convert tuple to list and return
        return list(expirations)

    except Exception as e:
        # Handle all errors gracefully - return error result, not exception
        error_msg = str(e)
        if "404" in error_msg or "No data found" in error_msg:
            return OptionsError(ticker=ticker, error_message="Invalid ticker symbol")
        if "Connection" in error_msg or "Network" in error_msg:
            return OptionsError(
                ticker=ticker, error_message="Network error - check connection"
            )
        return OptionsError(
            ticker=ticker, error_message=f"Failed to fetch options: {error_msg}"
        )
