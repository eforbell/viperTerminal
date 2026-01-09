"""ChartContext - shared immutable data structure for chart dimensions and data.

This module provides the ChartContext dataclass, which serves as the single source
of truth for all chart-related dimensions and data. It ensures perfect alignment
between the price chart, volume bars, indicators (RSI, MACD, etc.), and X-axis.

Design principles:
- Immutable (frozen=True) - safe to pass around without side effects
- Single source of truth - all components use the same dimensions
- Computed properties - derived values calculated consistently
- Factory pattern - from_historical_data() creates context from data
"""

from dataclasses import dataclass
from datetime import datetime

from viper.services.history_data import HistoricalData


@dataclass(frozen=True)
class ChartContext:
    """Immutable chart context holding all shared dimensions and data.

    This dataclass is the contract between ChartPanel and all rendering components
    (chart_renderer, indicator panels, X-axis). It ensures perfect horizontal
    alignment by providing consistent width calculations to all components.

    Attributes:
        ticker: Stock/crypto ticker symbol (e.g., "AAPL", "BTC-USD")
        period: User-friendly period (e.g., "1W", "1M", "3M")
        dates: List of datetime objects for each data point
        prices: Closing prices (matches dates length)
        volumes: Trading volumes (matches dates length)
        opens: Opening prices (matches dates length)
        closes: Closing prices (same as prices, for symmetry with opens)
        highs: High prices (matches dates length)
        lows: Low prices (matches dates length)
        total_width: Total terminal width available for chart
        total_height: Total terminal height available for chart
        y_axis_width: Width reserved for Y-axis labels (default 12)

    Computed properties:
        chart_area_width: Width available for actual chart data (total_width - y_axis_width)

    Example:
        >>> from viper.services.history_data import HistoricalData
        >>> data = HistoricalData(...)
        >>> context = ChartContext.from_historical_data(data, width=100, height=30)
        >>> context.chart_area_width
        88  # 100 - 12
    """

    ticker: str
    period: str
    dates: list[datetime]
    prices: list[float]
    volumes: list[int]
    opens: list[float]
    closes: list[float]
    highs: list[float]
    lows: list[float]
    total_width: int
    total_height: int
    y_axis_width: int = 12

    @property
    def chart_area_width(self) -> int:
        """Width available for chart data after Y-axis is reserved.

        This is the critical dimension used by all components for horizontal alignment.
        All chart data, volume bars, and indicator lines render within this width.

        Returns:
            Usable width for chart content (total_width - y_axis_width)
        """
        return self.total_width - self.y_axis_width

    @classmethod
    def from_historical_data(
        cls,
        data: HistoricalData,
        width: int,
        height: int,
        y_axis_width: int = 12,
    ) -> "ChartContext":
        """Factory method to create ChartContext from HistoricalData.

        This is the standard way to create a ChartContext from fetched market data.
        It extracts all necessary fields and combines them with dimension parameters.

        Args:
            data: Historical market data from yfinance
            width: Total terminal width available
            height: Total terminal height available
            y_axis_width: Width to reserve for Y-axis labels (default 12)

        Returns:
            Immutable ChartContext ready for rendering

        Example:
            >>> data = await fetch_historical_data("AAPL", "1M")
            >>> context = ChartContext.from_historical_data(data, width=100, height=30)
            >>> render_chart(context)
        """
        return cls(
            ticker=data.ticker,
            period=data.period,
            dates=data.dates,
            prices=data.prices,
            volumes=data.volumes,
            opens=data.opens,
            closes=data.prices,  # closes = prices for symmetry
            highs=data.highs,
            lows=data.lows,
            total_width=width,
            total_height=height,
            y_axis_width=y_axis_width,
        )
