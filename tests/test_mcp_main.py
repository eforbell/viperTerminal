"""Tests for the MCP main entry point."""

from unittest.mock import patch

from viper.mcp.__main__ import main


def test_main_sets_up_logging_and_runs_server() -> None:
    """main() should configure logging and run stdio MCP server."""
    with (
        patch("viper.mcp.__main__.setup_mcp_logging") as mock_setup,
        patch("viper.mcp.__main__.get_mcp_logger") as mock_get_logger,
        patch("viper.mcp.__main__.mcp.run") as mock_run,
    ):
        main()

        mock_setup.assert_called_once()
        mock_get_logger.assert_called_once()
        mock_get_logger.return_value.info.assert_called_once()
        mock_run.assert_called_once_with(transport="stdio")
