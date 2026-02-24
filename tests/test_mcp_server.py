"""Tests for MCP server creation and tool registration."""

from viper.mcp.server import mcp


class TestMCPServer:
    """Tests for the MCP server instance."""

    def test_server_exists(self) -> None:
        """Server instance should be created."""
        assert mcp is not None

    def test_server_name(self) -> None:
        """Server should have the correct name."""
        assert mcp.name == "viper-market-data"

    def test_all_tools_registered(self) -> None:
        """All 11 tools should be registered."""
        tools = mcp._tool_manager._tools
        expected_tools = {
            "get_quote",
            "get_price_history",
            "get_technical_indicators",
            "get_option_expirations",
            "get_options_chain",
            "get_news",
            "get_stock_info",
            "get_crypto_info",
            "get_watchlist",
            "add_to_watchlist",
            "remove_from_watchlist",
        }
        registered = set(tools.keys())
        assert expected_tools == registered, (
            f"Missing: {expected_tools - registered}, "
            f"Extra: {registered - expected_tools}"
        )
