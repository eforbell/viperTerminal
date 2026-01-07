"""Error message formatting utilities."""

import asyncio

import httpx

from viper.services.crypto import CryptoError
from viper.services.stock import StockError


def format_error_message(error: StockError | CryptoError | Exception) -> str:
    """Format error messages in a user-friendly way.

    Args:
        error: The error to format (can be StockError, CryptoError, or Exception).

    Returns:
        A user-friendly error message string.
    """
    # Handle our custom error types
    if isinstance(error, (StockError, CryptoError)):
        message = error.error_message

        # Check for timeout (check specific "timed out" first, then "timeout")
        if "timeout" in message.lower() or "timed out" in message.lower():
            return f"Request timed out: {message}. Try again or check your connection."

        # Check for network-related errors in the message
        if any(
            keyword in message.lower() for keyword in ["network", "connection", "offline"]
        ):
            return f"Network error: {message}. Check your connection and try again."

        # Return the message as-is if it's already descriptive
        return message

    # Handle httpx network exceptions
    if isinstance(error, (httpx.ConnectError, httpx.NetworkError)):
        return "Network error: Unable to connect. Check your internet connection and try again."

    # Handle httpx timeout
    if isinstance(error, httpx.TimeoutException):
        return "Request timed out: The server took too long to respond. Try again."

    # Handle asyncio timeout
    if isinstance(error, asyncio.TimeoutError):
        return "Request timed out: The operation took too long. Try again."

    # Handle generic exceptions
    # Don't expose raw exception details to the user
    error_type = type(error).__name__
    return f"Unexpected error: {error_type}. Please try again or check the logs."


def is_network_error(error: StockError | CryptoError | Exception) -> bool:
    """Check if an error is network-related.

    Args:
        error: The error to check.

    Returns:
        True if the error is network-related, False otherwise.
    """
    # Check if it's a network exception type
    if isinstance(error, (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException)):
        return True

    # Check if it's a timeout
    if isinstance(error, asyncio.TimeoutError):
        return True

    # Check error message for network keywords
    if isinstance(error, (StockError, CryptoError)):
        message = error.error_message.lower()
        return any(
            keyword in message
            for keyword in ["network", "connection", "timeout", "offline", "timed out"]
        )

    return False
