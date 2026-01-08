# Defect: 6M Date Range Not Using Full Plot Area

## Problem
When viewing charts with the 6M (6 month) timeframe option (key "4"), the price chart 
data does not fill the entire horizontal plot area. Other timeframes (1W, 1M, 3M, 1Y, 
5Y, MAX) appear to use the full width correctly.

## Observed Behavior
- 6M charts show data clustered in approximately 2/3 of the chart width
- Empty space appears on the left side of the chart
- Volume and RSI indicators follow the same pattern (also truncated)

## Expected Behavior
- Chart data should span the full width of the plot area
- All timeframes should behave consistently

## Possible Causes
1. yfinance may return different data density for 6M period
2. Interpolation/upsampling logic may have edge case for 6M data count
3. Period mapping in yfinance may result in unusual data point count

## Files to Investigate
- `viper/services/history_data.py` - Period mapping and data fetching
- `viper/widgets/chart_renderer.py` - Interpolation logic thresholds
- `viper/widgets/chart_panel.py` - Dimension calculations

## Priority
Low - cosmetic issue, functionality works correctly
