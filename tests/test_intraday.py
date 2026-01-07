"""Tests for intraday data fetching service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from viper.services.stock import (
    IntradayData,
    IntradayError,
    fetch_intraday_data,
)


@pytest.mark.asyncio
async def test_fetch_intraday_data_success():
    """Test successful intraday data fetch."""
    # Mock yfinance Ticker
    mock_ticker = MagicMock()

    # Create mock DataFrame with realistic intraday data
    timestamps = pd.date_range("2024-01-01 09:30", periods=5, freq="5min")
    mock_hist = pd.DataFrame(
        {"Close": [150.0, 151.0, 150.5, 152.0, 151.5]}, index=timestamps
    )
    mock_ticker.history.return_value = mock_hist

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("AAPL", period="1d", interval="5m")

    assert isinstance(result, IntradayData)
    assert result.ticker == "AAPL"
    assert len(result.prices) == 5
    assert result.prices == [150.0, 151.0, 150.5, 152.0, 151.5]
    assert len(result.timestamps) == 5
    assert result.interval == "5m"
    assert result.period == "1d"


@pytest.mark.asyncio
async def test_fetch_intraday_data_empty_dataframe():
    """Test handling of empty DataFrame (no data available)."""
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()  # Empty DataFrame

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("INVALID", period="1d", interval="5m")

    assert isinstance(result, IntradayError)
    assert result.ticker == "INVALID"
    assert "No intraday data available" in result.error_message


@pytest.mark.asyncio
async def test_fetch_intraday_data_none_dataframe():
    """Test handling of None DataFrame."""
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = None

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("INVALID", period="1d", interval="5m")

    assert isinstance(result, IntradayError)
    assert result.ticker == "INVALID"
    assert "No intraday data available" in result.error_message


@pytest.mark.asyncio
async def test_fetch_intraday_data_empty_prices():
    """Test handling of DataFrame with no Close prices."""
    mock_ticker = MagicMock()
    # DataFrame with columns but no data
    mock_hist = pd.DataFrame({"Close": []})
    mock_ticker.history.return_value = mock_hist

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("TEST", period="1d", interval="5m")

    assert isinstance(result, IntradayError)
    assert result.ticker == "TEST"
    assert "No intraday data available" in result.error_message


@pytest.mark.asyncio
async def test_fetch_intraday_data_network_error():
    """Test handling of network errors."""
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = ConnectionError("Network error")

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("AAPL", period="1d", interval="5m")

    assert isinstance(result, IntradayError)
    assert result.ticker == "AAPL"
    assert "Network error" in result.error_message


@pytest.mark.asyncio
async def test_fetch_intraday_data_timeout():
    """Test timeout handling."""
    mock_ticker = MagicMock()

    # Simulate a slow operation
    def slow_history(*args, **kwargs):
        import time

        time.sleep(2)
        return pd.DataFrame()

    mock_ticker.history.side_effect = slow_history

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("AAPL", period="1d", interval="5m", timeout=0.1)

    assert isinstance(result, IntradayError)
    assert result.ticker == "AAPL"
    assert "timed out" in result.error_message


@pytest.mark.asyncio
async def test_fetch_intraday_data_404_error():
    """Test handling of 404 error (invalid ticker)."""
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = Exception("404 Client Error")

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("INVALID", period="1d", interval="5m")

    assert isinstance(result, IntradayError)
    assert result.ticker == "INVALID"
    assert "Invalid ticker symbol" in result.error_message


@pytest.mark.asyncio
async def test_fetch_intraday_data_generic_exception():
    """Test handling of generic exceptions."""
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = ValueError("Something went wrong")

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("AAPL", period="1d", interval="5m")

    assert isinstance(result, IntradayError)
    assert result.ticker == "AAPL"
    assert "Failed to fetch intraday data" in result.error_message
    assert "Something went wrong" in result.error_message


@pytest.mark.asyncio
async def test_fetch_intraday_data_ticker_normalization():
    """Test that ticker symbols are normalized (uppercase, stripped)."""
    mock_ticker = MagicMock()

    timestamps = pd.date_range("2024-01-01 09:30", periods=3, freq="5min")
    mock_hist = pd.DataFrame({"Close": [100.0, 101.0, 102.0]}, index=timestamps)
    mock_ticker.history.return_value = mock_hist

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker) as mock_yf:
        result = await fetch_intraday_data("  aapl  ", period="1d", interval="5m")

    # Verify Ticker was called with normalized symbol
    mock_yf.assert_called_once_with("AAPL")

    assert isinstance(result, IntradayData)
    assert result.ticker == "AAPL"


@pytest.mark.asyncio
async def test_fetch_intraday_data_different_periods():
    """Test fetching with different period and interval parameters."""
    mock_ticker = MagicMock()

    timestamps = pd.date_range("2024-01-01 09:30", periods=10, freq="1h")
    mock_hist = pd.DataFrame(
        {"Close": [i * 10.0 for i in range(10)]}, index=timestamps
    )
    mock_ticker.history.return_value = mock_hist

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("TSLA", period="5d", interval="1h")

    assert isinstance(result, IntradayData)
    assert result.ticker == "TSLA"
    assert result.period == "5d"
    assert result.interval == "1h"
    assert len(result.prices) == 10

    # Verify history was called with correct parameters
    mock_ticker.history.assert_called_once_with(period="5d", interval="1h")


@pytest.mark.asyncio
async def test_fetch_intraday_data_timestamp_conversion():
    """Test that pandas timestamps are converted to Python datetime objects."""
    mock_ticker = MagicMock()

    timestamps = pd.date_range("2024-01-01 09:30", periods=3, freq="5min")
    mock_hist = pd.DataFrame({"Close": [100.0, 101.0, 102.0]}, index=timestamps)
    mock_ticker.history.return_value = mock_hist

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_intraday_data("AAPL", period="1d", interval="5m")

    assert isinstance(result, IntradayData)
    # Verify all timestamps are Python datetime objects
    for ts in result.timestamps:
        assert isinstance(ts, datetime)
