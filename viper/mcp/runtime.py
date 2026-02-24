"""Runtime configuration helpers for the MCP server."""

import os
from pathlib import Path

import yfinance as yf  # type: ignore[import-untyped]


def configure_mcp_runtime() -> None:
    """Configure runtime settings needed for stable MCP operation.

    Specifically, ensure yfinance timezone cache writes to a writable path.
    """
    env_cache_dir = os.getenv("VIPER_MCP_YF_TZ_CACHE_DIR")
    if env_cache_dir:
        cache_dir = Path(env_cache_dir).expanduser()
    else:
        cache_dir = Path.home() / ".cache" / "viper" / "yfinance"

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache_dir))
        return
    except OSError:
        # Final fallback for locked-down environments.
        fallback = Path("/tmp/viper-yfinance-cache")
        fallback.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(fallback))
