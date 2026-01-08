"""Tests for crypto info fetching service using yfinance."""

from unittest.mock import MagicMock, patch

import pytest

from viper.services.crypto import CryptoInfo, CryptoInfoError, fetch_crypto_info


@pytest.mark.asyncio
async def test_fetch_crypto_info_success() -> None:
    """Test successful crypto info fetch."""
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "symbol": "BTC-USD",
        "longName": "Bitcoin USD",
        "description": "Bitcoin is a decentralized digital currency.",
        "website": "https://bitcoin.org",
    }

    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = await fetch_crypto_info("BTC")

    assert isinstance(result, CryptoInfo)
    assert result.symbol == "BTC"
    assert result.info["longName"] == "Bitcoin USD"
    assert result.info["website"] == "https://bitcoin.org"


@pytest.mark.asyncio
async def test_fetch_crypto_info_normalizes_symbol() -> None:
    """Test that symbol is normalized to uppercase and stripped."""
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "symbol": "BTC-USD",
        "longName": "Bitcoin USD",
    }

    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = await fetch_crypto_info("  btc  ")

    assert isinstance(result, CryptoInfo)
    assert result.symbol == "BTC"


@pytest.mark.asyncio
async def test_fetch_crypto_info_unknown_symbol() -> None:
    """Test unknown crypto symbol."""
    result = await fetch_crypto_info("UNKNOWN")

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "UNKNOWN"
    assert "Unknown crypto symbol" in result.error_message


@pytest.mark.asyncio
async def test_fetch_crypto_info_exception() -> None:
    """Test exception handling during info fetch."""

    def raise_exception(pair: str) -> None:
        raise RuntimeError("Network error")

    with patch("yfinance.Ticker", side_effect=raise_exception):
        result = await fetch_crypto_info("BTC")

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "BTC"
    assert "Failed to fetch info" in result.error_message


@pytest.mark.asyncio
async def test_fetch_crypto_info_empty_response() -> None:
    """Test empty info response."""
    mock_ticker = MagicMock()
    mock_ticker.info = {}

    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = await fetch_crypto_info("BTC")

    assert isinstance(result, CryptoInfoError)
    assert "Invalid response format" in result.error_message
