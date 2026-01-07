"""Tests for the main Viper Terminal application."""

from unittest.mock import AsyncMock, patch

import pytest
from textual.widgets import Footer, Header

from viper.app import ViperApp
from viper.services.stock import StockError, StockQuote
from viper.widgets import QuotePanel, TickerInput


@pytest.mark.asyncio
async def test_app_launches_without_error() -> None:
    """Test that the app can be instantiated and launched."""
    app = ViperApp()
    async with app.run_test() as pilot:
        # App should be running
        assert pilot.app is app
        assert app.title == "VIPER TERMINAL"


@pytest.mark.asyncio
async def test_header_renders_correctly() -> None:
    """Test that the header is present and displays the app title."""
    app = ViperApp()
    async with app.run_test():
        # Should have a Header widget
        header = app.query_one(Header)
        assert header is not None
        # Title should be visible in the header
        assert app.title == "VIPER TERMINAL"


@pytest.mark.asyncio
async def test_footer_renders_correctly() -> None:
    """Test that the footer is present and shows keybindings."""
    app = ViperApp()
    async with app.run_test():
        # Should have a Footer widget
        footer = app.query_one(Footer)
        assert footer is not None


@pytest.mark.asyncio
async def test_quit_keybinding_works() -> None:
    """Test that pressing 'q' quits the application."""
    app = ViperApp()
    async with app.run_test() as pilot:
        # Press 'q' to quit
        await pilot.press("q")
        # App should exit cleanly (the context manager handles this)


@pytest.mark.asyncio
async def test_color_theme() -> None:
    """Test that the app uses the correct color theme."""
    app = ViperApp()
    assert app.THEME["background"] == "#000000"
    assert app.THEME["accent"] == "#00ff00"
    assert app.THEME["surface"] == "#111111"


@pytest.mark.asyncio
async def test_ticker_input_widget_present() -> None:
    """Test that the TickerInput widget is present in the app."""
    app = ViperApp()
    async with app.run_test():
        # Should have a TickerInput widget
        ticker_input = app.query_one(TickerInput)
        assert ticker_input is not None


@pytest.mark.asyncio
async def test_quote_panel_widget_present() -> None:
    """Test that the QuotePanel widget is present in the app."""
    app = ViperApp()
    async with app.run_test():
        # Should have a QuotePanel widget
        quote_panel = app.query_one(QuotePanel)
        assert quote_panel is not None


@pytest.mark.asyncio
async def test_ticker_lookup_triggers_quote_fetch() -> None:
    """Test that submitting a ticker triggers quote fetching and display."""
    app = ViperApp()

    # Mock the fetch_stock_quote function
    mock_quote = StockQuote(
        ticker="AAPL",
        price=150.00,
        change=5.00,
        change_percent=3.45,
        volume=50000000,
        market_cap=2500000000000,
        high_52w=180.00,
        low_52w=120.00,
        name="Apple Inc.",
    )

    with patch("viper.app.fetch_stock_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        async with app.run_test() as pilot:
            ticker_input = app.query_one(TickerInput)
            quote_panel = app.query_one(QuotePanel)

            # Initially should be in empty state
            assert quote_panel._state == "empty"

            # Submit a ticker
            ticker_input.focus()
            ticker_input.value = "AAPL"
            await pilot.press("enter")

            # Wait for async event handling
            await pilot.pause()

            # The fetch should have been called
            mock_fetch.assert_called_once_with("AAPL")

            # Quote panel should now be in success state
            assert quote_panel._state == "success"
            assert isinstance(quote_panel._quote, StockQuote)
            assert quote_panel._quote.ticker == "AAPL"


@pytest.mark.asyncio
async def test_ticker_lookup_handles_error() -> None:
    """Test that errors from quote fetching are displayed correctly."""
    app = ViperApp()

    # Mock the fetch_stock_quote function to return an error
    mock_error = StockError(ticker="INVALID", error_message="Invalid ticker symbol")

    with patch("viper.app.fetch_stock_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_error

        async with app.run_test() as pilot:
            ticker_input = app.query_one(TickerInput)
            quote_panel = app.query_one(QuotePanel)

            # Submit an invalid ticker
            ticker_input.focus()
            ticker_input.value = "INVALID"
            await pilot.press("enter")

            # Wait for async event handling
            await pilot.pause()

            # The fetch should have been called
            mock_fetch.assert_called_once_with("INVALID")

            # Quote panel should now be in error state
            assert quote_panel._state == "error"
            assert isinstance(quote_panel._quote, StockError)
            assert quote_panel._quote.error_message == "Invalid ticker symbol"
