"""Technical indicator calculations for chart analysis.

This module provides pure functions for calculating technical indicators
like Simple Moving Average (SMA), Exponential Moving Average (EMA), and
Relative Strength Index (RSI).

All functions return lists with None values where calculations can't be performed
(e.g., first N-1 values for an N-period moving average).
"""


def calculate_sma(prices: list[float], period: int) -> list[float | None]:
    """Calculate Simple Moving Average over a given period.

    SMA is the arithmetic mean of the last N prices, where N = period.

    Args:
        prices: List of price values to calculate SMA over
        period: Number of periods to average (e.g., 20, 50, 200)

    Returns:
        List of SMA values with same length as prices.
        First (period-1) values are None since SMA can't be calculated.

    Examples:
        >>> calculate_sma([1, 2, 3, 4, 5], 3)
        [None, None, 2.0, 3.0, 4.0]

        >>> calculate_sma([10, 20, 30], 5)
        [None, None, None]  # Not enough data for period=5
    """
    if period <= 0:
        raise ValueError("Period must be positive")

    if not prices:
        return []

    result: list[float | None] = []

    for i in range(len(prices)):
        # Not enough data points yet for this period
        if i < period - 1:
            result.append(None)
        else:
            # Calculate average of last 'period' prices
            window = prices[i - period + 1 : i + 1]
            sma_value = sum(window) / period
            result.append(sma_value)

    return result
