# Feature 1: MVP Terminal (Complete)

**Status**: ✅ Complete  
**Branch**: `viper/feature-mvp-terminal`  
**Stories**: VPR-001 through VPR-015 (15 stories)  
**Completed**: 2026-01-07

## Summary

The MVP Bloomberg-like terminal with core quote lookup functionality.

### Capabilities Delivered
- Stock quotes via yfinance (price, change, volume, market cap, 52W range)
- Crypto quotes via CoinGecko (price, 24h change, market cap)
- Intraday sparkline charts
- Watchlist with auto-refresh
- Command history with Up/Down navigation
- Info panel (sector, industry, description)
- Multi-panel layout with Tab navigation
- Vim-style j/k list navigation
- Help screen and first-run onboarding
- Persistent config, watchlist, and history
- Logging with rotation

### Key Commands
| Command | Action |
|---------|--------|
| `TICKER` | Look up quote |
| `W TICKER` | Add to watchlist |
| `D TICKER` | Remove from watchlist |

### Key Bindings
| Key | Action |
|-----|--------|
| `q` | Quit |
| `/` | Focus input |
| `i` | Toggle info panel |
| `Tab` | Cycle panels |
| `j/k` | Navigate watchlist |
| `?/F1` | Help |

### Files
- PRD: [features/feature-1-prd.json](features/feature-1-prd.json)
- Progress: [progress.txt](progress.txt)
