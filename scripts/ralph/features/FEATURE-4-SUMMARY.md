# Feature 4: Chart Layout Bug Fixes

## Summary

This feature fixes critical layout bugs in the chart panel. After Feature 4 is complete, you'll have a **fully working chart view** with volume and RSI displaying correctly. Architectural improvements (ChartContext, X-axis extraction) are deferred to Feature 5.

## Bugs Being Fixed

| Bug | File | Fix Story |
|-----|------|-----------|
| Volume/X-axis hidden when RSI visible | volume-bar-occlusion-with-RSI-loaded.png | **VPR-043** |
| RSI shows stale data on ticker switch | rsi-defect-2, rsi-defect-3 | VPR-041 |
| Volume toggle adds complexity | - | VPR-042 (removal) |

## Root Cause

The bug is in `ChartPanel._render_chart()` height calculation:

```python
# BUGGY CODE:
rsi_height = 7 if self.is_rsi_visible() else 0
available_height = self.size.height - 7 - volume_height - rsi_height  # BUG!
```

When RSI is visible, it takes 8 lines (7 height + 1 margin-top) from #chart-content's space
We must account for this because self.size.height is ChartPanel's full height,
but #chart-content (where we render) gets reduced when RSI is visible

## Stories (5 total, focused on fixes)

| ID | Title | Effort | Purpose |
|----|-------|--------|---------|
| VPR-040 | Characterization tests | Medium | Capture current behavior BEFORE fixing |
| VPR-041 | Fix RSI stale data | Small | RSI updates on ticker change |
| VPR-042 | Remove volume toggle | Small | Simplify before core fix |
| VPR-043 | **Fix height calculation** | Medium | **CORE BUG FIX** |
| VPR-044 | Verification & cleanup | Small | Confirm all bugs fixed |

### Dependency Graph

```
VPR-040 ──────┬──────→ VPR-041 ──┐
(characterize)│                   │
              │                   ├──→ VPR-044 (verify)
VPR-042 ──────┴──────→ VPR-043 ──┘
(volume always)       (HEIGHT FIX)
```

## What's Deferred to Feature 5

| Item | Why Deferred |
|------|--------------|
| ChartContext dataclass | Architecture improvement, not bug fix |
| Perfect pixel alignment | "Good enough" alignment achieved in F4 |
| X-axis extraction | Architecture improvement, not bug fix |
| rsi-defect-1-width-mismatch | Fixed by ChartContext in F5 |

## Success Criteria for Feature 4

- [x] Volume bars visible when RSI is toggled on
- [x] X-axis visible when RSI is toggled on  
- [x] RSI updates when switching tickers
- [x] Volume always on (no toggle)
- [x] All tests pass, coverage ≥ 90%

## After Feature 4

You can **test and ship** the bug fixes. Feature 5 (architecture refactoring) starts on a fresh branch with:
- VPR-050: ChartContext dataclass
- VPR-051: Integrate ChartContext
- VPR-052: Extract X-axis
- VPR-053: Visual polish

## Files Modified (Feature 4 only)

- `viper/widgets/chart_panel.py` - fix height calc, remove volume toggle
- `viper/widgets/indicator_panel.py` - ensure refresh on show_indicator()
- `viper/app.py` - remove volume keybinding
- `viper/config.py` - remove volume_enabled
- `viper/widgets/help_screen.py` - update docs
