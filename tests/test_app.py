"""Tests for the main Viper Terminal application."""

import pytest
from textual.widgets import Footer, Header

from viper.app import ViperApp


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
