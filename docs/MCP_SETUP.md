# Viper MCP Server Setup

The Viper MCP server exposes real-time market data to any MCP-compatible LLM client — no API key required.

## Installation

```bash
pip install -e .
```

This installs the `viper-mcp` command.

## Available Tools

| Tool | Description |
|------|-------------|
| `get_quote` | Real-time stock/crypto quotes |
| `get_price_history` | Historical OHLCV data |
| `get_technical_indicators` | SMA, EMA, RSI, MACD |
| `get_option_expirations` | Available option expiration dates |
| `get_options_chain` | Options calls/puts for an expiration |
| `get_news` | Recent news headlines |
| `get_stock_info` | Extended stock information |
| `get_crypto_info` | Extended crypto information |
| `get_watchlist` | View your watchlist |
| `add_to_watchlist` | Add a ticker to watchlist |
| `remove_from_watchlist` | Remove a ticker from watchlist |

## Claude Code

Add to your Claude Code MCP settings (`~/.claude/claude_code_config.json`):

```json
{
  "mcpServers": {
    "viper-market-data": {
      "command": "viper-mcp",
      "args": []
    }
  }
}
```

Or if installed in a virtualenv:

```json
{
  "mcpServers": {
    "viper-market-data": {
      "command": "/path/to/venv/bin/viper-mcp",
      "args": []
    }
  }
}
```

## Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "viper-market-data": {
      "command": "viper-mcp",
      "args": []
    }
  }
}
```

## Generic MCP Client

The server uses stdio transport. Launch it as:

```bash
viper-mcp
```

Or via Python module:

```bash
python -m viper.mcp
```

## Shared Watchlist

The MCP server shares the same watchlist file as the Viper TUI at `~/.config/viper/watchlist.json`. Changes made via MCP tools are immediately visible in the TUI, and vice versa.

## Troubleshooting

**"command not found: viper-mcp"**
Ensure the package is installed (`pip install -e .`) and the install location is on your PATH.

**Tools not appearing**
Restart your MCP client after updating the config. Check the client's MCP logs for connection errors.

**Import errors**
Ensure all dependencies are installed: `pip install -e ".[dev]"`
