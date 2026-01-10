# Feature 7: MACD Indicator

## Summary

Add MACD (Moving Average Convergence Divergence) technical indicator to chart view. MACD is a trend-following momentum indicator showing the relationship between two moving averages. This feature follows the established IndicatorPanel pattern from RSI and leverages the ChartContext architecture from Feature 5.

## What is MACD?

**MACD Components:**
- **MACD Line**: 12-period EMA minus 26-period EMA (fast-moving line)
- **Signal Line**: 9-period EMA of the MACD line (slow-moving trigger line)
- **Histogram**: MACD line minus Signal line (visual divergence representation)

**Trading Signals:**
- **Bullish Crossover**: MACD crosses above Signal → potential buy signal
- **Bearish Crossover**: MACD crosses below Signal → potential sell signal
- **Zero Line Cross**: MACD crossing zero indicates trend direction change
- **Divergence**: Price makes new high/low but MACD doesn't → trend reversal warning

## Visual Design

```
Chart Layout with MACD:
┌─────────────────────────────────────────┐
│ Price Chart + Volume (always visible)   │
│ ▂▃▄▅▆▇█▇▆▅▄▃▂▁  [cyan line]           │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ RSI: 52.34  [cyan line + red/green ref] │
│ ▃▄▅▄▃▂▃▄▅▆▅▄▃▂  (0-100 scale)         │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ MACD: 1.23  Signal: 0.87  Hist: 0.36   │
│ ▂▃▄▅▄▃▂▁ [cyan] MACD line               │
│ ▁▂▃▄▃▂▁  [yellow] Signal line           │
│ ▃▄▅▆▅▄▃ [green/red] Histogram           │
│ ─────────────────── [white] Zero line   │
│                     (-10 to +10 scale)  │
└─────────────────────────────────────────┘
└─────────────────────────────────────────┘
│ X-Axis (shared, rendered once at bottom)│
└─────────────────────────────────────────┘
```

**Colors:**
- MACD Line: `[cyan]` (consistent with RSI)
- Signal Line: `[yellow]` (distinct from MACD)
- Histogram: `[green]` for positive, `[red]` for negative
- Zero Line: `[white]` or `[dim white]`

## Key Differences from RSI

| Aspect | RSI | MACD |
|--------|-----|------|
| Scale | 0 to 100 (always positive) | -10 to +10 (can be negative) |
| Components | 1 line | 3 lines (MACD + Signal + Histogram) |
| Reference Lines | 70 (overbought), 30 (oversold) | 0 (zero line) |
| Height | 4 lines | 7 lines (needs room for histogram) |
| Data Requirement | 15 prices (14 + 1) | 34 prices (33 + 1) |
| Interpretation | Momentum (overbought/oversold) | Trend (convergence/divergence) |

## Stories (6 total)

| ID | Title | Effort | Purpose |
|----|-------|--------|---------|
| VPR-070 | Prefix keybinding system | Medium | Implement 't' prefix, refactor RSI/MA keys |
| VPR-071 | MACD calculation service | Small | Pure math function |
| VPR-072 | MACDPanel widget | Medium | UI component with 3 lines + histogram |
| VPR-073 | ChartPanel integration | Medium | Add to compose(), caching, toggle |
| VPR-074 | Add MACD to keybindings | Small | 't-m' routing, documentation |
| VPR-075 | Testing & polish | Small | Integration tests, visual verification |

### Dependency Graph

```
VPR-070 (prefix keys) ──┬──→ VPR-074 (add MACD to keys) ──→ VPR-075 (test)
                        │                                        ↑
VPR-071 (MACD calc) ────→ VPR-072 (widget) ──→ VPR-073 (integrate) ──┘
```

**Key Point:** VPR-070 establishes prefix system and refactors existing indicators BEFORE adding MACD. This lets us test the pattern with RSI/MA, then add MACD to proven infrastructure.

## Technical Details

### MACD Calculation

```python
def calculate_macd(
    prices: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """
    Returns: (macd_line, signal_line, histogram)
    
    Formula:
    1. fast_ema = calculate_ema(prices, 12)
    2. slow_ema = calculate_ema(prices, 26)
    3. macd_line = fast_ema - slow_ema
    4. signal_line = calculate_ema(macd_line, 9)
    5. histogram = macd_line - signal_line
    
    First 33 values are None:
    - 25 None from 26-period slow EMA
    - 8 more None from 9-period signal EMA
    - Total: 33 None values
    """
```

### Histogram Rendering Strategy

Histogram is rendered using vertical bars **centered at zero line**:

- **Positive values** (MACD > Signal): Green bars extending upward from zero
- **Negative values** (MACD < Signal): Red bars extending downward from zero
- **Character set**: Use block chars `▁▂▃▄▅▆▇█` for varying heights
- **Alignment**: Histogram bars align with MACD/Signal data points

Similar to volume bars but centered instead of bottom-aligned.

### MACDPanel Configuration

```python
class MACDPanel(IndicatorPanel):
    def __init__(self):
        super().__init__(
            name="MACD",
            min_value=-10.0,
            max_value=10.0,
            height=7,  # More height than RSI (4)
            reference_lines=[
                HorizontalLine(
                    value=0.0,
                    label="0",
                    style="solid",
                    color="white"
                )
            ]
        )
```

### Integration Pattern (Follow RSI)

**ChartPanel changes:**
```python
def compose(self):
    yield Container(id="chart-content")
    yield self._rsi_panel    # Existing
    yield self._macd_panel   # NEW - stacks below RSI

def show_chart(self, data: HistoricalData):
    # Calculate MACD
    macd, signal, hist = calculate_macd(data.prices, 12, 26, 9)
    self._macd_line = macd
    self._signal_line = signal
    self._histogram = hist
    
    # Update MACD panel (even if hidden to avoid stale data)
    if self._macd_panel and len(data.prices) >= 34:
        self._macd_panel.show_macd(
            macd, signal, hist, 
            context=self._chart_context
        )
```

**Keybinding (Prefix System):**
- Prefix: `t` (for "technical" indicators)
- Key: `t` then `m` (for MACD)
- Action: `toggle_macd`
- Works when chart is visible (check `_chart_panel_visible`)
- Each toggle requires full `t-m` press (stateless, no mode)

**Other Technical Indicator Keys:**
- `t` `r` - Toggle RSI (refactored from `r`)
- `t` `m` - Toggle MACD (new)
- `t` `a` - Cycle MA (refactored from `m`, cycles: off → SMA20 → SMA50 → both)
- Future: `t` `s` - Stochastic, `t` `b` - Bollinger Bands

## Existing Foundation (Already Built)

✅ **IndicatorPanel Base Class** (VPR-038):
- Handles sub-panel rendering, reference lines, braille charts
- Receives ChartContext for perfect alignment
- Has show_indicator() pattern to follow

✅ **ChartContext** (Feature 5):
- Provides `chart_area_width` for horizontal alignment
- Immutable dataclass, safe to pass around
- Used by RSI, will be used by MACD

✅ **EMA Calculation** (VPR-034):
- `calculate_ema(prices, period)` already implemented
- Returns list[float | None] with proper None handling
- MACD will call this 3 times (fast, slow, signal)

✅ **RSI Implementation Pattern** (VPR-039):
- Shows how to extend IndicatorPanel
- Shows integration into ChartPanel
- Shows toggle behavior and keybinding
- MACD follows this exact pattern

## Files to Create

**New:**
- `viper/widgets/macd_panel.py` - MACDPanel widget class
- `tests/test_macd_calculation.py` - Unit tests for calculate_macd()
- `tests/test_macd_panel.py` - Widget tests for MACDPanel

**Modified:**
- `viper/services/indicators.py` - Add calculate_macd() function
- `viper/widgets/chart_panel.py` - Integrate MACD panel
- `viper/app.py` - Add 'm' keybinding
- `viper/widgets/help_screen.py` - Document MACD
- `viper/widgets/__init__.py` - Export MACDPanel

## Success Criteria

- [ ] MACD displays with 3 components (line, signal, histogram)
- [ ] Histogram colors render correctly (green positive, red negative)
- [ ] MACD aligns horizontally with price chart and RSI
- [ ] Toggle 'm' works with RSI also visible (both can show simultaneously)
- [ ] MACD updates immediately when ticker changes (no stale data)
- [ ] Crossovers between MACD and Signal are visually clear
- [ ] All tests pass (unit, widget, integration)
- [ ] Coverage ≥ 90%
- [ ] mypy --strict passes
- [ ] Works at 80x24 minimum terminal size

## Out of Scope (Future Features)

- MACD period configuration (use standard 12/26/9)
- Histogram style options (bars only, no fill)
- Automated divergence detection/alerts
- MACD histogram color gradient
- Other indicators (Stochastic, Bollinger Bands)

## Why MACD is Important

1. **Trend Following**: Shows trend strength and direction changes
2. **Momentum**: Identifies acceleration/deceleration of price movement
3. **Crossovers**: Clear buy/sell signals when lines cross
4. **Divergence**: Early warning of trend reversals
5. **Complements RSI**: RSI shows overbought/oversold, MACD shows trend

MACD + RSI together provide comprehensive technical analysis view.

## Next Steps After Feature 7

With MACD complete, we'll have:
- ✅ Price chart with volume overlay
- ✅ Moving averages (SMA, EMA) on price chart
- ✅ RSI oscillator (momentum indicator)
- ✅ MACD oscillator (trend indicator)

**Future indicators to consider:**
- Stochastic Oscillator (momentum, 0-100 scale like RSI)
- Bollinger Bands (volatility, overlay on price chart)
- Volume indicators (OBV, Volume Rate of Change)
