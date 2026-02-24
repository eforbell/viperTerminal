# Viper Terminal

A personal Bloomberg-like terminal for stock and crypto quotes with a beautiful console UI.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Real-time quotes** for stocks and cryptocurrencies
- **Interactive charts** with multiple timeframes (1W to MAX)
- **Technical indicators** - SMA, EMA, RSI, MACD
- **Options chains** with IV analysis, filtering, and multi-expiration view
- **News feed** with in-app article reader
- **Keyboard-driven interface** - no mouse needed

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/viper.git
cd viper

# Install
pip install .

# Run
viper
```

**Need more detailed instructions?** See [INSTALL.md](INSTALL.md) for:
- Step-by-step guides for macOS, Linux, and Windows
- Installing from wheel files
- Building standalone binaries
- Troubleshooting common issues

## Usage

```bash
viper
```

### Keybindings

| Key | Action |
|-----|--------|
| `/` | Search for a ticker |
| `q` | Quit |
| `?` | Show help screen |
| `Tab` | Switch panels |

**Chart Controls:**
| Key | Action |
|-----|--------|
| `1-7` | Change timeframe (1W, 1M, 3M, 6M, 1Y, 5Y, MAX) |
| `v` | Toggle chart style (line/candlestick) |
| `t a` | Cycle moving averages (Off → SMA → EMA → Both) |
| `t r` | Toggle RSI |
| `t m` | Toggle MACD |

**Options Panel:**
| Key | Action |
|-----|--------|
| `o` | Toggle options panel |
| `j/k` | Navigate up/down |
| `[/]` | Previous/next expiration |
| `c/p` | Show calls/puts |
| `f` | Filter (All/ITM/OTM) |
| `a` | Jump to ATM strike |
| `s` | Summary view |

**News Panel:**
| Key | Action |
|-----|--------|
| `n` | Toggle news panel |
| `j/k` | Navigate articles |
| `Enter` | Read article |

## Configuration

Viper can be customized via a config file at `~/.config/viper/config.toml`.

### Example Configuration

```toml
# Watchlist settings
refresh_interval = 60              # Auto-refresh interval in seconds
streaming_enabled = false          # Enable real-time streaming mode on startup
default_watchlist = ["AAPL", "MSFT", "BTC-USD"]

# Chart settings
chart_style = "candlestick"        # 'braille', 'block', or 'candlestick'
default_chart_timeframe = "1Y"     # '1W', '1M', '3M', '6M', '1Y', '5Y', 'MAX'
chart_refresh_interval = 30        # Chart refresh interval in seconds for candlestick mode (0 to disable)

# News settings
news_enabled = true
news_max_items = 10

# Theme colors (optional)
[theme_colors]
positive = "#00ff00"
negative = "#ff0000"
background = "#000000"
```

### Options

| Setting | Default | Description |
|---------|---------|-------------|
| `refresh_interval` | `60` | Watchlist auto-refresh interval in seconds |
| `streaming_enabled` | `false` | Enable real-time streaming mode for watchlist on startup |
| `default_watchlist` | `[]` | Tickers to load on startup |
| `chart_style` | `"candlestick"` | Chart visualization: `braille`, `block`, or `candlestick` |
| `default_chart_timeframe` | `"1Y"` | Initial chart timeframe |
| `chart_refresh_interval` | `30` | Chart refresh interval in seconds for candlestick mode (0 to disable) |
| `news_enabled` | `true` | Enable news panel |
| `news_max_items` | `10` | Max news items to display |
| `theme_colors.positive` | `"#00ff00"` | Color for positive values |
| `theme_colors.negative` | `"#ff0000"` | Color for negative values |
| `theme_colors.background` | `"#000000"` | Background color |

## Building Distributions

### Build a wheel (for pip install)

```bash
./scripts/packaging/build-wheel.sh    # macOS/Linux
scripts\packaging\build-wheel.bat     # Windows
```

### Build a standalone binary

```bash
./scripts/packaging/build-binary.sh   # macOS/Linux
scripts\packaging\build-binary.bat    # Windows
```

See [INSTALL.md](INSTALL.md) for details.

## Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Type checking

```bash
mypy viper
```

### Linting

```bash
ruff check .
```

## Requirements

- Python 3.10 or higher
- Terminal with Unicode support (for charts)
- Internet connection (for market data)

## MCP Server

Viper includes an MCP (Model Context Protocol) server that exposes market data to LLM clients like Claude Code and Claude Desktop.

```bash
# Install
pip install -e .

# The viper-mcp command is now available
viper-mcp
```

Add to your Claude Code config:

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

Then ask Claude: *"What's the price of AAPL?"* and it will call `get_quote` automatically.
You can also scan multiple symbols with indicator rules via `get_scan` (e.g., RSI/MA filters).

See [docs/MCP_SETUP.md](docs/MCP_SETUP.md) for full setup instructions.

Note: Viper MCP uses stdio transport by default. Your MCP client should launch `viper-mcp` itself; running a separate manual background process is not required for normal use.

## Data Sources

- Stock/crypto data: [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance)
- News: Yahoo Finance RSS feeds

## License

MIT License - see LICENSE file for details.
