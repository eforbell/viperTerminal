"""Tests for configuration management."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from viper.config import Config, get_config_path, load_config


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = Config()

        assert config.refresh_interval == 60
        assert config.theme_colors == {
            "positive": "#00ff00",
            "negative": "#ff0000",
            "background": "#000000",
        }
        assert config.default_watchlist == []

    def test_custom_refresh_interval(self) -> None:
        """Test custom refresh interval."""
        config = Config(refresh_interval=120)
        assert config.refresh_interval == 120

    def test_custom_theme_colors(self) -> None:
        """Test custom theme colors."""
        custom_colors = {
            "positive": "#00aa00",
            "negative": "#aa0000",
            "background": "#111111",
        }
        config = Config(theme_colors=custom_colors)
        assert config.theme_colors == custom_colors

    def test_custom_default_watchlist(self) -> None:
        """Test custom default watchlist."""
        watchlist = ["AAPL", "GOOGL", "BTC"]
        config = Config(default_watchlist=watchlist)
        assert config.default_watchlist == watchlist

    def test_invalid_refresh_interval_negative(self) -> None:
        """Test that negative refresh interval falls back to default."""
        config = Config(refresh_interval=-10)
        assert config.refresh_interval == 60

    def test_invalid_refresh_interval_zero(self) -> None:
        """Test that zero refresh interval falls back to default."""
        config = Config(refresh_interval=0)
        assert config.refresh_interval == 60

    def test_invalid_theme_colors_type(self) -> None:
        """Test that invalid theme_colors type falls back to default."""
        config = Config(theme_colors="invalid")  # type: ignore[arg-type]
        assert config.theme_colors == {
            "positive": "#00ff00",
            "negative": "#ff0000",
            "background": "#000000",
        }

    def test_invalid_default_watchlist_type(self) -> None:
        """Test that invalid default_watchlist type falls back to default."""
        config = Config(default_watchlist="invalid")  # type: ignore[arg-type]
        assert config.default_watchlist == []


class TestGetConfigPath:
    """Tests for get_config_path function."""

    def test_returns_correct_path(self) -> None:
        """Test that get_config_path returns the correct path."""
        path = get_config_path()
        assert path == Path.home() / ".config" / "viper" / "config.toml"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_file_not_exists(self) -> None:
        """Test loading config when file doesn't exist."""
        with patch("viper.config.get_config_path") as mock_get_path:
            mock_path = Mock(spec=Path)
            mock_path.exists.return_value = False
            mock_get_path.return_value = mock_path

            config = load_config()

            # Should return default config
            assert config.refresh_interval == 60
            assert config.theme_colors == {
                "positive": "#00ff00",
                "negative": "#ff0000",
                "background": "#000000",
            }
            assert config.default_watchlist == []

    def test_load_config_with_all_values(self, tmp_path: Path) -> None:
        """Test loading config with all custom values."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
refresh_interval = 120
default_watchlist = ["AAPL", "GOOGL", "BTC"]

[theme_colors]
positive = "#00aa00"
negative = "#aa0000"
background = "#111111"
"""
        )

        with patch("viper.config.get_config_path", return_value=config_file):
            config = load_config()

        assert config.refresh_interval == 120
        assert config.theme_colors == {
            "positive": "#00aa00",
            "negative": "#aa0000",
            "background": "#111111",
        }
        assert config.default_watchlist == ["AAPL", "GOOGL", "BTC"]

    def test_load_config_partial_values(self, tmp_path: Path) -> None:
        """Test loading config with only some values set."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("refresh_interval = 90\n")

        with patch("viper.config.get_config_path", return_value=config_file):
            config = load_config()

        # Custom value
        assert config.refresh_interval == 90

        # Defaults
        assert config.theme_colors == {
            "positive": "#00ff00",
            "negative": "#ff0000",
            "background": "#000000",
        }
        assert config.default_watchlist == []

    def test_load_config_invalid_toml(self, tmp_path: Path) -> None:
        """Test loading config with invalid TOML syntax."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("this is not valid toml [[[")

        with patch("viper.config.get_config_path", return_value=config_file):
            config = load_config()

        # Should fall back to defaults
        assert config.refresh_interval == 60
        assert config.theme_colors == {
            "positive": "#00ff00",
            "negative": "#ff0000",
            "background": "#000000",
        }
        assert config.default_watchlist == []

    def test_load_config_read_error(self, tmp_path: Path) -> None:
        """Test loading config when file cannot be read."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("refresh_interval = 90")

        with patch("viper.config.get_config_path", return_value=config_file):
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                config = load_config()

        # Should fall back to defaults
        assert config.refresh_interval == 60

    def test_load_config_invalid_refresh_interval_in_file(
        self, tmp_path: Path
    ) -> None:
        """Test that invalid refresh interval in file triggers validation."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("refresh_interval = -10\n")

        with patch("viper.config.get_config_path", return_value=config_file):
            config = load_config()

        # Validation should correct it to 60
        assert config.refresh_interval == 60

    def test_load_config_invalid_theme_colors_in_file(self, tmp_path: Path) -> None:
        """Test that invalid theme_colors in file triggers validation."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('theme_colors = "not a dict"\n')

        with patch("viper.config.get_config_path", return_value=config_file):
            config = load_config()

        # Validation should correct it to defaults
        assert config.theme_colors == {
            "positive": "#00ff00",
            "negative": "#ff0000",
            "background": "#000000",
        }

    def test_load_config_invalid_watchlist_in_file(self, tmp_path: Path) -> None:
        """Test that invalid default_watchlist in file triggers validation."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_watchlist = "not a list"\n')

        with patch("viper.config.get_config_path", return_value=config_file):
            config = load_config()

        # Validation should correct it to empty list
        assert config.default_watchlist == []

    def test_load_config_unexpected_error(self, tmp_path: Path) -> None:
        """Test handling of unexpected errors during config load."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("refresh_interval = 90")

        with patch("viper.config.get_config_path", return_value=config_file):
            with patch("tomllib.load", side_effect=Exception("Unexpected error")):
                config = load_config()

        # Should fall back to defaults
        assert config.refresh_interval == 60

    def test_load_config_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty config file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        with patch("viper.config.get_config_path", return_value=config_file):
            config = load_config()

        # Should return all defaults
        assert config.refresh_interval == 60
        assert config.theme_colors == {
            "positive": "#00ff00",
            "negative": "#ff0000",
            "background": "#000000",
        }
        assert config.default_watchlist == []
