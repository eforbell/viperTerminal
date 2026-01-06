"""Tests for the TickerInput widget."""

import pytest
from textual.app import App, ComposeResult

from viper.widgets import TickerInput


class TickerInputTestApp(App[None]):
    """Test app for TickerInput widget."""

    def __init__(self) -> None:
        """Initialize test app."""
        super().__init__()
        self.received_events: list[TickerInput.TickerLookup] = []

    def compose(self) -> ComposeResult:
        """Compose the test app."""
        yield TickerInput()

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
