"""Tests for error message formatting utilities."""

import asyncio

import httpx
import pytest

from viper.services.crypto import CryptoError
from viper.services.stock import StockError
from viper.utils.error_formatter import format_error_message, is_network_error


def test_format_stock_error() -> None:
    """Test formatting a StockError."""
    error = StockError("AAPL", "Invalid ticker or no data available")
    formatted = format_error_message(error)
    assert formatted == "Invalid ticker or no data available"


def test_format_crypto_error() -> None:
    """Test formatting a CryptoError."""
    error = CryptoError("INVALID", "Unknown cryptocurrency symbol")
    formatted = format_error_message(error)
    assert formatted == "Unknown cryptocurrency symbol"


def test_format_network_error_in_message() -> None:
    """Test formatting an error with 'network' keyword in message."""
    error = StockError("AAPL", "Network connection failed")
    formatted = format_error_message(error)
    assert "Network error:" in formatted
    assert "Check your connection and try again" in formatted


def test_format_timeout_error_in_message() -> None:
    """Test formatting an error with 'timeout' keyword in message."""
    error = CryptoError("BTC", "Request timeout exceeded")
    formatted = format_error_message(error)
    assert "Request timed out:" in formatted
    assert "Try again or check your connection" in formatted


def test_format_timed_out_error_in_message() -> None:
    """Test formatting an error with 'timed out' phrase in message."""
    error = StockError("AAPL", "Connection timed out")
    formatted = format_error_message(error)
    assert "Request timed out:" in formatted


def test_format_httpx_connect_error() -> None:
    """Test formatting an httpx ConnectError."""
    error = httpx.ConnectError("Failed to connect")
    formatted = format_error_message(error)
    assert "Network error:" in formatted
    assert "Unable to connect" in formatted
    assert "Check your internet connection" in formatted


def test_format_httpx_network_error() -> None:
    """Test formatting an httpx NetworkError."""
    error = httpx.NetworkError("Network unreachable")
    formatted = format_error_message(error)
    assert "Network error:" in formatted
    assert "Unable to connect" in formatted


def test_format_httpx_timeout_exception() -> None:
    """Test formatting an httpx TimeoutException."""
    error = httpx.TimeoutException("Request timed out")
    formatted = format_error_message(error)
    assert "Request timed out:" in formatted
    assert "server took too long" in formatted


def test_format_asyncio_timeout_error() -> None:
    """Test formatting an asyncio.TimeoutError."""
    error = asyncio.TimeoutError()
    formatted = format_error_message(error)
    assert "Request timed out:" in formatted
    assert "operation took too long" in formatted


def test_format_generic_exception() -> None:
    """Test formatting a generic exception."""
    error = ValueError("Some unexpected error")
    formatted = format_error_message(error)
    assert "Unexpected error:" in formatted
    assert "ValueError" in formatted
    assert "try again or check the logs" in formatted.lower()


def test_format_generic_exception_no_raw_message() -> None:
    """Test that generic exceptions don't expose raw error details."""
    error = RuntimeError("Internal implementation detail")
    formatted = format_error_message(error)
    # Should not contain the raw message
    assert "Internal implementation detail" not in formatted
    # Should contain the error type
    assert "RuntimeError" in formatted


def test_is_network_error_httpx_connect() -> None:
    """Test detecting httpx ConnectError as network error."""
    error = httpx.ConnectError("Failed to connect")
    assert is_network_error(error) is True


def test_is_network_error_httpx_network() -> None:
    """Test detecting httpx NetworkError as network error."""
    error = httpx.NetworkError("Network unreachable")
    assert is_network_error(error) is True


def test_is_network_error_httpx_timeout() -> None:
    """Test detecting httpx TimeoutException as network error."""
    error = httpx.TimeoutException("Timeout")
    assert is_network_error(error) is True


def test_is_network_error_asyncio_timeout() -> None:
    """Test detecting asyncio.TimeoutError as network error."""
    error = asyncio.TimeoutError()
    assert is_network_error(error) is True


def test_is_network_error_stock_error_with_network_keyword() -> None:
    """Test detecting StockError with 'network' keyword."""
    error = StockError("AAPL", "Network connection failed")
    assert is_network_error(error) is True


def test_is_network_error_crypto_error_with_timeout_keyword() -> None:
    """Test detecting CryptoError with 'timeout' keyword."""
    error = CryptoError("BTC", "Request timeout")
    assert is_network_error(error) is True


def test_is_network_error_crypto_error_with_offline_keyword() -> None:
    """Test detecting CryptoError with 'offline' keyword."""
    error = CryptoError("ETH", "Service is offline")
    assert is_network_error(error) is True


def test_is_network_error_stock_error_without_network_keywords() -> None:
    """Test that StockError without network keywords is not detected as network error."""
    error = StockError("INVALID", "Invalid ticker symbol")
    assert is_network_error(error) is False


def test_is_network_error_generic_exception() -> None:
    """Test that generic exceptions are not detected as network errors."""
    error = ValueError("Some error")
    assert is_network_error(error) is False


def test_is_network_error_case_insensitive() -> None:
    """Test that network error detection is case-insensitive."""
    error1 = StockError("AAPL", "NETWORK ERROR")
    error2 = CryptoError("BTC", "Connection TIMEOUT")
    assert is_network_error(error1) is True
    assert is_network_error(error2) is True
