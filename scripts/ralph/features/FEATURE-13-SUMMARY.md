# Feature 13: Real-time Chart Tip Updates

## Summary

Extend the streaming infrastructure (Feature 12) to update the "tip" (most recent candle/point) of the chart in real-time. When streaming is active and the chart is visible, the last data point updates live as prices change.

**Scope:** Only the last interval (day/week/month based on chart timeframe) updates in real-time. Historical data remains static. Works for both candlestick and braille chart modes.

## Stories Overview

| ID | Title | Effort | Priority | Dependencies |
|----|-------|--------|----------|--------------|
| VPR-102 | Add multi-listener support to StreamingService | Small | 1 | Feature 12 |
| VPR-103 | ChartPanel streaming integration | Medium | 2 | VPR-102 |

**Dependency Flow:** VPR-102 -> VPR-103

---

## VPR-102: Add Multi-listener Support to StreamingService

### Problem
StreamingService currently accepts a single `on_quote` callback in `start()`. For ChartPanel to also receive quotes independently of WatchlistPanel, we need multiple listeners.

### Solution
Add listener registration methods to StreamingService:
- `add_quote_listener(callback)` - Register a callback to receive StreamingQuotes
- `remove_quote_listener(callback)` - Unregister a callback

Internally, maintain a list of listeners and invoke all of them when quotes arrive.

### Key Behaviors
- Multiple components can register listeners independently
- Each listener receives all quotes (filtering by symbol is caller's responsibility)
- Removing a listener that doesn't exist is a no-op (no error)
- The original `on_quote` parameter in `start()` remains for backward compatibility (registers as first listener)

### Acceptance Criteria
- [ ] `add_quote_listener(callback)` adds callback to internal list
- [ ] `remove_quote_listener(callback)` removes callback from list
- [ ] All registered listeners called when quote arrives
- [ ] Backward compatible with existing `start(on_quote=...)` usage
- [ ] Tests for add/remove/multiple listeners

---

## VPR-103: ChartPanel Streaming Integration

### Problem
ChartPanel displays static historical data. When streaming is active, the chart should update its last candle/point in real-time.

### Solution
ChartPanel subscribes to StreamingService for its current ticker and updates the tip data when quotes arrive.

### Subscription Lifecycle
- **On load_chart():** Subscribe to new ticker, unsubscribe from previous if any
- **On unmount:** Unsubscribe and remove listener (cleanup)
- **On streaming disabled:** No subscription, use polling data only

### Tip Update Logic

**Candlestick mode:**
- Update `prices[-1]` (close) with streaming price
- Update `highs[-1]` if streaming `day_high` exceeds current
- Update `lows[-1]` if streaming `day_low` is below current
- Update `volumes[-1]` with streaming volume
- Open price unchanged (from historical data)

**Braille/Line mode:**
- Update `prices[-1]` with streaming price
- Re-render chart

### Throttling
Start without throttling (update on every quote). If visual flicker becomes an issue, add throttling as a follow-up optimization.

### State Tracking
ChartPanel needs to track:
- Whether currently subscribed to streaming
- Which ticker is subscribed
- Reference to its quote listener callback (for removal)

### Acceptance Criteria
- [ ] ChartPanel subscribes when loading a ticker (if streaming enabled)
- [ ] ChartPanel unsubscribes when switching tickers
- [ ] ChartPanel unsubscribes and removes listener on unmount
- [ ] Last candle close price updates from streaming
- [ ] Last candle high/low update when exceeded
- [ ] Last candle volume updates from streaming
- [ ] Stats row recalculates with updated tip data
- [ ] Works for candlestick mode
- [ ] Works for braille/line mode
- [ ] No errors when streaming unavailable or disabled

---

## Technical Notes

### Open Price
StreamingQuote doesn't include open price. The open from historical data is correct for the period (market open for daily charts, period start for weekly/monthly).

### Symbol Filtering
ChartPanel's listener receives all streaming quotes. Filter to only process quotes matching `self._current_ticker`.

### Coexistence with WatchlistPanel
Both panels may subscribe to the same symbol. StreamingService handles this - the WebSocket subscription is shared, both listeners receive the quotes.

## Out of Scope
- Sub-daily chart intervals (1h, 15m, etc.)
- Historical backfill from streaming data
- Streaming-only mode (historical data always loaded first)

## Estimated Effort
**Total: Small-Medium (1-2 days)**
