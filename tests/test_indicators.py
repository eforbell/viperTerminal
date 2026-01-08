"""Tests for technical indicator calculations."""

import pytest

from viper.services.indicators import calculate_sma


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
