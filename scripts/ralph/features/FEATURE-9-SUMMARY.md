# Feature 9: Enhanced Options Explorer

## Summary

Extend the basic options chain (Feature 8) with practical analysis tools: filtering, near-the-money focus, IV color coding, volume/OI highlighting, multi-expiration summary view, and simplified IV rank. These enhancements transform the basic options viewer into a practical analysis tool.

## Prerequisites

Feature 9 builds directly on Feature 8. Complete and evaluate Feature 8 before starting this feature. Key evaluation points:

1. **Data fetch speed** - Is yfinance responsive enough for multi-expiration summary?
2. **Navigation feel** - Are users comfortable with `[` `]` for expiration cycling?
3. **Table readability** - Is column width sufficient for enhanced highlighting?

## New Keybindings

| Key | Action |
|-----|--------|
| `f` | Cycle filter: All -> ITM -> OTM -> All |
| `a` | Jump to ATM (at-the-money) strike |
| `s` | Toggle summary view (multi-expiration) |

Combined with Feature 8 keys: `o` (toggle), `j`/`k` (navigate), `[`/`]` (expiration), `c`/`p` (calls/puts)

## Visual Enhancements

### IV Color Coding

```
Strike    Bid     Ask    Last    Vol     OI      IV    ITM
──────────────────────────────────────────────────────────
 165.00   12.50   12.70   12.60   1,234   5,678   45%    Y   [red - high IV]
 167.50   10.30   10.50   10.40   2,345   8,901   38%    Y   [yellow - medium]
 170.00    8.20    8.40    8.30   5,678  12,345   32%    Y   [yellow - medium]
 172.50    6.10    6.30    6.20   3,456  10,234   25%    N   [green - low IV]
```

- **Green** (low IV): Options relatively cheap - good for buying
- **Yellow** (medium IV): Normal pricing
- **Red** (high IV): Options relatively expensive - good for selling

### Volume/OI Highlighting

```
Strike    Bid     Ask    Last    Vol      OI       IV    ITM
──────────────────────────────────────────────────────────
 170.00    8.20    8.40    8.30  *15,678  12,345   31%    Y   [* = high volume, bold]
 172.50    6.10    6.30    6.20   3,456  *45,678   29%    N   [* = high OI]
```

High volume/OI (>2x average) indicates institutional interest.

### Multi-Expiration Summary View

```
OPTIONS: AAPL | SUMMARY VIEW | Press Enter to expand
─────────────────────────────────────────────────────
Expiration    Call (ATM)      Put (ATM)      IV
─────────────────────────────────────────────────────
Mar 15      12.50 / 12.70   8.20 / 8.40    32%  ← selected
Mar 22      14.30 / 14.50   9.10 / 9.30    35%
Mar 29      16.20 / 16.40   10.50 / 10.70  38%
Apr 05      18.10 / 18.30   12.20 / 12.40  36%
Apr 12      19.80 / 20.00   13.60 / 13.80  34%
─────────────────────────────────────────────────────
IV Rank: 45% [yellow]
```

Quick overview of all expirations - Enter to drill into specific date.

## Stories (6 total)

| ID | Title | Effort | Purpose |
|----|-------|--------|---------|
| VPR-082 | Filter mode - ITM/OTM/All | Small | Focus on relevant strikes |
| VPR-083 | Near-the-money focus | Medium | Auto-scroll to ATM, 'a' key jump |
| VPR-084 | IV color coding | Medium | Visual IV analysis |
| VPR-085 | Volume/OI highlighting | Small | Spot institutional interest |
| VPR-086 | Multi-expiration summary | Medium | Quick overview of all expirations |
| VPR-087 | IV rank calculation | Medium | Simplified relative IV rank |

### Dependency Graph

```
VPR-082 (filter) → VPR-083 (ATM) → VPR-084 (IV color) → VPR-085 (vol/OI) → VPR-086 (summary) → VPR-087 (IV rank)
```

## Technical Details

### Filter Implementation

```python
_filter_mode: Literal['all', 'itm', 'otm'] = 'all'

def _apply_filter(self, contracts: list[OptionContract]) -> list[OptionContract]:
    if self._filter_mode == 'all':
        return contracts
    elif self._filter_mode == 'itm':
        return [c for c in contracts if c.in_the_money]
    else:  # otm
        return [c for c in contracts if not c.in_the_money]
```

### ATM Strike Calculation

```python
def _find_atm_strike(self, contracts: list[OptionContract], current_price: float) -> float:
    """Find strike closest to current stock price."""
    return min(contracts, key=lambda c: abs(c.strike - current_price)).strike
```

### IV Color Logic

```python
def _get_iv_color(self, iv: float, min_iv: float, max_iv: float) -> str:
    """Color based on IV position in range."""
    if max_iv == min_iv:
        return "yellow"  # No range, use neutral

    range_size = max_iv - min_iv
    low_threshold = min_iv + range_size / 3
    high_threshold = min_iv + 2 * range_size / 3

    if iv < low_threshold:
        return "green"   # Low IV - cheap options
    elif iv < high_threshold:
        return "yellow"  # Medium IV
    else:
        return "red"     # High IV - expensive options
```

### Simplified IV Rank

```python
def _calculate_iv_rank(self, atm_iv: float, min_iv: float, max_iv: float) -> float:
    """
    Simplified IV rank based on current chain only.
    NOTE: Not true 52-week IV rank (requires historical data).
    """
    if max_iv == min_iv:
        return 50.0  # No range, return middle
    return ((atm_iv - min_iv) / (max_iv - min_iv)) * 100
```

## Important Limitations

### IV Rank is Simplified

True IV rank compares current IV to 52-week historical IV range. yfinance doesn't provide historical IV data, so our "IV rank" compares current ATM IV to the IV range within the current options chain. This is still useful for:

- Comparing relative pricing within an expiration
- Identifying unusually expensive/cheap strikes
- Quick visual assessment of IV distribution

**Not useful for:**
- True high/low IV assessment vs. history
- Volatility trading strategies that depend on historical percentile

### No Greeks

Greeks (delta, theta, gamma, vega) require:
1. Black-Scholes calculation
2. Risk-free interest rate
3. Dividend yield
4. scipy dependency (for normal distribution)

Deferred to future feature if needed. Most users get Greeks from their broker.

## Files Modified

**Extended:**
- `viper/widgets/options_panel.py` - All new features added here
- `viper/widgets/help_screen.py` - New keybindings (f, a, s)
- `viper/app.py` - May need to pass current price to options panel

**New:**
- `tests/test_options_enhancements.py` - Tests for Feature 9

## Success Criteria

- [ ] Filter mode cycles ITM/OTM/All with 'f' key
- [ ] ATM strike highlighted and 'a' jumps to it
- [ ] IV color coding renders correctly
- [ ] High volume/OI contracts highlighted
- [ ] Summary view shows all expirations
- [ ] Enter on summary drills into full view
- [ ] IV rank displays in header
- [ ] All features work with existing navigation
- [ ] All tests pass with >= 90% coverage
- [ ] mypy --strict passes

## Out of Scope (Future Features)

- Greeks calculation (delta, theta, gamma, vega)
- True historical IV rank (52-week)
- Payoff diagrams
- Strategy builder (spreads, straddles, etc.)
- Break-even calculators
- Probability calculators

## Why This Matters

Feature 9 transforms options browsing into options analysis:

| Feature 8 (Basic) | Feature 9 (Enhanced) |
|-------------------|----------------------|
| View raw options data | Filter to relevant strikes |
| Scroll through all strikes | Jump directly to ATM |
| Read IV numbers | Visually assess IV (colors) |
| Check volume manually | Spot high-activity contracts |
| Navigate one expiration at a time | Quick multi-expiration overview |

These enhancements make the options panel practical for real analysis, not just data viewing.
