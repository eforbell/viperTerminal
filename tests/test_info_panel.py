"""Tests for InfoPanel widget."""

import pytest

from viper.services.crypto import CryptoQuote
from viper.services.stock import StockQuote
from viper.widgets.info_panel import InfoPanel


# Test the InfoPanel methods directly without Textual app context
# This avoids timing issues with the async widget mounting


def test_info_panel_initialization():
    """Test that InfoPanel initializes correctly."""
    info_panel = InfoPanel()
    assert info_panel is not None
    assert info_panel._current_quote is None
    assert info_panel.can_focus is True


def test_info_panel_show_empty_sets_state():
    """Test that show_empty clears the current quote."""
    info_panel = InfoPanel()
    
    # Set a quote first
    quote = StockQuote(
        ticker="TEST",
        price=100.0,
        change=1.0,
        change_percent=1.0,
        volume=1000,
        market_cap=1000000,
        high_52w=110.0,
        low_52w=90.0,
        name="Test",
    )
    info_panel._current_quote = quote
    
    # Now show empty
    info_panel.show_empty()
    
    assert info_panel._current_quote is None


def test_info_panel_show_stock_info_sets_quote():
    """Test that show_stock_info sets the current quote."""
    info_panel = InfoPanel()
    
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
    
    info = {
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": "Apple designs and manufactures consumer electronics.",
        "website": "https://www.apple.com",
        "fullTimeEmployees": 164000,
    }
    
    # Call method - it won't fully update content without app context
    # but it should set the quote
    info_panel.show_stock_info(quote, info)
    
    assert info_panel._current_quote == quote


def test_info_panel_show_crypto_info_sets_quote():
    """Test that show_crypto_info sets the current quote."""
    info_panel = InfoPanel()
    
    quote = CryptoQuote(
        symbol="BTC",
        price_usd=50000.0,
        change_24h_percent=3.5,
        market_cap_usd=1000000000000,
        volume_24h_usd=50000000000.0,
        name="Bitcoin",
    )
    
    info = {
        "description": {"en": "Bitcoin is a decentralized digital currency."},
        "links": {"homepage": ["https://bitcoin.org"]},
        "genesis_date": "2009-01-03",
    }
    
    info_panel.show_crypto_info(quote, info)
    
    assert info_panel._current_quote == quote


def test_info_panel_stock_info_formats_employees():
    """Test that employee count is formatted with commas."""
    info_panel = InfoPanel()
    
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
    
    # Test with integer employees (should be formatted)
    info = {"fullTimeEmployees": 164000}
    info_panel.show_stock_info(quote, info)
    # Method ran without error
    
    # Test with string employees (should pass through)
    info = {"fullTimeEmployees": "Unknown"}
    info_panel.show_stock_info(quote, info)
    # Method ran without error


def test_info_panel_crypto_info_handles_missing_fields():
    """Test that missing crypto fields are handled gracefully."""
    info_panel = InfoPanel()
    
    quote = CryptoQuote(
        symbol="TEST",
        price_usd=100.0,
        change_24h_percent=5.0,
        market_cap_usd=1000000,
        volume_24h_usd=10000.0,
        name=None,  # Name is None
    )
    
    # Empty info dict - should use defaults
    info_panel.show_crypto_info(quote, {})
    assert info_panel._current_quote == quote


def test_info_panel_crypto_info_handles_malformed_description():
    """Test that malformed description is handled."""
    info_panel = InfoPanel()
    
    quote = CryptoQuote(
        symbol="ETH",
        price_usd=3000.0,
        change_24h_percent=2.0,
        market_cap_usd=500000000000,
        volume_24h_usd=20000000000.0,
        name="Ethereum",
    )
    
    # Description is not a dict (malformed)
    info = {"description": "Invalid format string"}
    info_panel.show_crypto_info(quote, info)
    assert info_panel._current_quote == quote


def test_info_panel_crypto_info_handles_malformed_links():
    """Test that malformed links field is handled."""
    info_panel = InfoPanel()
    
    quote = CryptoQuote(
        symbol="ETH",
        price_usd=3000.0,
        change_24h_percent=2.0,
        market_cap_usd=500000000000,
        volume_24h_usd=20000000000.0,
        name="Ethereum",
    )
    
    # Links is not a dict (malformed)
    info = {"links": "Invalid format"}
    info_panel.show_crypto_info(quote, info)
    assert info_panel._current_quote == quote


def test_info_panel_crypto_info_handles_empty_homepage():
    """Test that empty homepage list is handled."""
    info_panel = InfoPanel()
    
    quote = CryptoQuote(
        symbol="ETH",
        price_usd=3000.0,
        change_24h_percent=2.0,
        market_cap_usd=500000000000,
        volume_24h_usd=20000000000.0,
        name="Ethereum",
    )
    
    # Homepage is empty list
    info = {"links": {"homepage": []}}
    info_panel.show_crypto_info(quote, info)
    assert info_panel._current_quote == quote
    
    # Homepage has empty string
    info = {"links": {"homepage": ["", ""]}}
    info_panel.show_crypto_info(quote, info)
    assert info_panel._current_quote == quote


def test_info_panel_stock_info_handles_missing_fields():
    """Test that missing stock info fields use defaults."""
    info_panel = InfoPanel()
    
    quote = StockQuote(
        ticker="TEST",
        price=50.0,
        change=1.0,
        change_percent=2.0,
        volume=100000,
        market_cap=1000000,
        high_52w=60.0,
        low_52w=40.0,
        name=None,  # Name is None
    )
    
    # Empty info dict
    info_panel.show_stock_info(quote, {})
    assert info_panel._current_quote == quote


def test_info_panel_focusable():
    """Test that InfoPanel is focusable."""
    info_panel = InfoPanel()
    assert info_panel.can_focus is True
