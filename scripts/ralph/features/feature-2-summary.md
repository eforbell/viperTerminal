# Feature 2: News Feed & Historical Charts

## Overview

This feature set adds two major capabilities to Viper Terminal:
1. **News Feed** - Real-time financial news for watched tickers
2. **Historical Charts** - Multi-timeframe price charts (1W, 1M, 3M, 6M, 1Y, 5Y)

These transform Viper from a "quote lookup tool" into a more complete market analysis terminal.

---

## Feature 2A: News Feed Integration

### What It Does
- Display recent news headlines for the currently viewed ticker
- Show news in a dedicated panel (toggle with `n` key)
- Headlines are clickable (open in browser) or expandable for summary
- Auto-refresh news on ticker change
- Filter by relevance/recency

### Data Sources (Free Options)
| Source | Pros | Cons |
|--------|------|------|
| **Yahoo Finance RSS** | Free, no API key, same source as yfinance | Limited formatting, no summaries |
| **Finnhub** | Free tier (60 calls/min), good quality | Requires API key signup |
| **Alpha Vantage News** | Free tier (25 calls/day), includes sentiment | Low rate limit |
| **NewsAPI.org** | Great quality, 100 calls/day free | Requires attribution |
| **Google News RSS** | Free, no key | Generic search, not finance-focused |

**Recommendation**: Start with Yahoo Finance RSS (no signup, aligns with yfinance). Can add Finnhub later for richer data.

### User Experience
```
┌─────────────────────────────────────────────────────────────┐
│ AAPL - Apple Inc.                                           │
│ $192.53  +$2.34 (+1.23%)                                    │
│ ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆▇                                       │
├─────────────────────────────────────────────────────────────┤
│ 📰 NEWS                                            [n]=hide │
│ ─────────────────────────────────────────────────────────── │
│ • Apple announces new AI features for iPhone       2h ago   │
│ • AAPL hits 52-week high amid tech rally          4h ago   │
│ • Warren Buffett increases Apple stake            1d ago   │
│ • Q4 earnings beat expectations                   2d ago   │
└─────────────────────────────────────────────────────────────┘
```

### Key Commands
- `n` - Toggle news panel visibility
- `j/k` - Navigate news items (when panel focused)
- `Enter` - Open article in browser / expand summary
- `r` - Refresh news

---

## Feature 2B: Historical Price Charts

### What It Does
- Display price history as ASCII/Unicode chart
- Multiple timeframes: 1W, 1M, 3M, 6M, 1Y, 5Y, MAX
- Show OHLC or closing prices
- Volume bars below price chart (optional)
- Key stats: period high/low, % change over period

### Data Source
**yfinance** already supports this! The `Ticker.history()` method accepts:
- `period`: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
- `interval`: "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"

### User Experience
```
┌─────────────────────────────────────────────────────────────┐
│ AAPL - Apple Inc.  [1W] [1M] [3M] [6M] [1Y] [5Y]           │
│ $192.53  +$2.34 (+1.23%)                                    │
├─────────────────────────────────────────────────────────────┤
│ 1 Year Price History                    High: $198  Low: $164│
│ $198 ┤                              ╭───╮                    │
│      │                         ╭───╯   ╰──╮                 │
│ $185 ┤                    ╭───╯           ╰───╮             │
│      │               ╭───╯                    ╰──╮          │
│ $172 ┤          ╭───╯                            ╰──╮       │
│      │     ╭───╯                                    ╰───    │
│ $164 ┼────╯                                                 │
│      └──────────────────────────────────────────────────────│
│      Jan   Feb   Mar   Apr   May   Jun   Jul   Aug   Sep    │
├─────────────────────────────────────────────────────────────┤
│ Volume                                                       │
│ ▄▂▃▅▇▄▃▂▄▅▆▄▃▂▄▅▇█▆▄▃▂▄▅▆▇▅▄▃▂▄▅▆▄▃▂▄▅▇▆▅▄▃▂▄▅▆▇▅▄         │
└─────────────────────────────────────────────────────────────┘
```

### Key Commands
- `c` - Toggle chart panel / cycle through timeframes
- `1-6` - Quick timeframe select (1=1W, 2=1M, 3=3M, 4=6M, 5=1Y, 6=5Y)
- `v` - Toggle volume bars

### Chart Rendering Options
1. **Unicode Box Drawing** - `─│╭╮╯╰` for smooth lines
2. **Braille Patterns** - `⠀⠁⠂⠃...⣿` for high resolution (2x4 dots per char)
3. **Block Elements** - `▁▂▃▄▅▆▇█` (already used in sparkline)
4. **ASCII Only** - `-|/\` for maximum compatibility

**Recommendation**: Use Braille patterns for main chart (highest resolution), blocks for volume.

---

## Implementation Priority

### Phase 1: Historical Charts (Higher Priority)
Why first:
- Uses existing yfinance (no new dependencies/API keys)
- Core functionality for any trading terminal
- Builds on existing sparkline widget
- More deterministic (easier to test)

### Phase 2: News Feed
Why second:
- Requires new data source integration
- Need to handle API keys/rate limits
- Content is dynamic (harder to test)
- Can be a "nice to have" initially

---

## Technical Considerations

### Chart Widget Architecture
```
ChartPanel (Widget)
├── ChartHeader (timeframe selector, stats)
├── PriceChart (main price visualization)
├── VolumeChart (optional volume bars)
└── ChartFooter (date axis labels)
```

### News Widget Architecture
```
NewsPanel (Widget)
├── NewsHeader ("NEWS" title, refresh indicator)
├── NewsList (VerticalScroll)
│   └── NewsItem[] (headline, source, time, expandable)
└── NewsFooter (keybindings hint)
```

### Data Caching Strategy
- Cache historical data for 5 minutes (avoid repeated fetches)
- Cache news for 2 minutes
- Background refresh when panel is visible
- Clear cache on ticker change

---

## Story Breakdown (See feature-2-prd.json)

| ID | Title | Priority | Estimate |
|----|-------|----------|----------|
| VPR-016 | Historical data service | 1 | Medium |
| VPR-017 | Chart rendering engine | 2 | Large |
| VPR-018 | Chart panel widget | 3 | Medium |
| VPR-019 | Timeframe selection UI | 4 | Small |
| VPR-020 | Volume visualization | 5 | Small |
| VPR-021 | News data service | 6 | Medium |
| VPR-022 | News panel widget | 7 | Medium |
| VPR-023 | News item expansion | 8 | Small |
| VPR-024 | Browser integration | 9 | Small |

---

## Questions to Resolve

1. **Chart Style**: Braille vs Unicode box drawing? (Braille = higher res, box = cleaner look)
2. **News Source**: Start with RSS or go straight to Finnhub API?
3. **Panel Layout**: Replace quote panel or add as third panel?
4. **Crypto Charts**: yfinance has limited crypto history - use CoinGecko for crypto charts?

---

## Success Metrics

- Chart renders correctly for all timeframes
- News loads within 2 seconds
- No performance degradation with charts visible
- Works on 80x24 terminal minimum
- 90%+ test coverage maintained
