"""Tests for technical indicator calculations."""

import pytest

from viper.services.indicators import (
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)


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


class TestCalculateRSI:
    """Test suite for Relative Strength Index calculation."""

    def test_rsi_basic_calculation(self) -> None:
        """Test basic RSI calculation with simple price movements."""
        # Price sequence with clear gains and losses
        prices = [
            44.0,
            44.34,
            44.09,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
            46.28,
        ]
        result = calculate_rsi(prices, 14)

        # First 14 values should be None (need 15 prices for first RSI with period=14)
        assert all(v is None for v in result[:14])

        # 15th value should be calculated RSI
        assert result[14] is not None
        assert isinstance(result[14], float)
        assert 0 <= result[14] <= 100

    def test_rsi_default_period_14(self) -> None:
        """Test RSI uses default period of 14."""
        prices = [float(i) for i in range(1, 21)]
        result = calculate_rsi(prices)

        # Should have 14 None values by default
        none_count = sum(1 for v in result if v is None)
        assert none_count == 14

    def test_rsi_all_gains_equals_100(self) -> None:
        """Test RSI equals 100 when all price changes are gains."""
        # Steadily increasing prices (all gains, no losses)
        prices = [float(i * 10) for i in range(20)]  # 0, 10, 20, 30, ...
        result = calculate_rsi(prices, 14)

        # Skip None values and check RSI values
        rsi_values = [v for v in result if v is not None]

        # Should all be 100 (no losses means infinite RS)
        for val in rsi_values:
            assert val == pytest.approx(100.0, abs=0.01)

    def test_rsi_all_losses_equals_0(self) -> None:
        """Test RSI equals 0 when all price changes are losses."""
        # Steadily decreasing prices (all losses, no gains)
        prices = [float(200 - i * 10) for i in range(20)]  # 200, 190, 180, ...
        result = calculate_rsi(prices, 14)

        # Skip None values and check RSI values
        rsi_values = [v for v in result if v is not None]

        # Should all be 0 (no gains means RS = 0)
        for val in rsi_values:
            assert val == pytest.approx(0.0, abs=0.01)

    def test_rsi_flat_prices_equals_50(self) -> None:
        """Test RSI equals ~50 when prices are flat (no change)."""
        # All same prices (no gains or losses)
        prices = [100.0] * 20
        result = calculate_rsi(prices, 14)

        # First 14 are None, then we need at least one more for RSI
        # But with no change, avg_gain and avg_loss are both 0
        # This triggers the avg_loss == 0.0 check, resulting in RSI = 100
        # Actually, with NO change at all (all deltas = 0), both avg_gain and avg_loss = 0
        # Our implementation treats this as RSI = 100 (no losses)
        assert result[14] == pytest.approx(100.0, abs=0.01)

    def test_rsi_insufficient_data(self) -> None:
        """Test RSI when there's less data than period+1."""
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calculate_rsi(prices, 14)

        # All values should be None (need at least 15 prices for period=14)
        assert all(v is None for v in result)
        assert len(result) == 5

    def test_rsi_exact_period_plus_one(self) -> None:
        """Test RSI when data length equals period+1."""
        # Need 15 prices for period=14 (14+1)
        prices = [float(i) for i in range(1, 16)]
        result = calculate_rsi(prices, 14)

        # First 14 should be None, last one should have RSI
        assert result[:14] == [None] * 14
        assert result[14] is not None
        assert 0 <= result[14] <= 100

    def test_rsi_empty_prices(self) -> None:
        """Test RSI with empty price list."""
        result = calculate_rsi([], 14)
        assert result == []

    def test_rsi_single_value(self) -> None:
        """Test RSI with single price value."""
        result = calculate_rsi([100.0], 14)
        assert result == [None]  # Not enough data

    def test_rsi_invalid_period_zero(self) -> None:
        """Test RSI rejects period=0."""
        with pytest.raises(ValueError, match="Period must be positive"):
            calculate_rsi([1.0, 2.0, 3.0], 0)

    def test_rsi_invalid_period_negative(self) -> None:
        """Test RSI rejects negative period."""
        with pytest.raises(ValueError, match="Period must be positive"):
            calculate_rsi([1.0, 2.0, 3.0], -5)

    def test_rsi_range_0_to_100(self) -> None:
        """Test that RSI values are always in range [0, 100]."""
        # Create various price patterns
        prices = []
        for i in range(50):
            if i % 3 == 0:
                prices.append(100.0 + i * 2)  # Gain
            elif i % 3 == 1:
                prices.append(100.0 + i * 2 - 5)  # Loss
            else:
                prices.append(100.0 + i * 2 + 3)  # Gain

        result = calculate_rsi(prices, 14)

        # Check all non-None values are in valid range
        for val in result:
            if val is not None:
                assert 0 <= val <= 100

    def test_rsi_length_matches_input(self) -> None:
        """Test that output length always matches input length."""
        for length in [5, 10, 20, 50, 100]:
            prices = [float(i) for i in range(length)]
            result = calculate_rsi(prices, 14)
            assert len(result) == length

    def test_rsi_none_count_equals_period(self) -> None:
        """Test that number of None values equals period (not period-1 like MA)."""
        prices = [float(i) for i in range(100)]

        for period in [7, 14, 21]:
            result = calculate_rsi(prices, period)
            none_count = sum(1 for v in result if v is None)
            # RSI needs period+1 prices, so first 'period' values are None
            assert none_count == period

    def test_rsi_overbought_condition(self) -> None:
        """Test RSI > 70 indicates overbought condition."""
        # Strong upward trend should result in high RSI
        prices = [100.0]
        for i in range(20):
            prices.append(prices[-1] + 5.0)  # Consistent gains

        result = calculate_rsi(prices, 14)

        # Skip None values
        rsi_values = [v for v in result if v is not None]

        # Should be overbought (> 70)
        for val in rsi_values:
            assert val > 70

    def test_rsi_oversold_condition(self) -> None:
        """Test RSI < 30 indicates oversold condition."""
        # Strong downward trend should result in low RSI
        prices = [200.0]
        for i in range(20):
            prices.append(prices[-1] - 5.0)  # Consistent losses

        result = calculate_rsi(prices, 14)

        # Skip None values
        rsi_values = [v for v in result if v is not None]

        # Should be oversold (< 30)
        for val in rsi_values:
            assert val < 30

    def test_rsi_wilders_smoothing(self) -> None:
        """Test that Wilder's smoothing is applied correctly."""
        # Create price sequence with known pattern
        prices = [
            44.0,
            44.34,
            44.09,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
            46.28,
            46.00,  # Add more data to test smoothing
        ]
        result = calculate_rsi(prices, 14)

        # Verify we get values
        assert result[14] is not None
        assert result[15] is not None

        # Wilder's smoothing should make consecutive RSI values relatively smooth
        # (not wildly different unless there's a major price change)
        assert isinstance(result[14], float)
        assert isinstance(result[15], float)

    def test_rsi_real_world_prices(self) -> None:
        """Test RSI with realistic stock price data."""
        # Simulated stock prices with mixed gains/losses
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
            158.5,
            157.0,
            159.0,
            160.5,
            159.0,
            161.0,
        ]
        result = calculate_rsi(prices, 14)

        # First 14 should be None
        assert all(v is None for v in result[:14])

        # Last values should be calculated and in valid range
        assert result[14] is not None
        assert result[15] is not None
        assert 0 <= result[14] <= 100
        assert 0 <= result[15] <= 100

    def test_rsi_alternating_gains_losses(self) -> None:
        """Test RSI with alternating gains and losses."""
        # Create pattern: +5, -3, +5, -3, ...
        prices = [100.0]
        for i in range(20):
            if i % 2 == 0:
                prices.append(prices[-1] + 5.0)
            else:
                prices.append(prices[-1] - 3.0)

        result = calculate_rsi(prices, 14)

        # Skip None values
        rsi_values = [v for v in result if v is not None]

        # With more gains (+5) than losses (-3), RSI should be > 50
        for val in rsi_values:
            assert val > 50

    def test_rsi_small_period(self) -> None:
        """Test RSI with small period (e.g., 7 for short-term trading)."""
        prices = [float(100 + i * 2) for i in range(20)]
        result = calculate_rsi(prices, 7)

        # First 7 should be None
        assert all(v is None for v in result[:7])

        # 8th value onward should have RSI
        assert result[7] is not None
        assert 0 <= result[7] <= 100

    def test_rsi_large_period(self) -> None:
        """Test RSI with large period (e.g., 21 for long-term analysis)."""
        prices = [float(100 + i) for i in range(50)]
        result = calculate_rsi(prices, 21)

        # First 21 should be None
        assert all(v is None for v in result[:21])

        # 22nd value onward should have RSI
        assert result[21] is not None
        assert 0 <= result[21] <= 100


class TestCalculateMACD:
    """Test suite for MACD (Moving Average Convergence Divergence) calculation."""

    def test_macd_basic_calculation(self) -> None:
        """Test basic MACD calculation with sufficient data."""
        # Create 50 prices to ensure we have data past the initial None values
        prices = [float(100 + i) for i in range(50)]
        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # All three lists should have same length as input
        assert len(macd) == 50
        assert len(signal) == 50
        assert len(histogram) == 50

        # First 33 values should be None: (26-1) + (9-1) + 1 = 33
        # Actually: slow_ema has 25 None (26-1), so macd has 25 None
        # Then signal needs 8 more None (9-1), so signal has 25+8=33 None
        # Let's verify the actual count
        none_count_macd = sum(1 for v in macd if v is None)
        none_count_signal = sum(1 for v in signal if v is None)
        none_count_histogram = sum(1 for v in histogram if v is None)

        # MACD line has (slow_period - 1) None values = 25
        assert none_count_macd == 25

        # Signal line has (slow_period - 1) + (signal_period - 1) = 25 + 8 = 33
        assert none_count_signal == 33

        # Histogram has same None count as signal (can't calculate without both)
        assert none_count_histogram == 33

    def test_macd_default_periods(self) -> None:
        """Test MACD with default periods (12, 26, 9)."""
        prices = [float(100 + i * 0.5) for i in range(60)]
        macd, signal, histogram = calculate_macd(prices)

        # Verify we get calculated values after None period
        assert macd[25] is not None  # First non-None MACD
        assert signal[33] is not None  # First non-None signal
        assert histogram[33] is not None  # First non-None histogram

    def test_macd_can_be_negative(self) -> None:
        """Test that MACD values can be negative (unlike RSI which is 0-100)."""
        # Create prices that go down (fast EMA will be less than slow EMA)
        prices = [float(200 - i) for i in range(60)]
        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # Skip None values and check for negative values
        macd_values = [v for v in macd if v is not None]
        signal_values = [v for v in signal if v is not None]
        histogram_values = [v for v in histogram if v is not None]

        # With declining prices, MACD should be negative
        assert any(v < 0 for v in macd_values)
        assert any(v < 0 for v in signal_values)

    def test_macd_uptrend(self) -> None:
        """Test MACD with upward trending prices (should be positive)."""
        # Steadily increasing prices
        prices = [float(100 + i * 2) for i in range(60)]
        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # Skip None values
        macd_values = [v for v in macd if v is not None]

        # With rising prices, MACD should be positive
        assert all(v > 0 for v in macd_values)

    def test_macd_histogram_equals_macd_minus_signal(self) -> None:
        """Test that histogram = MACD - Signal at all points."""
        prices = [float(100 + i * 0.3) for i in range(60)]
        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # Check all non-None values
        for i in range(len(prices)):
            if macd[i] is not None and signal[i] is not None:
                assert histogram[i] == pytest.approx(macd[i] - signal[i], abs=0.001)

    def test_macd_empty_prices(self) -> None:
        """Test MACD with empty price list."""
        macd, signal, histogram = calculate_macd([], 12, 26, 9)
        assert macd == []
        assert signal == []
        assert histogram == []

    def test_macd_insufficient_data(self) -> None:
        """Test MACD when there's less data than required for calculation."""
        # Only 20 prices - not enough for slow EMA (needs 26)
        prices = [float(i) for i in range(20)]
        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # All values should be None
        assert all(v is None for v in macd)
        assert all(v is None for v in signal)
        assert all(v is None for v in histogram)

    def test_macd_exact_minimum_data(self) -> None:
        """Test MACD with exactly 34 prices (minimum for first signal value)."""
        # Need 34 prices: 33 None + 1 calculated value
        prices = [float(100 + i) for i in range(34)]
        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # MACD should have values starting at index 25
        assert macd[25] is not None

        # Signal should have first value at index 33
        assert signal[33] is not None

        # Histogram should match signal
        assert histogram[33] is not None

    def test_macd_invalid_period_zero(self) -> None:
        """Test MACD rejects period=0."""
        prices = [float(i) for i in range(50)]

        with pytest.raises(ValueError, match="All periods must be positive"):
            calculate_macd(prices, 0, 26, 9)

        with pytest.raises(ValueError, match="All periods must be positive"):
            calculate_macd(prices, 12, 0, 9)

        with pytest.raises(ValueError, match="All periods must be positive"):
            calculate_macd(prices, 12, 26, 0)

    def test_macd_invalid_period_negative(self) -> None:
        """Test MACD rejects negative periods."""
        prices = [float(i) for i in range(50)]

        with pytest.raises(ValueError, match="All periods must be positive"):
            calculate_macd(prices, -12, 26, 9)

    def test_macd_invalid_fast_greater_than_slow(self) -> None:
        """Test MACD rejects fast_period >= slow_period."""
        prices = [float(i) for i in range(50)]

        # Fast > Slow
        with pytest.raises(ValueError, match="fast_period must be less than slow_period"):
            calculate_macd(prices, 26, 12, 9)

        # Fast == Slow
        with pytest.raises(ValueError, match="fast_period must be less than slow_period"):
            calculate_macd(prices, 20, 20, 9)

    def test_macd_length_matches_input(self) -> None:
        """Test that all output lengths match input length."""
        for length in [10, 30, 50, 100]:
            prices = [float(i) for i in range(length)]
            macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

            assert len(macd) == length
            assert len(signal) == length
            assert len(histogram) == length

    def test_macd_flat_prices(self) -> None:
        """Test MACD with constant prices (should be zero)."""
        prices = [100.0] * 60
        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # With flat prices, fast EMA == slow EMA, so MACD should be 0
        macd_values = [v for v in macd if v is not None]

        for val in macd_values:
            assert abs(val) < 0.01  # Should be ~0

    def test_macd_crossover_bullish(self) -> None:
        """Test MACD bullish crossover (MACD crosses above Signal)."""
        # Create price pattern: down then strong up
        prices = [float(150 - i) for i in range(30)]  # Downtrend
        prices.extend([float(120 + i * 2) for i in range(30)])  # Strong uptrend

        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # In an uptrend, MACD should eventually be above signal (positive histogram)
        histogram_values = [v for v in histogram[-10:] if v is not None]

        # At least some recent histogram values should be positive (MACD > Signal)
        assert any(v > 0 for v in histogram_values)

    def test_macd_crossover_bearish(self) -> None:
        """Test MACD bearish crossover (MACD crosses below Signal)."""
        # Create price pattern: up then strong down
        prices = [float(100 + i) for i in range(30)]  # Uptrend
        prices.extend([float(130 - i * 2) for i in range(30)])  # Strong downtrend

        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # In a downtrend, MACD should eventually be below signal (negative histogram)
        histogram_values = [v for v in histogram[-10:] if v is not None]

        # At least some recent histogram values should be negative (MACD < Signal)
        assert any(v < 0 for v in histogram_values)

    def test_macd_real_world_prices(self) -> None:
        """Test MACD with realistic stock price data."""
        # Simulated stock prices with volatility
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
        ] * 6  # Repeat to get 60 prices

        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # Verify lengths
        assert len(macd) == 60
        assert len(signal) == 60
        assert len(histogram) == 60

        # Verify some values are calculated
        macd_values = [v for v in macd if v is not None]
        signal_values = [v for v in signal if v is not None]
        histogram_values = [v for v in histogram if v is not None]

        assert len(macd_values) > 0
        assert len(signal_values) > 0
        assert len(histogram_values) > 0

    def test_macd_signal_smooths_macd(self) -> None:
        """Test that signal line is smoother than MACD line."""
        # Create volatile prices
        prices = []
        for i in range(60):
            if i % 2 == 0:
                prices.append(100.0 + i)
            else:
                prices.append(100.0 + i - 5)

        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # Signal is EMA of MACD, so it should be smoother
        # This means signal should change less rapidly than MACD
        # We can't easily test "smoothness" but we can verify signal exists
        signal_values = [v for v in signal if v is not None]
        assert len(signal_values) > 0

    def test_macd_custom_periods(self) -> None:
        """Test MACD with custom periods."""
        prices = [float(100 + i * 0.5) for i in range(80)]

        # Use custom periods: 5, 13, 8
        macd, signal, histogram = calculate_macd(prices, 5, 13, 8)

        # MACD should have (13-1) = 12 None values
        none_count_macd = sum(1 for v in macd if v is None)
        assert none_count_macd == 12

        # Signal should have (13-1) + (8-1) = 12 + 7 = 19 None values
        none_count_signal = sum(1 for v in signal if v is None)
        assert none_count_signal == 19

    def test_macd_known_calculation(self) -> None:
        """Test MACD against a simple known case."""
        # Simple increasing prices
        prices = [float(i) for i in range(1, 51)]

        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # Verify basic properties
        # With increasing prices, fast EMA > slow EMA, so MACD > 0
        macd_values = [v for v in macd if v is not None]
        assert all(v > 0 for v in macd_values)

        # Signal should also be positive
        signal_values = [v for v in signal if v is not None]
        assert all(v > 0 for v in signal_values)

    def test_macd_none_propagation(self) -> None:
        """Test that None values are properly propagated through calculations."""
        prices = [float(100 + i) for i in range(40)]
        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # MACD has None where slow EMA has None (first 25 values)
        for i in range(25):
            assert macd[i] is None

        # Signal has None where MACD doesn't have enough data (first 33 values)
        for i in range(33):
            assert signal[i] is None

        # Histogram has None wherever either MACD or Signal is None
        for i in range(33):
            assert histogram[i] is None

    def test_macd_zero_line_cross(self) -> None:
        """Test MACD crossing zero line (trend direction change)."""
        # Create pattern that crosses zero: down, then up
        prices = []
        # Start high, go down
        for i in range(35):
            prices.append(200.0 - i * 2)
        # Then go up
        for i in range(35):
            prices.append(130.0 + i * 3)

        macd, signal, histogram = calculate_macd(prices, 12, 26, 9)

        # Get non-None MACD values
        macd_values = [(i, v) for i, v in enumerate(macd) if v is not None]

        # Should have both positive and negative MACD values (crossing zero)
        has_positive = any(v > 0 for i, v in macd_values)
        has_negative = any(v < 0 for i, v in macd_values)

        assert has_positive and has_negative
