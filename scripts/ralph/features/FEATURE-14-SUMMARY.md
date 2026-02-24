# Feature 14: MCP Market Intelligence Server

## Summary

Expose Viper Terminal's market data services to MCP-compatible LLM clients (Claude Code, Claude Desktop, Codex, etc.) via a stdio-based FastMCP server. By running `viper-mcp`, any MCP client gains access to real-time market data — no API key required.

This flips the model: instead of bringing an LLM into Viper, we expose Viper's data to the user's *existing* LLM. The single most accretive addition because it multiplies the value of every existing service without modifying any existing code.

## Architecture

```
User's LLM Client (Claude Code, etc.)
        │ stdio (JSON-RPC)
        ▼
   viper-mcp process
   ┌─────────────────────┐
   │  FastMCP Server     │
   │  ┌───────────────┐  │
   │  │ Tool Adapters  │──┼──► viper/services/quote.py
   │  │ (thin wrappers)│──┼──► viper/services/history_data.py
   │  │                │──┼──► viper/services/indicators.py
   │  │                │──┼──► viper/services/options.py
   │  │                │──┼──► viper/services/news.py
   │  │                │──┼──► viper/services/watchlist.py
   │  └───────────────┘  │
   └─────────────────────┘
```

## Stories Overview

| ID | Title | Effort | Priority | Dependencies |
|----|-------|--------|----------|--------------|
| VPR-104 | Core MCP Server + get_quote Tool | Small | 1 | — |
| VPR-105 | Historical Data + Technical Indicators Tools | Small-Medium | 2 | VPR-104 |
| VPR-106 | Options + News + Info Tools | Small-Medium | 3 | VPR-104 |
| VPR-107 | Watchlist Tools + User Documentation | Small | 4 | VPR-104 |

**Dependency Flow:** VPR-104 → VPR-105, VPR-106, VPR-107 (all depend on core server)

---

## VPR-104: Core MCP Server + get_quote Tool

### Problem
Viper's market data is locked inside the TUI. Users with MCP-compatible LLM clients can't access it.

### Solution
Create `viper/mcp/` package with FastMCP server instance, stdio entry point, and first tool (`get_quote`).

### Files Created
- `viper/mcp/__init__.py` — Package init
- `viper/mcp/server.py` — FastMCP("viper-market-data") instance + tool imports
- `viper/mcp/__main__.py` — Entry point: `mcp.run(transport="stdio")`
- `viper/mcp/serializers.py` — `serialize_datetime()` helper
- `viper/mcp/tools/__init__.py` — Tools sub-package
- `viper/mcp/tools/quote.py` — `get_quote(symbol)` wrapping `fetch_quote()`
- `tests/test_mcp_server.py` — Server creation, tool registration smoke test
- `tests/test_mcp_quote.py` — Success/error paths for stock and crypto quotes

### Files Modified
- `pyproject.toml` — Add `mcp>=1.0.0` dependency, `viper-mcp` script entry point

---

## VPR-105: Historical Data + Technical Indicators Tools

### Problem
LLM clients need historical price data and technical analysis capabilities.

### Solution
Two tools: `get_price_history` returns OHLCV data with stats, `get_technical_indicators` returns current (last) value for SMA, EMA, RSI, and MACD.

### Key Design Decision
Indicator tool returns only current values (not full arrays) to prevent massive responses that would overwhelm LLM context windows.

### Files Created
- `viper/mcp/tools/history.py` — `get_price_history(symbol, period)`
- `viper/mcp/tools/indicators.py` — `get_technical_indicators(symbol, period, indicators, *_period)`
- `tests/test_mcp_history.py` — Success/error, datetime serialization
- `tests/test_mcp_indicators.py` — All indicators, subset, custom periods, error paths

---

## VPR-106: Options + News + Info Tools

### Problem
LLM clients need access to options chains, news, and extended company/crypto information.

### Solution
Five tools across three modules, all thin wrappers over existing services.

### Files Created
- `viper/mcp/tools/options.py` — `get_option_expirations`, `get_options_chain`
- `viper/mcp/tools/news.py` — `get_news(ticker, max_items)`
- `viper/mcp/tools/info.py` — `get_stock_info`, `get_crypto_info`
- `tests/test_mcp_options.py`, `tests/test_mcp_news.py`, `tests/test_mcp_info.py`

---

## VPR-107: Watchlist Tools + User Documentation

### Problem
LLM clients should be able to read and manage the same watchlist used by the TUI.

### Solution
Three watchlist tools with lazy-initialized WatchlistManager singleton. Setup documentation for Claude Code, Claude Desktop, and generic MCP clients.

### Files Created
- `viper/mcp/tools/watchlist.py` — `get_watchlist`, `add_to_watchlist`, `remove_from_watchlist`
- `tests/test_mcp_watchlist.py` — Add/remove/get round-trips
- `docs/MCP_SETUP.md` — Config instructions for all supported clients

### Files Modified
- `README.md` — Add MCP server section

---

## Tool Inventory (11 tools)

| Tool | Service | Key Parameters |
|------|---------|---------------|
| `get_quote` | `quote.fetch_quote` | `symbol` |
| `get_price_history` | `history_data.fetch_historical_data` | `symbol, period` |
| `get_technical_indicators` | `indicators.* + history_data` | `symbol, period, indicators, *_period` |
| `get_option_expirations` | `options.fetch_option_expirations` | `ticker` |
| `get_options_chain` | `options.fetch_option_chain` | `ticker, expiration` |
| `get_news` | `news.fetch_news` | `ticker, max_items` |
| `get_stock_info` | `stock.fetch_stock_info` | `ticker` |
| `get_crypto_info` | `crypto.fetch_crypto_info` | `symbol` |
| `get_watchlist` | `watchlist.WatchlistManager.get_all` | (none) |
| `add_to_watchlist` | `watchlist.WatchlistManager.add` | `ticker` |
| `remove_from_watchlist` | `watchlist.WatchlistManager.remove` | `ticker` |

## Key Design Decisions

1. **`mcp` as a required dependency** — `viper-mcp` is a first-class entry point
2. **All tools return `dict[str, object]`** — consistent, JSON-serializable
3. **Error convention**: `{"error": "message", "symbol": "X"}` — no exceptions
4. **Indicator tool returns current values only** — prevents massive responses
5. **Watchlist uses lazy singleton** — initialized on first call, shares persistence

## Estimated Effort

**Total: Medium (2-3 days)**
