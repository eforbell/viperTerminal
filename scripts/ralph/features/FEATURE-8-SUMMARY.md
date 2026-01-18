# Feature 8: Options Chain (Basic)

## Summary

Add basic options chain data exploration to Viper Terminal. Users can view calls and puts for any optionable ticker, navigate through expiration dates, and browse option contracts with key metrics (strike, bid/ask, volume, open interest, implied volatility).

## Why Options Data Matters

Options data is typically locked behind expensive broker subscriptions or specialized platforms. This feature brings free options exploration to the terminal using yfinance, enabling:

- **Quick options overview** without leaving the terminal
- **Strike price browsing** to find interesting contracts
- **Volume/OI analysis** to identify where money is flowing
- **IV comparison** across strikes and expirations

## Visual Design

```
OPTIONS: AAPL | 2024-03-15 | CALLS
─────────────────────────────────────────
Strike    Bid     Ask    Last    Vol     OI      IV    ITM
──────────────────────────────────────────────────────────
 165.00   12.50   12.70   12.60   1,234   5,678   35%    Y  ← selected (highlighted)
 167.50   10.30   10.50   10.40   2,345   8,901   33%    Y
 170.00    8.20    8.40    8.30   5,678  12,345   31%    Y
 172.50    6.10    6.30    6.20   3,456  10,234   29%    N
 175.00    4.20    4.40    4.30   8,901  15,678   27%    N
 177.50    2.50    2.70    2.60   4,567   9,012   25%    N
 180.00    1.20    1.40    1.30  12,345  20,456   24%    N
──────────────────────────────────────────────────────────
j/k: navigate  [ ]: change expiration  c/p: calls/puts  o: close
```

**Colors:**
- ITM contracts: `[green]` row or ITM indicator
- OTM contracts: default color
- Selected row: background highlight
- Header: `[cyan]`

## Keybindings

| Key | Action |
|-----|--------|
| `o` | Toggle options panel on/off |
| `j` / `k` | Navigate down/up in options table |
| `[` / `]` | Previous/next expiration date |
| `c` | Show calls |
| `p` | Show puts |

**Note:** Using `[` / `]` for expiration navigation instead of Tab, since Tab is used at the app level for panel switching.

## Stories (6 total)

| ID | Title | Effort | Purpose |
|----|-------|--------|---------|
| VPR-076 | Options service - expirations | Small | Fetch available expiration dates |
| VPR-077 | Options service - chain data | Small | Fetch calls/puts with all fields |
| VPR-078 | OptionsChainPanel widget | Medium | UI component with table display |
| VPR-079 | App integration - 'o' keybinding | Small | Toggle panel, load data |
| VPR-080 | Expiration selector [ ] | Small | Navigate between expirations |
| VPR-081 | Calls/Puts toggle c/p | Small | Switch between calls and puts |

### Dependency Graph

```
VPR-076 (expirations) → VPR-077 (chain) → VPR-078 (widget) → VPR-079 (app) → VPR-080 ([ ]) → VPR-081 (c/p)
```

All stories are sequential - each builds on the previous.

## Technical Details

### yfinance Options API

```python
import yfinance as yf

# Get available expirations
ticker = yf.Ticker("AAPL")
expirations = ticker.options  # tuple: ('2024-03-15', '2024-03-22', ...)

# Get option chain for specific expiration
chain = ticker.option_chain('2024-03-15')
calls_df = chain.calls  # pandas DataFrame
puts_df = chain.puts    # pandas DataFrame

# DataFrame columns:
# contractSymbol, lastTradeDate, strike, lastPrice, bid, ask,
# change, percentChange, volume, openInterest, impliedVolatility, inTheMoney
```

### Data Structures

```python
@dataclass
class OptionContract:
    strike: float
    bid: float
    ask: float
    last_price: float
    volume: int
    open_interest: int
    implied_volatility: float
    in_the_money: bool

@dataclass
class OptionsChain:
    ticker: str
    expiration: str
    calls: list[OptionContract]
    puts: list[OptionContract]

@dataclass
class OptionsError:
    ticker: str
    error_message: str
```

### Widget State Machine

```
┌─────────┐    load_options()    ┌─────────┐
│  empty  │ ──────────────────→  │ loading │
└─────────┘                      └─────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ↓                                   ↓
              ┌─────────┐                         ┌─────────┐
              │ success │                         │  error  │
              └─────────┘                         └─────────┘
```

### Panel Integration

Options panel follows the multi-purpose panel pattern:
- Toggled with `o` key at app level
- Can show alongside or instead of chart/news (implementation choice)
- Loads options data when shown with valid ticker
- Shows empty state when no ticker selected

## Files to Create

**New:**
- `viper/services/options.py` - Options data service
- `viper/widgets/options_panel.py` - OptionsChainPanel widget
- `tests/test_options_service.py` - Service unit tests
- `tests/test_options_panel.py` - Widget tests

**Modified:**
- `viper/app.py` - Add 'o' keybinding
- `viper/widgets/help_screen.py` - Document keybindings
- `viper/widgets/__init__.py` - Export OptionsChainPanel
- `viper/services/__init__.py` - Export options service

## Success Criteria

- [ ] Options panel displays for valid ticker with options
- [ ] All expirations navigable with `[` `]` keys
- [ ] Calls/Puts toggle with `c` `p` keys works
- [ ] `j` `k` navigation through table works
- [ ] Loading states display during fetch
- [ ] Error states for tickers without options
- [ ] Panel toggles with `o` key
- [ ] Help screen updated
- [ ] All tests pass with >= 90% coverage
- [ ] mypy --strict passes

## Out of Scope (Deferred to Feature 9)

- Greeks calculation (delta, theta, gamma, vega)
- IV rank/percentile calculations
- Filtering (ITM only, OTM only, volume threshold)
- Near-the-money focus/highlighting
- Multi-expiration view
- Strategy builder / payoff diagrams

## Evaluation Focus

Before proceeding to Feature 9, evaluate:

1. **Data fetch speed** - Is yfinance options API responsive enough?
2. **Navigation feel** - Are `[` `]` intuitive for expiration cycling?
3. **Table readability** - Are columns appropriately sized?
4. **Integration** - Does the panel coexist well with other views?

These insights will inform Feature 9 enhancements.
