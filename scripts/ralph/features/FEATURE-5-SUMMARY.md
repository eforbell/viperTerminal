# Feature 5: Chart Architecture Refactoring

## Summary

This feature builds on Feature 4's bug fixes to establish a clean, extensible architecture for chart components. Introduces ChartContext as single source of truth, perfect pixel alignment between price chart and indicators, and extracted X-axis rendering.

## Target Architecture (TradingView-style)

```
ChartPanel (orchestrator)
│
├── ChartContext (immutable shared data)
│   └── ticker, period, dates, prices, volumes
│   └── total_width, total_height, y_axis_width
│   └── chart_area_width (computed property)
│
├── #chart-content Container
│   ├── Header, timeframe selector, stats
│   ├── Price chart lines (Y-axis + braille data)
│   └── Volume bars (always visible, embedded)
│
├── IndicatorPanel[] (receive ChartContext for alignment)
│   └── RSIPanel (uses context.chart_area_width)
│   └── (future: MACDPanel, StochasticPanel)
│
└── Shared X-Axis (rendered ONCE at bottom)
    └── render_x_axis(context) → list[str]
```

**Key Principle:** All components use `context.chart_area_width` and `context.y_axis_width` for **perfect horizontal alignment**.

## Prerequisites

**Feature 4 must be complete and merged before starting Feature 5.**

After Feature 4:
- ✅ Volume bars always visible
- ✅ RSI toggles without occluding volume/X-axis
- ✅ RSI updates on ticker change
- ✅ All bugs fixed, working chart view

## Goals

| Goal | Story | Benefit |
|------|-------|---------|
| Single source of truth | VPR-050, VPR-051 | Clean dimension sharing |
| Perfect alignment | VPR-051 | RSI aligns exactly with price chart |
| Extracted X-axis | VPR-052 | Always visible, future-proof for MACD |
| Documentation | VPR-053 | AGENTS.md updated with learnings |

## Stories (4 total)

| ID | Title | Effort | Dependencies |
|----|-------|--------|--------------|
| VPR-050 | Create ChartContext dataclass | Small | - |
| VPR-051 | Integrate ChartContext | Medium | VPR-050 |
| VPR-052 | Extract X-axis rendering | Medium | VPR-051 |
| VPR-053 | Visual polish & testing | Small | VPR-051, VPR-052 |

### Dependency Graph (Linear)

```
VPR-050 → VPR-051 → VPR-052 → VPR-053
(context)  (integrate) (x-axis)  (polish)
```

## ChartContext Design

```python
@dataclass(frozen=True)
class ChartContext:
    ticker: str
    period: str
    dates: list[datetime]
    prices: list[float]
    volumes: list[int]
    opens: list[float]
    closes: list[float]
    total_width: int
    total_height: int
    y_axis_width: int = 12
    
    @property
    def chart_area_width(self) -> int:
        return self.total_width - self.y_axis_width
    
    @classmethod
    def from_historical_data(cls, data: HistoricalData, width: int, height: int) -> "ChartContext":
        ...
```

## What This Fixes

| Bug | How Fixed |
|-----|-----------|
| rsi-defect-1-width-mismatch | VPR-051: RSI uses context.chart_area_width |
| Hardcoded y_axis_padding | VPR-051: Uses context.y_axis_width |
| X-axis can be pushed out | VPR-052: Rendered once at bottom |

## Success Criteria

- [ ] ChartContext is single source of truth for dimensions
- [ ] RSI indicator aligns **perfectly** with price chart data
- [ ] X-axis rendered once at bottom, visible in all states
- [ ] All tests pass, coverage ≥ 90%
- [ ] Architecture documented, ready for MACD

## Files Modified

**New:**
- `viper/widgets/chart_context.py` - ChartContext dataclass
- `tests/test_chart_context.py` - unit tests

**Modified:**
- `viper/widgets/chart_panel.py` - integrate ChartContext
- `viper/widgets/chart_renderer.py` - extract X-axis, accept ChartContext
- `viper/widgets/indicator_panel.py` - use ChartContext for alignment
- `viper/widgets/rsi_panel.py` - pass ChartContext from parent

## Future Work Enabled

After Feature 5, adding new indicators (MACD, Stochastic) becomes straightforward:
1. Create new panel class extending IndicatorPanel
2. Add calculation to services/indicators.py
3. Panel receives ChartContext for alignment
4. X-axis automatically shared at bottom
