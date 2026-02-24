"""Tests for MCP runtime configuration."""

from pathlib import Path
from unittest.mock import patch

from viper.mcp.runtime import configure_mcp_runtime


class TestConfigureMCPRuntime:
    """Tests for yfinance runtime setup used by MCP server."""

    def test_sets_default_cache_path(self) -> None:
        """Should set yfinance cache path under the user's cache directory."""
        with patch("viper.mcp.runtime.yf.set_tz_cache_location") as mock_set:
            configure_mcp_runtime()
            mock_set.assert_called_once()
            configured_path = Path(mock_set.call_args.args[0])
            assert configured_path.name == "yfinance"

    def test_respects_env_override(self, tmp_path: Path) -> None:
        """Should use configured env var cache path when provided."""
        custom_cache = tmp_path / "custom-yf-cache"
        with (
            patch.dict(
                "viper.mcp.runtime.os.environ",
                {"VIPER_MCP_YF_TZ_CACHE_DIR": str(custom_cache)},
                clear=False,
            ),
            patch("viper.mcp.runtime.yf.set_tz_cache_location") as mock_set,
        ):
            configure_mcp_runtime()
            mock_set.assert_called_once_with(str(custom_cache))
