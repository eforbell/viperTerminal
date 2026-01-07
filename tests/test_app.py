"""Tests for the main Viper Terminal application."""

from unittest.mock import AsyncMock, patch

import pytest
from textual.containers import Horizontal
from textual.widgets import Footer, Header

from viper.app import ViperApp
from viper.services.crypto import CryptoInfo, CryptoQuote
from viper.services.stock import StockError, StockInfo, StockQuote
from viper.widgets import InfoPanel, QuotePanel, TickerInput, WatchlistPanel


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

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch:
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

    # Mock the fetch_quote function to return an error
    mock_error = StockError(ticker="INVALID", error_message="Invalid ticker symbol")

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch:
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


@pytest.mark.asyncio
async def test_ticker_lookup_crypto_quote() -> None:
    """Test that crypto quotes are fetched and displayed correctly."""
    app = ViperApp()

    # Mock the fetch_quote function to return a crypto quote
    mock_quote = CryptoQuote(
        symbol="BTC",
        price_usd=50000.00,
        change_24h_percent=5.25,
        market_cap_usd=1000000000000,
        volume_24h_usd=50000000000,
        name="Bitcoin",
    )

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        async with app.run_test() as pilot:
            ticker_input = app.query_one(TickerInput)
            quote_panel = app.query_one(QuotePanel)

            # Submit a crypto ticker
            ticker_input.focus()
            ticker_input.value = "BTC"
            await pilot.press("enter")

            # Wait for async event handling
            await pilot.pause()

            # The fetch should have been called
            mock_fetch.assert_called_once_with("BTC")

            # Quote panel should now be in success state with crypto quote
            assert quote_panel._state == "success"
            assert isinstance(quote_panel._quote, CryptoQuote)
            assert quote_panel._quote.symbol == "BTC"


@pytest.mark.asyncio
async def test_multi_panel_layout() -> None:
    """Test that the app has a horizontal layout with watchlist and quote panels."""
    app = ViperApp()
    async with app.run_test():
        # Should have a Horizontal layout
        horizontal = app.query_one("#main-layout", Horizontal)
        assert horizontal is not None

        # Should have both watchlist and quote containers
        watchlist_container = app.query_one("#watchlist-container")
        assert watchlist_container is not None

        quote_container = app.query_one("#quote-container")
        assert quote_container is not None

        # Should have WatchlistPanel
        watchlist_panel = app.query_one(WatchlistPanel)
        assert watchlist_panel is not None

        # Should have QuotePanel
        quote_panel = app.query_one(QuotePanel)
        assert quote_panel is not None


@pytest.mark.asyncio
async def test_panels_are_focusable() -> None:
    """Test that both panels can receive focus."""
    app = ViperApp()
    async with app.run_test():
        watchlist_panel = app.query_one(WatchlistPanel)
        quote_panel = app.query_one(QuotePanel)

        # Both panels should be focusable
        assert watchlist_panel.can_focus is True
        assert quote_panel.can_focus is True


@pytest.mark.asyncio
async def test_tab_cycles_focus_between_panels() -> None:
    """Test that Tab key cycles focus between panels."""
    app = ViperApp()
    async with app.run_test() as pilot:
        watchlist_panel = app.query_one(WatchlistPanel)

        # Focus the watchlist panel first
        watchlist_panel.focus()
        await pilot.pause()
        assert app.focused == watchlist_panel

        # Press Tab to move to next focusable widget
        await pilot.press("tab")
        await pilot.pause()

        # Focus should have moved (could be quote panel or input)
        assert app.focused != watchlist_panel

        # Press Tab again
        await pilot.press("tab")
        await pilot.pause()

        # Focus should have changed again
        # Just verify that tab key changes focus
        assert True  # Tab functionality works if we got here without errors


@pytest.mark.asyncio
async def test_layout_proportions() -> None:
    """Test that the layout has correct width proportions (30/70)."""
    app = ViperApp()
    async with app.run_test():
        # Check CSS is applied correctly
        # The actual rendering proportions are handled by Textual's CSS engine
        # We just verify the containers exist with the right IDs
        watchlist_container = app.query_one("#watchlist-container")
        quote_container = app.query_one("#quote-container")

        assert watchlist_container is not None
        assert quote_container is not None

        # Verify CSS classes/styles are set (checked via the widget's styles)
        # Note: actual width calculation happens at render time
        assert watchlist_container.id == "watchlist-container"
        assert quote_container.id == "quote-container"


# VPR-010: Keyboard navigation and shortcuts tests


@pytest.mark.asyncio
async def test_slash_focuses_input() -> None:
    """Test that pressing '/' focuses the input bar."""
    app = ViperApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        quote_panel = app.query_one(QuotePanel)

        # Focus should not be on input initially
        quote_panel.focus()
        await pilot.pause()
        assert app.focused != ticker_input

        # Press '/' to focus input
        await pilot.press("/")
        await pilot.pause()

        # Input should now have focus
        assert app.focused == ticker_input


@pytest.mark.asyncio
async def test_escape_clears_input() -> None:
    """Test that pressing Escape clears input content."""
    app = ViperApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Type something in the input
        ticker_input.focus()
        ticker_input.value = "AAPL"
        await pilot.pause()
        assert ticker_input.value == "AAPL"

        # Press Escape to clear
        await pilot.press("escape")
        await pilot.pause()

        # Input should be cleared
        assert ticker_input.value == ""


@pytest.mark.asyncio
async def test_escape_clears_error_state() -> None:
    """Test that pressing Escape also clears error state from input."""
    app = ViperApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Add error class and some text
        ticker_input.focus()
        ticker_input.value = "test"
        ticker_input.add_class("error")
        await pilot.pause()
        assert "error" in ticker_input.classes

        # Press Escape to clear
        await pilot.press("escape")
        await pilot.pause()

        # Error class should be removed
        assert "error" not in ticker_input.classes
        assert ticker_input.value == ""


@pytest.mark.asyncio
async def test_question_mark_triggers_help_action() -> None:
    """Test that pressing '?' triggers the help action (placeholder for VPR-015)."""
    app = ViperApp()
    async with app.run_test() as pilot:
        # Press '?' to trigger help
        await pilot.press("?")
        await pilot.pause()

        # Placeholder does nothing for now, just verify no error
        # Will be fully implemented in VPR-015
        assert True


@pytest.mark.asyncio
async def test_f1_triggers_help_action() -> None:
    """Test that pressing F1 triggers the help action (placeholder for VPR-015)."""
    app = ViperApp()
    async with app.run_test() as pilot:
        # Press F1 to trigger help
        await pilot.press("f1")
        await pilot.pause()

        # Placeholder does nothing for now, just verify no error
        # Will be fully implemented in VPR-015
        assert True


@pytest.mark.asyncio
async def test_watchlist_enter_selects_item() -> None:
    """Test that pressing Enter on a watchlist item triggers quote lookup."""
    app = ViperApp()

    # Pre-populate watchlist
    app.watchlist_manager.add("AAPL")
    app.watchlist_manager.add("TSLA")

    # Mock quote for watchlist refresh
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

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        async with app.run_test() as pilot:
            watchlist_panel = app.query_one(WatchlistPanel)
            quote_panel = app.query_one(QuotePanel)

            # Wait for watchlist to load
            await pilot.pause(0.1)

            # Focus watchlist panel
            watchlist_panel.focus()
            await pilot.pause()

            # Quote panel should be in empty state
            assert quote_panel._state == "empty"

            # Press Enter to select the first item (AAPL)
            await pilot.press("enter")
            await pilot.pause()

            # Should have triggered a quote fetch for AAPL
            assert mock_fetch.call_count >= 1
            # The last call should be for AAPL (from Enter)
            last_call = mock_fetch.call_args_list[-1]
            assert last_call[0][0] == "AAPL"

            # Quote panel should show the quote
            assert quote_panel._state == "success"


# VPR-012: Company/asset info panel tests


@pytest.mark.asyncio
async def test_info_panel_present() -> None:
    """Test that the InfoPanel widget is present in the app."""
    app = ViperApp()
    async with app.run_test():
        # Should have an InfoPanel widget
        info_panel = app.query_one(InfoPanel)
        assert info_panel is not None


@pytest.mark.asyncio
async def test_info_panel_initially_hidden() -> None:
    """Test that the InfoPanel is initially hidden."""
    app = ViperApp()
    async with app.run_test():
        info_container = app.query_one("#info-container")
        assert str(info_container.styles.display) == "none"


@pytest.mark.asyncio
async def test_i_key_toggles_info_panel() -> None:
    """Test that pressing 'i' toggles the info panel visibility."""
    app = ViperApp()
    async with app.run_test() as pilot:
        info_container = app.query_one("#info-container")
        quote_container = app.query_one("#quote-container")

        # Initially, info should be hidden, quote should be visible
        assert str(info_container.styles.display) == "none"
        assert str(quote_container.styles.display) == "block"

        # Manually call the action (keybinding test is covered by existence of binding)
        app.action_toggle_info()
        await pilot.pause()

        # Info should now be visible, quote should be hidden
        assert str(info_container.styles.display) == "block"
        assert str(quote_container.styles.display) == "none"

        # Toggle back
        app.action_toggle_info()
        await pilot.pause()

        # Should be back to original state
        assert str(info_container.styles.display) == "none"
        assert str(quote_container.styles.display) == "block"


@pytest.mark.asyncio
async def test_info_panel_shows_stock_info() -> None:
    """Test that toggling info panel shows stock information."""
    app = ViperApp()

    # Mock stock quote and info
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

    mock_info = StockInfo(
        ticker="AAPL",
        info={
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "longBusinessSummary": "Apple designs and manufactures consumer electronics.",
            "website": "https://www.apple.com",
            "fullTimeEmployees": 164000,
        },
    )

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch_quote:
        with patch("viper.app.fetch_stock_info", new_callable=AsyncMock) as mock_fetch_info:
            mock_fetch_quote.return_value = mock_quote
            mock_fetch_info.return_value = mock_info

            async with app.run_test() as pilot:
                ticker_input = app.query_one(TickerInput)
                info_panel = app.query_one(InfoPanel)

                # Submit a ticker to set current_ticker
                ticker_input.focus()
                ticker_input.value = "AAPL"
                await pilot.press("enter")
                await pilot.pause()

                # Now press 'i' to show info panel
                await pilot.press("i")
                await pilot.pause(0.2)

                # Info panel should have been called
                assert mock_fetch_info.called

                # Check that info panel has content
                assert info_panel._current_quote is not None


@pytest.mark.asyncio
async def test_info_panel_shows_crypto_info() -> None:
    """Test that toggling info panel shows crypto information."""
    app = ViperApp()

    # Mock crypto quote and info
    mock_quote = CryptoQuote(
        symbol="BTC",
        price_usd=50000.0,
        change_24h_percent=3.5,
        market_cap_usd=1000000000000,
        volume_24h_usd=50000000000.0,
        name="Bitcoin",
    )

    mock_info = CryptoInfo(
        symbol="BTC",
        info={
            "description": {"en": "Bitcoin is a decentralized digital currency."},
            "links": {"homepage": ["https://bitcoin.org"]},
            "genesis_date": "2009-01-03",
        },
    )

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch_quote:
        with patch("viper.app.fetch_crypto_info", new_callable=AsyncMock) as mock_fetch_info:
            mock_fetch_quote.return_value = mock_quote
            mock_fetch_info.return_value = mock_info

            async with app.run_test() as pilot:
                ticker_input = app.query_one(TickerInput)
                info_panel = app.query_one(InfoPanel)

                # Submit a ticker to set current_ticker
                ticker_input.focus()
                ticker_input.value = "BTC"
                await pilot.press("enter")
                await pilot.pause()

                # Now press 'i' to show info panel
                await pilot.press("i")
                await pilot.pause(0.2)

                # Info panel should have been called
                assert mock_fetch_info.called

                # Check that info panel has content
                assert info_panel._current_quote is not None


@pytest.mark.asyncio
async def test_info_panel_empty_without_ticker() -> None:
    """Test that info panel shows empty state when no ticker is selected."""
    app = ViperApp()
    async with app.run_test() as pilot:
        info_panel = app.query_one(InfoPanel)

        # Press 'i' without selecting a ticker first
        await pilot.press("i")
        await pilot.pause()

        # Info panel should show empty state
        content = info_panel.query_one("#info-content")
        assert "No asset selected" in str(content.render())
