"""Tests for the HelpScreen modal."""

import pytest
from textual.app import App
from textual.events import Key

from viper.widgets.help_screen import HelpScreen


class HelpScreenTestApp(App[None]):
    """Test app for HelpScreen."""

    def __init__(self, help_screen: HelpScreen) -> None:
        """Initialize test app with help screen."""
        super().__init__()
        self._help_screen = help_screen

    def on_mount(self) -> None:
        """Mount the help screen on startup."""
        self.push_screen(self._help_screen)


@pytest.mark.asyncio
async def test_help_screen_renders_title() -> None:
    """Test that help screen renders the title."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Check title is rendered
        label = app.screen.query_one("#help-title")
        assert "VIPER TERMINAL - Help" in str(label.render())


@pytest.mark.asyncio
async def test_help_screen_renders_commands_section() -> None:
    """Test that help screen renders commands section."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Check commands section is present
        statics = app.screen.query(".help-section-title")
        assert any("COMMANDS" in str(static.render()) for static in statics)


@pytest.mark.asyncio
async def test_help_screen_renders_keybindings_section() -> None:
    """Test that help screen renders keybindings section."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Check keybindings section is present
        statics = app.screen.query(".help-section-title")
        assert any("KEYBINDINGS" in str(static.render()) for static in statics)


@pytest.mark.asyncio
async def test_help_screen_renders_features_section() -> None:
    """Test that help screen renders features section."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Check features section is present
        statics = app.screen.query(".help-section-title")
        assert any("FEATURES" in str(static.render()) for static in statics)


@pytest.mark.asyncio
async def test_help_screen_dismisses_on_enter() -> None:
    """Test that help screen dismisses when Enter is pressed."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test() as pilot:
        # Simulate Enter key press
        help_screen.on_key(Key(key="enter", character="\r"))
        await pilot.pause()

        # Help screen should be dismissed (app should show base screen)
        assert not isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_help_screen_dismisses_on_escape() -> None:
    """Test that help screen dismisses when Escape is pressed."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test() as pilot:
        # Simulate Escape key press
        help_screen.on_key(Key(key="escape", character="\x1b"))
        await pilot.pause()

        # Help screen should be dismissed
        assert not isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_welcome_screen_renders_welcome_title() -> None:
    """Test that welcome screen renders welcome title."""
    help_screen = HelpScreen(is_welcome=True)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Check welcome title is rendered
        label = app.screen.query_one("#help-title")
        assert "Welcome to VIPER TERMINAL" in str(label.render())


@pytest.mark.asyncio
async def test_welcome_screen_renders_welcome_message() -> None:
    """Test that welcome screen renders welcome message."""
    help_screen = HelpScreen(is_welcome=True)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Check welcome message is rendered
        label = app.screen.query_one("#help-welcome-message")
        assert "Thank you" in str(label.render())


@pytest.mark.asyncio
async def test_help_screen_renders_footer() -> None:
    """Test that help screen renders footer with dismiss instructions."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Check footer is rendered
        footer = app.screen.query_one("#help-footer")
        assert "Press Enter or Esc to close" in str(footer.render())


@pytest.mark.asyncio
async def test_welcome_screen_renders_different_footer() -> None:
    """Test that welcome screen renders different footer text."""
    help_screen = HelpScreen(is_welcome=True)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Check footer has continue text
        footer = app.screen.query_one("#help-footer")
        assert "Press Enter or Esc to continue" in str(footer.render())


@pytest.mark.asyncio
async def test_help_screen_ignores_other_keys() -> None:
    """Test that help screen doesn't dismiss on other keys."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test() as pilot:
        # Simulate other key press (e.g., 'a')
        help_screen.on_key(Key(key="a", character="a"))
        await pilot.pause()

        # Help screen should still be shown
        assert isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_help_screen_shows_all_commands() -> None:
    """Test that help screen shows all documented commands."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Get all items in the help content
        items = app.screen.query(".help-item")
        item_texts = [str(item.render()) for item in items]
        combined_text = " ".join(item_texts)

        # Check for key commands
        assert "TICKER" in combined_text or "Look up" in combined_text
        assert "W TICKER" in combined_text or "Add ticker" in combined_text
        assert "D TICKER" in combined_text or "Remove ticker" in combined_text


@pytest.mark.asyncio
async def test_help_screen_shows_all_keybindings() -> None:
    """Test that help screen shows all keybindings."""
    help_screen = HelpScreen(is_welcome=False)
    app = HelpScreenTestApp(help_screen)

    async with app.run_test():
        # Get all items in the help content
        items = app.screen.query(".help-item")
        item_texts = [str(item.render()) for item in items]
        combined_text = " ".join(item_texts)

        # Check for key keybindings
        assert "q" in combined_text or "Quit" in combined_text
        assert "/" in combined_text or "Focus input" in combined_text
        assert "Tab" in combined_text or "Cycle" in combined_text
