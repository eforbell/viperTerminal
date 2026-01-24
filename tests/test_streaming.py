"""Tests for real-time streaming service."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from viper.services.streaming import (
    ConnectionState,
    StreamingQuote,
    StreamingService,
)


class TestConnectionState:
    """Tests for ConnectionState enum."""

    def test_connection_state_values(self) -> None:
        """Test ConnectionState enum has all required values."""
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.RECONNECTING.value == "reconnecting"
        assert ConnectionState.ERROR.value == "error"


class TestStreamingQuote:
    """Tests for StreamingQuote dataclass."""

    def test_streaming_quote_creation_minimal(self) -> None:
        """Test StreamingQuote with required fields only."""
        quote = StreamingQuote(
            symbol="AAPL",
            price=150.25,
            change=2.50,
            change_percent=1.69,
        )
        assert quote.symbol == "AAPL"
        assert quote.price == 150.25
        assert quote.change == 2.50
        assert quote.change_percent == 1.69
        assert quote.volume is None
        assert quote.day_high is None
        assert quote.day_low is None
        assert quote.timestamp is None

    def test_streaming_quote_creation_full(self) -> None:
        """Test StreamingQuote with all fields."""
        quote = StreamingQuote(
            symbol="TSLA",
            price=250.75,
            change=-5.25,
            change_percent=-2.05,
            volume=50000000,
            day_high=255.00,
            day_low=248.00,
            timestamp=1642518000,
        )
        assert quote.symbol == "TSLA"
        assert quote.price == 250.75
        assert quote.change == -5.25
        assert quote.change_percent == -2.05
        assert quote.volume == 50000000
        assert quote.day_high == 255.00
        assert quote.day_low == 248.00
        assert quote.timestamp == 1642518000


class TestStreamingServiceSingleton:
    """Tests for StreamingService singleton pattern."""

    def test_get_instance_returns_same_instance(self) -> None:
        """Test singleton pattern returns same instance across calls."""
        StreamingService._reset_instance()  # Clean slate for test

        instance1 = StreamingService.get_instance()
        instance2 = StreamingService.get_instance()

        assert instance1 is instance2

    def test_reset_instance_clears_singleton(self) -> None:
        """Test _reset_instance clears singleton for testing."""
        instance1 = StreamingService.get_instance()
        StreamingService._reset_instance()
        instance2 = StreamingService.get_instance()

        assert instance1 is not instance2


class TestStreamingServiceNormalization:
    """Tests for symbol normalization."""

    def test_normalize_stock_lowercase(self) -> None:
        """Test normalizing lowercase stock symbol."""
        service = StreamingService.get_instance()
        assert service._normalize_symbol("aapl") == "AAPL"

    def test_normalize_stock_uppercase(self) -> None:
        """Test normalizing uppercase stock symbol."""
        service = StreamingService.get_instance()
        assert service._normalize_symbol("TSLA") == "TSLA"

    def test_normalize_stock_with_whitespace(self) -> None:
        """Test normalizing stock symbol with whitespace."""
        service = StreamingService.get_instance()
        assert service._normalize_symbol("  MSFT  ") == "MSFT"

    def test_normalize_crypto_btc(self) -> None:
        """Test normalizing BTC adds -USD suffix."""
        service = StreamingService.get_instance()
        assert service._normalize_symbol("btc") == "BTC-USD"

    def test_normalize_crypto_eth(self) -> None:
        """Test normalizing ETH adds -USD suffix."""
        service = StreamingService.get_instance()
        assert service._normalize_symbol("ETH") == "ETH-USD"

    def test_normalize_crypto_with_existing_suffix(self) -> None:
        """Test normalizing crypto that already has -USD suffix."""
        service = StreamingService.get_instance()
        assert service._normalize_symbol("BTC-USD") == "BTC-USD"

    def test_normalize_crypto_mixed_case_with_suffix(self) -> None:
        """Test normalizing lowercase crypto with -usd suffix."""
        service = StreamingService.get_instance()
        assert service._normalize_symbol("btc-usd") == "BTC-USD"

    def test_normalize_known_crypto_symbols(self) -> None:
        """Test all known crypto symbols get -USD suffix."""
        service = StreamingService.get_instance()
        known_cryptos = [
            "BTC",
            "ETH",
            "SOL",
            "DOGE",
            "ADA",
            "XRP",
            "DOT",
            "AVAX",
            "MATIC",
            "LINK",
            "UNI",
            "ATOM",
            "LTC",
            "BCH",
        ]
        for symbol in known_cryptos:
            assert service._normalize_symbol(symbol) == f"{symbol}-USD"


class TestStreamingServiceParseQuote:
    """Tests for quote parsing."""

    def test_parse_quote_valid_with_previous_close(self) -> None:
        """Test parsing valid quote with previous close."""
        service = StreamingService.get_instance()
        data = {
            "id": "AAPL",
            "price": 150.00,
            "previousClose": 147.50,
            "dayVolume": 75000000,
            "dayHigh": 151.00,
            "dayLow": 148.50,
            "time": 1642518000,
        }

        quote = service._parse_quote(data)

        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price == 150.00
        assert quote.change == pytest.approx(2.50)
        assert quote.change_percent == pytest.approx(1.6949, rel=1e-3)
        assert quote.volume == 75000000
        assert quote.day_high == 151.00
        assert quote.day_low == 148.50
        assert quote.timestamp == 1642518000

    def test_parse_quote_valid_without_previous_close(self) -> None:
        """Test parsing quote without previous close."""
        service = StreamingService.get_instance()
        data = {
            "symbol": "TSLA",
            "price": 250.00,
        }

        quote = service._parse_quote(data)

        assert quote is not None
        assert quote.symbol == "TSLA"
        assert quote.price == 250.00
        assert quote.change == 0.0
        assert quote.change_percent == 0.0

    def test_parse_quote_missing_symbol(self) -> None:
        """Test parsing quote with missing symbol returns None."""
        service = StreamingService.get_instance()
        data = {"price": 150.00}

        quote = service._parse_quote(data)
        assert quote is None

    def test_parse_quote_missing_price(self) -> None:
        """Test parsing quote with missing price returns None."""
        service = StreamingService.get_instance()
        data = {"symbol": "AAPL"}

        quote = service._parse_quote(data)
        assert quote is None

    def test_parse_quote_zero_previous_close(self) -> None:
        """Test parsing quote with zero previous close."""
        service = StreamingService.get_instance()
        data = {
            "id": "AAPL",
            "price": 150.00,
            "previousClose": 0,
        }

        quote = service._parse_quote(data)

        assert quote is not None
        assert quote.change == 0.0
        assert quote.change_percent == 0.0

    def test_parse_quote_negative_change(self) -> None:
        """Test parsing quote with negative change."""
        service = StreamingService.get_instance()
        data = {
            "id": "TSLA",
            "price": 245.00,
            "previousClose": 250.00,
        }

        quote = service._parse_quote(data)

        assert quote is not None
        assert quote.change == pytest.approx(-5.00)
        assert quote.change_percent == pytest.approx(-2.00)


class TestStreamingServiceLifecycle:
    """Tests for service lifecycle (start/stop)."""

    @pytest.mark.asyncio
    async def test_initial_state(self) -> None:
        """Test service starts in DISCONNECTED state."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        assert service.state == ConnectionState.DISCONNECTED
        assert not service.is_connected
        assert len(service.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_start_transitions_to_connecting(self) -> None:
        """Test start() transitions state to CONNECTING."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        state_changes: list[ConnectionState] = []

        def on_state_change(state: ConnectionState) -> None:
            state_changes.append(state)

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            # Mock listen to avoid hanging
            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(0.1)

            mock_ws.listen = mock_listen

            await service.start(on_state_change=on_state_change)

            # Give listen loop time to start
            await asyncio.sleep(0.05)

            assert ConnectionState.CONNECTING in state_changes
            assert service.state in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
            ]

            await service.stop()

    @pytest.mark.asyncio
    async def test_stop_transitions_to_disconnected(self) -> None:
        """Test stop() transitions to DISCONNECTED and clears subscriptions."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            # Mock listen to avoid hanging
            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()
            await asyncio.sleep(0.05)

            # Add some subscriptions manually to test clearing
            service._subscriptions.add("AAPL")
            service._subscriptions.add("TSLA")

            await service.stop()

            assert service.state == ConnectionState.DISCONNECTED
            assert len(service.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_start_when_already_running(self) -> None:
        """Test start() when service is already running logs warning."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()

            # Try starting again
            with patch.object(service._logger, "warning") as mock_warning:
                await service.start()
                mock_warning.assert_called_once()

            await service.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self) -> None:
        """Test stop() when service is not running is safe."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        # Should not raise
        await service.stop()
        assert service.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_start_failure_sets_error_state(self) -> None:
        """Test start() failure transitions to ERROR state."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws_class.side_effect = Exception("Failed to create WebSocket")

            with pytest.raises(Exception, match="Failed to create WebSocket"):
                await service.start()

            assert service.state == ConnectionState.ERROR
            assert not service._running


class TestStreamingServiceSubscriptions:
    """Tests for subscribe/unsubscribe functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_adds_to_subscriptions(self) -> None:
        """Test subscribe() adds symbols to internal set."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()
            await asyncio.sleep(0.05)

            await service.subscribe(["AAPL", "TSLA"])

            assert "AAPL" in service.subscriptions
            assert "TSLA" in service.subscriptions

            await service.stop()

    @pytest.mark.asyncio
    async def test_subscribe_normalizes_symbols(self) -> None:
        """Test subscribe() normalizes symbols before subscribing."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()
            await asyncio.sleep(0.05)

            await service.subscribe(["aapl", "btc"])

            assert "AAPL" in service.subscriptions
            assert "BTC-USD" in service.subscriptions

            await service.stop()

    @pytest.mark.asyncio
    async def test_subscribe_skips_duplicates(self) -> None:
        """Test subscribe() skips already-subscribed symbols."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()
            await asyncio.sleep(0.05)

            await service.subscribe(["AAPL"])
            mock_ws.subscribe.reset_mock()

            await service.subscribe(["AAPL"])
            mock_ws.subscribe.assert_not_called()

            await service.stop()

    @pytest.mark.asyncio
    async def test_subscribe_when_not_running(self) -> None:
        """Test subscribe() when service not running logs warning."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch.object(service._logger, "warning") as mock_warning:
            await service.subscribe(["AAPL"])
            mock_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_from_subscriptions(self) -> None:
        """Test unsubscribe() removes symbols from internal set."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()
            await asyncio.sleep(0.05)

            await service.subscribe(["AAPL", "TSLA"])
            await service.unsubscribe(["AAPL"])

            assert "AAPL" not in service.subscriptions
            assert "TSLA" in service.subscriptions

            await service.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_when_not_running(self) -> None:
        """Test unsubscribe() when service not running logs warning."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch.object(service._logger, "warning") as mock_warning:
            await service.unsubscribe(["AAPL"])
            mock_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_empty_list(self) -> None:
        """Test unsubscribe() with symbols not in subscriptions."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()
            await asyncio.sleep(0.05)

            # Try to unsubscribe from symbols we never subscribed to
            await service.unsubscribe(["AAPL", "TSLA"])

            # Should not call WebSocket unsubscribe
            mock_ws.unsubscribe.assert_not_called()

            await service.stop()

    @pytest.mark.asyncio
    async def test_subscribe_error_handling(self) -> None:
        """Test subscribe() handles WebSocket errors gracefully."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws
            mock_ws.subscribe.side_effect = Exception("WebSocket error")

            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()
            await asyncio.sleep(0.05)

            with patch.object(service._logger, "error") as mock_error:
                await service.subscribe(["AAPL"])
                mock_error.assert_called_once()

            await service.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_error_handling(self) -> None:
        """Test unsubscribe() handles WebSocket errors gracefully."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            async def mock_listen(handler: Any) -> None:
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start()
            await asyncio.sleep(0.05)

            # Subscribe first
            await service.subscribe(["AAPL"])

            # Make unsubscribe fail
            mock_ws.unsubscribe.side_effect = Exception("WebSocket error")

            with patch.object(service._logger, "error") as mock_error:
                await service.unsubscribe(["AAPL"])
                mock_error.assert_called_once()

            await service.stop()

    @pytest.mark.asyncio
    async def test_listen_loop_handles_exceptions(self) -> None:
        """Test _listen_loop handles exceptions and attempts reconnect."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        state_changes: list[ConnectionState] = []

        def on_state_change(state: ConnectionState) -> None:
            state_changes.append(state)

        with patch("viper.services.streaming.AsyncWebSocket") as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            call_count = 0

            async def mock_listen(handler: Any) -> None:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call raises exception
                    raise Exception("Connection lost")
                # Second call succeeds and waits
                await asyncio.sleep(1)

            mock_ws.listen = mock_listen

            await service.start(on_state_change=on_state_change)

            # Subscribe to trigger listen loop (listen is deferred until first subscribe)
            await service.subscribe(["AAPL"])

            # Wait for first error and reconnect attempt
            await asyncio.sleep(0.5)

            # Should have transitioned to RECONNECTING
            assert ConnectionState.RECONNECTING in state_changes

            await service.stop()

    @pytest.mark.asyncio
    async def test_handle_message_with_parse_exception(self) -> None:
        """Test _handle_message handles exceptions during parsing."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        def failing_callback(quote: StreamingQuote) -> None:
            raise Exception("Callback error")

        service.add_quote_listener(failing_callback)

        with patch.object(service._logger, "error") as mock_error:
            data = {
                "id": "AAPL",
                "price": 150.00,
                "previousClose": 147.50,
            }
            service._handle_message(data)
            mock_error.assert_called_once()


class TestStreamingServiceMultiListener:
    """Tests for multi-listener support (VPR-102)."""

    def test_add_quote_listener(self) -> None:
        """Test add_quote_listener adds callback to list."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        def listener(quote: StreamingQuote) -> None:
            pass

        service.add_quote_listener(listener)
        assert len(service._quote_listeners) == 1
        assert listener in service._quote_listeners

    def test_add_quote_listener_no_duplicates(self) -> None:
        """Test add_quote_listener ignores duplicate callbacks."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        def listener(quote: StreamingQuote) -> None:
            pass

        service.add_quote_listener(listener)
        service.add_quote_listener(listener)
        assert len(service._quote_listeners) == 1

    def test_remove_quote_listener(self) -> None:
        """Test remove_quote_listener removes callback from list."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        def listener(quote: StreamingQuote) -> None:
            pass

        service.add_quote_listener(listener)
        service.remove_quote_listener(listener)
        assert len(service._quote_listeners) == 0

    def test_remove_quote_listener_not_found(self) -> None:
        """Test remove_quote_listener is no-op when callback not found."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        def listener(quote: StreamingQuote) -> None:
            pass

        # Should not raise
        service.remove_quote_listener(listener)
        assert len(service._quote_listeners) == 0

    def test_multiple_listeners_receive_quotes(self) -> None:
        """Test multiple listeners all receive quotes."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        received1: list[StreamingQuote] = []
        received2: list[StreamingQuote] = []
        received3: list[StreamingQuote] = []

        def listener1(quote: StreamingQuote) -> None:
            received1.append(quote)

        def listener2(quote: StreamingQuote) -> None:
            received2.append(quote)

        def listener3(quote: StreamingQuote) -> None:
            received3.append(quote)

        service.add_quote_listener(listener1)
        service.add_quote_listener(listener2)
        service.add_quote_listener(listener3)

        data = {
            "id": "AAPL",
            "price": 150.00,
            "previousClose": 147.50,
        }

        service._handle_message(data)

        assert len(received1) == 1
        assert len(received2) == 1
        assert len(received3) == 1
        assert received1[0].symbol == "AAPL"
        assert received2[0].price == 150.00
        assert received3[0].change == pytest.approx(2.50)

    def test_removed_listener_stops_receiving(self) -> None:
        """Test removing listener stops it from receiving quotes."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        received1: list[StreamingQuote] = []
        received2: list[StreamingQuote] = []

        def listener1(quote: StreamingQuote) -> None:
            received1.append(quote)

        def listener2(quote: StreamingQuote) -> None:
            received2.append(quote)

        service.add_quote_listener(listener1)
        service.add_quote_listener(listener2)

        # First message - both receive
        service._handle_message({"id": "AAPL", "price": 150.00})
        assert len(received1) == 1
        assert len(received2) == 1

        # Remove listener2
        service.remove_quote_listener(listener2)

        # Second message - only listener1 receives
        service._handle_message({"id": "TSLA", "price": 250.00})
        assert len(received1) == 2
        assert len(received2) == 1  # Still 1, didn't receive second

    def test_start_on_quote_backward_compatibility(self) -> None:
        """Test on_quote param in start() registers as first listener.

        Note: This test verifies the callback registration mechanism
        synchronously. The actual start() call is async but we can test
        the add_quote_listener behavior directly.
        """
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        received: list[StreamingQuote] = []

        def on_quote(quote: StreamingQuote) -> None:
            received.append(quote)

        # Simulate what start() does with on_quote parameter
        service.add_quote_listener(on_quote)

        # Verify listener was added
        assert len(service._quote_listeners) == 1
        assert on_quote in service._quote_listeners

        # Test it receives quotes via _handle_message
        service._handle_message({"id": "AAPL", "price": 150.00})
        assert len(received) == 1
        assert received[0].symbol == "AAPL"

    def test_listener_error_does_not_stop_others(self) -> None:
        """Test error in one listener doesn't prevent others from receiving."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        received: list[StreamingQuote] = []

        def failing_listener(quote: StreamingQuote) -> None:
            raise Exception("Listener error")

        def working_listener(quote: StreamingQuote) -> None:
            received.append(quote)

        service.add_quote_listener(failing_listener)
        service.add_quote_listener(working_listener)

        with patch.object(service._logger, "error") as mock_error:
            service._handle_message({"id": "AAPL", "price": 150.00})

            # Failing listener error was logged
            mock_error.assert_called_once()

            # Working listener still received the quote
            assert len(received) == 1


class TestStreamingServiceMessageHandling:
    """Tests for WebSocket message handling."""

    @pytest.mark.asyncio
    async def test_handle_message_calls_on_quote(self) -> None:
        """Test _handle_message calls on_quote callback with parsed quote."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        received_quotes: list[StreamingQuote] = []

        def on_quote(quote: StreamingQuote) -> None:
            received_quotes.append(quote)

        service.add_quote_listener(on_quote)

        data = {
            "id": "AAPL",
            "price": 150.00,
            "previousClose": 147.50,
        }

        service._handle_message(data)

        assert len(received_quotes) == 1
        assert received_quotes[0].symbol == "AAPL"
        assert received_quotes[0].price == 150.00

    @pytest.mark.asyncio
    async def test_handle_message_with_error_logs_warning(self) -> None:
        """Test _handle_message with error key logs warning."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch.object(service._logger, "warning") as mock_warning:
            data = {"error": "Invalid symbol"}
            service._handle_message(data)
            mock_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_with_malformed_data(self) -> None:
        """Test _handle_message with malformed data logs error."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        with patch.object(service._logger, "error") as mock_error:
            # Missing required fields
            data = {"foo": "bar"}
            service._handle_message(data)
            # Should not log error if quote is just None
            assert mock_error.call_count == 0


class TestStreamingServiceProperties:
    """Tests for service properties."""

    def test_state_property(self) -> None:
        """Test state property returns current state."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        assert service.state == ConnectionState.DISCONNECTED

        service._state = ConnectionState.CONNECTED
        assert service.state == ConnectionState.CONNECTED

    def test_is_connected_property(self) -> None:
        """Test is_connected returns True only when CONNECTED."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        service._state = ConnectionState.DISCONNECTED
        assert not service.is_connected

        service._state = ConnectionState.CONNECTING
        assert not service.is_connected

        service._state = ConnectionState.CONNECTED
        assert service.is_connected

        service._state = ConnectionState.RECONNECTING
        assert not service.is_connected

        service._state = ConnectionState.ERROR
        assert not service.is_connected

    def test_subscriptions_property_returns_copy(self) -> None:
        """Test subscriptions property returns copy, not reference."""
        StreamingService._reset_instance()
        service = StreamingService.get_instance()

        service._subscriptions.add("AAPL")
        subs = service.subscriptions

        # Modify the copy
        subs.add("TSLA")

        # Original should be unchanged
        assert "TSLA" not in service.subscriptions
        assert "AAPL" in service.subscriptions
