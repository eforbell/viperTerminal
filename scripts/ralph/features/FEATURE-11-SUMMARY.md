# Feature 11: Odds and Ends

## Summary

A collection of small UX improvements to tighten up the app. These are quality-of-life enhancements that make daily use smoother without major architectural changes.

**STABILITY AND PERFORMANCE ARE PARAMOUNT** - Recent gains in app stability must be preserved. All changes should be surgical and thoroughly tested.

## Stories Overview

| ID | Title | Effort | Purpose |
|----|-------|--------|---------|
| VPR-093 | Configurable chart refresh for candlestick mode | Small | Auto-refresh chart at configurable interval |
| VPR-094 | Multi-ticker watchlist operations | Small | Add/delete multiple tickers at once |
| VPR-095 | Command mode - exit input focus | Medium | Global key to escape input bar |
| VPR-096 | Page Up/Down in options panel | Small | Fast navigation in long lists |

All stories are independent and can be developed in parallel.

---

## VPR-093: Configurable Chart Refresh for Candlestick Mode

### Problem
When viewing candlestick charts, the chart doesn't auto-refresh even though the watchlist data is being updated in the background.

### Solution
Add a configurable timer that triggers chart re-render when candlestick mode is active.

### Config Option

Add to `~/.config/viper/config.toml`:

```toml
chart_refresh_interval = 30  # seconds (0 to disable)
```

| Setting | Default | Description |
|---------|---------|-------------|
| `chart_refresh_interval` | `30` | Chart refresh interval in seconds for candlestick mode. Set to 0 to disable. |

### Key Points
- **Configurable** - users can tune interval or disable (set to 0)
- **Default 30s** - reasonable balance between freshness and performance
- **No new API calls** - uses existing cached data from watchlist refresh
- **Candlestick only** - refresh only active in candlestick mode
- **No flicker** - smooth update without visual disruption

### Technical Approach
```python
# In Config dataclass
chart_refresh_interval: int = 30  # 0 to disable

# In ChartPanel
def _start_refresh_timer(self):
    interval = self._config.chart_refresh_interval
    if self._chart_style == ChartStyle.CANDLESTICK and interval > 0:
        self._refresh_timer = self.set_timer(float(interval), self._refresh_chart)

def _refresh_chart(self):
    # Re-render with current cached data
    self._render_current_chart()
    self._start_refresh_timer()  # Restart timer
```

---

## VPR-094: Multi-Ticker Watchlist Operations

### Problem
Adding multiple tickers to watchlist requires submitting one at a time. Tedious when building a watchlist from scratch.

### Solution
Extend existing `w` (add) and `d` (delete) commands to accept space-delimited tickers.

### Examples
```
Add multiple:    w AAPL MSFT GOOGL BTC-USD
Delete multiple: d AAPL MSFT
Single (unchanged): w AAPL
```

### Key Points
- **Keep existing pattern** - `w` for add, `d` for delete, just allow multiple tickers
- **No mixing operations** - prefix determines operation for all tickers
- **Handles dashes** - tickers like `BTC-USD` work correctly (no `-TICKER` syntax)
- **Partial success** - valid tickers processed even if some fail
- **Clear feedback** - "Added: AAPL, MSFT. Failed: INVALID"
- **Backwards compatible** - single ticker input still works

### Technical Approach
```python
def _handle_watchlist_command(self, command: str, tickers: str) -> None:
    """Handle w (add) or d (delete) with multiple tickers."""
    ticker_list = tickers.upper().split()

    if command == 'w':
        successes, failures = self._add_tickers(ticker_list)
    else:  # command == 'd'
        successes, failures = self._remove_tickers(ticker_list)

    self._show_feedback(command, successes, failures)
```

---

## VPR-095: Command Mode - Exit Input Focus

### Problem
After submitting a ticker to watchlist or selecting from search, user is stuck in input mode. Cannot use chart (`v`), news (`n`), or options (`o`) keys without first tabbing to another panel.

### Solution
Add global `Escape` key that exits input focus and enables command keybindings.

### User Flow
```
1. User types "AAPL" and presses Enter → added to watchlist
2. User is still in input bar focus
3. User presses Escape → exits input focus (command mode)
4. User can now press 'o' for options, 'n' for news, 'v' for chart toggle
5. User presses '/' → returns to input/search mode
```

### Key Points
- **Escape** is standard for exiting input/modal states
- **Context-dependent** - no conflict with news reader (different focus)
- **'/'** returns to search/input mode (familiar from vim/less)
- **Tab** navigation continues to work as before
- **Visual indicator** shows current mode in status bar

### Escape Key Context

| Focus Context | Escape Action |
|---------------|---------------|
| Input bar | Exit to command mode (new) |
| News reader | Back to news listing (existing) |
| Options panel | No current use |

No conflict - each widget handles its own key events when focused.

### Keybinding Summary

| Key | In Input Mode | In Command Mode |
|-----|---------------|-----------------|
| Escape | Exit to command mode | No-op |
| / | Type '/' | Enter input mode |
| o, n, v | Type character | Toggle options/news/chart |
| Tab | Next panel | Next panel |
| 1-7 | Type number | Change timeframe |

---

## VPR-096: Page Up/Down in Options Panel

### Problem
Options panels can have dozens or hundreds of strikes. Navigating with `j`/`k` one item at a time is tedious.

### Solution
Add `PgUp`/`PgDn` keybindings to jump multiple items at once.

### Key Points
- **Page size**: 10 items (or visible page height)
- **j/k** continue to work for single-item navigation
- **Bounds checking** - stop at first/last item
- **Selection follows** - highlight moves with page jump

### New Keybindings

| Key | Action |
|-----|--------|
| PgUp | Move up 10 items |
| PgDn | Move down 10 items |
| j | Move down 1 item (unchanged) |
| k | Move up 1 item (unchanged) |

### Technical Approach
```python
def action_page_down(self) -> None:
    """Move selection down by page size."""
    page_size = 10
    new_index = min(self._selected_index + page_size, len(self._options) - 1)
    self._selected_index = new_index
    self._refresh_display()
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `viper/widgets/chart_panel.py` | Add refresh timer for candlestick mode |
| `viper/widgets/ticker_input.py` | Parse multi-ticker input |
| `viper/widgets/watchlist_panel.py` | Handle batch add/delete |
| `viper/app.py` | Command mode focus handling |
| `viper/widgets/options_panel.py` | Add PgUp/PgDn handlers |
| `viper/widgets/help_screen.py` | Document new keybindings |

---

## Success Criteria

- [ ] Chart refreshes at configured interval in candlestick mode without flicker
- [ ] `chart_refresh_interval` config option works (default 30s, 0 disables)
- [ ] User can add multiple tickers: `w AAPL MSFT GOOGL BTC-USD`
- [ ] User can delete multiple tickers: `d AAPL MSFT`
- [ ] Escape key exits input mode, enabling chart/news/options keys
- [ ] `/` returns to input mode from command mode
- [ ] PgUp/PgDn navigates options list by 10 items
- [ ] All existing functionality continues to work unchanged
- [ ] All tests pass with >= 90% coverage
- [ ] mypy --strict passes with no errors

---

## Risk Assessment

**Level: LOW**

| Risk | Mitigation |
|------|------------|
| Timer causes performance issues | Timer only active in candlestick mode, uses cached data |
| Multi-ticker parsing edge cases | Comprehensive input validation, partial success handling |
| Focus handling complexity | Leverage Textual's built-in focus system |
| Breaks existing keybindings | Thorough testing of all key combinations |

---

## Out of Scope

- Vim-style command line (`:w`, `:q` commands)
- Customizable refresh intervals
- Drag-and-drop watchlist reordering
- Options panel filtering by Greeks
- Batch operations on options (multi-select)
