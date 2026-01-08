# Defect: RSI Panel Width Shorter Than Volume Bars

## Problem
The RSI indicator panel renders with a fixed width of 70 characters, while the volume 
bars dynamically calculate their width based on the chart area. This causes RSI to 
appear shorter than the volume bars, breaking visual alignment.

## Root Cause
In `indicator_panel.py`, the chart width is hardcoded:
```python
chart_width = 70  # Reserve space for padding
```

Volume bars use dynamic width calculation in `chart_panel.py`:
```python
chart_area_width = available_width - dimensions.y_axis_width
```

## Solution
1. Pass the chart width to the indicator panel's `show_indicator()` method
2. Store and use this width for rendering instead of hardcoded value
3. Ensure the indicator panel respects the same width as volume bars

## Files Affected
- `viper/widgets/indicator_panel.py` - Add width parameter
- `viper/widgets/chart_panel.py` - Pass width to RSI panel
