"""RSI (Relative Strength Index) indicator panel widget.

This module provides an RSI indicator panel that displays the RSI oscillator
with overbought (70) and oversold (30) reference lines.
"""

from viper.widgets.indicator_panel import HorizontalLine, IndicatorPanel


class RSIPanel(IndicatorPanel):
    """Panel for displaying the Relative Strength Index (RSI) indicator.

    RSI is a momentum oscillator that ranges from 0 to 100:
    - RSI > 70: Overbought condition (red line)
    - RSI < 30: Oversold condition (green line)
    - RSI 30-70: Neutral range
    """

    def __init__(self) -> None:
        """Initialize the RSI panel with standard RSI configuration."""
        # Define RSI reference lines: overbought (70) and oversold (30)
        reference_lines = [
            HorizontalLine(
                value=70.0,
                label="Overbought (70)",
                style="dashed",
                color="\033[31m"  # Red for overbought
            ),
            HorizontalLine(
                value=30.0,
                label="Oversold (30)",
                style="dashed",
                color="\033[32m"  # Green for oversold
            ),
        ]

        # Initialize with RSI-specific configuration
        super().__init__(
            name="RSI",
            height=4,  # 4 lines for RSI chart
            min_value=0.0,
            max_value=100.0,
            reference_lines=reference_lines
        )
