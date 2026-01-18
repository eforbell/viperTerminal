# Feature 10: Candlestick Chart View

## Summary

Add an alternative price chart visualization using candlestick patterns. Users can toggle between the existing line chart and candlestick view with a single keypress. This feature builds on the existing chart infrastructure with minimal disruption - the line chart remains the stable default.

## Why Candlesticks?

| Line Chart | Candlestick Chart |
|------------|-------------------|
| Shows closing prices only | Shows Open, High, Low, Close (OHLC) |
| Good for trend overview | Shows intraday price range |
| Simple and clean | Reveals market sentiment per period |
| Familiar to casual users | Standard format for traders |

Candlesticks provide more information per data point, showing not just where the price ended but how it moved during each period.

## New Keybinding

| Key | Action |
|-----|--------|
| `v` | Toggle chart view: Line -> Candlestick -> Line |

The 'v' key (for "view") cycles between chart styles. No data refetch needed - same OHLC data, different rendering.

## Interval Display

When candlestick mode is active, the header shows what each candle represents:

```
AAPL - 1M Chart [Candlestick · Daily]
AAPL - 5Y Chart [Candlestick · Weekly]
AAPL - MAX Chart [Candlestick · Monthly]
```

| Period | Interval | Each Candle = |
|--------|----------|---------------|
| 1W | 1d | 1 Day |
| 1M | 1d | 1 Day |
| 3M | 1d | 1 Day |
| 6M | 1d | 1 Day |
| 1Y | 1d | 1 Day |
| 2Y | 1wk | 1 Week |
| 5Y | 1wk | 1 Week |
| MAX | 1mo | 1 Month |

This helps users understand the granularity of what they're viewing.

## Visual Preview

### Candlestick Anatomy

```
    │       ← Upper wick (high)
    │
   ███      ← Body (open to close)
   ███         Green = bullish (close > open)
   ███         Red = bearish (close < open)
    │
    │       ← Lower wick (low)
```

### Expected Chart Appearance

```
AAPL - $178.52 (+1.23%)                    [CANDLESTICK]
   $182.00 │
           │    ██
           │    ██ │
   $180.00 │ █  ██ ██    ██
           │ █  ██ ██ █  ██ █
   $178.00 │ ██ █  █  ██ █  ██ ██
           │ ██    │  ██    ██ ██
   $176.00 │ │        │       │
           └──────────────────────────────
           01/10                    01/17
```

Green candles show buying pressure (price up), red candles show selling pressure (price down).

## Stories (5 total)

| ID | Title | Effort | Purpose |
|----|-------|--------|---------|
| VPR-088 | Add CANDLESTICK to ChartStyle enum | Small | Foundation - extend existing enum |
| VPR-089 | Implement candlestick rendering logic | Medium | Core rendering with OHLC display |
| VPR-090 | Add chart style toggle keybinding | Small | 'v' key to switch views |
| VPR-091 | Ensure overlay compatibility | Small | SMA/EMA work on candlesticks |
| VPR-092 | Handle edge cases and polish | Small | Various timeframes, crypto, resize |

### Dependency Graph

```
VPR-088 (enum) → VPR-089 (rendering) → VPR-090 (toggle) → VPR-091 (overlays) → VPR-092 (polish)
```

## Technical Approach

### Why This Is Low-Risk

| Factor | Details |
|--------|---------|
| Data already exists | `HistoricalData` has `opens`, `closes`, `highs`, `lows` |
| Architecture ready | `ChartStyle` enum has BRAILLE/BLOCK - add CANDLESTICK |
| Isolated change | New `_render_candlestick()` method, existing code untouched |
| Easy rollback | Line chart remains default, candlestick is opt-in |

### Rendering Strategy

```python
# Add to ChartStyle enum
class ChartStyle(Enum):
    BRAILLE = "braille"      # Existing
    BLOCK = "block"          # Existing
    CANDLESTICK = "candlestick"  # New

# Single character per candle for maximum density
def _render_candlestick(self, ...) -> RenderedChart:
    # For each data point:
    # 1. Calculate body position (open to close)
    # 2. Draw upper wick (body top to high)
    # 3. Draw lower wick (body bottom to low)
    # 4. Color green if close > open, red otherwise
```

### Downsampling OHLC Data

When screen width < data points, we create representative candles:

```python
def _downsample_ohlc(self, ohlc_data, target_size):
    # Group periods and create representative candle:
    # - Open: First open in group
    # - High: Max high in group
    # - Low: Min low in group
    # - Close: Last close in group
```

This preserves the price range information that would be lost with simple averaging.

### Y-Axis Scaling

```python
# Line chart: uses close prices
min_price = min(closes)
max_price = max(closes)

# Candlestick: must use high/low for full wicks
min_price = min(lows)
max_price = max(highs)
```

## Unicode Characters

| Purpose | Characters | Notes |
|---------|------------|-------|
| Candle body | `▁▂▃▄▅▆▇█` | Block height shows body size |
| Wicks | `│` `╎` `┆` | Thin vertical lines |
| Combined | Braille patterns | For sub-character precision |

Start simple with blocks, iterate on visual quality.

## Compatibility

### Indicators Still Work

| Component | Status |
|-----------|--------|
| SMA/EMA overlays | Work on candlestick view |
| RSI panel | Unchanged (below chart) |
| MACD panel | Unchanged (below chart) |
| Volume bars | Aligned with candlesticks |

### All Timeframes Supported

| Timeframe | Notes |
|-----------|-------|
| 1W | ~5 candles, clearly visible |
| 1M | ~20-22 candles |
| 3M/6M | Downsampled as needed |
| 1Y | Weekly candles effectively |
| 5Y/MAX | Monthly candles effectively |

## Files Modified

**Modified:**
- `viper/widgets/chart_renderer.py` - Add CANDLESTICK style and `_render_candlestick()`
- `viper/widgets/chart_panel.py` - Add 'v' keybinding and style state
- `viper/widgets/help_screen.py` - Document 'v' keybinding

**New:**
- `tests/test_candlestick_renderer.py` - Candlestick-specific tests

## Success Criteria

- [ ] 'v' key toggles between line and candlestick view
- [ ] Candlesticks clearly show open, high, low, close
- [ ] Bullish candles are green, bearish candles are red
- [ ] Wicks visible extending from candle bodies
- [ ] Overlays (SMA/EMA) work on candlestick view
- [ ] Volume bars align correctly with candlesticks
- [ ] RSI/MACD panels unaffected by chart style
- [ ] No regression in existing line chart functionality
- [ ] Works with all timeframes (1W through MAX)
- [ ] Works with both stocks and crypto
- [ ] All tests pass with >= 90% coverage
- [ ] mypy --strict passes

## Out of Scope (Future Features)

- Heikin-Ashi candles (smoothed candlesticks)
- Candle pattern recognition (doji, hammer, engulfing, etc.)
- Hollow vs filled candle option
- Customizable candle colors
- Multi-timeframe candlestick comparison

## Risk Assessment

**Level: LOW**

| Risk | Mitigation |
|------|------------|
| Breaks line chart | Additive code only - existing render methods untouched |
| Performance | Same data, just different rendering - no new API calls |
| Terminal compatibility | Same Unicode approach as existing braille charts |
| Visual quality | Start simple, iterate - can always toggle back to line |

## Why This Matters

Candlestick charts are the standard for technical analysis. Adding this view:

1. **Familiarity** - Traders expect candlestick charts
2. **More information** - See price range, not just closing price
3. **Market sentiment** - Green/red immediately shows direction
4. **Professional feel** - Elevates Viper from "stock ticker" to "trading terminal"

The toggle approach means users who prefer line charts keep their familiar view, while traders get the candlestick option they expect.
