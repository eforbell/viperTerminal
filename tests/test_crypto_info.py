"""Tests for crypto info fetching service."""

import httpx
import pytest
import respx

from viper.services.crypto import CryptoInfo, CryptoInfoError, fetch_crypto_info


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_success():
    """Test successful crypto info fetch."""
    mock_data = {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "description": {
            "en": "Bitcoin is a decentralized digital currency.",
        },
        "links": {
            "homepage": ["https://bitcoin.org", ""],
        },
        "genesis_date": "2009-01-03",
    }

    respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    result = await fetch_crypto_info("BTC")

    assert isinstance(result, CryptoInfo)
    assert result.symbol == "BTC"
    assert result.info["name"] == "Bitcoin"
    assert result.info["genesis_date"] == "2009-01-03"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_normalizes_symbol():
    """Test that symbol is normalized to uppercase and stripped."""
    mock_data = {"id": "bitcoin", "name": "Bitcoin"}

    route = respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    result = await fetch_crypto_info("  btc  ")

    assert isinstance(result, CryptoInfo)
    assert result.symbol == "BTC"
    assert route.called


@pytest.mark.asyncio
async def test_fetch_crypto_info_unknown_symbol():
    """Test handling of unknown crypto symbol."""
    result = await fetch_crypto_info("UNKNOWN")

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "UNKNOWN"
    assert "Unknown crypto symbol" in result.error_message


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_rate_limit():
    """Test handling of rate limit (429) with retry."""
    # First request returns 429, second succeeds
    mock_data = {"id": "bitcoin", "name": "Bitcoin"}

    route = respx.get("https://api.coingecko.com/api/v3/coins/bitcoin")
    route.side_effect = [
        httpx.Response(429, text="Rate limit exceeded"),
        httpx.Response(200, json=mock_data),
    ]

    result = await fetch_crypto_info("BTC", max_retries=3)

    assert isinstance(result, CryptoInfo)
    assert result.symbol == "BTC"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_rate_limit_exhausted():
    """Test handling when rate limit retries are exhausted."""
    route = respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
        return_value=httpx.Response(429, text="Rate limit exceeded")
    )

    result = await fetch_crypto_info("BTC", max_retries=2)

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "BTC"
    assert "Rate limit exceeded after" in result.error_message
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_http_error():
    """Test handling of HTTP errors (non-200 status)."""
    respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    result = await fetch_crypto_info("BTC")

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "BTC"
    assert "HTTP 500" in result.error_message


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_invalid_response():
    """Test handling of invalid JSON response."""
    respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
        return_value=httpx.Response(200, json="not a dict")
    )

    result = await fetch_crypto_info("BTC")

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "BTC"
    assert "Invalid response format" in result.error_message


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_timeout():
    """Test handling of request timeout."""

    async def delayed_response(request):
        import asyncio

        await asyncio.sleep(2)
        return httpx.Response(200, json={"id": "bitcoin"})

    respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(side_effect=delayed_response)

    result = await fetch_crypto_info("BTC", timeout=0.1)

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "BTC"
    assert "timed out" in result.error_message


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_network_error():
    """Test handling of network connection errors."""
    respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    result = await fetch_crypto_info("BTC")

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "BTC"
    assert "Network error" in result.error_message


@pytest.mark.asyncio
@respx.mock
async def test_fetch_crypto_info_request_error():
    """Test handling of general request errors."""
    respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
        side_effect=httpx.RequestError("Request failed")
    )

    result = await fetch_crypto_info("BTC")

    assert isinstance(result, CryptoInfoError)
    assert result.symbol == "BTC"
    assert "Request failed" in result.error_message
