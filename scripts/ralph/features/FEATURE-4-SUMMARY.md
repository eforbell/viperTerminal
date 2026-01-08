# Feature 4: Chart Layout Architecture Refactoring

## Summary

This feature addresses layout bugs discovered when using RSI indicator with volume bars, where toggling visibility causes components to occlude each other. Rather than patching the symptoms, we're refactoring the chart panel architecture to establish consistent patterns for sub-panels.

## The Problem

The current `ChartPanel` has an inconsistent internal architecture:

| Component | Current Implementation | Problem |
|-----------|----------------------|---------|
| Price chart | Rendered as Labels in `#chart-content` | ✓ OK |
| Volume bars | Rendered as Labels in `#chart-content` | Special-cased, intertwined with chart height calc |
| RSI panel | Separate `IndicatorPanel` widget, sibling to `#chart-content` | Different widget type, causes layout conflicts |
| X-axis | Part of price chart render | Should be shared, rendered once at bottom |

When RSI is toggled, height calculations conflict, and volume bars (or X-axis labels) get visually occluded.

## The Solution

### New Architecture

```
ChartPanel (orchestrator)
│
├── ChartContext (shared immutable data)
│   └── dates, prices, volumes, chart_width, y_axis_width, period
│
├── Price + Volume Section
│   ├── Header, timeframe selector, stats
│   ├── Price chart lines (Y-axis + braille data)
│   └── Volume bars (always visible, embedded)
│
├── IndicatorPanel[] 
│   └── RSIPanel (receives ChartContext for alignment)
│
└── Shared X-Axis (rendered ONCE at bottom)
```

### Key Changes

1. **Volume is always on** - Simplifies logic, matches traditional charting UX
2. **ChartContext dataclass** - Single source of truth for dimensions and data
3. **X-axis extracted** - Rendered once after all panels, not inside price chart
4. **Explicit height management** - Parent calculates, children render within bounds

## Stories

| ID | Title | Complexity | Dependencies |
|----|-------|------------|--------------|
| VPR-040 | Create ChartContext shared data structure | Small | - |
| VPR-041 | Extract X-axis rendering to standalone component | Medium | VPR-040 |
| VPR-042 | Lock volume as always-on and clean up rendering | Small | - |
| VPR-043 | Refactor IndicatorPanel to use ChartContext | Medium | VPR-040 |
| VPR-044 | Refactor ChartPanel layout orchestration | Large | VPR-041, 042, 043 |
| VPR-045 | Visual polish and alignment verification | Small | VPR-044 |

## Critical Learnings to Apply

From `AGENTS.md` - these MUST be followed:

1. **NO ANSI ESCAPE CODES** - Use Rich markup `[green]text[/green]` not `\033[32m`
2. **Label markup=True** - Required for Rich markup colors to render
3. **Explicit heights** - Don't rely on CSS `auto` or `1fr` for predictable layout
4. **display toggle** - Use `styles.display = "block"/"none"` for visibility

## Scope

### In Scope
- Layout refactoring and bug fixes
- ChartContext shared data structure  
- X-axis extraction
- Volume always-on simplification
- RSI alignment fix

### Out of Scope
- New indicators (MACD, Stochastic)
- Candlestick rendering
- Semi-transparent overlapping volume

## Success Criteria

- [ ] RSI toggle works without occluding volume or X-axis
- [ ] RSI indicator aligns horizontally with price chart
- [ ] X-axis appears once at bottom in all states
- [ ] All 678+ tests pass
- [ ] Coverage ≥ 90%
- [ ] mypy --strict clean

## Estimated Effort

This is primarily a refactoring effort - the rendering logic is already working (braille charts, volume bars, RSI calculation). The work is reorganizing how these components are composed and how they share dimensions.

**Estimated: 4-6 stories, medium complexity overall**

## Files Affected

**Modify:**
- `viper/widgets/chart_panel.py` - main refactoring
- `viper/widgets/chart_renderer.py` - extract X-axis
- `viper/widgets/indicator_panel.py` - use ChartContext
- `viper/widgets/rsi_panel.py` - interface updates
- `viper/app.py` - remove volume keybinding
- `viper/config.py` - remove volume_enabled
- `viper/widgets/help_screen.py` - update docs

**Create:**
- `viper/widgets/chart_context.py` (or add to existing module)
