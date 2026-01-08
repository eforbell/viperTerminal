# Defect: RSI Shows Same Data for Different Tickers

## Problem
When switching between tickers (e.g., AAPL to STRC), the RSI panel displays 
identical-looking data for both, even though the price charts clearly show 
different price movements.

## Root Cause
The RSI is calculated in `_calculate_rsi()` which IS called from `show_chart()`. 
However, the RSI panel is only updated IF visible at the time of calculation:

```python
if self._rsi_panel and self._rsi_values:
    # Update only happens if panel exists and has values
```

But the panel may not be re-rendering with new data properly. The `show_indicator()` 
method is called, but the panel's internal state may not be triggering a visual refresh.

## Additional Issue
The `_calculate_rsi()` method updates the panel, but the visual update may not 
propagate correctly because `_render_content()` is called AFTER `_calculate_rsi()`, 
and the indicator panel is a sibling widget that doesn't get re-rendered by 
`_render_content()`.

## Solution
1. Ensure RSI panel refresh is explicitly called when ticker changes
2. Force RSI panel to re-render its content when `show_indicator()` is called
3. Check if `_render_content()` in indicator_panel.py is being invoked properly

## Files Affected
- `viper/widgets/indicator_panel.py` - Verify render logic
- `viper/widgets/chart_panel.py` - Ensure proper refresh sequence
