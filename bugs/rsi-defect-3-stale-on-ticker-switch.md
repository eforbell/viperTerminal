# Defect: RSI Panel Stays Resident When Switching Tickers

## Problem
When switching between tickers, the price chart and volume bars fully re-render 
with new data, but the RSI panel retains its old display until manually toggled 
off and on again.

## Root Cause
The RSI panel is a sibling widget to the chart content container, not a child.
When `_render_content()` clears and rebuilds the chart-content container, it 
doesn't touch the RSI panel widget:

```python
def _render_content(self) -> None:
    container = self.query_one("#chart-content", Container)
    container.remove_children()  # Only clears chart-content, not RSI panel
```

The RSI panel only updates via `show_indicator()`, which is called from 
`_calculate_rsi()`. But if the panel's `_render_content()` method isn't 
explicitly triggered, the visual display doesn't update.

## Solution
1. Force RSI panel to call its `_render_content()` after `show_indicator()` updates data
2. Alternatively, treat RSI panel refresh as part of the chart render cycle
3. Ensure RSI panel visibility state doesn't prevent data updates

## Files Affected
- `viper/widgets/indicator_panel.py` - Force re-render in show_indicator()
- `viper/widgets/chart_panel.py` - Coordinate RSI refresh with chart refresh
