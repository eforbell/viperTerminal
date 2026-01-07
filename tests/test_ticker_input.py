"""Tests for the TickerInput widget."""

from pathlib import Path

import pytest
from textual.app import App, ComposeResult

from viper.services.history import HistoryManager
from viper.widgets import TickerInput


class TickerInputTestApp(App[None]):
    """Test app for TickerInput widget."""

    def __init__(self, history_manager: HistoryManager | None = None) -> None:
        """Initialize test app."""
        super().__init__()
        self.received_events: list[TickerInput.TickerLookup] = []
        self.history_manager = history_manager

    def compose(self) -> ComposeResult:
        """Compose the test app."""
        yield TickerInput(history_manager=self.history_manager)

    def on_ticker_input_ticker_lookup(self, event: TickerInput.TickerLookup) -> None:
        """Handle ticker lookup events."""
        self.received_events.append(event)


@pytest.mark.asyncio
async def test_ticker_input_renders() -> None:
    """Test that the TickerInput widget renders correctly."""
    app = TickerInputTestApp()
    async with app.run_test():
        # Get the ticker input widget
        ticker_input = app.query_one(TickerInput)
        assert ticker_input is not None
        assert ticker_input.placeholder == "Enter ticker symbol (e.g., AAPL, BTC)"


@pytest.mark.asyncio
async def test_empty_input_shows_error() -> None:
    """Test that submitting empty input shows an error state."""
    app = TickerInputTestApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Focus the input and submit empty value
        ticker_input.focus()
        await pilot.press("enter")

        # Should have error class
        assert ticker_input.has_class("error")

        # Value should still be empty
        assert ticker_input.value == ""


@pytest.mark.asyncio
async def test_whitespace_only_input_shows_error() -> None:
    """Test that submitting whitespace-only input shows an error state."""
    app = TickerInputTestApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Focus the input and type whitespace
        ticker_input.focus()
        await pilot.press("space", "space", "space")
        await pilot.press("enter")

        # Should have error class
        assert ticker_input.has_class("error")

        # Value should be cleared
        assert ticker_input.value == ""


@pytest.mark.asyncio
async def test_uppercase_normalization() -> None:
    """Test that ticker symbols are normalized to uppercase."""
    app = TickerInputTestApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Focus and type lowercase ticker
        ticker_input.focus()
        ticker_input.value = "aapl"
        await pilot.press("enter")

        # Should have received event with uppercase ticker
        assert len(app.received_events) == 1
        assert app.received_events[0].ticker == "AAPL"


@pytest.mark.asyncio
async def test_input_clears_after_submission() -> None:
    """Test that the input is cleared after successful submission."""
    app = TickerInputTestApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Focus and type ticker
        ticker_input.focus()
        ticker_input.value = "TSLA"
        await pilot.press("enter")

        # Input should be cleared
        assert ticker_input.value == ""


@pytest.mark.asyncio
async def test_ticker_lookup_event_emission() -> None:
    """Test that TickerLookup events are emitted correctly."""
    app = TickerInputTestApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Submit a valid ticker
        ticker_input.focus()
        ticker_input.value = "BTC"
        await pilot.press("enter")

        # Should have received exactly one event
        assert len(app.received_events) == 1
        assert isinstance(app.received_events[0], TickerInput.TickerLookup)
        assert app.received_events[0].ticker == "BTC"


@pytest.mark.asyncio
async def test_mixed_case_normalization() -> None:
    """Test normalization of mixed-case input."""
    app = TickerInputTestApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Submit mixed-case ticker
        ticker_input.focus()
        ticker_input.value = "GoOgL"
        await pilot.press("enter")

        # Should normalize to uppercase
        assert len(app.received_events) == 1
        assert app.received_events[0].ticker == "GOOGL"


@pytest.mark.asyncio
async def test_error_state_clears_on_valid_input() -> None:
    """Test that error state is removed when valid input is submitted."""
    app = TickerInputTestApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # First submit empty to get error state
        ticker_input.focus()
        await pilot.press("enter")
        assert ticker_input.has_class("error")

        # Now submit valid input
        ticker_input.value = "MSFT"
        await pilot.press("enter")

        # Error class should be removed
        assert not ticker_input.has_class("error")


@pytest.mark.asyncio
async def test_ticker_with_leading_trailing_whitespace() -> None:
    """Test that leading and trailing whitespace is trimmed."""
    app = TickerInputTestApp()
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Submit ticker with whitespace
        ticker_input.focus()
        ticker_input.value = "  nvda  "
        await pilot.press("enter")

        # Should trim whitespace and normalize
        assert len(app.received_events) == 1
        assert app.received_events[0].ticker == "NVDA"


# History navigation tests


@pytest.mark.asyncio
async def test_ticker_added_to_history(tmp_path: Path) -> None:
    """Test that submitting a ticker adds it to history."""
    manager = HistoryManager(config_dir=tmp_path)
    app = TickerInputTestApp(history_manager=manager)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)

        # Submit ticker
        ticker_input.focus()
        ticker_input.value = "AAPL"
        await pilot.press("enter")

        # Should be in history
        assert manager.get_all() == ["AAPL"]


@pytest.mark.asyncio
async def test_up_arrow_navigates_history(tmp_path: Path) -> None:
    """Test that Up arrow key navigates through history."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")
    manager.add("MSFT")

    app = TickerInputTestApp(history_manager=manager)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        ticker_input.focus()

        # Press up arrow
        await pilot.press("up")
        assert ticker_input.value == "MSFT"

        await pilot.press("up")
        assert ticker_input.value == "TSLA"

        await pilot.press("up")
        assert ticker_input.value == "AAPL"


@pytest.mark.asyncio
async def test_down_arrow_navigates_history(tmp_path: Path) -> None:
    """Test that Down arrow key navigates forward in history."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")
    manager.add("MSFT")

    app = TickerInputTestApp(history_manager=manager)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        ticker_input.focus()

        # Navigate up first
        await pilot.press("up")
        await pilot.press("up")
        await pilot.press("up")

        # Now navigate down
        await pilot.press("down")
        assert ticker_input.value == "TSLA"

        await pilot.press("down")
        assert ticker_input.value == "MSFT"

        await pilot.press("down")
        assert ticker_input.value == ""  # Back to beginning


@pytest.mark.asyncio
async def test_up_arrow_at_end_of_history(tmp_path: Path) -> None:
    """Test that Up arrow at end of history stays at last item."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")

    app = TickerInputTestApp(history_manager=manager)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        ticker_input.focus()

        # Navigate to end
        await pilot.press("up")
        assert ticker_input.value == "AAPL"

        # Try to go further
        await pilot.press("up")
        assert ticker_input.value == "AAPL"  # Still at end


@pytest.mark.asyncio
async def test_down_arrow_at_beginning_of_history(tmp_path: Path) -> None:
    """Test that Down arrow at beginning of history does nothing."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")

    app = TickerInputTestApp(history_manager=manager)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        ticker_input.focus()

        # Press down at beginning
        await pilot.press("down")
        assert ticker_input.value == ""  # No change


@pytest.mark.asyncio
async def test_typing_resets_history_navigation(tmp_path: Path) -> None:
    """Test that typing resets history navigation state."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")
    manager.add("TSLA")

    app = TickerInputTestApp(history_manager=manager)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        ticker_input.focus()

        # Navigate up
        await pilot.press("up")
        assert ticker_input.value == "TSLA"
        await pilot.press("up")
        assert ticker_input.value == "AAPL"

        # Type something (simulates user typing, which resets navigation)
        await pilot.press("m")

        # Navigate up again - should start from beginning (most recent)
        await pilot.press("up")
        assert ticker_input.value == "TSLA"  # Back to most recent


@pytest.mark.asyncio
async def test_history_navigation_without_manager(tmp_path: Path) -> None:
    """Test that history navigation works gracefully without manager."""
    app = TickerInputTestApp(history_manager=None)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        ticker_input.focus()

        # Press up/down - should not crash
        await pilot.press("up")
        await pilot.press("down")
        assert ticker_input.value == ""


@pytest.mark.asyncio
async def test_cursor_position_after_history_navigation(tmp_path: Path) -> None:
    """Test that cursor is positioned at end after history navigation."""
    manager = HistoryManager(config_dir=tmp_path)
    manager.add("AAPL")

    app = TickerInputTestApp(history_manager=manager)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        ticker_input.focus()

        # Navigate up
        await pilot.press("up")

        # Cursor should be at end
        assert ticker_input.cursor_position == len("AAPL")


@pytest.mark.asyncio
async def test_empty_history_navigation(tmp_path: Path) -> None:
    """Test navigation with empty history."""
    manager = HistoryManager(config_dir=tmp_path)
    app = TickerInputTestApp(history_manager=manager)
    async with app.run_test() as pilot:
        ticker_input = app.query_one(TickerInput)
        ticker_input.focus()

        # Press up/down with empty history
        await pilot.press("up")
        assert ticker_input.value == ""

        await pilot.press("down")
        assert ticker_input.value == ""
