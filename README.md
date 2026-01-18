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
| `1-7` | Change timeframe (1W, 1M, 3M, 6M, 1Y, 2Y, 5Y) |
| `0` | MAX timeframe |
| `t s` | Toggle SMA |
| `t e` | Toggle EMA |
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

## Data Sources

- Stock/crypto data: [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance)
- News: Yahoo Finance RSS feeds

## License

MIT License - see LICENSE file for details.
