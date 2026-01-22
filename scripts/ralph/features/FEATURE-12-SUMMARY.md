# Feature 12: Real-time Watchlist Mode

## Summary

Introduce WebSocket streaming via yfinance's `AsyncWebSocket` to enable live price updates for the watchlist. This is an **exploratory feature** to validate streaming architecture before potentially expanding to charts and other components.

**EXPLORATORY AND INCREMENTAL** - The goal is to prove the concept works reliably before broader adoption. Polling remains the default and fallback.

## Stories Overview

| ID | Title | Effort | Priority | Dependencies |
|----|-------|--------|----------|--------------|
| VPR-097 | Create StreamingService singleton | Medium | 1 | None |
| VPR-098 | Integrate streaming into WatchlistPanel | Medium | 2 | VPR-097 |
| VPR-099 | Add keybinding and app integration | Small | 3 | VPR-098 |
| VPR-100 | Visual indicators for streaming mode | Small | 4 | VPR-098, VPR-099 |
| VPR-101 | Add streaming_enabled config option | Small | 5 | VPR-098 |

**Dependency Flow:** VPR-097 -> VPR-098 -> (VPR-099, VPR-100, VPR-101 in parallel)

---

## VPR-097: Create StreamingService Singleton

### Problem
Currently, watchlist data refreshes via polling every 60 seconds. For users who want real-time prices, this is too slow.

### Solution
Create a `StreamingService` that wraps yfinance's `AsyncWebSocket` and manages the WebSocket connection lifecycle.

### yfinance AsyncWebSocket Capabilities
- **Endpoint:** `wss://streamer.finance.yahoo.com/?version=2`
- **Update model:** Server-push (no fixed refresh interval)
- **Update frequency:** Real-time as prices change - can be multiple times per second for active tickers during market hours
- **Heartbeat:** 15-second keep-alive ping to maintain connection (not a refresh interval)
- **Automatic reconnection:** Exponential backoff on failures
- **Message format:** Base64-encoded protobuf, decoded to Python dict
- **Supported symbols:** Stocks (AAPL, TSLA) and Crypto (BTC-USD, ETH-USD)

### Polling vs Streaming
| Aspect | Polling (Current) | Streaming (New) |
|--------|-------------------|-----------------|
| Model | We request data every 60s | Server pushes data as it changes |
| Latency | Up to 60 seconds stale | Sub-second |
| Network | Request/response per refresh | Persistent connection |
| Update frequency | Fixed interval | Variable (real-time) |

### Key Components

```python
class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class StreamingQuote:
    symbol: str
    price: float
    change: float          # Calculated: price - previousClose
    change_percent: float  # Calculated: (change / previousClose) * 100
    volume: int | None = None
    day_high: float | None = None
    day_low: float | None = None
    timestamp: int | None = None

class StreamingService:
    """Singleton service for WebSocket streaming."""

    _instance: "StreamingService | None" = None

    @classmethod
    def get_instance(cls) -> "StreamingService": ...

    @classmethod
    def _reset_instance(cls) -> None: ...  # For testing only

    async def start(self, on_quote, on_state_change) -> None: ...
    async def stop(self) -> None: ...
    async def subscribe(self, symbols: list[str]) -> None: ...
    async def unsubscribe(self, symbols: list[str]) -> None: ...

    @property
    def state(self) -> ConnectionState: ...

    @property
    def is_connected(self) -> bool: ...

    @property
    def subscriptions(self) -> set[str]: ...
```

### Symbol Normalization
- Stocks: Uppercase, trim whitespace (`aapl` -> `AAPL`)
- Crypto: Known symbols get -USD suffix (`BTC` -> `BTC-USD`, `ETH` -> `ETH-USD`)
- Already formatted: Preserved (`BTC-USD` stays `BTC-USD`)

**Known crypto symbols:** BTC, ETH, SOL, DOGE, ADA, XRP, DOT, AVAX, MATIC, LINK, UNI, ATOM, LTC, BCH

### Parsing WebSocket Messages

The WebSocket sends dict messages. Key fields to extract:
```python
def _parse_quote(self, data: dict[str, Any]) -> StreamingQuote | None:
    symbol = data.get('id') or data.get('symbol')
    price = data.get('price')
    prev_close = data.get('previousClose', 0)

    # Calculate change and percent
    change = price - prev_close if prev_close else 0
    change_pct = (change / prev_close * 100) if prev_close else 0

    return StreamingQuote(
        symbol=symbol,
        price=price,
        change=change,
        change_percent=change_pct,
        volume=data.get('dayVolume'),
        ...
    )
```

---

## VPR-098: Integrate Streaming into WatchlistPanel

### Problem
WatchlistPanel needs to consume streaming data and display real-time updates.

### Solution
Add streaming state and Textual Messages to WatchlistPanel for thread-safe UI updates.

### New Instance Variables
Add to `__init__` after `self._initial_load = True` (line 116):
```python
self._streaming_enabled: bool = False
self._streaming_quotes: dict[str, StreamingQuote] = {}
self._streaming_service: StreamingService | None = None
self._connection_state: ConnectionState = ConnectionState.DISCONNECTED
```

### New Message Classes
Add after existing `TickerSelected` class (after line 99):
```python
class StreamingQuoteReceived(Message):
    """Posted when a streaming quote arrives."""
    def __init__(self, quote: StreamingQuote) -> None:
        super().__init__()
        self.quote = quote

class StreamingStateChanged(Message):
    """Posted when connection state changes."""
    def __init__(self, state: ConnectionState) -> None:
        super().__init__()
        self.state = state
```

### CRITICAL: Callback-to-Message Bridge
StreamingService callbacks run in WebSocket's async context. To safely post Textual Messages, **must use `app.call_from_thread()`**:

```python
def _on_streaming_quote(self, quote: StreamingQuote) -> None:
    """Callback from StreamingService - runs in WebSocket context."""
    self._streaming_quotes[quote.symbol] = quote
    # Thread-safe way to post message to Textual event loop
    if self.app:
        self.app.call_from_thread(self.post_message, self.StreamingQuoteReceived(quote))

def _on_connection_state_change(self, state: ConnectionState) -> None:
    """Callback from StreamingService when connection state changes."""
    self._connection_state = state
    if self.app:
        self.app.call_from_thread(self.post_message, self.StreamingStateChanged(state))
```

### Enable/Disable Methods
```python
async def _enable_streaming(self) -> None:
    """Enable real-time streaming mode."""
    if self._streaming_enabled:
        return

    try:
        self._streaming_service = StreamingService.get_instance()
        await self._streaming_service.start(
            on_quote=self._on_streaming_quote,
            on_state_change=self._on_connection_state_change,
        )

        # Subscribe to all current watchlist tickers
        tickers = self._watchlist_manager.get_all()
        if tickers:
            await self._streaming_service.subscribe(tickers)

        self._streaming_enabled = True
        self._render_items()
    except Exception as e:
        # Failed to start - stay in polling mode
        get_logger().error(f'Failed to enable streaming: {e}')
        self._streaming_enabled = False
        self._streaming_service = None
        if self.app:
            self.app.notify('Streaming unavailable - using polling', severity='warning')

async def _disable_streaming(self) -> None:
    """Disable streaming and return to polling-only mode."""
    if not self._streaming_enabled:
        return

    if self._streaming_service:
        await self._streaming_service.stop()
        self._streaming_service = None

    self._streaming_enabled = False
    self._streaming_quotes.clear()
    self._connection_state = ConnectionState.DISCONNECTED
    self._render_items()

def toggle_streaming(self) -> None:
    """Toggle between polling and streaming modes."""
    if self._streaming_enabled:
        self.run_worker(self._disable_streaming())
    else:
        self.run_worker(self._enable_streaming())
```

### IMPORTANT: Polling Behavior
**Polling continues during streaming.** Do NOT stop the `set_interval` timer.
- Reason: Streaming may not have data for all symbols immediately
- Streaming quotes take precedence when both are available
- Polling provides fallback data

### Modify `_render_items()` - Data Selection Logic
Replace `quote = self._quotes.get(ticker)` with:
```python
# Prefer streaming quote if available and streaming is enabled
streaming_quote = self._streaming_quotes.get(ticker) if self._streaming_enabled else None
polling_quote = self._quotes.get(ticker)

if streaming_quote:
    # Use streaming data
    line = self._format_streaming_quote_line(ticker, streaming_quote)
    change_pct = streaming_quote.change_percent
elif polling_quote and not isinstance(polling_quote, QuoteError):
    # Fall back to polling data
    line = self._format_quote_line(ticker, polling_quote)
    change_pct = (polling_quote.change_percent if hasattr(polling_quote, 'change_percent')
                  else polling_quote.change_24h_percent)
elif polling_quote:  # QuoteError
    line = f'{ticker}: Error'
    change_pct = 0.0
else:
    line = f'{ticker}: Loading...'
    change_pct = 0.0
```

### New Format Method for StreamingQuote
```python
def _format_streaming_quote_line(self, ticker: str, quote: StreamingQuote) -> str:
    """Format a streaming quote for display."""
    price_str = f'${quote.price:,.2f}'

    if quote.change_percent > 0:
        change_str = f'+{quote.change_percent:.2f}%'
    elif quote.change_percent < 0:
        change_str = f'{quote.change_percent:.2f}%'
    else:
        change_str = '0.00%'

    # MUST match existing format: '{ticker:8s} {price_str:>12s} {change_str:>8s}'
    return f'{ticker:8s} {price_str:>12s} {change_str:>8s}'
```

### Modify Header Rendering
Add at start of `_render_items()` (before line 157):
```python
# Update header to show streaming state
header = self.query_one('.panel-header', Label)
if self._streaming_enabled:
    if self._connection_state == ConnectionState.CONNECTED:
        header.update('WATCHLIST [LIVE]')
    elif self._connection_state == ConnectionState.CONNECTING:
        header.update('WATCHLIST [CONNECTING...]')
    elif self._connection_state == ConnectionState.RECONNECTING:
        header.update('WATCHLIST [RECONNECTING...]')
    else:
        header.update('WATCHLIST')
else:
    header.update('WATCHLIST')
```

### Modify `on_ticker_added()` (line 262)
```python
def on_ticker_added(self, ticker: str) -> None:
    """Handle a ticker being added to the watchlist."""
    # Subscribe to streaming if active
    if self._streaming_enabled and self._streaming_service:
        self.run_worker(self._streaming_service.subscribe([ticker]))
    # Always refresh polling quotes
    self.run_worker(self.refresh_quotes())
```

### Modify `on_ticker_removed()` (line 270)
```python
def on_ticker_removed(self, ticker: str) -> None:
    """Handle a ticker being removed from the watchlist."""
    # Unsubscribe from streaming if active
    if self._streaming_enabled and self._streaming_service:
        self.run_worker(self._streaming_service.unsubscribe([ticker]))
    # Clean up cached quotes
    if ticker in self._quotes:
        del self._quotes[ticker]
    if ticker in self._streaming_quotes:
        del self._streaming_quotes[ticker]
    self._render_items()
```

### Message Handlers
```python
def on_watchlist_panel_streaming_quote_received(
    self, event: StreamingQuoteReceived
) -> None:
    """Handle streaming quote message - re-render display."""
    self._render_items()

def on_watchlist_panel_streaming_state_changed(
    self, event: StreamingStateChanged
) -> None:
    """Handle connection state change - update header."""
    self._connection_state = event.state
    self._render_items()
```

---

## VPR-099: Add Keybinding and App Integration

### Problem
Users need a way to toggle streaming mode.

### Solution
Add `s` keybinding and integrate with StatusBar for visual feedback.

### Acceptance Criteria
- Add `s` keybinding to ViperApp BINDINGS list
- `action_toggle_streaming` queries WatchlistPanel and calls `toggle_streaming()`
- Handle `StreamingStateChanged` message bubbled from WatchlistPanel
- Update StatusBar based on connection state
- Show user notification on toggle: "Streaming enabled" / "Streaming disabled"
- Add command palette entry: category='Watchlist', label='Toggle Real-time Mode'

### StatusBar Text Mapping
| Connection State | StatusBar Display |
|------------------|-------------------|
| CONNECTED | `Streaming` |
| CONNECTING | `Connecting...` |
| RECONNECTING | `Reconnecting...` |
| DISCONNECTED/ERROR | (empty/default) |

### Constraints
- Follow existing keybinding patterns in app.py (see 'r' for refresh, 'o' for options)
- Follow existing command palette patterns in ViperCommands tuple
- Must NOT conflict with existing keybindings
- Message handler naming must follow Textual convention: `on_<widget>_<message_name>`

---

## VPR-100: Visual Indicators for Streaming Mode

### Problem
Users need visual confirmation that streaming is active and working.

### Solution
Update watchlist header to show streaming state.

### Header Text Mapping
| State | Header Text |
|-------|-------------|
| Polling (default) | `WATCHLIST` |
| Streaming connected | `WATCHLIST [LIVE]` |
| Streaming connecting | `WATCHLIST [CONNECTING...]` |
| Streaming reconnecting | `WATCHLIST [RECONNECTING...]` |

### Acceptance Criteria
- Header update logic in `_render_items()` to stay in sync
- Use `query_one('.panel-header', Label)` to find header widget
- No visual flicker during rapid streaming updates
- Update help_screen.py HELP_TEXT with `s` keybinding

### Constraints
- Header indicator is implemented in VPR-098's `_render_items()` - this story validates it works
- Do NOT add animation or color changes that could cause flicker
- Keep indicator text concise (terminal width is limited)

---

## VPR-101: Add streaming_enabled Config Option

### Problem
Power users may want streaming enabled by default on startup.

### Solution
Add `streaming_enabled` boolean to Config dataclass.

### Config Option
```toml
# ~/.config/viper/config.toml
streaming_enabled = false  # Set to true to enable streaming on startup
```

| Setting | Default | Type | Description |
|---------|---------|------|-------------|
| `streaming_enabled` | `false` | bool | Enable real-time streaming for watchlist on startup |

### Acceptance Criteria
- Add `streaming_enabled: bool = False` to Config dataclass
- Load from config.toml, validate is boolean type
- If invalid type: log warning, use default False
- WatchlistPanel accepts `streaming_enabled` parameter in `__init__`
- If enabled, call `_enable_streaming()` in `on_mount()`
- app.py reads config and passes to WatchlistPanel constructor
- Update README.md Configuration section

### Constraints
- Follow existing config field patterns (see `refresh_interval`, `chart_refresh_interval`)
- Follow existing validation patterns in `__post_init__`
- Auto-enable on mount must handle errors gracefully (fall back to polling)

---

## Files to Create

| File | Purpose |
|------|---------|
| `viper/services/streaming.py` | StreamingService, StreamingQuote, ConnectionState |
| `tests/test_streaming.py` | Unit tests for streaming service |

## Files to Modify

| File | Changes |
|------|---------|
| `viper/services/__init__.py` | Export streaming module |
| `viper/widgets/watchlist_panel.py` | Streaming integration, messages, toggle |
| `viper/widgets/status_bar.py` | Add streaming state display |
| `viper/app.py` | Add 's' keybinding, handle state messages, command palette |
| `viper/config.py` | Add streaming_enabled option |
| `viper/widgets/help_screen.py` | Document 's' keybinding |
| `README.md` | Document streaming_enabled config option |

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ViperApp                                 │
│                                                                  │
│  ┌────────────────┐     ┌──────────────────┐    ┌────────────┐  │
│  │ WatchlistPanel │◄────│ Textual Messages │◄───│ Streaming  │  │
│  │                │     │                  │    │ Service    │  │
│  │ _render_items()│     │ QuoteReceived    │    │            │  │
│  │                │     │ StateChanged     │    │ subscribe()│  │
│  └────────────────┘     └──────────────────┘    │ listen()   │  │
│                                                  └─────┬──────┘  │
│                                                        │         │
│                                              ┌─────────▼───────┐ │
│                                              │ yfinance        │ │
│                                              │ AsyncWebSocket  │ │
│                                              │                 │ │
│                                              │ Yahoo Finance   │ │
│                                              │ WebSocket       │ │
│                                              └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

- [ ] StreamingService connects and receives real-time quotes
- [ ] Pressing `s` toggles between polling and streaming modes
- [ ] Watchlist header shows `[LIVE]` when streaming is active
- [ ] Status bar shows connection state
- [ ] Adding/removing tickers updates subscriptions correctly
- [ ] Streaming gracefully falls back to polling on failure
- [ ] Config option `streaming_enabled` works
- [ ] No performance degradation when streaming is active
- [ ] All existing polling functionality unchanged
- [ ] All tests pass with >= 87% coverage
- [ ] mypy --strict passes with no errors

---

## Risk Assessment

**Level: MEDIUM**

| Risk | Mitigation |
|------|------------|
| First WebSocket integration | Polling remains default fallback |
| Yahoo WebSocket availability | yfinance handles reconnection |
| Connection lifecycle complexity | Singleton pattern, proper cleanup |
| Increased network usage | Opt-in feature, not default |

---

## Exploratory Goals

This feature is intentionally scoped to watchlist only. The goals are:

1. **Validate yfinance AsyncWebSocket** - Understand its behavior, reliability, and update frequency
2. **Test Textual integration** - Ensure message-based updates work smoothly
3. **Measure performance impact** - Assess app responsiveness with streaming active
4. **Identify issues early** - Rate limiting, connection stability, resource usage

### Future Expansion (Post-Validation)
- Real-time candlestick chart updates
- Price alerts and notifications
- News panel with live ticker mentions

---

## Out of Scope

- Real-time chart streaming (future feature)
- Price alerts based on streaming data
- Historical data via WebSocket (not supported)
- Custom WebSocket endpoints
- Per-ticker streaming toggle
- Streaming for options data
