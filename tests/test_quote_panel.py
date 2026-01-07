"""Tests for the QuotePanel widget."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label, LoadingIndicator

from viper.services.crypto import CryptoError, CryptoQuote
from viper.services.stock import IntradayData, IntradayError, StockError, StockQuote
from viper.widgets import QuotePanel
from viper.widgets.sparkline import SparklineWidget


class QuotePanelTestApp(App[None]):
    """Test app for QuotePanel widget."""

    def compose(self) -> ComposeResult:
        """Compose test app."""
        yield QuotePanel()


@pytest.mark.asyncio
async def test_quote_panel_empty_state() -> None:
    """Test that the quote panel displays empty state by default."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Should start in empty state
        assert panel._state == "empty"

        # Should display empty message
        labels = panel.query(Label)
        assert len(labels) > 0
        assert any("No ticker selected" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_quote_panel_loading_state() -> None:
    """Test that the quote panel displays loading state correctly."""
    app = QuotePanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(QuotePanel)

        # Show loading state
        panel.show_loading()

        # Wait for UI to update
        await pilot.pause()

        # Should update state
        assert panel._state == "loading"

        # Should display loading indicator and message
        loading_indicators = panel.query(LoadingIndicator)
        assert len(loading_indicators) == 1

        labels = panel.query(Label)
        assert any("Loading..." in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_quote_panel_success_state_positive_change() -> None:
    """Test displaying a successful quote with positive change."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create a mock quote with positive change
        quote = StockQuote(
            ticker="AAPL",
            price=150.50,
            change=5.25,
            change_percent=3.61,
            volume=50000000,
            market_cap=2500000000000,
            high_52w=180.00,
            low_52w=120.00,
            name="Apple Inc.",
        )

        # Show the quote
        panel.show_quote(quote)

        # Should update state
        assert panel._state == "success"
        assert panel._quote == quote

        # Check that ticker and name are displayed
        labels = panel.query(Label)
        ticker_labels = [
            label for label in labels if "AAPL" in str(label.render())
        ]
        assert len(ticker_labels) > 0
        assert any("Apple Inc." in str(label.render()) for label in ticker_labels)

        # Check that price is displayed with positive styling
        price_labels = [
            label for label in labels if "150.50" in str(label.render())
        ]
        assert len(price_labels) > 0
        price_label = price_labels[0]
        assert "positive" in price_label.classes

        # Check that change is displayed with + sign
        assert any("+$5.25" in str(label.render()) for label in labels)
        assert any("(+3.61%)" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_quote_panel_success_state_negative_change() -> None:
    """Test displaying a successful quote with negative change."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create a mock quote with negative change
        quote = StockQuote(
            ticker="TSLA",
            price=200.75,
            change=-10.50,
            change_percent=-4.97,
            volume=30000000,
            market_cap=700000000000,
            high_52w=250.00,
            low_52w=180.00,
        )

        # Show the quote
        panel.show_quote(quote)

        # Should update state
        assert panel._state == "success"

        # Check that price is displayed with negative styling
        labels = panel.query(Label)
        price_labels = [
            label for label in labels if "200.75" in str(label.render())
        ]
        assert len(price_labels) > 0
        price_label = price_labels[0]
        assert "negative" in price_label.classes

        # Check that change is displayed (negative sign from number itself)
        assert any("$10.50" in str(label.render()) for label in labels)
        assert any("4.97%" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_quote_panel_success_state_zero_change() -> None:
    """Test displaying a successful quote with zero change."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create a mock quote with zero change
        quote = StockQuote(
            ticker="MSFT",
            price=300.00,
            change=0.0,
            change_percent=0.0,
            volume=20000000,
            market_cap=2200000000000,
            high_52w=320.00,
            low_52w=280.00,
        )

        # Show the quote
        panel.show_quote(quote)

        # Should update state
        assert panel._state == "success"

        # Check that price is displayed with neutral styling
        labels = panel.query(Label)
        price_labels = [
            label for label in labels if "300.00" in str(label.render())
        ]
        assert len(price_labels) > 0
        price_label = price_labels[0]
        assert "neutral" in price_label.classes


@pytest.mark.asyncio
async def test_quote_panel_error_state() -> None:
    """Test displaying an error state."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create an error
        error = StockError(ticker="INVALID", error_message="Invalid ticker symbol")

        # Show the error
        panel.show_error(error)

        # Should update state
        assert panel._state == "error"
        assert panel._quote == error

        # Should display error message
        labels = panel.query(Label)
        error_labels = [
            label for label in labels if "Error:" in str(label.render())
        ]
        assert len(error_labels) > 0
        assert any("Invalid ticker symbol" in str(label.render()) for label in error_labels)


@pytest.mark.asyncio
async def test_quote_panel_number_formatting_with_decimals() -> None:
    """Test that numbers are formatted correctly with decimal places."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create a quote with specific numbers to test formatting
        quote = StockQuote(
            ticker="TEST",
            price=1234.567,
            change=123.456,
            change_percent=12.345,
            volume=123456789,
            market_cap=1234567890123,
            high_52w=1500.99,
            low_52w=900.01,
        )

        # Show the quote
        panel.show_quote(quote)

        labels = panel.query(Label)

        # Price should be formatted with 2 decimals and commas
        assert any("1,234.57" in str(label.render()) for label in labels)

        # Change should be formatted with 2 decimals and commas
        assert any("123.46" in str(label.render()) for label in labels)

        # Change percent should be formatted with 2 decimals
        assert any("12.35%" in str(label.render()) for label in labels)

        # Volume should be formatted with commas and no decimals
        assert any("123,456,789" in str(label.render()) for label in labels)

        # Market cap should be formatted with commas and no decimals
        assert any("1,234,567,890,123" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_quote_panel_without_company_name() -> None:
    """Test displaying a quote without a company name."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create a quote without a name
        quote = StockQuote(
            ticker="BTC",
            price=45000.00,
            change=1000.00,
            change_percent=2.27,
            volume=10000,
            market_cap=900000000000,
            high_52w=69000.00,
            low_52w=15000.00,
            name=None,
        )

        # Show the quote
        panel.show_quote(quote)

        # Should display just the ticker
        labels = panel.query(Label)
        ticker_labels = [
            label for label in labels if "BTC" in str(label.render())
        ]
        assert len(ticker_labels) > 0
        # Should not have " - " separator since there's no name
        assert not any(" - " in str(label.render()) for label in ticker_labels)


@pytest.mark.asyncio
async def test_quote_panel_state_transitions() -> None:
    """Test transitioning between different states."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Start with empty
        assert panel._state == "empty"

        # Transition to loading
        panel.show_loading()
        assert panel._state == "loading"

        # Transition to success
        quote = StockQuote(
            ticker="AAPL",
            price=150.00,
            change=5.00,
            change_percent=3.45,
            volume=50000000,
            market_cap=2500000000000,
            high_52w=180.00,
            low_52w=120.00,
        )
        panel.show_quote(quote)
        assert panel._state == "success"

        # Transition to error
        error = StockError(ticker="INVALID", error_message="Test error")
        panel.show_error(error)
        assert panel._state == "error"

        # Back to empty
        panel.show_empty()
        assert panel._state == "empty"


@pytest.mark.asyncio
async def test_quote_panel_displays_all_data_fields() -> None:
    """Test that all data fields from acceptance criteria are displayed."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        quote = StockQuote(
            ticker="AAPL",
            price=150.50,
            change=5.25,
            change_percent=3.61,
            volume=50000000,
            market_cap=2500000000000,
            high_52w=180.00,
            low_52w=120.00,
            name="Apple Inc.",
        )

        panel.show_quote(quote)

        labels = panel.query(Label)
        label_texts = [str(label.render()) for label in labels]

        # Check all required fields are present
        # Ticker
        assert any("AAPL" in text for text in label_texts)

        # Price
        assert any("150.50" in text for text in label_texts)

        # Change and change%
        assert any("5.25" in text for text in label_texts)
        assert any("3.61%" in text for text in label_texts)

        # Volume
        assert any("Volume" in text and "50,000,000" in text for text in label_texts)

        # Market cap
        assert any("Market Cap" in text and "2,500,000,000,000" in text for text in label_texts)

        # 52-week high/low
        assert any("52W Range" in text for text in label_texts)
        assert any("180.00" in text for text in label_texts)
        assert any("120.00" in text for text in label_texts)


# Crypto quote tests
@pytest.mark.asyncio
async def test_quote_panel_crypto_quote_positive_change() -> None:
    """Test displaying a crypto quote with positive 24h change."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create a crypto quote with positive change
        quote = CryptoQuote(
            symbol="BTC",
            price_usd=50000.00,
            change_24h_percent=5.25,
            market_cap_usd=1000000000000,
            volume_24h_usd=50000000000,
            name="Bitcoin",
        )

        # Show the quote
        panel.show_quote(quote)

        # Should update state
        assert panel._state == "success"
        assert panel._quote == quote

        # Check that symbol and name are displayed
        labels = panel.query(Label)
        symbol_labels = [label for label in labels if "BTC" in str(label.render())]
        assert len(symbol_labels) > 0
        assert any("Bitcoin" in str(label.render()) for label in symbol_labels)

        # Check that price is displayed with positive styling
        price_labels = [label for label in labels if "50,000.00" in str(label.render())]
        assert len(price_labels) > 0
        price_label = price_labels[0]
        assert "positive" in price_label.classes

        # Check that 24h change is displayed with + sign
        assert any("24h" in str(label.render()) for label in labels)
        assert any("(+5.25%)" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_quote_panel_crypto_quote_negative_change() -> None:
    """Test displaying a crypto quote with negative 24h change."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create a crypto quote with negative change
        quote = CryptoQuote(
            symbol="ETH",
            price_usd=3000.00,
            change_24h_percent=-3.75,
            market_cap_usd=400000000000,
            volume_24h_usd=20000000000,
            name="Ethereum",
        )

        # Show the quote
        panel.show_quote(quote)

        # Should update state
        assert panel._state == "success"

        # Check that price is displayed with negative styling
        labels = panel.query(Label)
        price_labels = [label for label in labels if "3,000.00" in str(label.render())]
        assert len(price_labels) > 0
        price_label = price_labels[0]
        assert "negative" in price_label.classes

        # Check that 24h change percentage is displayed
        assert any("3.75%" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_quote_panel_crypto_quote_all_fields() -> None:
    """Test that all crypto data fields are displayed."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        quote = CryptoQuote(
            symbol="BTC",
            price_usd=50000.00,
            change_24h_percent=2.5,
            market_cap_usd=1000000000000,
            volume_24h_usd=50000000000,
            name="Bitcoin",
        )

        panel.show_quote(quote)

        labels = panel.query(Label)
        label_texts = [str(label.render()) for label in labels]

        # Check all required fields are present
        # Symbol
        assert any("BTC" in text for text in label_texts)

        # Name
        assert any("Bitcoin" in text for text in label_texts)

        # Price
        assert any("50,000.00" in text for text in label_texts)

        # 24h change%
        assert any("2.5%" in text or "2.50%" in text for text in label_texts)

        # 24h Volume
        assert any("24h Volume" in text and "50,000,000,000" in text for text in label_texts)

        # Market cap
        assert any("Market Cap" in text and "1,000,000,000,000" in text for text in label_texts)


@pytest.mark.asyncio
async def test_quote_panel_crypto_error() -> None:
    """Test displaying a crypto error state."""
    app = QuotePanelTestApp()
    async with app.run_test():
        panel = app.query_one(QuotePanel)

        # Create a crypto error
        error = CryptoError(symbol="UNKNOWN", error_message="Unknown crypto symbol: UNKNOWN")

        # Show the error
        panel.show_error(error)

        # Should update state
        assert panel._state == "error"
        assert panel._quote == error

        # Should display error message
        labels = panel.query(Label)
        error_labels = [label for label in labels if "Error:" in str(label.render())]
        assert len(error_labels) > 0
        assert any("Unknown crypto symbol" in str(label.render()) for label in error_labels)


# Sparkline integration tests
@pytest.mark.asyncio
async def test_quote_panel_stock_with_sparkline_success() -> None:
    """Test that stock quote displays sparkline when intraday data is available."""
    app = QuotePanelTestApp()

    # Mock successful intraday data fetch
    # Create timestamps at 5-minute intervals
    base_time = datetime(2024, 1, 1, 9, 30)
    from datetime import timedelta

    timestamps = [base_time + timedelta(minutes=i * 5) for i in range(10)]
    mock_intraday_data = IntradayData(
        ticker="AAPL",
        prices=[150.0 + i for i in range(10)],
        timestamps=timestamps,
        interval="5m",
        period="1d",
    )

    with patch(
        "viper.widgets.quote_panel.fetch_intraday_data",
        new=AsyncMock(return_value=mock_intraday_data),
    ):
        async with app.run_test() as pilot:
            panel = app.query_one(QuotePanel)

            quote = StockQuote(
                ticker="AAPL",
                price=150.50,
                change=5.25,
                change_percent=3.61,
                volume=50000000,
                market_cap=2500000000000,
                high_52w=180.00,
                low_52w=120.00,
                name="Apple Inc.",
            )

            panel.show_quote(quote)

            # Wait for async sparkline fetch and render
            await pilot.pause(0.2)

            # Should have a sparkline widget
            sparklines = panel.query(SparklineWidget)
            assert len(sparklines) == 1

            # Sparkline should have data
            sparkline = sparklines[0]
            assert sparkline._prices == mock_intraday_data.prices
            assert sparkline._label == "Intraday (1d, 5m)"


@pytest.mark.asyncio
async def test_quote_panel_stock_with_sparkline_error() -> None:
    """Test that stock quote shows 'No data' sparkline when intraday fetch fails."""
    app = QuotePanelTestApp()

    # Mock failed intraday data fetch
    mock_error = IntradayError(
        ticker="AAPL", error_message="No intraday data available"
    )

    with patch(
        "viper.widgets.quote_panel.fetch_intraday_data",
        new=AsyncMock(return_value=mock_error),
    ):
        async with app.run_test() as pilot:
            panel = app.query_one(QuotePanel)

            quote = StockQuote(
                ticker="AAPL",
                price=150.50,
                change=5.25,
                change_percent=3.61,
                volume=50000000,
                market_cap=2500000000000,
                high_52w=180.00,
                low_52w=120.00,
            )

            panel.show_quote(quote)

            # Wait for async sparkline fetch and render
            await pilot.pause(0.2)

            # Should have a sparkline widget
            sparklines = panel.query(SparklineWidget)
            assert len(sparklines) == 1

            # Sparkline should show no data
            sparkline = sparklines[0]
            assert sparkline._prices is None
            assert sparkline._label == "Intraday (1d, 5m)"


@pytest.mark.asyncio
async def test_quote_panel_crypto_no_sparkline() -> None:
    """Test that crypto quotes do NOT display sparkline (stocks only)."""
    app = QuotePanelTestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(QuotePanel)

        quote = CryptoQuote(
            symbol="BTC",
            price_usd=50000.00,
            change_24h_percent=5.25,
            market_cap_usd=1000000000000,
            volume_24h_usd=50000000000,
            name="Bitcoin",
        )

        panel.show_quote(quote)

        # Wait a bit to ensure no async sparkline fetch happens
        await pilot.pause(0.2)

        # Should NOT have a sparkline widget (crypto doesn't support sparkline)
        sparklines = panel.query(SparklineWidget)
        assert len(sparklines) == 0
