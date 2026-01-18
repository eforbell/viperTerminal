"""Tests for the watchlist panel widget."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App

from viper.services.crypto import CryptoQuote
from viper.services.stock import StockError, StockQuote
from viper.services.watchlist import WatchlistManager
from viper.widgets.watchlist_panel import WatchlistPanel


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def watchlist_manager(temp_config_dir: Path) -> WatchlistManager:
    """Create a WatchlistManager with a temporary config directory."""
    return WatchlistManager(config_dir=temp_config_dir)


class WatchlistTestApp(App[None]):
    """Test app for WatchlistPanel."""

    def __init__(self, watchlist_manager: WatchlistManager, refresh_interval: int = 60) -> None:
        """Initialize test app."""
        super().__init__()
        self.watchlist_manager = watchlist_manager
        self.refresh_interval = refresh_interval

    def compose(self):
        """Create child widgets."""
        yield WatchlistPanel(
            watchlist_manager=self.watchlist_manager,
            refresh_interval=self.refresh_interval,
        )


async def test_panel_empty_state(watchlist_manager: WatchlistManager) -> None:
    """Test that empty watchlist shows empty state message."""
    app = WatchlistTestApp(watchlist_manager)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause()

        # Should show empty state
        labels = panel.query("Label")
        label_texts = [str(label.render()) for label in labels]
        assert "No tickers in watchlist" in label_texts


@patch("viper.widgets.watchlist_panel.fetch_quote")
async def test_panel_displays_watchlist_items(
    mock_fetch: AsyncMock, watchlist_manager: WatchlistManager
) -> None:
    """Test that panel displays watchlist items."""
    # Add items to watchlist
    watchlist_manager.add("AAPL")
    watchlist_manager.add("GOOGL")

    # Create a function to return appropriate quote based on ticker
    async def fetch_side_effect(ticker: str):
        if ticker == "AAPL":
            return StockQuote(
                ticker="AAPL",
                name="Apple Inc.",
                price=150.0,
                change=5.0,
                change_percent=3.45,
                volume=100000,
                market_cap=2500000000,
                high_52w=180.0,
                low_52w=120.0,
            )
        return StockQuote(
            ticker="GOOGL",
            name="Alphabet Inc.",
            price=2800.0,
            change=-10.0,
            change_percent=-0.36,
            volume=50000,
            market_cap=1800000000,
            high_52w=3000.0,
            low_52w=2500.0,
        )

    mock_fetch.side_effect = fetch_side_effect

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause(0.1)  # Wait for mount refresh to complete

        # Check that items are displayed
        labels = panel.query(".watchlist-item")
        assert len(labels) == 2

        # Check content contains ticker symbols
        label_texts = [str(label.render()) for label in labels]
        assert any("AAPL" in text for text in label_texts)
        assert any("GOOGL" in text for text in label_texts)


async def test_panel_shows_loading_state(watchlist_manager: WatchlistManager) -> None:
    """Test that panel shows loading spinner during initial load."""
    watchlist_manager.add("AAPL")

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        # Simulate initial load state (no quotes fetched yet)
        panel._quotes.clear()
        panel._initial_load = True
        panel._render_items()
        await pilot.pause()

        # Should show loading spinner with "Loading" text
        loading_containers = panel.query(".loading-container")
        assert len(loading_containers) == 1

        # Check that loading text mentions ticker count
        labels = panel.query(".loading-text")
        assert len(labels) == 1
        label_text = str(labels[0].render())
        assert "Loading" in label_text


@patch("viper.widgets.watchlist_panel.fetch_quote")
async def test_panel_shows_error_state(
    mock_fetch: AsyncMock, watchlist_manager: WatchlistManager
) -> None:
    """Test that panel shows error state when quote fetch fails."""
    watchlist_manager.add("INVALID")

    # Mock fetch to return error
    mock_fetch.return_value = StockError(
        ticker="INVALID", error_message="Invalid ticker symbol"
    )

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await panel.refresh_quotes()
        await pilot.pause()

        # Should show error state
        labels = panel.query(".watchlist-item")
        label_texts = [str(label.render()) for label in labels]
        assert any("Error" in text for text in label_texts)


@patch("viper.widgets.watchlist_panel.fetch_quote")
async def test_panel_positive_change_color(
    mock_fetch: AsyncMock, watchlist_manager: WatchlistManager
) -> None:
    """Test that positive changes are colored green."""
    watchlist_manager.add("AAPL")

    mock_fetch.return_value = StockQuote(
        ticker="AAPL",
        name="Apple Inc.",
        price=150.0,
        change=5.0,
        change_percent=3.45,
        volume=100000,
        market_cap=2500000000,
        high_52w=180.0,
        low_52w=120.0,
    )

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await panel.refresh_quotes()
        await pilot.pause()

        # Check that positive class is applied
        positive_labels = panel.query(".positive")
        assert len(positive_labels) > 0


@patch("viper.widgets.watchlist_panel.fetch_quote")
async def test_panel_negative_change_color(
    mock_fetch: AsyncMock, watchlist_manager: WatchlistManager
) -> None:
    """Test that negative changes are colored red."""
    watchlist_manager.add("GOOGL")

    mock_fetch.return_value = StockQuote(
        ticker="GOOGL",
        name="Alphabet Inc.",
        price=2800.0,
        change=-10.0,
        change_percent=-0.36,
        volume=50000,
        market_cap=1800000000,
        high_52w=3000.0,
        low_52w=2500.0,
    )

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await panel.refresh_quotes()
        await pilot.pause()

        # Check that negative class is applied
        negative_labels = panel.query(".negative")
        assert len(negative_labels) > 0


@patch("viper.widgets.watchlist_panel.fetch_quote")
async def test_panel_crypto_quote_display(
    mock_fetch: AsyncMock, watchlist_manager: WatchlistManager
) -> None:
    """Test that crypto quotes are displayed correctly."""
    watchlist_manager.add("BTC")

    mock_fetch.return_value = CryptoQuote(
        symbol="BTC",
        name="Bitcoin",
        price_usd=45000.0,
        change_24h_percent=2.5,
        market_cap_usd=850000000000,
        volume_24h_usd=30000000000,
    )

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await panel.refresh_quotes()
        await pilot.pause()

        # Check that crypto quote is displayed
        labels = panel.query(".watchlist-item")
        label_texts = [str(label.render()) for label in labels]
        assert any("BTC" in text for text in label_texts)
        # Check for positive color
        positive_labels = panel.query(".positive")
        assert len(positive_labels) > 0


@patch("viper.widgets.watchlist_panel.fetch_quote")
async def test_panel_number_formatting(
    mock_fetch: AsyncMock, watchlist_manager: WatchlistManager
) -> None:
    """Test that numbers are formatted with commas and decimals."""
    watchlist_manager.add("AAPL")

    mock_fetch.return_value = StockQuote(
        ticker="AAPL",
        name="Apple Inc.",
        price=150.25,
        change=5.0,
        change_percent=3.45,
        volume=100000,
        market_cap=2500000000,
        high_52w=180.0,
        low_52w=120.0,
    )

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await panel.refresh_quotes()
        await pilot.pause()

        # Check formatting in displayed text
        labels = panel.query(".watchlist-item")
        label_texts = [str(label.render()) for label in labels]
        text = label_texts[0]
        # Should have price with 2 decimals
        assert "150.25" in text
        # Should have percentage with 2 decimals
        assert "3.45%" in text


@patch("viper.widgets.watchlist_panel.fetch_quote")
async def test_on_ticker_added(
    mock_fetch: AsyncMock, watchlist_manager: WatchlistManager
) -> None:
    """Test that on_ticker_added triggers refresh."""
    mock_fetch.return_value = StockQuote(
        ticker="AAPL",
        name="Apple Inc.",
        price=150.0,
        change=5.0,
        change_percent=3.45,
        volume=100000,
        market_cap=2500000000,
        high_52w=180.0,
        low_52w=120.0,
    )

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)

        # Add ticker
        watchlist_manager.add("AAPL")
        panel.on_ticker_added("AAPL")
        await pilot.pause(0.1)  # Give worker time to run

        # Should have fetched and displayed
        labels = panel.query(".watchlist-item")
        assert len(labels) > 0


async def test_on_ticker_removed(watchlist_manager: WatchlistManager) -> None:
    """Test that on_ticker_removed updates display."""
    watchlist_manager.add("AAPL")
    watchlist_manager.add("GOOGL")

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)

        # Store a quote in the cache
        panel._quotes["AAPL"] = StockQuote(
            ticker="AAPL",
            name="Apple Inc.",
            price=150.0,
            change=5.0,
            change_percent=3.45,
            volume=100000,
            market_cap=2500000000,
            high_52w=180.0,
            low_52w=120.0,
        )

        # Remove ticker
        watchlist_manager.remove("AAPL")
        panel.on_ticker_removed("AAPL")
        await pilot.pause()

        # Quote should be removed from cache
        assert "AAPL" not in panel._quotes


@patch("viper.widgets.watchlist_panel.fetch_quote")
async def test_refresh_interval_timer(
    mock_fetch: AsyncMock, watchlist_manager: WatchlistManager
) -> None:
    """Test that auto-refresh timer works."""
    watchlist_manager.add("AAPL")

    mock_fetch.return_value = StockQuote(
        ticker="AAPL",
        name="Apple Inc.",
        price=150.0,
        change=5.0,
        change_percent=3.45,
        volume=100000,
        market_cap=2500000000,
        high_52w=180.0,
        low_52w=120.0,
    )

    # Short refresh interval for testing
    app = WatchlistTestApp(watchlist_manager, refresh_interval=1)

    async with app.run_test() as pilot:
        await pilot.pause(0.1)  # Wait for initial mount/refresh

        # Check initial fetch happened
        initial_call_count = mock_fetch.call_count

        # Wait for at least one refresh cycle
        await pilot.pause(1.2)

        # Should have called fetch again
        assert mock_fetch.call_count > initial_call_count


# VPR-010: Keyboard navigation tests


@pytest.mark.asyncio
async def test_j_key_navigates_down(watchlist_manager: WatchlistManager) -> None:
    """Test that pressing 'j' navigates down the watchlist."""
    # Add multiple items to watchlist
    watchlist_manager.add("AAPL")
    watchlist_manager.add("TSLA")
    watchlist_manager.add("MSFT")

    mock_quote = StockQuote(
        ticker="AAPL",
        name="Apple Inc.",
        price=150.0,
        change=5.0,
        change_percent=3.45,
        volume=100000,
        market_cap=2500000000,
        high_52w=180.0,
        low_52w=120.0,
    )

    with patch("viper.widgets.watchlist_panel.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        app = WatchlistTestApp(watchlist_manager)
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)

            # Wait for initial refresh
            await pilot.pause(0.1)

            # Focus the panel
            panel.focus()
            await pilot.pause()

            # Initially selected index should be 0
            assert panel._selected_index == 0

            # Press 'j' to move down
            await pilot.press("j")
            await pilot.pause()

            # Selected index should be 1
            assert panel._selected_index == 1

            # Press 'j' again to move down
            await pilot.press("j")
            await pilot.pause()

            # Selected index should be 2
            assert panel._selected_index == 2

            # Press 'j' again - should stay at 2 (last item)
            await pilot.press("j")
            await pilot.pause()

            # Selected index should still be 2 (can't go beyond last item)
            assert panel._selected_index == 2


@pytest.mark.asyncio
async def test_k_key_navigates_up(watchlist_manager: WatchlistManager) -> None:
    """Test that pressing 'k' navigates up the watchlist."""
    # Add multiple items to watchlist
    watchlist_manager.add("AAPL")
    watchlist_manager.add("TSLA")
    watchlist_manager.add("MSFT")

    mock_quote = StockQuote(
        ticker="AAPL",
        name="Apple Inc.",
        price=150.0,
        change=5.0,
        change_percent=3.45,
        volume=100000,
        market_cap=2500000000,
        high_52w=180.0,
        low_52w=120.0,
    )

    with patch("viper.widgets.watchlist_panel.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        app = WatchlistTestApp(watchlist_manager)
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)

            # Wait for initial refresh
            await pilot.pause(0.1)

            # Focus the panel
            panel.focus()
            await pilot.pause()

            # Move to index 2 first
            panel._selected_index = 2
            panel._render_items()
            await pilot.pause()
            assert panel._selected_index == 2

            # Press 'k' to move up
            await pilot.press("k")
            await pilot.pause()

            # Selected index should be 1
            assert panel._selected_index == 1

            # Press 'k' again to move up
            await pilot.press("k")
            await pilot.pause()

            # Selected index should be 0
            assert panel._selected_index == 0

            # Press 'k' again - should stay at 0 (first item)
            await pilot.press("k")
            await pilot.pause()

            # Selected index should still be 0 (can't go before first item)
            assert panel._selected_index == 0


@pytest.mark.asyncio
async def test_enter_emits_ticker_selected(watchlist_manager: WatchlistManager) -> None:
    """Test that pressing Enter emits TickerSelected event."""
    # Add items to watchlist
    watchlist_manager.add("AAPL")
    watchlist_manager.add("TSLA")

    mock_quote = StockQuote(
        ticker="AAPL",
        name="Apple Inc.",
        price=150.0,
        change=5.0,
        change_percent=3.45,
        volume=100000,
        market_cap=2500000000,
        high_52w=180.0,
        low_52w=120.0,
    )

    with patch("viper.widgets.watchlist_panel.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        # Test app that captures messages
        class MessageCapturingApp(App[None]):
            def __init__(self, watchlist_manager: WatchlistManager) -> None:
                super().__init__()
                self.watchlist_manager = watchlist_manager
                self.captured_messages: list[WatchlistPanel.TickerSelected] = []

            def compose(self):
                yield WatchlistPanel(
                    watchlist_manager=self.watchlist_manager,
                    refresh_interval=60,
                )

            def on_watchlist_panel_ticker_selected(
                self, event: WatchlistPanel.TickerSelected
            ) -> None:
                self.captured_messages.append(event)

        app = MessageCapturingApp(watchlist_manager)
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)

            # Wait for initial refresh
            await pilot.pause(0.1)

            # Focus the panel
            panel.focus()
            await pilot.pause()

            # Selected index should be 0 (AAPL)
            assert panel._selected_index == 0

            # Press Enter to select
            await pilot.press("enter")
            await pilot.pause()

            # Should have emitted TickerSelected event with AAPL
            assert len(app.captured_messages) == 1
            assert app.captured_messages[0].ticker == "AAPL"

            # Navigate down and press Enter again
            await pilot.press("j")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            # Should have emitted another event with TSLA
            assert len(app.captured_messages) == 2
            assert app.captured_messages[1].ticker == "TSLA"


@pytest.mark.asyncio
async def test_navigation_works_with_empty_watchlist(watchlist_manager: WatchlistManager) -> None:
    """Test that j/k/enter don't crash when watchlist is empty."""
    # Don't add any items

    app = WatchlistTestApp(watchlist_manager)
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)

        # Wait for initial mount
        await pilot.pause(0.1)

        # Focus the panel
        panel.focus()
        await pilot.pause()

        # Try navigation keys - should not crash
        await pilot.press("j")
        await pilot.pause()
        await pilot.press("k")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        # Index should still be 0
        assert panel._selected_index == 0


@pytest.mark.asyncio
async def test_selected_item_visual_highlight(watchlist_manager: WatchlistManager) -> None:
    """Test that the selected item has the 'selected' CSS class."""
    # Add items to watchlist
    watchlist_manager.add("AAPL")
    watchlist_manager.add("TSLA")

    mock_quote = StockQuote(
        ticker="AAPL",
        name="Apple Inc.",
        price=150.0,
        change=5.0,
        change_percent=3.45,
        volume=100000,
        market_cap=2500000000,
        high_52w=180.0,
        low_52w=120.0,
    )

    with patch("viper.widgets.watchlist_panel.fetch_quote", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_quote

        app = WatchlistTestApp(watchlist_manager)
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)

            # Wait for initial refresh
            await pilot.pause(0.1)

            # Get the labels in the content
            from textual.widgets import Label
            labels = panel.query("Label.watchlist-item")

            # First item (index 0) should have 'selected' class
            first_label = labels.first(Label)
            assert "selected" in first_label.classes

            # Press 'j' to move down
            panel.focus()
            await pilot.press("j")
            await pilot.pause()

            # Refresh labels
            labels = panel.query("Label.watchlist-item")

            # Now second item should have 'selected' class
            second_label = labels.nodes[1]
            assert "selected" in second_label.classes
