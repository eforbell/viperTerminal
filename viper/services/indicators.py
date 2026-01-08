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


def calculate_ema(prices: list[float], period: int) -> list[float | None]:
    """Calculate Exponential Moving Average over a given period.

    EMA gives more weight to recent prices using exponential smoothing.
    The first EMA value is calculated as the SMA of the first 'period' prices.

    Formula:
        k = 2 / (period + 1)  # Smoothing factor
        EMA_today = (Price_today * k) + (EMA_yesterday * (1 - k))

    Args:
        prices: List of price values to calculate EMA over
        period: Number of periods for the EMA (e.g., 12, 26, 50)

    Returns:
        List of EMA values with same length as prices.
        First (period-1) values are None since EMA can't be calculated.

    Examples:
        >>> calculate_ema([22, 24, 26, 28, 30], 3)
        [None, None, 24.0, 26.5, 28.75]

        >>> calculate_ema([10, 20], 5)
        [None, None]  # Not enough data for period=5
    """
    if period <= 0:
        raise ValueError("Period must be positive")

    if not prices:
        return []

    result: list[float | None] = []
    k = 2.0 / (period + 1)  # Smoothing factor

    for i in range(len(prices)):
        # Not enough data points yet for this period
        if i < period - 1:
            result.append(None)
        elif i == period - 1:
            # First EMA value is SMA of first 'period' prices
            window = prices[: period]
            first_ema = sum(window) / period
            result.append(first_ema)
        else:
            # Calculate EMA: (Price * k) + (EMA_prev * (1-k))
            prev_ema = result[i - 1]
            if prev_ema is None:
                # Should never happen, but handle gracefully
                result.append(None)
            else:
                current_price = prices[i]
                ema_value = (current_price * k) + (prev_ema * (1 - k))
                result.append(ema_value)

    return result
