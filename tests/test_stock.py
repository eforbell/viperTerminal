"""Tests for stock quote fetching service."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from viper.services.stock import StockError, StockQuote, fetch_stock_quote


def create_mock_fast_info(
    last_price: float | None = None,
    previous_close: float | None = None,
    last_volume: int | None = None,
    market_cap: int | None = None,
) -> MagicMock:
    """Create a mock FastInfo object with attribute access."""
    mock = MagicMock()
    mock.last_price = last_price
    mock.previous_close = previous_close
    mock.last_volume = last_volume
    mock.market_cap = market_cap
    return mock


class TestStockQuote:
    """Tests for StockQuote dataclass."""

    def test_stock_quote_creation(self) -> None:
        """Test StockQuote dataclass instantiation."""
        quote = StockQuote(
            ticker="AAPL",
            price=150.0,
            change=2.5,
            change_percent=1.69,
            volume=50000000,
            market_cap=2500000000000,
            high_52w=180.0,
            low_52w=120.0,
            name="Apple Inc.",
        )
        assert quote.ticker == "AAPL"
        assert quote.price == 150.0
        assert quote.change == 2.5
        assert quote.change_percent == 1.69
        assert quote.volume == 50000000
        assert quote.market_cap == 2500000000000
        assert quote.high_52w == 180.0
        assert quote.low_52w == 120.0
        assert quote.name == "Apple Inc."

    def test_stock_quote_optional_name(self) -> None:
        """Test StockQuote with optional name field."""
        quote = StockQuote(
            ticker="TEST",
            price=100.0,
            change=0.0,
            change_percent=0.0,
            volume=1000,
            market_cap=1000000,
            high_52w=110.0,
            low_52w=90.0,
        )
        assert quote.name is None


class TestStockError:
    """Tests for StockError dataclass."""

    def test_stock_error_creation(self) -> None:
        """Test StockError dataclass instantiation."""
        error = StockError(ticker="INVALID", error_message="Invalid ticker symbol")
        assert error.ticker == "INVALID"
        assert error.error_message == "Invalid ticker symbol"


class TestFetchStockQuote:
    """Tests for fetch_stock_quote async function."""

    @pytest.mark.asyncio
    async def test_fetch_valid_ticker(self) -> None:
        """Test fetching a valid ticker returns StockQuote."""
        # Mock yfinance Ticker and fast_info as object with attributes
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=150.0,
            previous_close=147.5,
            last_volume=50000000,
            market_cap=2500000000000,
        )
        mock_ticker.info = {
            "fiftyTwoWeekHigh": 180.0,
            "fiftyTwoWeekLow": 120.0,
            "longName": "Apple Inc.",
        }

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("AAPL")

        assert isinstance(result, StockQuote)
        assert result.ticker == "AAPL"
        assert result.price == 150.0
        assert result.change == 2.5
        assert result.change_percent == pytest.approx(1.6949, rel=1e-3)
        assert result.volume == 50000000
        assert result.market_cap == 2500000000000
        assert result.high_52w == 180.0
        assert result.low_52w == 120.0
        assert result.name == "Apple Inc."

    @pytest.mark.asyncio
    async def test_fetch_ticker_uppercase_normalization(self) -> None:
        """Test ticker is normalized to uppercase."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=100.0,
            previous_close=100.0,
            last_volume=1000,
            market_cap=1000000,
        )
        mock_ticker.info = {
            "fiftyTwoWeekHigh": 110.0,
            "fiftyTwoWeekLow": 90.0,
        }

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_stock_quote("aapl")

        assert isinstance(result, StockQuote)
        assert result.ticker == "AAPL"
        # Verify yfinance was called with uppercase ticker
        mock_yf.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_fetch_ticker_with_whitespace(self) -> None:
        """Test ticker whitespace is stripped."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=100.0,
            previous_close=100.0,
            last_volume=1000,
            market_cap=1000000,
        )
        mock_ticker.info = {}

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker) as mock_yf:
            result = await fetch_stock_quote("  tsla  ")

        assert isinstance(result, StockQuote)
        assert result.ticker == "TSLA"
        mock_yf.assert_called_once_with("TSLA")

    @pytest.mark.asyncio
    async def test_fetch_invalid_ticker(self) -> None:
        """Test fetching an invalid ticker returns StockError."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info()  # No data available

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("INVALID")

        assert isinstance(result, StockError)
        assert result.ticker == "INVALID"
        assert "Invalid ticker or no data available" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_missing_price_data(self) -> None:
        """Test handling when price data is missing."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(previous_close=100.0)  # Missing last_price

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("TEST")

        assert isinstance(result, StockError)
        assert "Invalid ticker or no data available" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_network_error(self) -> None:
        """Test handling network errors."""
        with patch(
            "viper.services.stock.yf.Ticker",
            side_effect=Exception("Connection error: Failed to connect"),
        ):
            result = await fetch_stock_quote("AAPL")

        assert isinstance(result, StockError)
        assert result.ticker == "AAPL"
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_404_error(self) -> None:
        """Test handling 404 errors (invalid ticker from API)."""
        with patch(
            "viper.services.stock.yf.Ticker",
            side_effect=Exception("404 Client Error: Not Found"),
        ):
            result = await fetch_stock_quote("NOTREAL")

        assert isinstance(result, StockError)
        assert result.ticker == "NOTREAL"
        assert "Invalid ticker symbol" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_timeout(self) -> None:
        """Test handling request timeout."""
        # Mock a slow response that exceeds timeout
        def slow_ticker(*args: object, **kwargs: object) -> Mock:
            import time

            time.sleep(2)
            return Mock()

        with patch("viper.services.stock.yf.Ticker", side_effect=slow_ticker):
            result = await fetch_stock_quote("AAPL", timeout=0.1)

        assert isinstance(result, StockError)
        assert result.ticker == "AAPL"
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_with_custom_timeout(self) -> None:
        """Test fetch with custom timeout value."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=100.0,
            previous_close=100.0,
            last_volume=1000,
            market_cap=1000000,
        )
        mock_ticker.info = {}

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("AAPL", timeout=5.0)

        assert isinstance(result, StockQuote)

    @pytest.mark.asyncio
    async def test_fetch_with_missing_volume(self) -> None:
        """Test handling when optional fields are missing."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=100.0,
            previous_close=95.0,
            # Missing: last_volume, market_cap (will be None)
        )
        mock_ticker.info = {}

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("TEST")

        assert isinstance(result, StockQuote)
        assert result.volume == 0  # Default value
        assert result.market_cap == 0  # Default value

    @pytest.mark.asyncio
    async def test_fetch_with_info_exception(self) -> None:
        """Test handling when regular info fetch fails but fast_info succeeds."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=150.0,
            previous_close=147.5,
            last_volume=1000000,
            market_cap=500000000,
        )
        # Make info property raise exception
        type(mock_ticker).info = property(lambda self: (_ for _ in ()).throw(Exception("Error")))

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("AAPL")

        assert isinstance(result, StockQuote)
        # Should fall back to price for 52w range
        assert result.high_52w == 150.0
        assert result.low_52w == 150.0
        assert result.name is None

    @pytest.mark.asyncio
    async def test_fetch_zero_division_protection(self) -> None:
        """Test change percent calculation with zero previous close."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=100.0,
            previous_close=0.0,  # Edge case: zero previous close
            last_volume=1000,
            market_cap=1000000,
        )
        mock_ticker.info = {}

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("TEST")

        assert isinstance(result, StockQuote)
        assert result.change_percent == 0.0  # Should not crash with division by zero

    @pytest.mark.asyncio
    async def test_fetch_malformed_response(self) -> None:
        """Test handling malformed API response."""
        mock_ticker = MagicMock()
        # fast_info raises AttributeError when accessing properties
        mock_fast_info = MagicMock()
        mock_fast_info.last_price = property(lambda self: (_ for _ in ()).throw(AttributeError()))
        type(mock_ticker).fast_info = property(lambda self: "malformed")

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("TEST")

        assert isinstance(result, StockError)

    @pytest.mark.asyncio
    async def test_fetch_positive_change(self) -> None:
        """Test calculation with positive price change."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=105.0,
            previous_close=100.0,
            last_volume=1000,
            market_cap=1000000,
        )
        mock_ticker.info = {}

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("TEST")

        assert isinstance(result, StockQuote)
        assert result.change == 5.0
        assert result.change_percent == 5.0

    @pytest.mark.asyncio
    async def test_fetch_negative_change(self) -> None:
        """Test calculation with negative price change."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = create_mock_fast_info(
            last_price=95.0,
            previous_close=100.0,
            last_volume=1000,
            market_cap=1000000,
        )
        mock_ticker.info = {}

        with patch("viper.services.stock.yf.Ticker", return_value=mock_ticker):
            result = await fetch_stock_quote("TEST")

        assert isinstance(result, StockQuote)
        assert result.change == -5.0
        assert result.change_percent == -5.0
