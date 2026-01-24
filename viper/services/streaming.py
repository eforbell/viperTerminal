"""Real-time streaming service for WebSocket price updates."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from yfinance import AsyncWebSocket  # type: ignore[import-untyped]

from viper.utils.logger import get_logger


class ConnectionState(Enum):
    """WebSocket connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class StreamingQuote:
    """Real-time quote data from WebSocket stream."""

    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int | None = None
    day_high: float | None = None
    day_low: float | None = None
    timestamp: int | None = None


class StreamingService:
    """Singleton service for managing WebSocket streaming."""

    _instance: "StreamingService | None" = None

    @classmethod
    def get_instance(cls) -> "StreamingService":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def _reset_instance(cls) -> None:
        """Reset singleton for testing purposes only."""
        cls._instance = None

    def __init__(self) -> None:
        """Initialize the streaming service."""
        self._ws: AsyncWebSocket | None = None
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._subscriptions: set[str] = set()
        self._quote_listeners: list[Callable[[StreamingQuote], None]] = []
        self._on_state_change: Callable[[ConnectionState], None] | None = None
        self._listen_task: asyncio.Task[None] | None = None
        self._running: bool = False
        self._logger = get_logger()

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize a symbol for WebSocket subscription.

        Args:
            symbol: Raw symbol string (e.g., "aapl", "btc", "BTC-USD")

        Returns:
            Normalized symbol (e.g., "AAPL", "BTC-USD", "BTC-USD")
        """
        symbol = symbol.upper().strip()

        # Known crypto symbols need -USD suffix for Yahoo WebSocket
        CRYPTO_SYMBOLS = {
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
        }

        if symbol in CRYPTO_SYMBOLS:
            return f"{symbol}-USD"

        # Already has -USD suffix (e.g., BTC-USD passed directly)
        if symbol.endswith("-USD") and symbol[:-4] in CRYPTO_SYMBOLS:
            return symbol

        return symbol

    def _parse_quote(self, data: dict[str, Any]) -> StreamingQuote | None:
        """Parse WebSocket message dict into StreamingQuote.

        Args:
            data: Raw WebSocket message dictionary

        Returns:
            StreamingQuote if valid, None if malformed
        """
        symbol = data.get("id") or data.get("symbol")
        price = data.get("price")

        if not symbol or price is None:
            return None

        # Use change/change_percent directly from message if available
        # Otherwise calculate from previousClose
        change = data.get("change")
        change_pct = data.get("change_percent")

        if change is None or change_pct is None:
            # Fall back to calculation from previousClose
            prev_close = data.get("previousClose", 0)
            if prev_close and prev_close > 0:
                change = price - prev_close
                change_pct = (change / prev_close) * 100
            else:
                change = 0.0
                change_pct = 0.0

        # Handle volume - may be string in some messages
        volume = data.get("dayVolume") or data.get("day_volume")
        if isinstance(volume, str):
            try:
                volume = int(volume)
            except ValueError:
                volume = None

        return StreamingQuote(
            symbol=str(symbol),
            price=float(price),
            change=float(change),
            change_percent=float(change_pct),
            volume=volume,
            day_high=data.get("dayHigh"),
            day_low=data.get("dayLow"),
            timestamp=data.get("time"),
        )

    async def start(
        self,
        on_quote: Callable[[StreamingQuote], None] | None = None,
        on_state_change: Callable[[ConnectionState], None] | None = None,
    ) -> None:
        """Start the streaming service.

        Note: This initializes the WebSocket but doesn't start listening yet.
        Listening begins when the first subscription is made via subscribe().

        Args:
            on_quote: Callback for receiving quote updates
            on_state_change: Callback for connection state changes
        """
        if self._running:
            self._logger.warning("StreamingService already running")
            return

        # Register on_quote as first listener for backward compatibility
        if on_quote is not None:
            self.add_quote_listener(on_quote)
        self._on_state_change = on_state_change

        self._set_state(ConnectionState.CONNECTING)

        try:
            self._ws = AsyncWebSocket(verbose=False)
            self._running = True  # Only set running after WebSocket created
            # Note: Don't start listen task here - wait until first subscribe()
            # yfinance WebSocket needs subscriptions before listen() is called
            self._logger.info("StreamingService started (waiting for subscriptions)")
        except Exception as e:
            self._logger.error(f"Failed to start StreamingService: {e}")
            self._set_state(ConnectionState.ERROR)
            self._running = False
            self._ws = None
            raise

    async def stop(self) -> None:
        """Stop the streaming service and close connection."""
        if not self._running:
            return

        self._running = False

        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

        self._subscriptions.clear()
        self._set_state(ConnectionState.DISCONNECTED)
        self._logger.info("StreamingService stopped")

    def add_quote_listener(
        self, callback: Callable[[StreamingQuote], None]
    ) -> None:
        """Add a quote listener callback.

        Args:
            callback: Function to call when quotes arrive
        """
        if callback not in self._quote_listeners:
            self._quote_listeners.append(callback)
            self._logger.debug(f"Added quote listener, total: {len(self._quote_listeners)}")

    def remove_quote_listener(
        self, callback: Callable[[StreamingQuote], None]
    ) -> None:
        """Remove a quote listener callback.

        This is a no-op if the callback is not found.

        Args:
            callback: Function to remove from listeners
        """
        try:
            self._quote_listeners.remove(callback)
            self._logger.debug(f"Removed quote listener, total: {len(self._quote_listeners)}")
        except ValueError:
            pass  # No-op if callback not found

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to symbols for real-time updates.

        Args:
            symbols: List of ticker symbols to subscribe to
        """
        if not self._ws or not self._running:
            self._logger.warning("Cannot subscribe: service not running")
            return

        normalized = [self._normalize_symbol(s) for s in symbols]
        new_symbols = [s for s in normalized if s not in self._subscriptions]

        if not new_symbols:
            return

        try:
            await self._ws.subscribe(new_symbols)
            self._subscriptions.update(new_symbols)
            self._logger.info(f"Subscribed to: {new_symbols}")

            # Start listening after first subscription (yfinance needs subs before listen)
            if self._listen_task is None:
                self._listen_task = asyncio.create_task(self._listen_loop())
                self._logger.info("Started listening for messages")
        except Exception as e:
            self._logger.error(f"Failed to subscribe to {new_symbols}: {e}")
            # Set error state and re-raise so caller can handle gracefully
            self._set_state(ConnectionState.ERROR)
            raise

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from symbols.

        Args:
            symbols: List of ticker symbols to unsubscribe from
        """
        if not self._ws or not self._running:
            self._logger.warning("Cannot unsubscribe: service not running")
            return

        normalized = [self._normalize_symbol(s) for s in symbols]
        to_remove = [s for s in normalized if s in self._subscriptions]

        if not to_remove:
            return

        try:
            await self._ws.unsubscribe(to_remove)
            self._subscriptions.difference_update(to_remove)
            self._logger.info(f"Unsubscribed from: {to_remove}")
        except Exception as e:
            self._logger.error(f"Failed to unsubscribe from {to_remove}: {e}")

    async def _listen_loop(self) -> None:
        """Main loop for receiving WebSocket messages."""
        while self._running:
            try:
                self._set_state(ConnectionState.CONNECTED)
                await self._ws.listen(self._handle_message)  # type: ignore
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"WebSocket error: {e}")
                if self._running:
                    self._set_state(ConnectionState.RECONNECTING)
                    await asyncio.sleep(3)  # Backoff before reconnect attempt

    def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle a decoded WebSocket message.

        Args:
            data: Decoded message dictionary
        """
        if "error" in data:
            self._logger.warning(f'WebSocket message error: {data.get("error")}')
            return

        try:
            quote = self._parse_quote(data)
            if quote:
                for listener in self._quote_listeners:
                    try:
                        listener(quote)
                    except Exception as e:
                        self._logger.error(f"Quote listener error: {e}")
        except Exception as e:
            self._logger.error(f"Failed to parse quote: {e}")

    def _set_state(self, state: ConnectionState) -> None:
        """Update connection state and notify callback.

        Args:
            state: New connection state
        """
        if self._state != state:
            self._state = state
            self._logger.info(f"Connection state changed: {state.value}")
            if self._on_state_change:
                self._on_state_change(state)

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket is connected."""
        return self._state == ConnectionState.CONNECTED

    @property
    def subscriptions(self) -> set[str]:
        """Currently subscribed symbols (copy)."""
        return self._subscriptions.copy()
