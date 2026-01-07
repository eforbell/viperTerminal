"""Tests for InfoPanel widget."""

from textual.app import App

from viper.services.crypto import CryptoQuote
from viper.services.stock import StockQuote
from viper.widgets.info_panel import InfoPanel


class InfoPanelTestApp(App[None]):
    """Test app that mounts an InfoPanel."""

    def compose(self):
        """Compose the test app."""
        yield InfoPanel()


async def test_info_panel_initialization():
    """Test that InfoPanel initializes correctly."""
    app = InfoPanelTestApp()
    async with app.run_test():
        info_panel = app.query_one(InfoPanel)
        assert info_panel is not None
        assert info_panel._current_quote is None


async def test_info_panel_empty_state():
    """Test that InfoPanel shows empty state correctly."""
    app = InfoPanelTestApp()
    async with app.run_test() as pilot:
        info_panel = app.query_one(InfoPanel)
        info_panel.show_empty()
        await pilot.pause()

        # Check that content shows empty message
        content = info_panel.query_one("#info-content")
        assert "No asset selected" in str(content.render())


async def test_info_panel_stock_info_display():
    """Test that InfoPanel displays stock info correctly."""
    app = InfoPanelTestApp()
    async with app.run_test() as pilot:
        info_panel = app.query_one(InfoPanel)

        # Create a stock quote
        quote = StockQuote(
            ticker="AAPL",
            price=150.0,
            change=2.5,
            change_percent=1.7,
            volume=1000000,
            market_cap=2500000000,
            high_52w=180.0,
            low_52w=120.0,
            name="Apple Inc.",
        )

        # Create mock info dict
        info = {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "longBusinessSummary": "Apple designs and manufactures consumer electronics.",
            "website": "https://www.apple.com",
            "fullTimeEmployees": 164000,
        }

        # Display stock info
        info_panel.show_stock_info(quote, info)
        await pilot.pause()

        # Check that content shows stock info
        content = info_panel.query_one("#info-content")
        rendered = str(content.render())

        assert "Apple Inc." in rendered
        assert "AAPL" in rendered
        assert "Technology" in rendered
        assert "Consumer Electronics" in rendered
        assert "164,000" in rendered  # Formatted with commas
        assert "https://www.apple.com" in rendered
        assert "Apple designs and manufactures consumer electronics." in rendered


async def test_info_panel_stock_info_missing_fields():
    """Test that InfoPanel handles missing stock info fields gracefully."""
    app = InfoPanelTestApp()
    async with app.run_test() as pilot:
        info_panel = app.query_one(InfoPanel)

        # Create a stock quote
        quote = StockQuote(
            ticker="TEST",
            price=50.0,
            change=1.0,
            change_percent=2.0,
            volume=100000,
            market_cap=1000000,
            high_52w=60.0,
            low_52w=40.0,
            name=None,
        )

        # Create info dict with missing fields
        info = {}

        # Display stock info
        info_panel.show_stock_info(quote, info)
        await pilot.pause()

        # Check that content shows N/A for missing fields
        content = info_panel.query_one("#info-content")
        rendered = str(content.render())

        assert "TEST" in rendered
        assert "N/A" in rendered  # Missing fields should show N/A


async def test_info_panel_crypto_info_display():
    """Test that InfoPanel displays crypto info correctly."""
    app = InfoPanelTestApp()
    async with app.run_test() as pilot:
        info_panel = app.query_one(InfoPanel)

        # Create a crypto quote
        quote = CryptoQuote(
            symbol="BTC",
            price_usd=50000.0,
            change_24h_percent=3.5,
            market_cap_usd=1000000000000,
            volume_24h_usd=50000000000.0,
            name="Bitcoin",
        )

        # Create mock info dict
        info = {
            "description": {
                "en": "Bitcoin is a decentralized digital currency.",
            },
            "links": {
                "homepage": ["https://bitcoin.org", ""],
            },
            "genesis_date": "2009-01-03",
        }

        # Display crypto info
        info_panel.show_crypto_info(quote, info)
        await pilot.pause()

        # Check that content shows crypto info
        content = info_panel.query_one("#info-content")
        rendered = str(content.render())

        assert "Bitcoin" in rendered
        assert "BTC" in rendered
        assert "2009-01-03" in rendered
        assert "https://bitcoin.org" in rendered
        assert "Bitcoin is a decentralized digital currency." in rendered


async def test_info_panel_crypto_info_missing_fields():
    """Test that InfoPanel handles missing crypto info fields gracefully."""
    app = InfoPanelTestApp()
    async with app.run_test() as pilot:
        info_panel = app.query_one(InfoPanel)

        # Create a crypto quote
        quote = CryptoQuote(
            symbol="TEST",
            price_usd=100.0,
            change_24h_percent=5.0,
            market_cap_usd=1000000,
            volume_24h_usd=10000.0,
            name=None,
        )

        # Create info dict with missing fields
        info = {}

        # Display crypto info
        info_panel.show_crypto_info(quote, info)
        await pilot.pause()

        # Check that content shows defaults for missing fields
        content = info_panel.query_one("#info-content")
        rendered = str(content.render())

        assert "TEST" in rendered
        assert "N/A" in rendered  # Missing fields should show N/A
        assert "No description available" in rendered


async def test_info_panel_crypto_info_malformed_description():
    """Test that InfoPanel handles malformed description field."""
    app = InfoPanelTestApp()
    async with app.run_test() as pilot:
        info_panel = app.query_one(InfoPanel)

        quote = CryptoQuote(
            symbol="ETH",
            price_usd=3000.0,
            change_24h_percent=2.0,
            market_cap_usd=500000000000,
            volume_24h_usd=20000000000.0,
            name="Ethereum",
        )

        # Malformed description (not a dict)
        info = {
            "description": "Invalid format",
        }

        info_panel.show_crypto_info(quote, info)
        await pilot.pause()

        content = info_panel.query_one("#info-content")
        rendered = str(content.render())

        assert "No description available" in rendered


async def test_info_panel_crypto_info_malformed_links():
    """Test that InfoPanel handles malformed links field."""
    app = InfoPanelTestApp()
    async with app.run_test() as pilot:
        info_panel = app.query_one(InfoPanel)

        quote = CryptoQuote(
            symbol="ETH",
            price_usd=3000.0,
            change_24h_percent=2.0,
            market_cap_usd=500000000000,
            volume_24h_usd=20000000000.0,
            name="Ethereum",
        )

        # Malformed links (not a dict)
        info = {
            "links": "Invalid format",
        }

        info_panel.show_crypto_info(quote, info)
        await pilot.pause()

        content = info_panel.query_one("#info-content")
        rendered = str(content.render())

        assert "N/A" in rendered  # Website should be N/A


async def test_info_panel_focusable():
    """Test that InfoPanel is focusable."""
    app = InfoPanelTestApp()
    async with app.run_test():
        info_panel = app.query_one(InfoPanel)
        assert info_panel.can_focus is True
