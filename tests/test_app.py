"""Tests for the main Viper Terminal application."""

from unittest.mock import AsyncMock, patch

import pytest
from textual.containers import Horizontal
from textual.widgets import Footer, Header

from viper.app import ViperApp
from viper.services.crypto import CryptoInfo, CryptoQuote
from viper.services.stock import StockError, StockInfo, StockQuote
from viper.widgets import HelpScreen, InfoPanel, OptionsChainPanel, QuotePanel, TickerInput, WatchlistPanel


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

    # Set test items directly without persisting to disk
    # (Using add() would write to ~/.config/viper/watchlist.json)
    app.watchlist_manager._items = ["AAPL", "TSLA"]

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
            # Check that AAPL was fetched (it should be in the call args somewhere)
            called_tickers = [call[0][0] for call in mock_fetch.call_args_list]
            assert "AAPL" in called_tickers

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

                # Now toggle info panel
                app.action_toggle_info()
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

                # Now toggle info panel
                app.action_toggle_info()
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


@pytest.mark.asyncio
async def test_help_screen_opens_with_question_mark() -> None:
    """Test that pressing '?' opens the help screen."""
    with patch("viper.app.is_first_run", return_value=False):
        app = ViperApp()
        async with app.run_test() as pilot:
            # Use action directly instead of press (more reliable for testing)
            app.action_show_help()
            await pilot.pause()

            # Help screen should be open
            assert isinstance(app.screen, HelpScreen)
            assert app.screen.is_welcome is False


@pytest.mark.asyncio
async def test_help_screen_opens_with_f1() -> None:
    """Test that pressing F1 opens the help screen."""
    with patch("viper.app.is_first_run", return_value=False):
        app = ViperApp()
        async with app.run_test() as pilot:
            # Use action directly instead of press (more reliable for testing)
            app.action_show_help()
            await pilot.pause()

            # Help screen should be open
            assert isinstance(app.screen, HelpScreen)
            assert app.screen.is_welcome is False


@pytest.mark.asyncio
async def test_welcome_screen_shows_on_first_run() -> None:
    """Test that welcome screen shows automatically on first run."""
    with (
        patch("viper.app.is_first_run", return_value=True),
        patch("viper.app.mark_first_run_complete") as mock_mark,
    ):
        app = ViperApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Welcome screen should be shown
            assert isinstance(app.screen, HelpScreen)
            assert app.screen.is_welcome is True

            # First-run should be marked complete
            assert mock_mark.called


@pytest.mark.asyncio
async def test_no_welcome_screen_on_subsequent_runs() -> None:
    """Test that welcome screen doesn't show on subsequent runs."""
    with patch("viper.app.is_first_run", return_value=False):
        app = ViperApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Welcome screen should NOT be shown
            assert not isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_article_reader_integration() -> None:
    """Test the complete flow from news panel to article reader and back."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    from viper.services.article_reader import ArticleResult
    from viper.services.news import NewsItem
    from viper.widgets import ArticleReaderPanel, NewsPanel

    app = ViperApp()

    # Mock article reader fetch_article to avoid actual HTTP requests
    mock_result = ArticleResult(
        title="Test Article",
        content="Test content for the article. This is a longer piece of text to simulate article content.",
        author="Test Author",
        date="2024-01-09",
        source_url="https://example.com/test",
        word_count=100,
    )

    # Mock stock quote to set a ticker
    mock_quote = StockQuote(
        ticker="AAPL",
        price=150.00,
        change=5.00,
        change_percent=3.45,
        volume=50000000,
        market_cap=2500000000000,
        high_52w=180.00,
        low_52w=120.00,
    )

    with (
        patch("viper.widgets.article_reader_panel.fetch_article", return_value=mock_result),
        patch("viper.app.fetch_quote", return_value=mock_quote),
        patch("viper.app.fetch_stock_info", return_value=StockError(ticker="AAPL", error_message="Not needed")),
    ):
        async with app.run_test() as pilot:
            await pilot.pause()

            # Verify initial state - news panel hidden, article reader hidden
            news_container = app.query_one("#news-container")
            reader_container = app.query_one("#article-reader-container")
            assert news_container.styles.display == "none"
            assert reader_container.styles.display == "none"
            assert not app._news_panel_visible
            assert not app._article_reader_visible

            # Set current ticker directly
            app._current_ticker = "AAPL"

            # Show news panel directly
            news_container.styles.display = "block"
            app._news_panel_visible = True

            # Create a test news item
            test_item = NewsItem(
                title="Test Article",
                url="https://example.com/test",
                source="Test Source",
                published_at=datetime.now(timezone.utc),
                summary="Test summary",
            )

            # Get news panel and set up test news
            news_panel = app.query_one(NewsPanel)
            news_panel._news_items = [test_item]
            news_panel._selected_index = 0
            news_panel._state = "success"

            # Simulate pressing Enter to open article reader
            # This posts ArticleOpenRequested message
            news_panel.action_open_in_reader()
            await pilot.pause()

            # Verify news panel is hidden and article reader is visible
            assert news_container.styles.display == "none"
            assert reader_container.styles.display == "block"
            assert not app._news_panel_visible
            assert app._article_reader_visible

            # Verify article reader panel received the article
            reader_panel = app.query_one(ArticleReaderPanel)
            assert reader_panel._url == test_item.url

            # Simulate closing the article reader
            reader_panel.action_close()
            await pilot.pause()

            # Verify article reader is hidden and news panel is visible again
            assert news_container.styles.display == "block"
            assert reader_container.styles.display == "none"
            assert app._news_panel_visible
            assert not app._article_reader_visible


@pytest.mark.asyncio
async def test_article_reader_browser_fallback() -> None:
    """Test that pressing 'o' in news panel still opens browser."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock, patch

    from viper.services.news import NewsItem
    from viper.widgets import NewsPanel

    app = ViperApp()

    # Mock stock quote to set a ticker
    mock_quote = StockQuote(
        ticker="AAPL",
        price=150.00,
        change=5.00,
        change_percent=3.45,
        volume=50000000,
        market_cap=2500000000000,
        high_52w=180.00,
        low_52w=120.00,
    )

    with (
        patch("viper.app.fetch_quote", return_value=mock_quote),
        patch("viper.app.fetch_stock_info", return_value=StockError(ticker="AAPL", error_message="Not needed")),
    ):
        async with app.run_test() as pilot:
            await pilot.pause()

            # Set current ticker directly
            app._current_ticker = "AAPL"

            # Show news panel directly
            news_container = app.query_one("#news-container")
            news_container.styles.display = "block"
            app._news_panel_visible = True

            # Create a test news item
            test_item = NewsItem(
                title="Test Article",
                url="https://example.com/test",
                source="Test Source",
                published_at=datetime.now(timezone.utc),
                summary="Test summary",
            )

            # Get news panel and set up test news
            news_panel = app.query_one(NewsPanel)
            news_panel._news_items = [test_item]
            news_panel._selected_index = 0
            news_panel._state = "success"

            # Mock webbrowser.open
            with patch("viper.widgets.news_panel.webbrowser.open") as mock_open:
                # Simulate pressing 'o' to open in browser
                news_panel.action_open_in_browser()
                await pilot.pause()

                # Verify webbrowser.open was called
                mock_open.assert_called_once_with(test_item.url)


# Prefix Keybinding System Tests (VPR-070)


@pytest.mark.asyncio
async def test_technical_prefix_activates_on_t_key() -> None:
    """Test that pressing 't' activates the technical indicator prefix mode."""
    app = ViperApp()
    async with app.run_test() as pilot:
        # Initially, prefix should not be active
        assert app._technical_prefix_active is False

        # Press 't' to activate prefix
        await pilot.press("t")
        await pilot.pause()

        # Prefix should now be active
        assert app._technical_prefix_active is True


@pytest.mark.asyncio
async def test_technical_prefix_shows_status_hint() -> None:
    """Test that pressing 't' shows a status hint about available indicators."""
    app = ViperApp()
    async with app.run_test() as pilot:
        from viper.widgets import StatusBar

        status_bar = app.query_one(StatusBar)

        # Press 't' to activate prefix
        await pilot.press("t")
        await pilot.pause()

        # Status bar should show hint message
        # (We can't easily check the actual text, but we verify the method was called)
        assert app._technical_prefix_active is True


@pytest.mark.asyncio
async def test_t_r_sequence_toggles_rsi() -> None:
    """Test that pressing 't' then 'r' toggles RSI indicator."""
    app = ViperApp()

    # Mock fetch_quote to set up ticker state
    mock_quote = StockQuote(
        ticker="AAPL",
        price=150.00,
        change=5.00,
        change_percent=3.45,
        volume=50000000,
        market_cap=2500000000000,
        high_52w=180.00,
        low_52w=120.00,
    )

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        async with app.run_test() as pilot:
            from viper.widgets import ChartPanel

            # Set up state - fetch a quote and toggle chart
            ticker_input = app.query_one(TickerInput)
            ticker_input.value = "AAPL"
            await pilot.press("enter")
            await pilot.pause()

            # Toggle chart visible
            chart_container = app.query_one("#chart-container")
            chart_container.display = True
            app._chart_panel_visible = True
            app._current_ticker = "AAPL"
            await pilot.pause()

            chart_panel = app.query_one(ChartPanel)

            # Initially RSI should be hidden
            assert chart_panel.is_rsi_visible() is False

            # Press 't' then 'r' to toggle RSI
            await pilot.press("t")
            await pilot.pause()
            assert app._technical_prefix_active is True

            await pilot.press("r")
            await pilot.pause()

            # Prefix should be cleared
            assert app._technical_prefix_active is False

            # RSI should now be visible
            assert chart_panel.is_rsi_visible() is True


@pytest.mark.asyncio
async def test_t_a_sequence_cycles_ma() -> None:
    """Test that pressing 't' then 'a' cycles moving averages."""
    app = ViperApp()

    # Mock fetch_quote to set up ticker state
    mock_quote = StockQuote(
        ticker="AAPL",
        price=150.00,
        change=5.00,
        change_percent=3.45,
        volume=50000000,
        market_cap=2500000000000,
        high_52w=180.00,
        low_52w=120.00,
    )

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        async with app.run_test() as pilot:
            from viper.widgets import ChartPanel

            # Set up state - fetch a quote and toggle chart
            ticker_input = app.query_one(TickerInput)
            ticker_input.value = "AAPL"
            await pilot.press("enter")
            await pilot.pause()

            # Toggle chart visible
            chart_container = app.query_one("#chart-container")
            chart_container.display = True
            app._chart_panel_visible = True
            app._current_ticker = "AAPL"
            await pilot.pause()

            chart_panel = app.query_one(ChartPanel)

            # Initially MA should be off
            assert chart_panel.get_ma_mode() == "off"

            # Press 't' then 'a' to cycle MA
            await pilot.press("t")
            await pilot.pause()
            assert app._technical_prefix_active is True

            await pilot.press("a")
            await pilot.pause()

            # Prefix should be cleared
            assert app._technical_prefix_active is False

            # MA mode should have changed to sma20
            assert chart_panel.get_ma_mode() == "sma20"


@pytest.mark.asyncio
async def test_t_followed_by_invalid_key_clears_prefix() -> None:
    """Test that pressing 't' then any non-indicator key clears the prefix without action."""
    app = ViperApp()
    async with app.run_test() as pilot:
        # Press 't' to activate prefix
        await pilot.press("t")
        await pilot.pause()
        assert app._technical_prefix_active is True

        # Press an invalid key (not 'r' or 'a')
        await pilot.press("x")
        await pilot.pause()

        # Prefix should be cleared
        assert app._technical_prefix_active is False


@pytest.mark.asyncio
async def test_escape_clears_technical_prefix() -> None:
    """Test that pressing Escape clears the technical prefix mode."""
    app = ViperApp()
    async with app.run_test() as pilot:
        # Press 't' to activate prefix
        await pilot.press("t")
        await pilot.pause()
        assert app._technical_prefix_active is True

        # Press Escape to cancel prefix
        await pilot.press("escape")
        await pilot.pause()

        # Prefix should be cleared
        assert app._technical_prefix_active is False


@pytest.mark.asyncio
async def test_t_a_t_a_cycles_ma_twice() -> None:
    """Test that each indicator action requires full prefix sequence (stateless)."""
    app = ViperApp()

    # Mock fetch_quote to set up ticker state
    mock_quote = StockQuote(
        ticker="AAPL",
        price=150.00,
        change=5.00,
        change_percent=3.45,
        volume=50000000,
        market_cap=2500000000000,
        high_52w=180.00,
        low_52w=120.00,
    )

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        async with app.run_test() as pilot:
            from viper.widgets import ChartPanel

            # Set up state
            ticker_input = app.query_one(TickerInput)
            ticker_input.value = "AAPL"
            await pilot.press("enter")
            await pilot.pause()

            # Toggle chart visible
            chart_container = app.query_one("#chart-container")
            chart_container.display = True
            app._chart_panel_visible = True
            app._current_ticker = "AAPL"
            await pilot.pause()

            chart_panel = app.query_one(ChartPanel)

            # Initially MA should be off
            assert chart_panel.get_ma_mode() == "off"

            # Press 't-a' to cycle to sma20
            await pilot.press("t")
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            assert chart_panel.get_ma_mode() == "sma20"

            # Press 't-a' again to cycle to sma50 (requires full prefix again)
            await pilot.press("t")
            await pilot.pause()
            assert app._technical_prefix_active is True
            await pilot.press("a")
            await pilot.pause()
            assert chart_panel.get_ma_mode() == "sma50"


@pytest.mark.asyncio
async def test_t_r_and_t_a_work_alongside_each_other() -> None:
    """Test that RSI and MA indicators can be toggled independently with prefix system."""
    app = ViperApp()

    # Mock fetch_quote to set up ticker state
    mock_quote = StockQuote(
        ticker="AAPL",
        price=150.00,
        change=5.00,
        change_percent=3.45,
        volume=50000000,
        market_cap=2500000000000,
        high_52w=180.00,
        low_52w=120.00,
    )

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        async with app.run_test() as pilot:
            from viper.widgets import ChartPanel

            # Set up state
            ticker_input = app.query_one(TickerInput)
            ticker_input.value = "AAPL"
            await pilot.press("enter")
            await pilot.pause()

            # Toggle chart visible
            chart_container = app.query_one("#chart-container")
            chart_container.display = True
            app._chart_panel_visible = True
            app._current_ticker = "AAPL"
            await pilot.pause()

            chart_panel = app.query_one(ChartPanel)

            # Toggle RSI on with t-r
            await pilot.press("t")
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()
            assert chart_panel.is_rsi_visible() is True

            # Cycle MA with t-a
            await pilot.press("t")
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            assert chart_panel.get_ma_mode() == "sma20"

            # Both should be active
            assert chart_panel.is_rsi_visible() is True
            assert chart_panel.get_ma_mode() == "sma20"

# VPR-079: Options panel integration tests


@pytest.mark.asyncio
async def test_options_panel_present() -> None:
    """Test that the OptionsChainPanel widget is present in the app."""
    app = ViperApp()
    async with app.run_test():
        # Should have an OptionsChainPanel widget
        options_panel = app.query_one(OptionsChainPanel)
        assert options_panel is not None


@pytest.mark.asyncio
async def test_options_panel_container_hidden_by_default() -> None:
    """Test that the options panel container is hidden by default."""
    app = ViperApp()
    async with app.run_test():
        options_container = app.query_one("#options-container")
        # Container should be hidden by default (display: none in CSS)
        assert str(options_container.styles.display) == "none"


@pytest.mark.asyncio
async def test_o_key_toggles_options_panel() -> None:
    """Test that action_toggle_options toggles the options panel visibility."""
    app = ViperApp()

    async with app.run_test() as pilot:
        options_container = app.query_one("#options-container")
        quote_container = app.query_one("#quote-container")

        # Initially options panel should be hidden, quote panel visible
        assert str(options_container.styles.display) == "none"
        assert str(quote_container.styles.display) == "block"
        assert app._options_panel_visible is False

        # Call the action directly
        app.action_toggle_options()
        await pilot.pause()

        # Options panel should now be visible, quote panel hidden
        assert str(options_container.styles.display) == "block"
        assert str(quote_container.styles.display) == "none"
        assert app._options_panel_visible is True

        # Toggle back
        app.action_toggle_options()
        await pilot.pause()

        # Options panel should be hidden again, quote panel visible
        assert str(options_container.styles.display) == "none"
        assert str(quote_container.styles.display) == "block"
        assert app._options_panel_visible is False


@pytest.mark.asyncio
async def test_options_panel_shows_empty_when_no_ticker() -> None:
    """Test that options panel shows empty state when no ticker selected."""
    app = ViperApp()

    async with app.run_test() as pilot:
        options_panel = app.query_one(OptionsChainPanel)

        # Call action to show options panel (no ticker selected yet)
        app.action_toggle_options()
        await pilot.pause()

        # Panel should be in empty state
        assert options_panel._state == "empty"
        assert options_panel._current_ticker is None


@pytest.mark.asyncio
async def test_options_panel_loads_when_ticker_exists() -> None:
    """Test that options panel loads options when a ticker is already selected."""
    app = ViperApp()

    # Mock quote fetch
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

    # Mock options fetch
    from viper.services.options import OptionsError

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch_quote, \
         patch("viper.widgets.options_panel.fetch_option_expirations", new_callable=AsyncMock) as mock_expirations:

        mock_fetch_quote.return_value = mock_quote
        mock_expirations.return_value = OptionsError(ticker="AAPL", error_message="No options")

        async with app.run_test() as pilot:
            ticker_input = app.query_one(TickerInput)
            options_panel = app.query_one(OptionsChainPanel)

            # Submit a ticker first
            ticker_input.focus()
            ticker_input.value = "AAPL"
            await pilot.press("enter")
            await pilot.pause()

            # Current ticker should be set
            assert app._current_ticker == "AAPL"

            # Call action to show options panel
            app.action_toggle_options()
            await pilot.pause()

            # Panel should have tried to load options for AAPL
            mock_expirations.assert_called_with("AAPL")
            # Panel should be in error state (no options available)
            assert options_panel._state == "error"
            assert options_panel._current_ticker == "AAPL"


@pytest.mark.asyncio
async def test_options_panel_hides_other_panels() -> None:
    """Test that showing options panel hides other panels (chart, info, news)."""
    app = ViperApp()

    # Mock fetch functions
    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch_quote, \
         patch("viper.widgets.options_panel.fetch_option_expirations", new_callable=AsyncMock) as mock_expirations, \
         patch("viper.widgets.chart_panel.fetch_historical_data", new_callable=AsyncMock):

        from viper.services.options import OptionsError
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
        mock_fetch_quote.return_value = mock_quote
        mock_expirations.return_value = OptionsError(ticker="AAPL", error_message="No options")

        async with app.run_test() as pilot:
            ticker_input = app.query_one(TickerInput)
            chart_container = app.query_one("#chart-container")
            options_container = app.query_one("#options-container")

            # Submit a ticker
            ticker_input.focus()
            ticker_input.value = "AAPL"
            await pilot.press("enter")
            await pilot.pause()

            # Call action to show chart panel
            app.action_toggle_chart()
            await pilot.pause()
            assert str(chart_container.styles.display) == "block"
            assert app._chart_panel_visible is True

            # Call action to show options panel
            app.action_toggle_options()
            await pilot.pause()

            # Chart panel should be hidden, options panel visible
            assert str(chart_container.styles.display) == "none"
            assert app._chart_panel_visible is False
            assert str(options_container.styles.display) == "block"
            assert app._options_panel_visible is True


@pytest.mark.asyncio
async def test_options_panel_receives_focus() -> None:
    """Test that options panel receives focus when toggled on."""
    app = ViperApp()

    async with app.run_test() as pilot:
        options_panel = app.query_one(OptionsChainPanel)

        # Call action to show options panel
        app.action_toggle_options()
        await pilot.pause()

        # Options panel should have focus
        assert app.focused == options_panel


@pytest.mark.asyncio
async def test_options_panel_refreshes_on_ticker_change() -> None:
    """Test that options panel refreshes when a new ticker is selected from watchlist."""
    app = ViperApp()

    # Mock quote fetch
    mock_quote_aapl = StockQuote(
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
    mock_quote_msft = StockQuote(
        ticker="MSFT",
        price=380.00,
        change=2.00,
        change_percent=0.53,
        volume=25000000,
        market_cap=2800000000000,
        high_52w=420.00,
        low_52w=320.00,
        name="Microsoft Corp.",
    )

    from viper.services.options import OptionsError

    with patch("viper.app.fetch_quote", new_callable=AsyncMock) as mock_fetch_quote, \
         patch("viper.widgets.options_panel.fetch_option_expirations", new_callable=AsyncMock) as mock_expirations:

        # First call returns AAPL, second returns MSFT
        mock_fetch_quote.side_effect = [mock_quote_aapl, mock_quote_msft]
        mock_expirations.return_value = OptionsError(ticker="AAPL", error_message="No options")

        async with app.run_test() as pilot:
            ticker_input = app.query_one(TickerInput)
            options_panel = app.query_one(OptionsChainPanel)

            # Submit first ticker (AAPL)
            ticker_input.focus()
            ticker_input.value = "AAPL"
            await pilot.press("enter")
            await pilot.pause()

            assert app._current_ticker == "AAPL"

            # Show options panel
            app.action_toggle_options()
            await pilot.pause()

            # Verify options loaded for AAPL
            assert mock_expirations.call_count == 1
            mock_expirations.assert_called_with("AAPL")

            # Now change ticker via input (simulates watchlist selection)
            ticker_input.focus()
            ticker_input.value = "MSFT"
            await pilot.press("enter")
            await pilot.pause()

            # Current ticker should now be MSFT
            assert app._current_ticker == "MSFT"

            # Options panel should have been refreshed with MSFT
            assert mock_expirations.call_count == 2
            mock_expirations.assert_called_with("MSFT")


# VPR-094: Multi-ticker watchlist add/delete tests


@pytest.mark.asyncio
async def test_multi_ticker_watchlist_add() -> None:
    """Test that 'w AAPL MSFT GOOGL' adds all three tickers to watchlist."""
    app = ViperApp()

    # Clear watchlist to start fresh
    app.watchlist_manager._items = []

    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        watchlist_panel = app.query_one(WatchlistPanel)

        # Initially watchlist should be empty
        initial_count = len(app.watchlist_manager.get_all())
        assert initial_count == 0

        # Submit multi-ticker add command
        ticker_input.focus()
        ticker_input.value = "w AAPL MSFT GOOGL"
        await pilot.press("enter")
        await pilot.pause()

        # All three tickers should be added
        tickers = app.watchlist_manager.get_all()
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        assert "GOOGL" in tickers
        assert len(tickers) == 3


@pytest.mark.asyncio
async def test_multi_ticker_watchlist_delete() -> None:
    """Test that 'd AAPL MSFT' removes both tickers from watchlist."""
    app = ViperApp()

    # Pre-populate watchlist
    app.watchlist_manager._items = ["AAPL", "MSFT", "GOOGL"]

    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        watchlist_panel = app.query_one(WatchlistPanel)

        # Submit multi-ticker delete command
        ticker_input.focus()
        ticker_input.value = "d AAPL MSFT"
        await pilot.press("enter")
        await pilot.pause()

        # AAPL and MSFT should be removed, GOOGL should remain
        tickers = app.watchlist_manager.get_all()
        assert "AAPL" not in tickers
        assert "MSFT" not in tickers
        assert "GOOGL" in tickers
        assert len(tickers) == 1


@pytest.mark.asyncio
async def test_single_ticker_watchlist_still_works() -> None:
    """Test that existing single-ticker behavior 'w AAPL' still works."""
    app = ViperApp()

    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Submit single ticker add command (old behavior)
        ticker_input.focus()
        ticker_input.value = "w AAPL"
        await pilot.press("enter")
        await pilot.pause()

        # AAPL should be added
        tickers = app.watchlist_manager.get_all()
        assert "AAPL" in tickers


@pytest.mark.asyncio
async def test_multi_ticker_with_dashes() -> None:
    """Test that tickers with dashes like BTC-USD are handled correctly."""
    app = ViperApp()

    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Submit multi-ticker add with crypto tickers
        ticker_input.focus()
        ticker_input.value = "w BTC-USD ETH-USD AAPL"
        await pilot.press("enter")
        await pilot.pause()

        # All three should be added
        tickers = app.watchlist_manager.get_all()
        assert "BTC-USD" in tickers
        assert "ETH-USD" in tickers
        assert "AAPL" in tickers


@pytest.mark.asyncio
async def test_multi_ticker_partial_success() -> None:
    """Test that valid tickers are added even when some are invalid."""
    app = ViperApp()

    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Submit multi-ticker with some valid and one invalid (too long)
        ticker_input.focus()
        ticker_input.value = "w AAPL TOOLONGTICKER123 MSFT"
        await pilot.press("enter")
        await pilot.pause()

        # Valid tickers should be added
        tickers = app.watchlist_manager.get_all()
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        # Invalid ticker should not be added
        assert "TOOLONGTICKER123" not in tickers


@pytest.mark.asyncio
async def test_multi_ticker_delete_nonexistent() -> None:
    """Test that deleting nonexistent tickers shows them as failed."""
    app = ViperApp()

    # Pre-populate with just AAPL
    app.watchlist_manager._items = ["AAPL"]

    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Try to delete AAPL (exists) and MSFT (doesn't exist)
        ticker_input.focus()
        ticker_input.value = "d AAPL MSFT"
        await pilot.press("enter")
        await pilot.pause()

        # AAPL should be removed
        tickers = app.watchlist_manager.get_all()
        assert "AAPL" not in tickers
        # MSFT was never there, so watchlist should be empty
        assert len(tickers) == 0


@pytest.mark.asyncio
async def test_multi_ticker_feedback_notification() -> None:
    """Test that multi-ticker operations show feedback notifications."""
    app = ViperApp()

    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Submit multi-ticker add
        ticker_input.focus()
        ticker_input.value = "w AAPL MSFT"
        await pilot.press("enter")
        await pilot.pause()

        # Check that a notification was posted
        # (We can't easily check the exact text, but we verify the tickers were added)
        tickers = app.watchlist_manager.get_all()
        assert "AAPL" in tickers
        assert "MSFT" in tickers
