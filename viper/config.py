"""Configuration management for Viper Terminal."""

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from viper.utils.logger import get_logger

logger = get_logger()

# Valid chart styles
ChartStyleLiteral = Literal["braille", "block", "candlestick"]

# Valid timeframes
VALID_TIMEFRAMES = ["1W", "1M", "3M", "6M", "1Y", "5Y", "MAX"]


@dataclass
class Config:
    """Viper Terminal configuration."""

    # Watchlist settings
    refresh_interval: int = 60  # Watchlist refresh interval in seconds
    streaming_enabled: bool = False  # Enable real-time streaming mode for watchlist
    theme_colors: dict[str, str] = field(
        default_factory=lambda: {
            "positive": "#00ff00",
            "negative": "#ff0000",
            "background": "#000000",
        }
    )
    default_watchlist: list[str] = field(default_factory=list)

    # Chart settings
    default_chart_timeframe: str = "1Y"  # Default timeframe for charts
    chart_style: str = "candlestick"  # 'braille', 'block', or 'candlestick'
    chart_refresh_interval: int = 30  # Chart refresh interval in seconds for candlestick mode (0 to disable)

    # News settings
    news_enabled: bool = True  # Whether news panel is available
    news_max_items: int = 10  # Maximum news items to display

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        # Validate refresh_interval is positive
        if self.refresh_interval <= 0:
            logger.warning(
                f"Invalid refresh_interval {self.refresh_interval}, using default 60"
            )
            self.refresh_interval = 60

        # Validate streaming_enabled is bool
        if not isinstance(self.streaming_enabled, bool):
            logger.warning(
                f"Invalid streaming_enabled type {type(self.streaming_enabled)}, using default False"
            )
            self.streaming_enabled = False

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

        # Validate chart_style
        if self.chart_style not in ("braille", "block", "candlestick"):
            logger.warning(
                f"Invalid chart_style '{self.chart_style}', using default 'candlestick'"
            )
            self.chart_style = "candlestick"

        # Validate default_chart_timeframe
        if self.default_chart_timeframe not in VALID_TIMEFRAMES:
            logger.warning(
                f"Invalid default_chart_timeframe '{self.default_chart_timeframe}', using default '1Y'"
            )
            self.default_chart_timeframe = "1Y"

        # Validate news_enabled is bool
        if not isinstance(self.news_enabled, bool):
            logger.warning(
                f"Invalid news_enabled type {type(self.news_enabled)}, using default True"
            )
            self.news_enabled = True

        # Validate news_max_items is positive
        if not isinstance(self.news_max_items, int) or self.news_max_items <= 0:
            logger.warning(
                f"Invalid news_max_items '{self.news_max_items}', using default 10"
            )
            self.news_max_items = 10

        # Validate chart_refresh_interval is non-negative
        if not isinstance(self.chart_refresh_interval, int) or self.chart_refresh_interval < 0:
            logger.warning(
                f"Invalid chart_refresh_interval '{self.chart_refresh_interval}', using default 30"
            )
            self.chart_refresh_interval = 30


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

        # Watchlist settings
        if "refresh_interval" in data:
            config_dict["refresh_interval"] = data["refresh_interval"]

        if "streaming_enabled" in data:
            config_dict["streaming_enabled"] = data["streaming_enabled"]

        if "theme_colors" in data:
            config_dict["theme_colors"] = data["theme_colors"]

        if "default_watchlist" in data:
            config_dict["default_watchlist"] = data["default_watchlist"]

        # Chart settings
        if "default_chart_timeframe" in data:
            config_dict["default_chart_timeframe"] = data["default_chart_timeframe"]

        if "chart_style" in data:
            config_dict["chart_style"] = data["chart_style"]

        # News settings
        if "news_enabled" in data:
            config_dict["news_enabled"] = data["news_enabled"]

        if "news_max_items" in data:
            config_dict["news_max_items"] = data["news_max_items"]

        if "chart_refresh_interval" in data:
            config_dict["chart_refresh_interval"] = data["chart_refresh_interval"]

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
