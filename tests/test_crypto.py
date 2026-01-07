"""Tests for crypto quote fetching service."""

from unittest.mock import patch

import httpx
import pytest
import respx

from viper.services.crypto import (
    SYMBOL_TO_ID,
    CryptoError,
    CryptoQuote,
    fetch_crypto_quote,
)


class TestCryptoQuote:
    """Tests for CryptoQuote dataclass."""

    def test_crypto_quote_creation(self) -> None:
        """Test CryptoQuote dataclass instantiation."""
        quote = CryptoQuote(
            symbol="BTC",
            price_usd=45000.50,
            change_24h_percent=2.5,
            market_cap_usd=900000000000,
            volume_24h_usd=25000000000.0,
            name="Bitcoin",
        )
        assert quote.symbol == "BTC"
        assert quote.price_usd == 45000.50
        assert quote.change_24h_percent == 2.5
        assert quote.market_cap_usd == 900000000000
        assert quote.volume_24h_usd == 25000000000.0
        assert quote.name == "Bitcoin"

    def test_crypto_quote_optional_name(self) -> None:
        """Test CryptoQuote with optional name field."""
        quote = CryptoQuote(
            symbol="BTC",
            price_usd=45000.0,
            change_24h_percent=0.0,
            market_cap_usd=900000000000,
            volume_24h_usd=25000000000.0,
        )
        assert quote.name is None


class TestCryptoError:
    """Tests for CryptoError dataclass."""

    def test_crypto_error_creation(self) -> None:
        """Test CryptoError dataclass instantiation."""
        error = CryptoError(symbol="INVALID", error_message="Unknown crypto symbol: INVALID")
        assert error.symbol == "INVALID"
        assert error.error_message == "Unknown crypto symbol: INVALID"


class TestSymbolMapping:
    """Tests for symbol to ID mapping."""

    def test_symbol_to_id_mapping_exists(self) -> None:
        """Test that common crypto symbols have ID mappings."""
        assert SYMBOL_TO_ID["BTC"] == "bitcoin"
        assert SYMBOL_TO_ID["ETH"] == "ethereum"
        assert SYMBOL_TO_ID["DOGE"] == "dogecoin"
        assert SYMBOL_TO_ID["SOL"] == "solana"

    def test_symbol_to_id_has_reasonable_coverage(self) -> None:
        """Test that we have a decent number of symbols mapped."""
        assert len(SYMBOL_TO_ID) >= 20  # Should cover top cryptos


class TestFetchCryptoQuote:
    """Tests for fetch_crypto_quote async function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_valid_symbol(self) -> None:
        """Test fetching a valid crypto symbol returns CryptoQuote."""
        # Mock CoinGecko API response
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 45000.50},
                "price_change_percentage_24h": 2.5,
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000.0},
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.symbol == "BTC"
        assert result.price_usd == 45000.50
        assert result.change_24h_percent == 2.5
        assert result.market_cap_usd == 900000000000
        assert result.volume_24h_usd == 25000000000.0
        assert result.name == "Bitcoin"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_symbol_uppercase_normalization(self) -> None:
        """Test symbol is normalized to uppercase."""
        mock_response = {
            "name": "Ethereum",
            "market_data": {
                "current_price": {"usd": 3000.0},
                "price_change_percentage_24h": 1.5,
                "market_cap": {"usd": 360000000000},
                "total_volume": {"usd": 15000000000.0},
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/ethereum").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("eth")

        assert isinstance(result, CryptoQuote)
        assert result.symbol == "ETH"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_symbol_with_whitespace(self) -> None:
        """Test symbol whitespace is stripped."""
        mock_response = {
            "name": "Solana",
            "market_data": {
                "current_price": {"usd": 100.0},
                "price_change_percentage_24h": 0.0,
                "market_cap": {"usd": 50000000000},
                "total_volume": {"usd": 2000000000.0},
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/solana").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("  sol  ")

        assert isinstance(result, CryptoQuote)
        assert result.symbol == "SOL"

    @pytest.mark.asyncio
    async def test_fetch_unknown_symbol(self) -> None:
        """Test fetching an unknown symbol returns CryptoError."""
        result = await fetch_crypto_quote("NOTACRYPTO")

        assert isinstance(result, CryptoError)
        assert result.symbol == "NOTACRYPTO"
        assert "Unknown crypto symbol" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_rate_limit_429(self) -> None:
        """Test handling rate limit (429) response."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(429, text="Too Many Requests")
        )

        result = await fetch_crypto_quote("BTC", max_retries=1)

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "rate limit" in result.error_message.lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_rate_limit_retry_success(self) -> None:
        """Test retry logic succeeds after rate limit."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 45000.0},
                "price_change_percentage_24h": 0.0,
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000.0},
            },
        }

        # First call returns 429, second call succeeds
        route = respx.get("https://api.coingecko.com/api/v3/coins/bitcoin")
        route.side_effect = [
            httpx.Response(429, text="Too Many Requests"),
            httpx.Response(200, json=mock_response),
        ]

        result = await fetch_crypto_quote("BTC", max_retries=2)

        assert isinstance(result, CryptoQuote)
        assert result.symbol == "BTC"
        assert result.price_usd == 45000.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_rate_limit_exhausted_retries(self) -> None:
        """Test rate limit error after exhausting retries."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(429, text="Too Many Requests")
        )

        result = await fetch_crypto_quote("BTC", max_retries=2)

        assert isinstance(result, CryptoError)
        assert "Rate limit exceeded after 2 retries" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_http_error_404(self) -> None:
        """Test handling 404 HTTP error."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "HTTP 404" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_http_error_500(self) -> None:
        """Test handling 500 HTTP error."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "HTTP 500" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_timeout(self) -> None:
        """Test handling request timeout."""

        async def slow_request(*args: object, **kwargs: object) -> httpx.Response:
            import asyncio

            await asyncio.sleep(2)
            return httpx.Response(200, json={})

        with patch("httpx.AsyncClient.get", side_effect=slow_request):
            result = await fetch_crypto_quote("BTC", timeout=0.1)

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_with_custom_timeout(self) -> None:
        """Test fetch with custom timeout value."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 45000.0},
                "price_change_percentage_24h": 0.0,
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000.0},
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC", timeout=5.0)

        assert isinstance(result, CryptoQuote)

    @pytest.mark.asyncio
    async def test_fetch_network_error(self) -> None:
        """Test handling network connection errors."""
        with patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.ConnectError("Connection failed"),
        ):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_request_error(self) -> None:
        """Test handling other request errors."""
        with patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.RequestError("Request failed"),
        ):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "Request failed" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_missing_market_data(self) -> None:
        """Test handling response with missing market_data."""
        mock_response = {"name": "Bitcoin"}  # No market_data

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert "Missing market data" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_missing_price_data(self) -> None:
        """Test handling response with missing price data."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "price_change_percentage_24h": 0.0,
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert "Missing price data" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_missing_usd_price(self) -> None:
        """Test handling response with missing USD price."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"eur": 42000.0},  # No USD
                "price_change_percentage_24h": 0.0,
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert "Missing USD price" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_with_missing_optional_fields(self) -> None:
        """Test handling when optional fields are missing."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 45000.0},
                # Missing: price_change_percentage_24h, market_cap, total_volume
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.price_usd == 45000.0
        assert result.change_24h_percent == 0.0  # Default
        assert result.market_cap_usd == 0  # Default
        assert result.volume_24h_usd == 0.0  # Default

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_with_no_name(self) -> None:
        """Test handling when name is missing."""
        mock_response = {
            "market_data": {
                "current_price": {"usd": 45000.0},
                "price_change_percentage_24h": 2.5,
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000.0},
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.name is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_malformed_json(self) -> None:
        """Test handling malformed JSON response."""
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, text="not valid json")
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert "Failed to fetch quote" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_positive_change(self) -> None:
        """Test with positive 24h change."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 45000.0},
                "price_change_percentage_24h": 5.5,
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000.0},
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.change_24h_percent == 5.5

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_negative_change(self) -> None:
        """Test with negative 24h change."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 45000.0},
                "price_change_percentage_24h": -3.2,
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000.0},
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.change_24h_percent == -3.2

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_with_integer_values(self) -> None:
        """Test that integer values are properly converted to float."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 45000},  # Integer
                "price_change_percentage_24h": 2,  # Integer
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000},  # Integer
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoQuote)
        assert result.price_usd == 45000.0
        assert result.change_24h_percent == 2.0
        assert result.volume_24h_usd == 25000000000.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_api_params(self) -> None:
        """Test that API is called with correct parameters."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 45000.0},
                "price_change_percentage_24h": 0.0,
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000.0},
            },
        }

        route = respx.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
        ).mock(return_value=httpx.Response(200, json=mock_response))

        await fetch_crypto_quote("BTC")

        assert route.called

    @pytest.mark.asyncio
    async def test_fetch_unexpected_exception_during_retry(self) -> None:
        """Test handling unexpected exception during retry loop."""

        async def raise_exception(*args: object, **kwargs: object) -> httpx.Response:
            raise RuntimeError("Unexpected error")

        with patch("httpx.AsyncClient.get", side_effect=raise_exception):
            result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "Unexpected error" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_exhausted_retries_on_rate_limit(self) -> None:
        """Test that we return proper error after exhausting all retries."""
        # All attempts return 429
        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(429, text="Too Many Requests")
        )

        result = await fetch_crypto_quote("BTC", max_retries=3)

        assert isinstance(result, CryptoError)
        assert result.symbol == "BTC"
        assert "Rate limit exceeded after 3 retries" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_parse_response_value_error(self) -> None:
        """Test handling ValueError during response parsing."""
        mock_response = {
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": "not_a_number"},  # Invalid type
                "price_change_percentage_24h": 0.0,
                "market_cap": {"usd": 900000000000},
                "total_volume": {"usd": 25000000000.0},
            },
        }

        respx.get("https://api.coingecko.com/api/v3/coins/bitcoin").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crypto_quote("BTC")

        assert isinstance(result, CryptoError)
        assert "Failed to parse response" in result.error_message
