"""FastMCP server instance for Viper market data.

This module creates the MCP server and imports all tool modules
so their @mcp.tool() decorators register with the server.
"""

from mcp.server.fastmcp import FastMCP

from viper.mcp.runtime import configure_mcp_runtime

configure_mcp_runtime()

mcp = FastMCP("viper-market-data")

# Import tool modules to register their @mcp.tool() decorators
import viper.mcp.tools.history  # noqa: F401, E402
import viper.mcp.tools.indicators  # noqa: F401, E402
import viper.mcp.tools.info  # noqa: F401, E402
import viper.mcp.tools.news  # noqa: F401, E402
import viper.mcp.tools.options  # noqa: F401, E402
import viper.mcp.tools.quote  # noqa: F401, E402
import viper.mcp.tools.scan  # noqa: F401, E402
import viper.mcp.tools.watchlist  # noqa: F401, E402
