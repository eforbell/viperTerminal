"""Tests for the watchlist panel widget."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.app import App

from viper.services.crypto import CryptoQuote
from viper.services.stock import StockError, StockQuote
from viper.services.streaming import ConnectionState, StreamingQuote, StreamingService
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


# VPR-098: Streaming integration tests


@pytest.mark.asyncio
async def test_toggle_streaming_enables_streaming(watchlist_manager: WatchlistManager) -> None:
    """Test that toggle_streaming() enables streaming mode."""
    watchlist_manager.add("AAPL")
    watchlist_manager.add("TSLA")

    # Reset singleton before test
    StreamingService._reset_instance()

    with patch.object(
        StreamingService, "start", new_callable=AsyncMock
    ) as mock_start, patch.object(
        StreamingService, "subscribe", new_callable=AsyncMock
    ) as mock_subscribe:
        app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)
            await pilot.pause(0.1)

            # Initially should not be streaming
            assert panel._streaming_enabled is False

            # Toggle streaming on
            panel.toggle_streaming()
            await pilot.pause(0.2)

            # Should be enabled
            assert panel._streaming_enabled is True
            assert mock_start.called
            assert mock_subscribe.called
            # Should subscribe to all watchlist tickers
            assert mock_subscribe.call_args[0][0] == ["AAPL", "TSLA"]


@pytest.mark.asyncio
async def test_toggle_streaming_disables_streaming(watchlist_manager: WatchlistManager) -> None:
    """Test that toggle_streaming() disables streaming mode when already enabled."""
    watchlist_manager.add("AAPL")

    # Reset singleton before test
    StreamingService._reset_instance()

    with patch.object(
        StreamingService, "start", new_callable=AsyncMock
    ) as mock_start, patch.object(
        StreamingService, "stop", new_callable=AsyncMock
    ) as mock_stop, patch.object(
        StreamingService, "subscribe", new_callable=AsyncMock
    ):
        app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)
            await pilot.pause(0.1)

            # Enable streaming first
            panel.toggle_streaming()
            await pilot.pause(0.2)
            assert panel._streaming_enabled is True

            # Toggle streaming off
            panel.toggle_streaming()
            await pilot.pause(0.2)

            # Should be disabled
            assert panel._streaming_enabled is False
            assert mock_stop.called
            assert len(panel._streaming_quotes) == 0


@pytest.mark.asyncio
async def test_render_prefers_streaming_quote(watchlist_manager: WatchlistManager) -> None:
    """Test that _render_items() prefers streaming quotes over polling quotes."""
    watchlist_manager.add("AAPL")

    # Reset singleton before test
    StreamingService._reset_instance()

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause(0.1)

        # Set up polling quote
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

        # Set up streaming quote with different price
        panel._streaming_enabled = True
        panel._streaming_quotes["AAPL"] = StreamingQuote(
            symbol="AAPL",
            price=155.0,
            change=10.0,
            change_percent=6.89,
        )

        panel._render_items()
        await pilot.pause()

        # Check that streaming price is displayed
        labels = panel.query(".watchlist-item")
        label_texts = [str(label.render()) for label in labels]
        # Streaming price should be shown (155.0), not polling (150.0)
        assert any("155.00" in text for text in label_texts)


@pytest.mark.asyncio
async def test_render_falls_back_to_polling_quote(watchlist_manager: WatchlistManager) -> None:
    """Test that _render_items() falls back to polling quote when streaming unavailable."""
    watchlist_manager.add("AAPL")

    # Reset singleton before test
    StreamingService._reset_instance()

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause(0.1)

        # Set up only polling quote (no streaming quote)
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

        # Streaming is disabled
        panel._streaming_enabled = False

        panel._render_items()
        await pilot.pause()

        # Check that polling price is displayed
        labels = panel.query(".watchlist-item")
        label_texts = [str(label.render()) for label in labels]
        assert any("150.00" in text for text in label_texts)


@pytest.mark.asyncio
async def test_on_ticker_added_subscribes_to_streaming(
    watchlist_manager: WatchlistManager,
) -> None:
    """Test that on_ticker_added() subscribes to streaming when active."""
    # Reset singleton before test
    StreamingService._reset_instance()

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause(0.1)

        # Manually enable streaming and mock the service
        panel._streaming_enabled = True
        panel._streaming_service = MagicMock()
        panel._streaming_service.subscribe = AsyncMock()

        # Add a ticker
        watchlist_manager.add("TSLA")
        panel.on_ticker_added("TSLA")
        await pilot.pause(0.2)

        # Should have subscribed to the new ticker
        assert panel._streaming_service.subscribe.called
        assert panel._streaming_service.subscribe.call_args[0][0] == ["TSLA"]


@pytest.mark.asyncio
async def test_on_ticker_removed_unsubscribes_from_streaming(
    watchlist_manager: WatchlistManager,
) -> None:
    """Test that on_ticker_removed() unsubscribes from streaming when active."""
    watchlist_manager.add("AAPL")

    # Reset singleton before test
    StreamingService._reset_instance()

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause(0.1)

        # Manually enable streaming and mock the service
        panel._streaming_enabled = True
        panel._streaming_service = MagicMock()
        panel._streaming_service.unsubscribe = AsyncMock()

        # Add a streaming quote
        panel._streaming_quotes["AAPL"] = StreamingQuote(
            symbol="AAPL", price=150.0, change=5.0, change_percent=3.45
        )

        # Remove the ticker
        watchlist_manager.remove("AAPL")
        panel.on_ticker_removed("AAPL")
        await pilot.pause(0.2)

        # Should have unsubscribed
        assert panel._streaming_service.unsubscribe.called
        assert panel._streaming_service.unsubscribe.call_args[0][0] == ["AAPL"]
        # Should have cleared streaming quote
        assert "AAPL" not in panel._streaming_quotes


@pytest.mark.asyncio
async def test_streaming_quote_received_triggers_render(
    watchlist_manager: WatchlistManager,
) -> None:
    """Test that StreamingQuoteReceived message triggers re-render."""
    watchlist_manager.add("AAPL")

    # Reset singleton before test
    StreamingService._reset_instance()

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause(0.1)

        # Enable streaming
        panel._streaming_enabled = True

        # Manually add quote via callback (simulating what would happen)
        quote = StreamingQuote(
            symbol="AAPL", price=155.0, change=10.0, change_percent=6.89
        )
        panel._streaming_quotes["AAPL"] = quote

        # Post the message to trigger render
        panel.post_message(panel.StreamingQuoteReceived(quote))
        await pilot.pause()

        # Should have stored the quote
        assert "AAPL" in panel._streaming_quotes
        assert panel._streaming_quotes["AAPL"].price == 155.0


@pytest.mark.asyncio
async def test_streaming_state_changed_updates_header(
    watchlist_manager: WatchlistManager,
) -> None:
    """Test that StreamingStateChanged message updates connection state and triggers render."""
    # Reset singleton before test
    StreamingService._reset_instance()

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause(0.1)

        # Enable streaming
        panel._streaming_enabled = True

        # Test CONNECTED state
        panel.post_message(panel.StreamingStateChanged(ConnectionState.CONNECTED))
        await pilot.pause()
        assert panel._connection_state == ConnectionState.CONNECTED

        # Test CONNECTING state
        panel.post_message(panel.StreamingStateChanged(ConnectionState.CONNECTING))
        await pilot.pause()
        assert panel._connection_state == ConnectionState.CONNECTING

        # Test RECONNECTING state
        panel.post_message(panel.StreamingStateChanged(ConnectionState.RECONNECTING))
        await pilot.pause()
        assert panel._connection_state == ConnectionState.RECONNECTING


@pytest.mark.asyncio
async def test_format_streaming_quote_line() -> None:
    """Test that _format_streaming_quote_line() formats correctly."""
    from viper.services.watchlist import WatchlistManager

    manager = WatchlistManager()
    panel = WatchlistPanel(manager, refresh_interval=9999)

    # Test positive change
    quote = StreamingQuote(
        symbol="AAPL", price=155.50, change=10.0, change_percent=6.89
    )
    line = panel._format_streaming_quote_line("AAPL", quote)
    assert "AAPL" in line
    assert "$155.50" in line
    assert "+6.89%" in line

    # Test negative change
    quote = StreamingQuote(
        symbol="TSLA", price=200.25, change=-5.0, change_percent=-2.44
    )
    line = panel._format_streaming_quote_line("TSLA", quote)
    assert "TSLA" in line
    assert "$200.25" in line
    assert "-2.44%" in line

    # Test zero change
    quote = StreamingQuote(symbol="MSFT", price=300.00, change=0.0, change_percent=0.0)
    line = panel._format_streaming_quote_line("MSFT", quote)
    assert "MSFT" in line
    assert "$300.00" in line
    assert "0.00%" in line


@pytest.mark.asyncio
async def test_streaming_callbacks_post_messages(
    watchlist_manager: WatchlistManager,
) -> None:
    """Test that streaming callbacks post messages directly.

    Since yfinance AsyncWebSocket runs in the same asyncio event loop as Textual,
    we use post_message directly rather than call_from_thread.
    """
    watchlist_manager.add("AAPL")

    # Reset singleton before test
    StreamingService._reset_instance()

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        await pilot.pause(0.1)

        # Mock post_message to track calls
        original_post_message = panel.post_message
        post_message_calls: list[object] = []

        def mock_post_message(message: object) -> bool:
            post_message_calls.append(message)
            return original_post_message(message)

        panel.post_message = mock_post_message  # type: ignore

        # Call the streaming quote callback
        quote = StreamingQuote(
            symbol="AAPL", price=155.0, change=10.0, change_percent=6.89
        )
        panel._on_streaming_quote(quote)

        # Should have posted a StreamingQuoteReceived message
        assert len(post_message_calls) == 1
        assert isinstance(post_message_calls[0], WatchlistPanel.StreamingQuoteReceived)

        # Call the state change callback
        panel._on_connection_state_change(ConnectionState.CONNECTED)

        # Should have posted a StreamingStateChanged message
        assert len(post_message_calls) == 2
        assert isinstance(post_message_calls[1], WatchlistPanel.StreamingStateChanged)
