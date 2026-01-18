"""Options data fetching service using yfinance."""

import asyncio
import math
from dataclasses import dataclass
from typing import Any

import yfinance as yf  # type: ignore[import-untyped]


@dataclass
class OptionsError:
    """Error result from options fetch."""

    ticker: str
    error_message: str


@dataclass
class OptionContract:
    """Individual option contract data."""

    strike: float
    bid: float
    ask: float
    last_price: float
    volume: int
    open_interest: int
    implied_volatility: float
    in_the_money: bool


@dataclass
class OptionsChain:
    """Complete options chain for a given expiration."""

    ticker: str
    expiration: str
    calls: list[OptionContract]
    puts: list[OptionContract]


# Type aliases for results
OptionsExpirationsResult = list[str] | OptionsError
OptionsChainResult = OptionsChain | OptionsError


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


async def fetch_option_chain(
    ticker: str, expiration: str, timeout: float = 10.0
) -> OptionsChainResult:
    """
    Fetch option chain data for the given ticker and expiration date.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        expiration: Expiration date in YYYY-MM-DD format
        timeout: Maximum time to wait for response in seconds

    Returns:
        OptionsChain with calls and puts on success, OptionsError on failure

    Note:
        This function uses run_in_executor to not block the UI event loop.
        All network calls are performed in a thread pool.
    """
    ticker = ticker.upper().strip()

    try:
        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_chain_sync, ticker, expiration),
            timeout=timeout,
        )
    except TimeoutError:
        return OptionsError(ticker=ticker, error_message=f"Request timed out after {timeout}s")
    except Exception as e:
        return OptionsError(ticker=ticker, error_message=f"Unexpected error: {str(e)}")


def _fetch_chain_sync(ticker: str, expiration: str) -> OptionsChainResult:
    """
    Synchronous fetch operation for option chain. Called from executor.

    Args:
        ticker: Stock ticker symbol
        expiration: Expiration date in YYYY-MM-DD format

    Returns:
        OptionsChain on success, OptionsError on failure
    """
    try:
        stock = yf.Ticker(ticker)

        # Get option chain for specified expiration
        chain = stock.option_chain(expiration)

        # Convert DataFrames to list of OptionContract dataclasses
        calls = _parse_contracts_dataframe(chain.calls)
        puts = _parse_contracts_dataframe(chain.puts)

        return OptionsChain(ticker=ticker, expiration=expiration, calls=calls, puts=puts)

    except Exception as e:
        # Handle all errors gracefully - return error result, not exception
        error_msg = str(e)
        if "404" in error_msg or "No data found" in error_msg:
            return OptionsError(ticker=ticker, error_message="Invalid ticker symbol")
        if "not in list" in error_msg.lower() or "expiration" in error_msg.lower():
            return OptionsError(
                ticker=ticker, error_message=f"Invalid expiration date: {expiration}"
            )
        if "Connection" in error_msg or "Network" in error_msg:
            return OptionsError(
                ticker=ticker, error_message="Network error - check connection"
            )
        return OptionsError(
            ticker=ticker, error_message=f"Failed to fetch option chain: {error_msg}"
        )


def _parse_contracts_dataframe(df: Any) -> list[OptionContract]:
    """
    Parse pandas DataFrame from yfinance into list of OptionContract dataclasses.

    Args:
        df: DataFrame with columns: strike, bid, ask, lastPrice, volume,
            openInterest, impliedVolatility, inTheMoney

    Returns:
        List of OptionContract instances

    Note:
        Handles None/NaN values by defaulting to 0 for numeric fields and False for boolean.
    """
    contracts: list[OptionContract] = []

    for _, row in df.iterrows():
        # Extract values with safe defaults for NaN/None
        # Helper to check if value is NaN or None
        def safe_float(val: Any, default: float = 0.0) -> float:
            if val is None:
                return default
            try:
                f = float(val)
                return default if math.isnan(f) else f
            except (ValueError, TypeError):
                return default

        def safe_int(val: Any, default: int = 0) -> int:
            if val is None:
                return default
            try:
                f = float(val)
                return default if math.isnan(f) else int(f)
            except (ValueError, TypeError):
                return default

        strike = safe_float(row.get("strike", 0.0))
        bid = safe_float(row.get("bid", 0.0))
        ask = safe_float(row.get("ask", 0.0))
        last_price = safe_float(row.get("lastPrice", 0.0))
        volume = safe_int(row.get("volume", 0))
        open_interest = safe_int(row.get("openInterest", 0))
        implied_volatility = safe_float(row.get("impliedVolatility", 0.0))
        in_the_money = bool(row.get("inTheMoney", False))

        contract = OptionContract(
            strike=strike,
            bid=bid,
            ask=ask,
            last_price=last_price,
            volume=volume,
            open_interest=open_interest,
            implied_volatility=implied_volatility,
            in_the_money=in_the_money,
        )
        contracts.append(contract)

    return contracts
