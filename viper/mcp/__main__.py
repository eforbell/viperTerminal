"""Entry point for the viper-mcp command."""

from viper.mcp.server import mcp


def main() -> None:
    """Run the Viper MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
