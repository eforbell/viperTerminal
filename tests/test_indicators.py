"""Tests for technical indicator calculations."""

import pytest

from viper.services.indicators import calculate_ema, calculate_sma


class TestCalculateSMA:
    """Test suite for Simple Moving Average calculation."""

    def test_sma_basic_calculation(self) -> None:
        """Test basic SMA calculation with simple numbers."""
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calculate_sma(prices, 3)

        assert result == [None, None, 2.0, 3.0, 4.0]

    def test_sma_period_20(self) -> None:
        """Test SMA with common 20-period setting."""
        # Create 25 prices: 1 to 25
        prices = [float(i) for i in range(1, 26)]
        result = calculate_sma(prices, 20)

        # First 19 should be None
        assert all(v is None for v in result[:19])

        # 20th value: average of 1..20 = 10.5
        assert result[19] == 10.5

        # 21st value: average of 2..21 = 11.5
        assert result[20] == 11.5

        # Last value: average of 6..25 = 15.5
        assert result[24] == 15.5

    def test_sma_period_50(self) -> None:
        """Test SMA with common 50-period setting."""
        # Create 60 prices
        prices = [float(i) for i in range(1, 61)]
        result = calculate_sma(prices, 50)

        # First 49 should be None
        assert all(v is None for v in result[:49])

        # 50th value: average of 1..50 = 25.5
        assert result[49] == 25.5

        # Last value: average of 11..60 = 35.5
        assert result[59] == 35.5

    def test_sma_period_200(self) -> None:
        """Test SMA with common 200-period setting."""
        # Create 250 prices
        prices = [float(i) for i in range(1, 251)]
        result = calculate_sma(prices, 200)

        # First 199 should be None
        assert all(v is None for v in result[:199])

        # 200th value: average of 1..200 = 100.5
        assert result[199] == 100.5

        # Last value: average of 51..250 = 150.5
        assert result[249] == 150.5

    def test_sma_insufficient_data(self) -> None:
        """Test SMA when there's less data than period."""
        prices = [1.0, 2.0, 3.0]
        result = calculate_sma(prices, 5)

        # All values should be None (not enough data)
        assert result == [None, None, None]

    def test_sma_exact_period_size(self) -> None:
        """Test SMA when data length exactly equals period."""
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = calculate_sma(prices, 5)

        # First 4 should be None, last one should be average
        assert result[:4] == [None, None, None, None]
        assert result[4] == 30.0  # (10+20+30+40+50) / 5

    def test_sma_empty_prices(self) -> None:
        """Test SMA with empty price list."""
        result = calculate_sma([], 20)
        assert result == []

    def test_sma_single_value(self) -> None:
        """Test SMA with single price value."""
        result = calculate_sma([100.0], 1)
        assert result == [100.0]

    def test_sma_period_1(self) -> None:
        """Test SMA with period=1 (should equal original prices)."""
        prices = [10.0, 20.0, 30.0, 40.0]
        result = calculate_sma(prices, 1)
        assert result == prices

    def test_sma_invalid_period_zero(self) -> None:
        """Test SMA rejects period=0."""
        with pytest.raises(ValueError, match="Period must be positive"):
            calculate_sma([1.0, 2.0, 3.0], 0)

    def test_sma_invalid_period_negative(self) -> None:
        """Test SMA rejects negative period."""
        with pytest.raises(ValueError, match="Period must be positive"):
            calculate_sma([1.0, 2.0, 3.0], -5)

    def test_sma_real_world_prices(self) -> None:
        """Test SMA with realistic stock price data."""
        # Simulated AAPL-like prices
        prices = [
            150.0,
            152.5,
            151.0,
            153.0,
            154.5,
            152.0,
            155.0,
            156.5,
            154.0,
            157.0,
        ]
        result = calculate_sma(prices, 5)

        # First 4 should be None
        assert all(v is None for v in result[:4])

        # 5th value: average of first 5 prices
        assert result[4] == pytest.approx(152.2, abs=0.01)

        # 6th value: average of prices[1:6]
        assert result[5] == pytest.approx(152.6, abs=0.01)

        # Last value: average of last 5 prices
        assert result[9] == pytest.approx(154.9, abs=0.01)

    def test_sma_flat_prices(self) -> None:
        """Test SMA with constant prices (should equal price)."""
        prices = [100.0] * 10
        result = calculate_sma(prices, 5)

        # All non-None values should be 100.0
        assert all(v is None for v in result[:4])
        assert all(v == 100.0 for v in result[4:] if v is not None)

    def test_sma_volatile_prices(self) -> None:
        """Test SMA smooths volatile price swings."""
        # Alternating high/low prices
        prices = [100.0, 200.0, 100.0, 200.0, 100.0, 200.0]
        result = calculate_sma(prices, 3)

        # SMA should smooth the volatility
        assert result[0] is None
        assert result[1] is None
        assert result[2] == pytest.approx(133.33, abs=0.01)  # (100+200+100)/3
        assert result[3] == pytest.approx(166.67, abs=0.01)  # (200+100+200)/3
        assert result[4] == pytest.approx(133.33, abs=0.01)  # (100+200+100)/3
        assert result[5] == pytest.approx(166.67, abs=0.01)  # (200+100+200)/3

    def test_sma_length_matches_input(self) -> None:
        """Test that output length always matches input length."""
        for length in [1, 5, 10, 50, 100]:
            prices = [float(i) for i in range(length)]
            result = calculate_sma(prices, 20)
            assert len(result) == length

    def test_sma_none_count_correct(self) -> None:
        """Test that number of None values equals (period - 1)."""
        prices = [float(i) for i in range(100)]

        for period in [5, 10, 20, 50]:
            result = calculate_sma(prices, period)
            none_count = sum(1 for v in result if v is None)
            assert none_count == period - 1


class TestCalculateEMA:
    """Test suite for Exponential Moving Average calculation."""

    def test_ema_basic_calculation(self) -> None:
        """Test basic EMA calculation with simple numbers."""
        prices = [22.0, 24.0, 26.0, 28.0, 30.0]
        result = calculate_ema(prices, 3)

        # First 2 should be None (period - 1)
        assert result[0] is None
        assert result[1] is None

        # Third value is SMA of first 3: (22+24+26)/3 = 24.0
        assert result[2] == 24.0

        # k = 2/(3+1) = 0.5
        # Fourth value: (28 * 0.5) + (24 * 0.5) = 26.0
        assert result[3] == pytest.approx(26.0, abs=0.01)

        # Fifth value: (30 * 0.5) + (26 * 0.5) = 28.0
        assert result[4] == pytest.approx(28.0, abs=0.01)

    def test_ema_period_12(self) -> None:
        """Test EMA with common 12-period setting (MACD fast line)."""
        # Create 20 prices
        prices = [float(i) for i in range(1, 21)]
        result = calculate_ema(prices, 12)

        # First 11 should be None
        assert all(v is None for v in result[:11])

        # 12th value is SMA of first 12: average of 1..12 = 6.5
        assert result[11] == 6.5

        # Subsequent values should increase (since prices are increasing)
        assert result[12] is not None
        assert result[12] > result[11]

    def test_ema_period_26(self) -> None:
        """Test EMA with common 26-period setting (MACD slow line)."""
        # Create 40 prices
        prices = [float(i) for i in range(1, 41)]
        result = calculate_ema(prices, 26)

        # First 25 should be None
        assert all(v is None for v in result[:25])

        # 26th value is SMA of first 26: average of 1..26 = 13.5
        assert result[25] == 13.5

        # Subsequent values should increase
        assert result[26] is not None
        assert result[26] > result[25]

    def test_ema_period_50(self) -> None:
        """Test EMA with common 50-period setting."""
        # Create 60 prices
        prices = [float(i) for i in range(1, 61)]
        result = calculate_ema(prices, 50)

        # First 49 should be None
        assert all(v is None for v in result[:49])

        # 50th value is SMA of first 50: average of 1..50 = 25.5
        assert result[49] == 25.5

        # Verify it continues to calculate
        assert result[50] is not None
        assert result[59] is not None

    def test_ema_insufficient_data(self) -> None:
        """Test EMA when there's less data than period."""
        prices = [1.0, 2.0, 3.0]
        result = calculate_ema(prices, 5)

        # All values should be None (not enough data)
        assert result == [None, None, None]

    def test_ema_exact_period_size(self) -> None:
        """Test EMA when data length exactly equals period."""
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = calculate_ema(prices, 5)

        # First 4 should be None, last one should be SMA
        assert result[:4] == [None, None, None, None]
        assert result[4] == 30.0  # (10+20+30+40+50) / 5

    def test_ema_empty_prices(self) -> None:
        """Test EMA with empty price list."""
        result = calculate_ema([], 12)
        assert result == []

    def test_ema_single_value(self) -> None:
        """Test EMA with single price value."""
        result = calculate_ema([100.0], 1)
        assert result == [100.0]

    def test_ema_period_1(self) -> None:
        """Test EMA with period=1 (should equal original prices)."""
        prices = [10.0, 20.0, 30.0, 40.0]
        result = calculate_ema(prices, 1)
        # With period=1, k=2/(1+1)=1.0, so EMA equals current price
        assert result == prices

    def test_ema_invalid_period_zero(self) -> None:
        """Test EMA rejects period=0."""
        with pytest.raises(ValueError, match="Period must be positive"):
            calculate_ema([1.0, 2.0, 3.0], 0)

    def test_ema_invalid_period_negative(self) -> None:
        """Test EMA rejects negative period."""
        with pytest.raises(ValueError, match="Period must be positive"):
            calculate_ema([1.0, 2.0, 3.0], -5)

    def test_ema_real_world_prices(self) -> None:
        """Test EMA with realistic stock price data."""
        # Simulated AAPL-like prices
        prices = [
            150.0,
            152.5,
            151.0,
            153.0,
            154.5,
            152.0,
            155.0,
            156.5,
            154.0,
            157.0,
        ]
        result = calculate_ema(prices, 5)

        # First 4 should be None
        assert all(v is None for v in result[:4])

        # 5th value: SMA of first 5 prices
        assert result[4] == pytest.approx(152.2, abs=0.01)

        # k = 2/(5+1) = 0.333...
        # Subsequent values should be calculated
        assert result[5] is not None
        assert result[9] is not None

        # EMA should be close to but not equal to SMA (more weight on recent)
        assert isinstance(result[9], float)

    def test_ema_flat_prices(self) -> None:
        """Test EMA with constant prices (should equal price)."""
        prices = [100.0] * 10
        result = calculate_ema(prices, 5)

        # All non-None values should be 100.0 (no change in prices)
        assert all(v is None for v in result[:4])
        assert all(abs(v - 100.0) < 0.01 for v in result[4:] if v is not None)

    def test_ema_reacts_faster_than_sma(self) -> None:
        """Test that EMA reacts faster to price changes than SMA."""
        # Price jump in the middle
        prices = [100.0] * 10 + [150.0] * 10
        period = 5

        sma_result = calculate_sma(prices, period)
        ema_result = calculate_ema(prices, period)

        # At index 12 (2 periods after the jump), EMA should be closer to 150 than SMA
        sma_val = sma_result[12]
        ema_val = ema_result[12]

        assert sma_val is not None
        assert ema_val is not None

        # EMA should be higher (closer to new price of 150)
        assert ema_val > sma_val

    def test_ema_length_matches_input(self) -> None:
        """Test that output length always matches input length."""
        for length in [1, 5, 10, 50, 100]:
            prices = [float(i) for i in range(length)]
            result = calculate_ema(prices, 12)
            assert len(result) == length

    def test_ema_none_count_correct(self) -> None:
        """Test that number of None values equals (period - 1)."""
        prices = [float(i) for i in range(100)]

        for period in [5, 10, 12, 26, 50]:
            result = calculate_ema(prices, period)
            none_count = sum(1 for v in result if v is None)
            assert none_count == period - 1

    def test_ema_smoothing_factor(self) -> None:
        """Test that the smoothing factor k = 2/(period+1) is correctly applied."""
        # Simple test with period=3, k=0.5
        prices = [10.0, 10.0, 10.0, 20.0]  # Flat then jump
        result = calculate_ema(prices, 3)

        # First EMA is SMA: (10+10+10)/3 = 10.0
        assert result[2] == 10.0

        # Next EMA: (20 * 0.5) + (10 * 0.5) = 15.0
        assert result[3] == pytest.approx(15.0, abs=0.01)

    def test_ema_converges_upward_trend(self) -> None:
        """Test EMA behavior with consistent upward trend."""
        prices = [float(i * 2) for i in range(20)]  # 0, 2, 4, 6, ..., 38
        result = calculate_ema(prices, 5)

        # Skip None values
        ema_values = [v for v in result if v is not None]

        # EMA should be monotonically increasing for increasing prices
        for i in range(1, len(ema_values)):
            assert ema_values[i] > ema_values[i - 1]

    def test_ema_converges_downward_trend(self) -> None:
        """Test EMA behavior with consistent downward trend."""
        prices = [float(100 - i * 2) for i in range(20)]  # 100, 98, 96, ..., 62
        result = calculate_ema(prices, 5)

        # Skip None values
        ema_values = [v for v in result if v is not None]

        # EMA should be monotonically decreasing for decreasing prices
        for i in range(1, len(ema_values)):
            assert ema_values[i] < ema_values[i - 1]

    def test_ema_known_calculation(self) -> None:
        """Test EMA against a known hand-calculated example."""
        # Simple case: period=2, k=2/(2+1)=0.6667
        prices = [10.0, 12.0, 14.0, 16.0]
        result = calculate_ema(prices, 2)

        # First value is None
        assert result[0] is None

        # Second value is SMA: (10+12)/2 = 11.0
        assert result[1] == 11.0

        # Third value: (14 * 0.6667) + (11 * 0.3333) = 9.333 + 3.667 = 13.0
        assert result[2] == pytest.approx(13.0, abs=0.01)

        # Fourth value: (16 * 0.6667) + (13 * 0.3333) = 10.667 + 4.333 = 15.0
        assert result[3] == pytest.approx(15.0, abs=0.01)
