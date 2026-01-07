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
    """Test that panel shows loading state before quotes are fetched."""
    watchlist_manager.add("AAPL")

    app = WatchlistTestApp(watchlist_manager, refresh_interval=9999)

    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        # Clear quotes cache and render to show loading
        panel._quotes.clear()
        panel._render_items()
        await pilot.pause()

        # Should show loading state (quote not in cache)
        labels = panel.query(".watchlist-item")
        label_texts = [str(label.render()) for label in labels]
        assert any("Loading" in text for text in label_texts)


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
