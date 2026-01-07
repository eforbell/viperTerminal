"""Tests for the StatusBar widget."""

from datetime import datetime

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from viper.widgets.status_bar import StatusBar


class StatusBarTestApp(App[None]):
    """Test app for StatusBar."""

    def compose(self) -> ComposeResult:
        """Compose the test app."""
        yield StatusBar()


@pytest.mark.asyncio
async def test_status_bar_initial_state() -> None:
    """Test StatusBar shows correct initial state."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Check initial state
        connection_label = status_bar.query_one("#connection-status", Label)
        refresh_label = status_bar.query_one("#last-refresh", Label)

        assert str(connection_label.render()) == "Status: Online"
        assert str(refresh_label.render()) == "Last refresh: Never"


@pytest.mark.asyncio
async def test_status_bar_set_offline() -> None:
    """Test StatusBar can be set to offline."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Set offline
        status_bar.set_offline()
        await pilot.pause()

        connection_label = status_bar.query_one("#connection-status", Label)
        assert str(connection_label.render()) == "Status: Offline"


@pytest.mark.asyncio
async def test_status_bar_set_online() -> None:
    """Test StatusBar can be set back to online."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Set offline, then online
        status_bar.set_offline()
        await pilot.pause()
        status_bar.set_online()
        await pilot.pause()

        connection_label = status_bar.query_one("#connection-status", Label)
        assert str(connection_label.render()) == "Status: Online"


@pytest.mark.asyncio
async def test_status_bar_update_last_refresh() -> None:
    """Test StatusBar updates last refresh time."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Update last refresh
        before_update = datetime.now()
        status_bar.update_last_refresh()
        await pilot.pause()

        refresh_label = status_bar.query_one("#last-refresh", Label)
        rendered_text = str(refresh_label.render())

        # Should show time in HH:MM:SS format
        assert "Last refresh:" in rendered_text
        assert rendered_text != "Last refresh: Never"

        # The time should be the current time (within a few seconds)
        # Extract the time portion
        time_str = rendered_text.replace("Last refresh: ", "")
        refresh_time = datetime.strptime(time_str, "%H:%M:%S").time()
        before_time = before_update.time()

        # Check hour and minute match (second might differ)
        assert refresh_time.hour == before_time.hour
        assert refresh_time.minute == before_time.minute


@pytest.mark.asyncio
async def test_status_bar_multiple_refresh_updates() -> None:
    """Test StatusBar handles multiple refresh updates."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Update multiple times
        status_bar.update_last_refresh()
        await pilot.pause()

        refresh_label = status_bar.query_one("#last-refresh", Label)
        first_text = str(refresh_label.render())

        # Second update (in practice would be different time, but might be same second)
        status_bar.update_last_refresh()
        await pilot.pause()

        second_text = str(refresh_label.render())

        # Both should have valid time format
        assert "Last refresh:" in first_text
        assert "Last refresh:" in second_text
        assert first_text != "Last refresh: Never"
        assert second_text != "Last refresh: Never"


@pytest.mark.asyncio
async def test_status_bar_state_transitions() -> None:
    """Test StatusBar handles online/offline state transitions."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        connection_label = status_bar.query_one("#connection-status", Label)

        # Online -> Offline -> Online
        assert str(connection_label.render()) == "Status: Online"

        status_bar.set_offline()
        await pilot.pause()
        assert str(connection_label.render()) == "Status: Offline"

        status_bar.set_online()
        await pilot.pause()
        assert str(connection_label.render()) == "Status: Online"

        # Multiple offline calls
        status_bar.set_offline()
        await pilot.pause()
        status_bar.set_offline()
        await pilot.pause()
        assert str(connection_label.render()) == "Status: Offline"


@pytest.mark.asyncio
async def test_status_bar_set_message() -> None:
    """Test StatusBar can display a message."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Set a message
        status_bar.set_message("Opening in browser...")
        await pilot.pause()

        message_label = status_bar.query_one("#status-message", Label)
        assert str(message_label.render()) == "Opening in browser..."


@pytest.mark.asyncio
async def test_status_bar_clear_message() -> None:
    """Test StatusBar can clear a message."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Set then clear message
        status_bar.set_message("Test message")
        await pilot.pause()
        status_bar.clear_message()
        await pilot.pause()

        message_label = status_bar.query_one("#status-message", Label)
        assert str(message_label.render()) == ""


@pytest.mark.asyncio
async def test_status_bar_message_cleared_on_state_change() -> None:
    """Test StatusBar message is cleared when state changes."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Set message
        status_bar.set_message("Test message")
        await pilot.pause()

        # Online should clear message
        status_bar.set_online()
        await pilot.pause()

        message_label = status_bar.query_one("#status-message", Label)
        assert str(message_label.render()) == ""


@pytest.mark.asyncio
async def test_status_bar_message_cleared_on_refresh() -> None:
    """Test StatusBar message is cleared when refresh is updated."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        status_bar = app.query_one(StatusBar)
        await pilot.pause()

        # Set message
        status_bar.set_message("Test message")
        await pilot.pause()

        # Update refresh should clear message
        status_bar.update_last_refresh()
        await pilot.pause()

        message_label = status_bar.query_one("#status-message", Label)
        assert str(message_label.render()) == ""
