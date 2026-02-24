"""Entry point for the viper-mcp command."""

from viper.mcp.logging import get_mcp_logger, setup_mcp_logging
from viper.mcp.server import mcp


def main() -> None:
    """Run the Viper MCP server over stdio transport."""
    setup_mcp_logging()
    logger = get_mcp_logger()
    logger.info("Starting MCP server (transport=stdio)")
    try:
        mcp.run(transport="stdio")
    except Exception:
        logger.exception("MCP server crashed")
        raise


if __name__ == "__main__":
    main()
