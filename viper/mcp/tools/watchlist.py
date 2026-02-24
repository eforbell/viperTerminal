"""MCP tools for managing the watchlist."""

from viper.mcp.server import mcp
from viper.services.watchlist import WatchlistManager

_manager: WatchlistManager | None = None


def _get_manager() -> WatchlistManager:
    """Get or create the lazy-initialized WatchlistManager singleton."""
    global _manager  # noqa: PLW0603
    if _manager is None:
        _manager = WatchlistManager()
    return _manager


@mcp.tool()
async def get_watchlist() -> dict[str, object]:
    """Get all tickers in the watchlist.

    Returns:
        List of ticker symbols currently in the watchlist.
    """
    manager = _get_manager()
    tickers = manager.get_all()
    return {
        "tickers": tickers,
        "count": len(tickers),
    }


@mcp.tool()
async def add_to_watchlist(ticker: str) -> dict[str, object]:
    """Add a ticker to the watchlist.

    Args:
        ticker: Ticker symbol to add, e.g. "AAPL", "BTC"

    Returns:
        Confirmation with the updated watchlist.
    """
    manager = _get_manager()
    manager.add(ticker)
    tickers = manager.get_all()
    return {
        "added": ticker.upper().strip(),
        "tickers": tickers,
        "count": len(tickers),
    }


@mcp.tool()
async def remove_from_watchlist(ticker: str) -> dict[str, object]:
    """Remove a ticker from the watchlist.

    Args:
        ticker: Ticker symbol to remove, e.g. "AAPL", "BTC"

    Returns:
        Confirmation with the updated watchlist. Indicates if ticker was found.
    """
    manager = _get_manager()
    removed = manager.remove(ticker)
    tickers = manager.get_all()
    return {
        "removed": ticker.upper().strip(),
        "was_present": removed,
        "tickers": tickers,
        "count": len(tickers),
    }
