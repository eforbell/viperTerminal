# Feature 2: Historical Charts & News Feed

## Summary
This PR adds comprehensive historical price charting and news feed functionality to Viper Terminal, completing all 12 stories from the Feature 2 PRD with 565 passing tests and 90.55% coverage.

## ✨ New Features

### Historical Price Charts (VPR-016 to VPR-021)
- **Braille-based charting**: High-resolution charts using Unicode Braille patterns (2x4 dots per character)
- **Multiple timeframes**: 1W, 1M, 3M, 6M, 1Y, 5Y, MAX with hotkeys 1-7
- **Volume overlay**: Toggle volume bars with 'v' key, color-coded by price direction
- **Crypto support**: Automatic detection and historical data via CoinGecko API
- **Smart date formatting**: Adapts x-axis labels based on time period (MM/DD for short, YYYY for long)
- **Responsive design**: Charts adapt to terminal size with minimum dimensions enforced

### News Feed (VPR-022 to VPR-024)
- **Yahoo Finance RSS**: Real-time news headlines for stocks and crypto
- **j/k navigation**: Vim-style navigation through headlines
- **Item expansion**: Press 'e' to expand headlines and view summaries
- **Browser integration**: Press Enter to open articles in default browser
- **Status feedback**: Visual feedback when opening links ("Opening in browser...")
- **2-minute caching**: Reduced API calls with intelligent cache TTL

### Infrastructure (VPR-025 to VPR-027)
- **Generic cache layer**: Thread-safe in-memory caching with TTL support
- **Configuration extensions**: Chart style, default timeframe, volume/news toggle settings
- **Updated help screen**: Complete documentation of new keybindings and features

## 🎹 New Keybindings

| Key | Action |
|-----|--------|
| `c` | Toggle chart panel |
| `n` | Toggle news panel |
| `v` | Toggle volume bars (when chart visible) |
| `e` | Expand/collapse news item |
| `1-7` | Select chart timeframe (1W, 1M, 3M, 6M, 1Y, 5Y, MAX) |

## 🐛 Bug Fixes
- Fixed ticker context switching - chart/news now auto-refresh when selecting from watchlist
- Fixed volume bar alignment to match price chart width
- Fixed missing feedparser dependency in pyproject.toml

## 📊 Technical Details

### Architecture
- **Chart Renderer**: Modular design supporting both Braille and block character styles
- **Service Layer**: Separate services for historical data, news, and caching
- **Widget Pattern**: Reusable panel widgets with state management (empty, loading, success, error)

### Data Sources
- **Stock data**: yfinance for historical prices and intraday sparklines
- **Crypto data**: CoinGecko API with rate limit handling and exponential backoff
- **News data**: Yahoo Finance RSS feeds with feedparser library

### Performance
- **Smart downsampling**: Reduces data points to fit terminal width without losing extremes
- **Aggressive caching**: 5-minute cache for charts, 2-minute for news, 30-second for quotes
- **Async workers**: All data fetching runs in background workers to keep UI responsive

## 🧪 Testing
- **565 tests passing** (100% pass rate)
- **90.55% code coverage** (exceeds 90% threshold)
- **mypy --strict**: Full type safety with no errors
- **ruff**: Linting passes with no warnings

### Test Coverage by Module
- Services: 96-100% coverage
- Widgets: 95-100% coverage (except chart_panel at 98%)
- Core app: 91% coverage

## 📝 Configuration Example

```toml
# ~/.config/viper/config.toml
refresh_interval = 60  # Watchlist refresh in seconds

# Chart settings
default_chart_timeframe = "1M"
chart_style = "braille"  # or "block"
volume_enabled = false

# News settings
news_enabled = true
news_max_items = 10

# Default watchlist
default_watchlist = ["AAPL", "MSFT", "GOOGL", "BTC", "ETH"]

# Theme colors
[theme_colors]
positive = "#00ff00"
negative = "#ff0000"
neutral = "#ffffff"
```

## 🚀 Migration Notes
- No breaking changes to existing MVP functionality
- New dependency: `feedparser>=6.0.0` (automatically installed)
- Config file remains optional - all defaults work out of the box

## 📸 Features in Action
1. **Chart with volume**: Press 'c' to view chart, 'v' to toggle volume bars
2. **Timeframe switching**: Use 1-7 keys to quickly change periods
3. **News browsing**: Press 'n', use j/k to navigate, Enter to read full article
4. **Multi-panel workflow**: Seamlessly switch between quote, chart, info, and news panels

## 🎯 Success Criteria (All Met)
- ✅ All 12 stories pass acceptance criteria
- ✅ 90%+ test coverage achieved
- ✅ Charts render correctly for all timeframes
- ✅ News loads within 3 seconds
- ✅ No performance regression
- ✅ Works on terminals as small as 80x24
- ✅ Type safety with mypy --strict
- ✅ Code quality with ruff

## 📚 Documentation
- Updated AGENTS.md with 22 new story learnings
- Help screen includes all new features and keybindings
- Configuration options documented in code comments

## 🔗 Related Issues
- Implements Feature 2 from product roadmap
- Closes 12 user stories (VPR-016 through VPR-027)

---

**Ready to merge**: All tests pass, coverage exceeds threshold, no regressions detected.
