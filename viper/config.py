"""Configuration management for Viper Terminal."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from viper.utils.logger import get_logger

logger = get_logger()


@dataclass
class Config:
    """Viper Terminal configuration."""

    refresh_interval: int = 60  # Watchlist refresh interval in seconds
    theme_colors: dict[str, str] = field(
        default_factory=lambda: {
            "positive": "#00ff00",
            "negative": "#ff0000",
            "background": "#000000",
        }
    )
    default_watchlist: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        # Validate refresh_interval is positive
        if self.refresh_interval <= 0:
            logger.warning(
                f"Invalid refresh_interval {self.refresh_interval}, using default 60"
            )
            self.refresh_interval = 60

        # Validate theme_colors is a dict
        if not isinstance(self.theme_colors, dict):
            logger.warning(
                f"Invalid theme_colors type {type(self.theme_colors)}, using defaults"
            )
            self.theme_colors = {
                "positive": "#00ff00",
                "negative": "#ff0000",
                "background": "#000000",
            }

        # Validate default_watchlist is a list
        if not isinstance(self.default_watchlist, list):
            logger.warning(
                f"Invalid default_watchlist type {type(self.default_watchlist)}, using empty list"
            )
            self.default_watchlist = []


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".config" / "viper" / "config.toml"


def load_config() -> Config:
    """Load configuration from config.toml file.

    Returns:
        Config object with settings from file or defaults if file doesn't exist.
    """
    config_path = get_config_path()

    # If config file doesn't exist, return default config
    if not config_path.exists():
        logger.info(f"Config file not found at {config_path}, using defaults")
        return Config()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Extract values with defaults
        config_dict: dict[str, Any] = {}

        if "refresh_interval" in data:
            config_dict["refresh_interval"] = data["refresh_interval"]

        if "theme_colors" in data:
            config_dict["theme_colors"] = data["theme_colors"]

        if "default_watchlist" in data:
            config_dict["default_watchlist"] = data["default_watchlist"]

        logger.info(f"Loaded config from {config_path}")
        return Config(**config_dict)

    except tomllib.TOMLDecodeError as e:
        logger.error(f"Invalid TOML in config file: {e}")
        logger.info("Falling back to default configuration")
        return Config()

    except OSError as e:
        logger.error(f"Error reading config file: {e}")
        logger.info("Falling back to default configuration")
        return Config()

    except Exception as e:
        logger.error(f"Unexpected error loading config: {e}")
        logger.info("Falling back to default configuration")
        return Config()
