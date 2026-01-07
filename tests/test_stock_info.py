"""Tests for stock info fetching service."""

from unittest.mock import MagicMock, patch

import pytest

from viper.services.stock import StockInfo, StockInfoError, fetch_stock_info


@pytest.mark.asyncio
async def test_fetch_stock_info_success():
    """Test successful stock info fetch."""
    # Mock yfinance Ticker
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": "Test description",
        "website": "https://example.com",
        "fullTimeEmployees": 100000,
    }

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_stock_info("AAPL")

    assert isinstance(result, StockInfo)
    assert result.ticker == "AAPL"
    assert result.info["sector"] == "Technology"
    assert result.info["industry"] == "Consumer Electronics"


@pytest.mark.asyncio
async def test_fetch_stock_info_normalizes_ticker():
    """Test that ticker is normalized to uppercase and stripped."""
    mock_ticker = MagicMock()
    mock_ticker.info = {"test": "data"}

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker) as mock_yf:
        result = await fetch_stock_info("  aapl  ")

    assert isinstance(result, StockInfo)
    assert result.ticker == "AAPL"
    mock_yf.assert_called_once_with("AAPL")


@pytest.mark.asyncio
async def test_fetch_stock_info_invalid_ticker():
    """Test handling of invalid ticker symbol."""
    mock_ticker = MagicMock()
    mock_ticker.info = None

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_stock_info("INVALID")

    assert isinstance(result, StockInfoError)
    assert result.ticker == "INVALID"
    assert "No information available" in result.error_message


@pytest.mark.asyncio
async def test_fetch_stock_info_empty_dict():
    """Test handling of empty info dict."""
    mock_ticker = MagicMock()
    mock_ticker.info = {}

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_stock_info("TEST")

    # Empty dict is still valid, should return StockInfo
    assert isinstance(result, StockInfo)
    assert result.ticker == "TEST"
    assert result.info == {}


@pytest.mark.asyncio
async def test_fetch_stock_info_404_error():
    """Test handling of 404 error (invalid ticker)."""
    mock_ticker = MagicMock()
    mock_ticker.info
    type(mock_ticker).info = property(lambda self: (_ for _ in ()).throw(Exception("404 Not Found")))

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_stock_info("NOTFOUND")

    assert isinstance(result, StockInfoError)
    assert result.ticker == "NOTFOUND"
    assert "Invalid ticker symbol" in result.error_message


@pytest.mark.asyncio
async def test_fetch_stock_info_network_error():
    """Test handling of network errors."""
    mock_ticker = MagicMock()
    type(mock_ticker).info = property(
        lambda self: (_ for _ in ()).throw(Exception("Connection error"))
    )

    with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
        result = await fetch_stock_info("AAPL")

    assert isinstance(result, StockInfoError)
    assert result.ticker == "AAPL"
    assert "Network error" in result.error_message


@pytest.mark.asyncio
async def test_fetch_stock_info_timeout():
    """Test handling of request timeout."""
    import time

    def slow_fetch(*args, **kwargs):
        time.sleep(2)
        return MagicMock(info={"test": "data"})

    with patch("viper.services.stock.yf.Ticker", side_effect=slow_fetch):
        result = await fetch_stock_info("AAPL", timeout=0.1)

    assert isinstance(result, StockInfoError)
    assert result.ticker == "AAPL"
    assert "timed out" in result.error_message


@pytest.mark.asyncio
async def test_fetch_stock_info_general_exception():
    """Test handling of general exceptions."""
    with patch("viper.services.stock.yf.Ticker", side_effect=Exception("Unknown error")):
        result = await fetch_stock_info("AAPL")

    assert isinstance(result, StockInfoError)
    assert result.ticker == "AAPL"
    assert "Failed to fetch info" in result.error_message
