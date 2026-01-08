# Feature 3: Data Reliability & Chart Improvements

## Overview

Feature 3 focuses on **data reliability** and **chart enhancements**:
1. **Fix broken news feed** using yfinance built-in news (no API key!)
2. **Unify data source** - replace CoinGecko with yfinance for all crypto data
3. **Fix volume bar alignment** - root cause identified and ready to fix
4. **Add technical indicators** - SMA, EMA, and RSI with supporting infrastructure

This transforms Viper from "mostly working" to "rock-solid reliable data" while adding professional-grade technical analysis tools.

---

## 🔴 Critical Fixes

### News Feed (BROKEN → FIXED)

**Problem**: Yahoo Finance RSS feeds were discontinued (404 errors). News panel is completely non-functional.

**Solution**: yfinance has a built-in `.news` attribute that returns rich news data!

```python
import yfinance as yf
ticker = yf.Ticker('AAPL')
news = ticker.news  # Returns list of 10+ news items!

# Example item structure:
{
  "content": {
    "title": "Apple announces new AI features",
    "summary": "The company unveiled...",
    "pubDate": "2026-01-07T22:12:23Z",
    "provider": {"displayName": "Reuters"},
    "previewUrl": "https://finance.yahoo.com/..."
  }
}
```

**Benefits**:
- ✅ No API key required
- ✅ Already have yfinance dependency
- ✅ Rich data: title, summary, source, thumbnail
- ✅ Works for crypto too (BTC-USD)

---

### Volume Bar Alignment (BROKEN → FIXED)

**Problem**: Volume bars don't align with the price chart, especially with sparse data.

**Root Cause Discovered**:
```
When data points < 60% of chart width:
  - Price chart: INTERPOLATES/UPSAMPLES to fill entire width
  - Volume bars: Simple downsampling (doesn't match!)

Example with 21 data points, 48-char chart width:
  - Max data points for braille chart: 96 (48 * 2)
  - Interpolation threshold: 57 (96 * 0.6)
  - We have 21 < 57, so price chart upsamples to 96 points
  - But volume bars don't know about this interpolation!
```

**Solution**: Pass interpolation parameters from price renderer to volume renderer, apply same upsampling logic.

---

## 🔄 Data Source Unification

### Replace CoinGecko with yfinance for Crypto

**Problem**: CoinGecko has aggressive rate limits (429 errors) and requires different API handling.

**Solution**: yfinance supports crypto natively via `SYMBOL-USD` format:

```python
btc = yf.Ticker('BTC-USD')  # Bitcoin
eth = yf.Ticker('ETH-USD')  # Ethereum

# Full support:
btc.fast_info.last_price  # Current price
btc.history(period='1mo')  # Historical OHLCV
btc.news                   # News feed!
```

**Benefits**:
- ✅ Single data source for stocks AND crypto
- ✅ No rate limit issues (yfinance handles this)
- ✅ Simpler codebase (remove httpx, CoinGecko logic)
- ✅ Consistent data format
- ✅ Volume data for crypto charts!

**Supported Crypto**: BTC-USD, ETH-USD, ADA-USD, SOL-USD, DOGE-USD, XRP-USD, and many more.

---

## 📊 Technical Indicators

### Phase 1: Moving Averages (SMA/EMA)

**Simple Moving Average (SMA)**:
- Formula: `sum(last N prices) / N`
- Common periods: 20, 50, 100, 200 days
- Smoother line, lags price movements

**Exponential Moving Average (EMA)**:
- Formula: `EMA = Price * k + EMA_prev * (1-k)` where `k = 2/(period+1)`
- Reacts faster to recent prices
- Common periods: 12, 26, 50 days

**Chart Display**:
- `m` key cycles: Off → SMA20 → SMA50 → SMA20+50 → Off
- Overlay lines on price chart (cyan for SMA20, magenta for SMA50)
- Legend shows current values

### Phase 2: RSI with Sub-Panel Framework

**Relative Strength Index (RSI)**:
- Momentum oscillator ranging 0-100
- Formula: `100 - (100 / (1 + avg_gain / avg_loss))`
- < 30 = oversold (buy signal), > 70 = overbought (sell signal)

**Sub-Panel Framework**:
- New panel type for oscillator indicators
- Appears below price chart, above volume bars
- 3-5 lines of vertical space
- Horizontal markers for reference levels (30/70 for RSI)
- Toggle with `r` key

---

## User Stories Summary

| ID | Title | Priority | Effort | Milestone |
|----|-------|----------|--------|-----------|
| VPR-028 | Fix news service with yfinance | 1 | Medium | M1 |
| VPR-029 | Unify crypto quotes with yfinance | 2 | Medium | M1 |
| VPR-030 | Unify crypto historical with yfinance | 3 | Small | M1 |
| VPR-031 | Fix volume bar alignment | 4 | Medium | M2 |
| VPR-032 | Enable volume by default | 5 | Small | M2 |
| VPR-033 | SMA indicator service | 6 | Small | M3 |
| VPR-034 | EMA indicator service | 7 | Small | M3 |
| VPR-035 | Chart overlay support | 8 | Medium | M3 |
| VPR-036 | Moving average display | 9 | Medium | M3 |
| VPR-037 | RSI indicator service | 10 | Medium | M4 |
| VPR-038 | Sub-panel framework | 11 | Medium | M4 |
| VPR-039 | RSI panel implementation | 12 | Medium | M4 |

---

## Milestones

### M1: Data Source Reliability (VPR-028, VPR-029, VPR-030)
**Goal**: Fix news feed and unify on yfinance for all data
- Replace broken RSS with yfinance .news
- Replace CoinGecko with yfinance for crypto
- Single data source = simpler, more reliable

### M2: Volume Fix (VPR-031, VPR-032)
**Goal**: Fix volume bar alignment and enable by default
- Pass interpolation params to volume renderer
- Enable volume bars by default (users want this!)

### M3: Moving Averages (VPR-033, VPR-034, VPR-035, VPR-036)
**Goal**: Add SMA/EMA indicators with chart overlay support
- Pure calculation functions (no external deps)
- Chart renderer overlay support
- `m` key cycling through MA options

### M4: RSI Indicator (VPR-037, VPR-038, VPR-039)
**Goal**: Add RSI with sub-panel framework
- RSI calculation service
- Generic sub-panel framework (reusable for MACD, etc.)
- RSI visualization with 30/70 level markers

---

## Key Commands (after Feature 3)

| Key | Action |
|-----|--------|
| `c` | Toggle chart panel |
| `n` | Toggle news panel |
| `v` | Toggle volume bars (on by default!) |
| `m` | Cycle moving averages: Off → SMA20 → SMA50 → Both → Off |
| `r` | Toggle RSI indicator panel |
| `1-7` | Select chart timeframe |

---

## Dependencies

**Removed**:
- `feedparser` - no longer needed (was for RSS parsing)

**Simplified**:
- `httpx` - only used for tests now, not for CoinGecko

**Unchanged**:
- `yfinance` - now sole data source for stocks, crypto, and news!
- `textual` - TUI framework

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| yfinance API changes | Low | High | Already using successfully; version pin |
| Volume fix complexity | Medium | Medium | Root cause identified; progressive implementation |
| Indicator calc errors | Medium | Low | Test against TradingView/Yahoo Finance |

---

## Success Criteria

1. ✅ News panel functional again (using yfinance .news)
2. ✅ All crypto uses yfinance (no CoinGecko calls)
3. ✅ Volume bars align perfectly with price chart
4. ✅ Volume enabled by default
5. ✅ SMA/EMA overlay on charts with `m` key
6. ✅ RSI sub-panel with `r` key
7. ✅ All tests pass with 90%+ coverage
8. ✅ No API key required for any functionality
