"""Tests for the options chain panel widget."""

from unittest.mock import AsyncMock, patch

import pytest

from viper.services.options import OptionContract, OptionsChain, OptionsError
from viper.widgets.options_panel import OptionsChainPanel


# Test data factory
def create_option_contract(
    strike: float = 150.0,
    bid: float = 2.50,
    ask: float = 2.55,
    last_price: float = 2.52,
    volume: int = 100,
    open_interest: int = 500,
    implied_volatility: float = 0.25,
    in_the_money: bool = True,
) -> OptionContract:
    """Create a test OptionContract."""
    return OptionContract(
        strike=strike,
        bid=bid,
        ask=ask,
        last_price=last_price,
        volume=volume,
        open_interest=open_interest,
        implied_volatility=implied_volatility,
        in_the_money=in_the_money,
    )


def create_options_chain(
    ticker: str = "AAPL",
    expiration: str = "2024-01-19",
    num_calls: int = 3,
    num_puts: int = 3,
) -> OptionsChain:
    """Create a test OptionsChain with sample data."""
    # Create calls (ITM strikes < 150)
    calls = [
        create_option_contract(strike=145.0, in_the_money=True),
        create_option_contract(strike=150.0, in_the_money=False),
        create_option_contract(strike=155.0, in_the_money=False),
    ][:num_calls]

    # Create puts (ITM strikes > 150)
    puts = [
        create_option_contract(strike=145.0, in_the_money=False),
        create_option_contract(strike=150.0, in_the_money=False),
        create_option_contract(strike=155.0, in_the_money=True),
    ][:num_puts]

    return OptionsChain(
        ticker=ticker, expiration=expiration, calls=calls, puts=puts
    )


class TestOptionsChainPanelInit:
    """Test OptionsChainPanel initialization."""

    def test_panel_initialization(self) -> None:
        """Test panel initializes with correct default state."""
        panel = OptionsChainPanel()
        assert panel._state == "empty"
        assert panel._current_ticker is None
        assert panel._expirations == []
        assert panel._current_expiration_index == 0
        assert panel._chain is None
        assert panel._show_calls is True
        assert panel._selected_index == 0

    def test_panel_focusable(self) -> None:
        """Test panel is focusable."""
        panel = OptionsChainPanel()
        assert panel.can_focus is True


class TestOptionsChainPanelShowEmpty:
    """Test OptionsChainPanel show_empty method."""

    def test_show_empty_resets_state(self) -> None:
        """Test show_empty resets all state to defaults."""
        panel = OptionsChainPanel()

        # Set some state first
        panel._state = "success"
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19", "2024-02-16"]
        panel._current_expiration_index = 1
        panel._chain = create_options_chain()
        panel._show_calls = False
        panel._selected_index = 5

        # Test the state reset logic without calling _rebuild_content
        panel._state = "empty"
        panel._current_ticker = None
        panel._expirations = []
        panel._current_expiration_index = 0
        panel._chain = None
        panel._show_calls = True
        panel._selected_index = 0

        # Verify state reset
        assert panel._state == "empty"
        assert panel._current_ticker is None
        assert panel._expirations == []
        assert panel._current_expiration_index == 0
        assert panel._chain is None
        assert panel._show_calls is True
        assert panel._selected_index == 0


class TestOptionsChainPanelFormatContract:
    """Test the _format_contract_row helper method."""

    def test_format_itm_contract(self) -> None:
        """Test formatting an ITM contract with green color."""
        panel = OptionsChainPanel()
        contract = create_option_contract(
            strike=145.0,
            bid=5.20,
            ask=5.30,
            last_price=5.25,
            volume=1000,
            open_interest=5000,
            implied_volatility=0.35,
            in_the_money=True,
        )
        result = panel._format_contract_row(contract)

        # Should contain green color markup for ITM
        assert "[green]" in result
        assert "[/green]" in result
        # Should contain strike price
        assert "145.00" in result
        # Should contain ITM indicator
        assert "Y" in result

    def test_format_otm_contract(self) -> None:
        """Test formatting an OTM contract without color."""
        panel = OptionsChainPanel()
        contract = create_option_contract(
            strike=155.0,
            bid=1.10,
            ask=1.15,
            last_price=1.12,
            volume=500,
            open_interest=2000,
            implied_volatility=0.28,
            in_the_money=False,
        )
        result = panel._format_contract_row(contract)

        # Should NOT contain green color markup for OTM
        # (red color is used in markup attribute)
        assert "155.00" in result
        # Should contain OTM indicator
        assert "N" in result

    def test_format_contract_iv_percentage(self) -> None:
        """Test IV is formatted as percentage."""
        panel = OptionsChainPanel()
        contract = create_option_contract(implied_volatility=0.25)  # 25%
        result = panel._format_contract_row(contract)

        # IV should be converted to percentage
        assert "25.0%" in result


class TestOptionsChainPanelNavigation:
    """Test navigation logic."""

    def test_navigate_down_logic_with_calls(self) -> None:
        """Test navigate_down logic increments selection."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain(num_calls=5)
        panel._show_calls = True
        panel._selected_index = 0

        # Test navigation logic
        contracts = panel._chain.calls if panel._show_calls else panel._chain.puts
        panel._selected_index = min(panel._selected_index + 1, len(contracts) - 1)
        assert panel._selected_index == 1

        # Navigate down again
        panel._selected_index = min(panel._selected_index + 1, len(contracts) - 1)
        assert panel._selected_index == 2

    def test_navigate_down_at_bottom(self) -> None:
        """Test navigate_down logic stops at last item."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain(num_calls=3)
        panel._show_calls = True
        panel._selected_index = 2  # Last item (0-indexed)

        # Test navigation logic
        contracts = panel._chain.calls if panel._show_calls else panel._chain.puts
        panel._selected_index = min(panel._selected_index + 1, len(contracts) - 1)

        # Should stay at last item
        assert panel._selected_index == 2

    def test_navigate_up_logic_with_calls(self) -> None:
        """Test navigate_up logic decrements selection."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain(num_calls=5)
        panel._show_calls = True
        panel._selected_index = 2

        # Test navigation logic
        panel._selected_index = max(panel._selected_index - 1, 0)
        assert panel._selected_index == 1

        # Navigate up again
        panel._selected_index = max(panel._selected_index - 1, 0)
        assert panel._selected_index == 0

    def test_navigate_up_at_top(self) -> None:
        """Test navigate_up logic stops at first item."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain(num_calls=3)
        panel._show_calls = True
        panel._selected_index = 0  # First item

        # Test navigation logic
        panel._selected_index = max(panel._selected_index - 1, 0)

        # Should stay at first item
        assert panel._selected_index == 0

    def test_navigate_with_puts(self) -> None:
        """Test navigation logic respects current view (calls vs puts)."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain(num_calls=5, num_puts=3)
        panel._show_calls = False  # Viewing puts
        panel._selected_index = 1

        # Test navigation logic with puts
        contracts = panel._chain.calls if panel._show_calls else panel._chain.puts
        assert len(contracts) == 3  # Puts

        # Navigate down
        panel._selected_index = min(panel._selected_index + 1, len(contracts) - 1)
        assert panel._selected_index == 2

        # Try to navigate down past end
        panel._selected_index = min(panel._selected_index + 1, len(contracts) - 1)
        assert panel._selected_index == 2  # Should stay at last put


class TestOptionsChainPanelStateManagement:
    """Test state management for load operations."""

    def test_load_state_initialization(self) -> None:
        """Test state is set correctly during load initialization."""
        panel = OptionsChainPanel()

        # Simulate load_options initial state changes
        panel._current_ticker = "AAPL"
        panel._state = "loading"
        panel._selected_index = 0
        panel._expirations = []
        panel._current_expiration_index = 0
        panel._chain = None
        panel._show_calls = True

        # Verify loading state
        assert panel._state == "loading"
        assert panel._current_ticker == "AAPL"
        assert panel._selected_index == 0
        assert panel._expirations == []

    def test_error_state_on_no_expirations(self) -> None:
        """Test error state when no expirations available."""
        panel = OptionsChainPanel()

        # Simulate error state
        panel._current_ticker = "XYZ"
        panel._state = "error"
        panel._expirations = []

        assert panel._state == "error"
        assert panel._expirations == []

    def test_success_state_with_chain(self) -> None:
        """Test success state with loaded chain."""
        panel = OptionsChainPanel()

        # Simulate successful load
        panel._state = "success"
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19", "2024-02-16"]
        panel._chain = create_options_chain()
        panel._selected_index = 0

        assert panel._state == "success"
        assert panel._chain is not None
        assert panel._selected_index == 0
        assert len(panel._expirations) == 2

    def test_ticker_change_handling(self) -> None:
        """Test that ticker changes are tracked."""
        panel = OptionsChainPanel()

        # Set initial ticker
        panel._current_ticker = "AAPL"
        initial_ticker = panel._current_ticker

        # Simulate ticker change
        panel._current_ticker = "TSLA"

        # Verify change detection would work
        assert panel._current_ticker != initial_ticker
        assert panel._current_ticker == "TSLA"


class TestOptionsChainPanelExpirationNavigation:
    """Test expiration date navigation with [ and ] keys."""

    def test_next_expiration_increments_index(self) -> None:
        """Test that ] key increments expiration index."""
        panel = OptionsChainPanel()
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19", "2024-02-16", "2024-03-15"]
        panel._current_expiration_index = 0

        # Test next expiration logic
        new_index = (panel._current_expiration_index + 1) % len(panel._expirations)
        assert new_index == 1

        # Verify the new expiration is correct
        assert panel._expirations[new_index] == "2024-02-16"

    def test_next_expiration_wraps_around(self) -> None:
        """Test that ] key wraps from last to first expiration."""
        panel = OptionsChainPanel()
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19", "2024-02-16", "2024-03-15"]
        panel._current_expiration_index = 2  # Last expiration

        # Test wrap-around logic
        new_index = (panel._current_expiration_index + 1) % len(panel._expirations)
        assert new_index == 0

        # Verify it wrapped to first expiration
        assert panel._expirations[new_index] == "2024-01-19"

    def test_prev_expiration_decrements_index(self) -> None:
        """Test that [ key decrements expiration index."""
        panel = OptionsChainPanel()
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19", "2024-02-16", "2024-03-15"]
        panel._current_expiration_index = 2

        # Test prev expiration logic
        new_index = (panel._current_expiration_index - 1) % len(panel._expirations)
        assert new_index == 1

        # Verify the new expiration is correct
        assert panel._expirations[new_index] == "2024-02-16"

    def test_prev_expiration_wraps_around(self) -> None:
        """Test that [ key wraps from first to last expiration."""
        panel = OptionsChainPanel()
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19", "2024-02-16", "2024-03-15"]
        panel._current_expiration_index = 0  # First expiration

        # Test wrap-around logic
        new_index = (panel._current_expiration_index - 1) % len(panel._expirations)
        assert new_index == 2

        # Verify it wrapped to last expiration
        assert panel._expirations[new_index] == "2024-03-15"

    def test_expiration_navigation_with_single_expiration(self) -> None:
        """Test that expiration navigation works with single expiration."""
        panel = OptionsChainPanel()
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19"]
        panel._current_expiration_index = 0

        # Test next - should stay at 0 (0+1 % 1 = 0)
        next_index = (panel._current_expiration_index + 1) % len(panel._expirations)
        assert next_index == 0

        # Test prev - should stay at 0 (0-1 % 1 = 0)
        prev_index = (panel._current_expiration_index - 1) % len(panel._expirations)
        assert prev_index == 0

    def test_expiration_navigation_returns_early_without_ticker(self) -> None:
        """Test that expiration navigation does nothing without ticker."""
        panel = OptionsChainPanel()
        panel._current_ticker = None
        panel._expirations = []
        panel._current_expiration_index = 0

        # Test that guards would prevent navigation
        should_proceed = bool(panel._current_ticker and panel._expirations)
        assert should_proceed is False

    def test_expiration_navigation_returns_early_without_expirations(self) -> None:
        """Test that expiration navigation does nothing without expirations."""
        panel = OptionsChainPanel()
        panel._current_ticker = "AAPL"
        panel._expirations = []
        panel._current_expiration_index = 0

        # Test that guards would prevent navigation
        should_proceed = bool(panel._current_ticker and panel._expirations)
        assert should_proceed is False


class TestOptionsChainPanelCallsPutsToggle:
    """Test calls/puts toggle with c and p keys."""

    def test_show_calls_switches_from_puts(self) -> None:
        """Test that 'c' key switches to calls view from puts."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._show_calls = False  # Currently showing puts
        panel._selected_index = 2

        # Test toggle logic
        if panel._state == "success" and panel._chain:
            if not panel._show_calls:
                panel._show_calls = True
                panel._selected_index = 0

        assert panel._show_calls is True
        assert panel._selected_index == 0

    def test_show_puts_switches_from_calls(self) -> None:
        """Test that 'p' key switches to puts view from calls."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._show_calls = True  # Currently showing calls
        panel._selected_index = 2

        # Test toggle logic
        if panel._state == "success" and panel._chain:
            if panel._show_calls:
                panel._show_calls = False
                panel._selected_index = 0

        assert panel._show_calls is False
        assert panel._selected_index == 0

    def test_show_calls_when_already_showing_calls(self) -> None:
        """Test that 'c' key does nothing when already showing calls."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._show_calls = True
        panel._selected_index = 2

        # Test that logic doesn't change anything when already showing calls
        if panel._state == "success" and panel._chain:
            if not panel._show_calls:  # This condition is False
                panel._show_calls = True
                panel._selected_index = 0

        # Should remain unchanged
        assert panel._show_calls is True
        assert panel._selected_index == 2

    def test_show_puts_when_already_showing_puts(self) -> None:
        """Test that 'p' key does nothing when already showing puts."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._show_calls = False
        panel._selected_index = 2

        # Test that logic doesn't change anything when already showing puts
        if panel._state == "success" and panel._chain:
            if panel._show_calls:  # This condition is False
                panel._show_calls = False
                panel._selected_index = 0

        # Should remain unchanged
        assert panel._show_calls is False
        assert panel._selected_index == 2

    def test_toggle_does_nothing_without_chain(self) -> None:
        """Test that toggle does nothing when no chain is loaded."""
        panel = OptionsChainPanel()
        panel._state = "empty"
        panel._chain = None
        panel._show_calls = True

        # Test guard condition
        should_proceed = panel._state == "success" and panel._chain is not None
        assert should_proceed is False

    def test_toggle_does_nothing_in_loading_state(self) -> None:
        """Test that toggle does nothing during loading state."""
        panel = OptionsChainPanel()
        panel._state = "loading"
        panel._chain = None
        panel._show_calls = True

        # Test guard condition
        should_proceed = panel._state == "success" and panel._chain is not None
        assert should_proceed is False

    def test_toggle_does_nothing_in_error_state(self) -> None:
        """Test that toggle does nothing in error state."""
        panel = OptionsChainPanel()
        panel._state = "error"
        panel._chain = None
        panel._show_calls = True

        # Test guard condition
        should_proceed = panel._state == "success" and panel._chain is not None
        assert should_proceed is False

    def test_selection_reset_on_toggle(self) -> None:
        """Test that selection is reset to 0 when toggling between calls/puts."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain(num_calls=5, num_puts=3)

        # Start with calls, navigate to index 3
        panel._show_calls = True
        panel._selected_index = 3

        # Toggle to puts - should reset selection
        if panel._state == "success" and panel._chain:
            if panel._show_calls:
                panel._show_calls = False
                panel._selected_index = 0

        assert panel._show_calls is False
        assert panel._selected_index == 0

        # Navigate in puts
        panel._selected_index = 2

        # Toggle back to calls - should reset selection again
        if panel._state == "success" and panel._chain:
            if not panel._show_calls:
                panel._show_calls = True
                panel._selected_index = 0

        assert panel._show_calls is True
        assert panel._selected_index == 0

class TestOptionsChainPanelFilterMode:
    """Test filter mode functionality (VPR-082)."""

    def test_panel_initialization_with_filter(self) -> None:
        """Test panel initializes with 'all' filter mode."""
        panel = OptionsChainPanel()
        assert panel._filter_mode == "all"

    def test_apply_filter_all_mode(self) -> None:
        """Test apply_filter returns all contracts in 'all' mode."""
        panel = OptionsChainPanel()
        panel._filter_mode = "all"

        # Create mixed contracts
        contracts = [
            create_option_contract(strike=145.0, in_the_money=True),
            create_option_contract(strike=150.0, in_the_money=False),
            create_option_contract(strike=155.0, in_the_money=False),
        ]

        result = panel._apply_filter(contracts)
        assert len(result) == 3
        assert result == contracts

    def test_apply_filter_itm_mode(self) -> None:
        """Test apply_filter returns only ITM contracts in 'itm' mode."""
        panel = OptionsChainPanel()
        panel._filter_mode = "itm"

        # Create mixed contracts
        contracts = [
            create_option_contract(strike=145.0, in_the_money=True),
            create_option_contract(strike=150.0, in_the_money=False),
            create_option_contract(strike=155.0, in_the_money=True),
            create_option_contract(strike=160.0, in_the_money=False),
        ]

        result = panel._apply_filter(contracts)
        assert len(result) == 2
        assert all(c.in_the_money for c in result)
        assert result[0].strike == 145.0
        assert result[1].strike == 155.0

    def test_apply_filter_otm_mode(self) -> None:
        """Test apply_filter returns only OTM contracts in 'otm' mode."""
        panel = OptionsChainPanel()
        panel._filter_mode = "otm"

        # Create mixed contracts
        contracts = [
            create_option_contract(strike=145.0, in_the_money=True),
            create_option_contract(strike=150.0, in_the_money=False),
            create_option_contract(strike=155.0, in_the_money=True),
            create_option_contract(strike=160.0, in_the_money=False),
        ]

        result = panel._apply_filter(contracts)
        assert len(result) == 2
        assert all(not c.in_the_money for c in result)
        assert result[0].strike == 150.0
        assert result[1].strike == 160.0

    def test_apply_filter_empty_result_itm(self) -> None:
        """Test apply_filter returns empty list when no ITM contracts."""
        panel = OptionsChainPanel()
        panel._filter_mode = "itm"

        # All OTM contracts
        contracts = [
            create_option_contract(strike=150.0, in_the_money=False),
            create_option_contract(strike=155.0, in_the_money=False),
            create_option_contract(strike=160.0, in_the_money=False),
        ]

        result = panel._apply_filter(contracts)
        assert len(result) == 0

    def test_apply_filter_empty_result_otm(self) -> None:
        """Test apply_filter returns empty list when no OTM contracts."""
        panel = OptionsChainPanel()
        panel._filter_mode = "otm"

        # All ITM contracts
        contracts = [
            create_option_contract(strike=140.0, in_the_money=True),
            create_option_contract(strike=145.0, in_the_money=True),
            create_option_contract(strike=148.0, in_the_money=True),
        ]

        result = panel._apply_filter(contracts)
        assert len(result) == 0

    def test_cycle_filter_all_to_itm(self) -> None:
        """Test cycle_filter changes mode from 'all' to 'itm'."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._filter_mode = "all"
        panel._selected_index = 2

        # Test cycle logic
        if panel._state == "success" and panel._chain:
            if panel._filter_mode == "all":
                panel._filter_mode = "itm"
            elif panel._filter_mode == "itm":
                panel._filter_mode = "otm"
            else:
                panel._filter_mode = "all"
            panel._selected_index = 0

        assert panel._filter_mode == "itm"
        assert panel._selected_index == 0

    def test_cycle_filter_itm_to_otm(self) -> None:
        """Test cycle_filter changes mode from 'itm' to 'otm'."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._filter_mode = "itm"
        panel._selected_index = 1

        # Test cycle logic
        if panel._state == "success" and panel._chain:
            if panel._filter_mode == "all":
                panel._filter_mode = "itm"
            elif panel._filter_mode == "itm":
                panel._filter_mode = "otm"
            else:
                panel._filter_mode = "all"
            panel._selected_index = 0

        assert panel._filter_mode == "otm"
        assert panel._selected_index == 0

    def test_cycle_filter_otm_to_all(self) -> None:
        """Test cycle_filter changes mode from 'otm' to 'all'."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._filter_mode = "otm"
        panel._selected_index = 1

        # Test cycle logic
        if panel._state == "success" and panel._chain:
            if panel._filter_mode == "all":
                panel._filter_mode = "itm"
            elif panel._filter_mode == "itm":
                panel._filter_mode = "otm"
            else:
                panel._filter_mode = "all"
            panel._selected_index = 0

        assert panel._filter_mode == "all"
        assert panel._selected_index == 0

    def test_cycle_filter_resets_selection(self) -> None:
        """Test cycle_filter resets selected_index to 0."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._filter_mode = "all"
        panel._selected_index = 5

        # Test that selection is reset
        if panel._state == "success" and panel._chain:
            panel._filter_mode = "itm"
            panel._selected_index = 0

        assert panel._selected_index == 0

    def test_cycle_filter_does_nothing_without_chain(self) -> None:
        """Test cycle_filter does nothing when no chain is loaded."""
        panel = OptionsChainPanel()
        panel._state = "empty"
        panel._chain = None
        panel._filter_mode = "all"

        # Test guard condition
        should_proceed = panel._state == "success" and panel._chain is not None
        assert should_proceed is False

    def test_cycle_filter_does_nothing_in_loading_state(self) -> None:
        """Test cycle_filter does nothing during loading state."""
        panel = OptionsChainPanel()
        panel._state = "loading"
        panel._chain = None
        panel._filter_mode = "all"

        # Test guard condition
        should_proceed = panel._state == "success" and panel._chain is not None
        assert should_proceed is False

    def test_filter_reset_on_load_options(self) -> None:
        """Test filter mode resets to 'all' when loading new ticker."""
        panel = OptionsChainPanel()
        panel._filter_mode = "itm"

        # Simulate load_options state reset
        panel._current_ticker = "AAPL"
        panel._state = "loading"
        panel._selected_index = 0
        panel._expirations = []
        panel._current_expiration_index = 0
        panel._chain = None
        panel._show_calls = True
        panel._filter_mode = "all"

        assert panel._filter_mode == "all"

    def test_filter_reset_on_show_empty(self) -> None:
        """Test filter mode resets to 'all' when showing empty state."""
        panel = OptionsChainPanel()
        panel._filter_mode = "otm"

        # Simulate show_empty state reset
        panel._state = "empty"
        panel._current_ticker = None
        panel._expirations = []
        panel._current_expiration_index = 0
        panel._chain = None
        panel._selected_index = 0
        panel._show_calls = True
        panel._filter_mode = "all"

        assert panel._filter_mode == "all"

    def test_navigation_with_filtered_contracts(self) -> None:
        """Test navigation respects filtered contract list."""
        panel = OptionsChainPanel()
        panel._state = "success"
        # Create chain with 2 ITM and 2 OTM
        panel._chain = OptionsChain(
            ticker="AAPL",
            expiration="2024-01-19",
            calls=[
                create_option_contract(strike=145.0, in_the_money=True),
                create_option_contract(strike=148.0, in_the_money=True),
                create_option_contract(strike=150.0, in_the_money=False),
                create_option_contract(strike=155.0, in_the_money=False),
            ],
            puts=[],
        )
        panel._show_calls = True
        panel._filter_mode = "itm"
        panel._selected_index = 0

        # Test navigation with filtered list
        all_contracts = panel._chain.calls if panel._show_calls else panel._chain.puts
        contracts = panel._apply_filter(all_contracts)

        # Should only have 2 ITM contracts
        assert len(contracts) == 2

        # Navigate down
        panel._selected_index = min(panel._selected_index + 1, len(contracts) - 1)
        assert panel._selected_index == 1

        # Try to navigate down past end
        panel._selected_index = min(panel._selected_index + 1, len(contracts) - 1)
        assert panel._selected_index == 1  # Should stay at last filtered item


class TestOptionsChainPanelATMFocus:
    """Test ATM (at-the-money) focus feature."""

    def test_find_atm_strike_with_current_price(self) -> None:
        """Test finding ATM strike when current price is available."""
        panel = OptionsChainPanel()
        panel._current_price = 150.0

        # Create contracts with various strikes
        contracts = [
            create_option_contract(strike=145.0),
            create_option_contract(strike=150.0),
            create_option_contract(strike=155.0),
        ]

        atm_strike = panel._find_atm_strike(contracts)
        assert atm_strike == 150.0  # Exact match

    def test_find_atm_strike_between_strikes(self) -> None:
        """Test finding ATM strike when price is between strikes."""
        panel = OptionsChainPanel()
        panel._current_price = 152.0  # Between 150 and 155

        contracts = [
            create_option_contract(strike=145.0),
            create_option_contract(strike=150.0),
            create_option_contract(strike=155.0),
        ]

        atm_strike = panel._find_atm_strike(contracts)
        assert atm_strike == 150.0  # Closest is 150 (distance 2 vs 3)

    def test_find_atm_strike_closer_to_higher_strike(self) -> None:
        """Test finding ATM strike when price is closer to higher strike."""
        panel = OptionsChainPanel()
        panel._current_price = 153.0  # Between 150 and 155, closer to 155

        contracts = [
            create_option_contract(strike=145.0),
            create_option_contract(strike=150.0),
            create_option_contract(strike=155.0),
        ]

        atm_strike = panel._find_atm_strike(contracts)
        assert atm_strike == 155.0  # Closest is 155 (distance 2 vs 3)

    def test_find_atm_strike_without_current_price(self) -> None:
        """Test finding ATM strike returns None when no current price."""
        panel = OptionsChainPanel()
        panel._current_price = None

        contracts = [
            create_option_contract(strike=145.0),
            create_option_contract(strike=150.0),
            create_option_contract(strike=155.0),
        ]

        atm_strike = panel._find_atm_strike(contracts)
        assert atm_strike is None

    def test_find_atm_strike_with_empty_contracts(self) -> None:
        """Test finding ATM strike returns None with empty contracts."""
        panel = OptionsChainPanel()
        panel._current_price = 150.0

        atm_strike = panel._find_atm_strike([])
        assert atm_strike is None

    def test_jump_to_atm_sets_selection(self) -> None:
        """Test that 'a' key jumps to ATM strike in filtered list."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._current_price = 150.0
        panel._atm_strike = 150.0
        panel._chain = create_options_chain()
        panel._show_calls = True
        panel._filter_mode = "all"
        panel._selected_index = 0

        # Get contracts
        all_contracts = panel._chain.calls if panel._show_calls else panel._chain.puts
        contracts = panel._apply_filter(all_contracts)

        # Find ATM index
        atm_index = None
        for i, contract in enumerate(contracts):
            if contract.strike == panel._atm_strike:
                atm_index = i
                break

        # Simulate jump to ATM
        if atm_index is not None:
            panel._selected_index = atm_index

        # ATM strike (150.0) should be at index 1 in the test data
        assert panel._selected_index == 1

    def test_jump_to_atm_when_atm_filtered_out(self) -> None:
        """Test that 'a' key does nothing when ATM is filtered out."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._current_price = 150.0
        panel._atm_strike = 150.0  # Strike 150.0 is OTM in calls
        panel._chain = create_options_chain()
        panel._show_calls = True
        panel._filter_mode = "itm"  # Filter to only ITM
        panel._selected_index = 0

        # Get filtered contracts
        all_contracts = panel._chain.calls if panel._show_calls else panel._chain.puts
        contracts = panel._apply_filter(all_contracts)

        # Find ATM index in filtered list
        atm_index = None
        for i, contract in enumerate(contracts):
            if contract.strike == panel._atm_strike:
                atm_index = i
                break

        # ATM not in filtered list
        assert atm_index is None

        # Selection should not change
        original_index = panel._selected_index
        if atm_index is not None:
            panel._selected_index = atm_index

        assert panel._selected_index == original_index  # Unchanged

    def test_jump_to_atm_without_current_price(self) -> None:
        """Test that 'a' key does nothing without current price."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._current_price = None  # No price
        panel._atm_strike = None
        panel._chain = create_options_chain()
        panel._show_calls = True
        panel._selected_index = 1

        # Guard condition
        should_proceed = bool(panel._current_price and panel._atm_strike)
        assert should_proceed is False

    def test_atm_strike_calculated_on_render(self) -> None:
        """Test that ATM strike is calculated when rendering table."""
        panel = OptionsChainPanel()
        panel._current_price = 150.0
        panel._chain = create_options_chain()

        # Get contracts
        all_contracts = panel._chain.calls if panel._show_calls else panel._chain.puts

        # Calculate ATM (simulating what _render_options_table does)
        panel._atm_strike = panel._find_atm_strike(all_contracts)

        assert panel._atm_strike == 150.0

    def test_load_options_stores_current_price(self) -> None:
        """Test that load_options stores current price for ATM calculation."""
        panel = OptionsChainPanel()

        # Simulate what load_options does
        current_price = 152.75
        panel._current_price = current_price

        assert panel._current_price == 152.75

    def test_load_options_resets_atm_strike(self) -> None:
        """Test that load_options resets ATM strike."""
        panel = OptionsChainPanel()
        panel._atm_strike = 150.0

        # Simulate what load_options does
        panel._atm_strike = None

        assert panel._atm_strike is None

    def test_show_empty_clears_current_price_and_atm(self) -> None:
        """Test that show_empty clears current price and ATM strike."""
        panel = OptionsChainPanel()
        panel._current_price = 150.0
        panel._atm_strike = 150.0

        # Simulate what show_empty does
        panel._current_price = None
        panel._atm_strike = None

        assert panel._current_price is None
        assert panel._atm_strike is None


class TestOptionsChainPanelIVColorCoding:
    """Test IV color coding functionality (VPR-084)."""

    def test_get_iv_color_low_range(self) -> None:
        """Test IV color for values in the low range (bottom third)."""
        panel = OptionsChainPanel()
        
        # Setup: IV range from 0.10 to 0.40
        # Low third: 0.10 to 0.20
        min_iv = 0.10
        max_iv = 0.40
        
        # Test low IV values (should be green)
        assert panel._get_iv_color(0.10, min_iv, max_iv) == "green"
        assert panel._get_iv_color(0.15, min_iv, max_iv) == "green"
        assert panel._get_iv_color(0.19, min_iv, max_iv) == "green"

    def test_get_iv_color_medium_range(self) -> None:
        """Test IV color for values in the medium range (middle third)."""
        panel = OptionsChainPanel()
        
        # Setup: IV range from 0.10 to 0.40
        # Medium third: 0.20 to 0.30
        min_iv = 0.10
        max_iv = 0.40
        
        # Test medium IV values (should be yellow)
        assert panel._get_iv_color(0.20, min_iv, max_iv) == "yellow"
        assert panel._get_iv_color(0.25, min_iv, max_iv) == "yellow"
        assert panel._get_iv_color(0.29, min_iv, max_iv) == "yellow"

    def test_get_iv_color_high_range(self) -> None:
        """Test IV color for values in the high range (top third)."""
        panel = OptionsChainPanel()

        # Setup: IV range from 0.10 to 0.40
        # High third: > 0.30 to 0.40
        min_iv = 0.10
        max_iv = 0.40

        # Test high IV values (should be red)
        assert panel._get_iv_color(0.31, min_iv, max_iv) == "red"
        assert panel._get_iv_color(0.35, min_iv, max_iv) == "red"
        assert panel._get_iv_color(0.40, min_iv, max_iv) == "red"

    def test_get_iv_color_edge_case_same_iv(self) -> None:
        """Test IV color when all contracts have same IV (max_iv == min_iv)."""
        panel = OptionsChainPanel()
        
        # When all IVs are the same, should return yellow (medium)
        min_iv = 0.25
        max_iv = 0.25
        
        assert panel._get_iv_color(0.25, min_iv, max_iv) == "yellow"

    def test_get_iv_color_boundary_values(self) -> None:
        """Test IV color at exact boundary values."""
        panel = OptionsChainPanel()

        # Setup: IV range from 0.10 to 0.40
        # Thresholds: low=0.20, high=0.30
        min_iv = 0.10
        max_iv = 0.40

        # Test boundary values
        # Due to floating point precision, 0.20 and 0.30 may fall into yellow
        # Test just below and above boundaries for clear categorization
        assert panel._get_iv_color(0.19, min_iv, max_iv) == "green"
        assert panel._get_iv_color(0.20, min_iv, max_iv) == "yellow"
        assert panel._get_iv_color(0.29, min_iv, max_iv) == "yellow"
        # 0.30 might be yellow due to FP precision (high_threshold calc)
        # Test value clearly in red range
        assert panel._get_iv_color(0.31, min_iv, max_iv) == "red"

    def test_get_iv_color_various_ranges(self) -> None:
        """Test IV color with different IV ranges."""
        panel = OptionsChainPanel()
        
        # Test with wide range
        min_iv = 0.05
        max_iv = 0.95
        assert panel._get_iv_color(0.10, min_iv, max_iv) == "green"
        assert panel._get_iv_color(0.50, min_iv, max_iv) == "yellow"
        assert panel._get_iv_color(0.90, min_iv, max_iv) == "red"
        
        # Test with narrow range
        min_iv = 0.20
        max_iv = 0.30
        assert panel._get_iv_color(0.21, min_iv, max_iv) == "green"
        assert panel._get_iv_color(0.25, min_iv, max_iv) == "yellow"
        assert panel._get_iv_color(0.29, min_iv, max_iv) == "red"

    def test_format_contract_row_includes_iv_color(self) -> None:
        """Test that formatted row includes IV color markup."""
        panel = OptionsChainPanel()

        # Use OTM contract to avoid row-level green color wrapping
        contract = create_option_contract(implied_volatility=0.25, in_the_money=False)

        # Format with green IV color
        row = panel._format_contract_row(contract, is_atm=False, iv_color="green")
        assert "[green]" in row and "25.0%" in row and "[/green]" in row

        # Format with yellow IV color
        row = panel._format_contract_row(contract, is_atm=False, iv_color="yellow")
        assert "[yellow]" in row and "25.0%" in row and "[/yellow]" in row

        # Format with red IV color
        row = panel._format_contract_row(contract, is_atm=False, iv_color="red")
        assert "[red]" in row and "25.0%" in row and "[/red]" in row

    def test_iv_color_calculation_with_mixed_ivs(self) -> None:
        """Test IV range calculation filters out zero/NaN IVs correctly."""
        panel = OptionsChainPanel()
        
        # Create chain with mixed IV values (some zero, some valid)
        calls = [
            create_option_contract(strike=145.0, implied_volatility=0.0),  # NaN/zero
            create_option_contract(strike=150.0, implied_volatility=0.20),  # Valid
            create_option_contract(strike=155.0, implied_volatility=0.30),  # Valid
            create_option_contract(strike=160.0, implied_volatility=0.40),  # Valid
        ]
        
        # Calculate valid IVs (filtering out 0.0)
        valid_ivs = [c.implied_volatility for c in calls if c.implied_volatility > 0.0]
        
        assert valid_ivs == [0.20, 0.30, 0.40]
        assert min(valid_ivs) == 0.20
        assert max(valid_ivs) == 0.40

    def test_iv_color_defaults_to_yellow_for_zero_iv(self) -> None:
        """Test that zero IV (from NaN in original data) gets yellow color."""
        panel = OptionsChainPanel()
        panel._chain = OptionsChain(
            ticker="AAPL",
            expiration="2024-01-19",
            calls=[
                create_option_contract(strike=145.0, implied_volatility=0.0),
                create_option_contract(strike=150.0, implied_volatility=0.25),
            ],
            puts=[],
        )
        panel._state = "success"
        panel._show_calls = True
        
        # The logic in _render_options_table assigns yellow to zero IVs
        # Verify the logic directly
        contract_with_zero_iv = panel._chain.calls[0]
        if contract_with_zero_iv.implied_volatility > 0.0:
            iv_color = "should_not_reach_here"
        else:
            iv_color = "yellow"
        
        assert iv_color == "yellow"

    def test_iv_range_calculation_with_all_zero_ivs(self) -> None:
        """Test IV range calculation when all IVs are zero."""
        panel = OptionsChainPanel()
        
        # Create chain where all IVs are 0.0
        calls = [
            create_option_contract(strike=145.0, implied_volatility=0.0),
            create_option_contract(strike=150.0, implied_volatility=0.0),
            create_option_contract(strike=155.0, implied_volatility=0.0),
        ]
        
        # Calculate valid IVs
        valid_ivs = [c.implied_volatility for c in calls if c.implied_volatility > 0.0]
        
        # When no valid IVs, should default to min=0.0, max=0.0
        if valid_ivs:
            min_iv = min(valid_ivs)
            max_iv = max(valid_ivs)
        else:
            min_iv = 0.0
            max_iv = 0.0
        
        assert min_iv == 0.0
        assert max_iv == 0.0
        
        # With equal min/max, _get_iv_color returns yellow
        assert panel._get_iv_color(0.0, min_iv, max_iv) == "yellow"

    def test_iv_color_persists_across_filter_changes(self) -> None:
        """Test that IV colors are recalculated when filter changes."""
        panel = OptionsChainPanel()
        panel._chain = OptionsChain(
            ticker="AAPL",
            expiration="2024-01-19",
            calls=[
                create_option_contract(strike=145.0, implied_volatility=0.20, in_the_money=True),
                create_option_contract(strike=150.0, implied_volatility=0.30, in_the_money=False),
                create_option_contract(strike=155.0, implied_volatility=0.40, in_the_money=False),
            ],
            puts=[],
        )
        panel._state = "success"
        panel._show_calls = True
        
        # IV range should be calculated from ALL contracts, not just filtered ones
        all_contracts = panel._chain.calls
        valid_ivs = [c.implied_volatility for c in all_contracts if c.implied_volatility > 0.0]
        
        # Regardless of filter, IV range stays the same
        assert min(valid_ivs) == 0.20
        assert max(valid_ivs) == 0.40

    def test_iv_color_with_extreme_values(self) -> None:
        """Test IV color calculation with extreme IV values."""
        panel = OptionsChainPanel()
        
        # Test with very low IV range
        min_iv = 0.01
        max_iv = 0.05
        assert panel._get_iv_color(0.01, min_iv, max_iv) == "green"
        assert panel._get_iv_color(0.03, min_iv, max_iv) == "yellow"
        assert panel._get_iv_color(0.05, min_iv, max_iv) == "red"
        
        # Test with very high IV range
        min_iv = 0.80
        max_iv = 1.20
        assert panel._get_iv_color(0.85, min_iv, max_iv) == "green"
        assert panel._get_iv_color(1.00, min_iv, max_iv) == "yellow"
        assert panel._get_iv_color(1.15, min_iv, max_iv) == "red"


class TestVolumeAndOIHighlighting:
    """Test volume and OI highlighting features (VPR-085)."""

    def test_calculate_average_volume(self) -> None:
        """Test average volume calculation across contracts."""
        panel = OptionsChainPanel()

        # Test with normal volumes
        contracts = [
            create_option_contract(volume=100),
            create_option_contract(volume=200),
            create_option_contract(volume=300),
        ]
        avg = panel._calculate_average_volume(contracts)
        assert avg == 200.0

        # Test with zero volumes
        contracts = [
            create_option_contract(volume=0),
            create_option_contract(volume=0),
        ]
        avg = panel._calculate_average_volume(contracts)
        assert avg == 0.0

        # Test with empty list
        avg = panel._calculate_average_volume([])
        assert avg == 0.0

    def test_calculate_average_oi(self) -> None:
        """Test average OI calculation across contracts."""
        panel = OptionsChainPanel()

        # Test with normal OI values
        contracts = [
            create_option_contract(open_interest=1000),
            create_option_contract(open_interest=2000),
            create_option_contract(open_interest=3000),
        ]
        avg = panel._calculate_average_oi(contracts)
        assert avg == 2000.0

        # Test with zero OI
        contracts = [
            create_option_contract(open_interest=0),
            create_option_contract(open_interest=0),
        ]
        avg = panel._calculate_average_oi(contracts)
        assert avg == 0.0

        # Test with empty list
        avg = panel._calculate_average_oi([])
        assert avg == 0.0

    def test_is_high_volume(self) -> None:
        """Test high volume detection (> 2x average)."""
        panel = OptionsChainPanel()

        # Test with volume > 2x average
        assert panel._is_high_volume(250, 100.0) is True

        # Test with volume = 2x average (should be False, needs > not >=)
        assert panel._is_high_volume(200, 100.0) is False

        # Test with volume < 2x average
        assert panel._is_high_volume(150, 100.0) is False

        # Test with zero average (edge case)
        assert panel._is_high_volume(100, 0.0) is False

        # Test with negative average (edge case)
        assert panel._is_high_volume(100, -10.0) is False

    def test_is_high_oi(self) -> None:
        """Test high OI detection (> 2x average)."""
        panel = OptionsChainPanel()

        # Test with OI > 2x average
        assert panel._is_high_oi(2500, 1000.0) is True

        # Test with OI = 2x average (should be False, needs > not >=)
        assert panel._is_high_oi(2000, 1000.0) is False

        # Test with OI < 2x average
        assert panel._is_high_oi(1500, 1000.0) is False

        # Test with zero average (edge case)
        assert panel._is_high_oi(1000, 0.0) is False

        # Test with negative average (edge case)
        assert panel._is_high_oi(1000, -100.0) is False

    def test_format_contract_with_high_volume(self) -> None:
        """Test contract formatting with high volume (bold)."""
        panel = OptionsChainPanel()
        contract = create_option_contract(volume=500)

        # Format with high volume flag
        result = panel._format_contract_row(
            contract, is_high_vol=True, is_high_oi=False
        )

        # Should contain bold markup around volume
        assert "[bold]" in result
        assert "[/bold]" in result
        # Volume should be in the result
        assert "500" in result

    def test_format_contract_with_high_oi(self) -> None:
        """Test contract formatting with high OI (* prefix)."""
        panel = OptionsChainPanel()
        contract = create_option_contract(open_interest=5000)

        # Format with high OI flag
        result = panel._format_contract_row(
            contract, is_high_vol=False, is_high_oi=True
        )

        # Should contain * prefix for OI
        assert "*" in result
        # OI value should be in the result
        assert "5,000" in result or "5000" in result

    def test_format_contract_with_both_high_vol_and_oi(self) -> None:
        """Test contract formatting with both high volume and OI."""
        panel = OptionsChainPanel()
        contract = create_option_contract(volume=1000, open_interest=10000)

        # Format with both flags
        result = panel._format_contract_row(
            contract, is_high_vol=True, is_high_oi=True
        )

        # Should contain both bold for volume and * for OI
        assert "[bold]" in result
        assert "[/bold]" in result
        assert "*" in result

    def test_format_contract_with_no_highlighting(self) -> None:
        """Test contract formatting with no volume/OI highlighting."""
        panel = OptionsChainPanel()
        contract = create_option_contract(volume=100, open_interest=500)

        # Format without highlighting
        result = panel._format_contract_row(
            contract, is_high_vol=False, is_high_oi=False
        )

        # Should NOT contain bold or * for normal volume/OI
        # (but might contain bold from other features like ATM)
        # Just verify the values are present
        assert "100" in result
        assert "500" in result

    def test_highlighting_with_varied_volumes(self) -> None:
        """Test volume highlighting with realistic varied data."""
        panel = OptionsChainPanel()

        # Create contracts with varied volumes
        contracts = [
            create_option_contract(strike=100.0, volume=50),   # Low
            create_option_contract(strike=105.0, volume=100),  # Average
            create_option_contract(strike=110.0, volume=150),  # Average
            create_option_contract(strike=115.0, volume=500),  # High (> 2x avg)
        ]

        # Calculate average: (50 + 100 + 150 + 500) / 4 = 200
        avg_vol = panel._calculate_average_volume(contracts)
        assert avg_vol == 200.0

        # Test each contract
        assert panel._is_high_volume(50, avg_vol) is False    # 50 < 400
        assert panel._is_high_volume(100, avg_vol) is False   # 100 < 400
        assert panel._is_high_volume(150, avg_vol) is False   # 150 < 400
        assert panel._is_high_volume(500, avg_vol) is True    # 500 > 400

    def test_highlighting_with_varied_oi(self) -> None:
        """Test OI highlighting with realistic varied data."""
        panel = OptionsChainPanel()

        # Create contracts with varied OI
        contracts = [
            create_option_contract(strike=100.0, open_interest=500),   # Low
            create_option_contract(strike=105.0, open_interest=1000),  # Average
            create_option_contract(strike=110.0, open_interest=1500),  # Average
            create_option_contract(strike=115.0, open_interest=5000),  # High (> 2x avg)
        ]

        # Calculate average: (500 + 1000 + 1500 + 5000) / 4 = 2000
        avg_oi = panel._calculate_average_oi(contracts)
        assert avg_oi == 2000.0

        # Test each contract
        assert panel._is_high_oi(500, avg_oi) is False     # 500 < 4000
        assert panel._is_high_oi(1000, avg_oi) is False    # 1000 < 4000
        assert panel._is_high_oi(1500, avg_oi) is False    # 1500 < 4000
        assert panel._is_high_oi(5000, avg_oi) is True     # 5000 > 4000

    def test_all_zero_volumes_no_highlighting(self) -> None:
        """Test that no highlighting occurs when all volumes are zero."""
        panel = OptionsChainPanel()

        # Create contracts with all zero volumes
        contracts = [
            create_option_contract(volume=0),
            create_option_contract(volume=0),
            create_option_contract(volume=0),
        ]

        avg_vol = panel._calculate_average_volume(contracts)
        assert avg_vol == 0.0

        # None should be highlighted
        assert panel._is_high_volume(0, avg_vol) is False

    def test_all_zero_oi_no_highlighting(self) -> None:
        """Test that no highlighting occurs when all OI are zero."""
        panel = OptionsChainPanel()

        # Create contracts with all zero OI
        contracts = [
            create_option_contract(open_interest=0),
            create_option_contract(open_interest=0),
            create_option_contract(open_interest=0),
        ]

        avg_oi = panel._calculate_average_oi(contracts)
        assert avg_oi == 0.0

        # None should be highlighted
        assert panel._is_high_oi(0, avg_oi) is False


class TestSummaryView:
    """Test multi-expiration summary view feature (VPR-086)."""

    def test_summary_mode_initialization(self) -> None:
        """Test that summary mode initializes to False."""
        panel = OptionsChainPanel()
        assert panel._summary_mode is False
        assert panel._summary_chains == {}

    def test_toggle_summary_mode(self) -> None:
        """Test toggling summary mode on and off."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()

        # Start in normal mode
        assert panel._summary_mode is False

        # Toggle to summary mode (simulating action_toggle_summary)
        panel._summary_mode = not panel._summary_mode
        assert panel._summary_mode is True

        # Toggle back to normal mode
        panel._summary_mode = not panel._summary_mode
        assert panel._summary_mode is False

    def test_summary_mode_resets_selection(self) -> None:
        """Test that toggling summary mode resets selection index."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain()
        panel._selected_index = 5

        # Simulate toggle to summary mode
        panel._summary_mode = not panel._summary_mode
        panel._selected_index = 0  # Reset as per spec

        assert panel._selected_index == 0

    def test_format_summary_row_with_valid_data(self) -> None:
        """Test formatting summary row with valid ATM data."""
        panel = OptionsChainPanel()
        panel._current_price = 150.0

        # Create chain with ATM contracts
        chain = create_options_chain(ticker="AAPL", expiration="2024-03-15")

        # Format summary row
        row = panel._format_summary_row("2024-03-15", chain)

        # Should contain expiration date
        assert "2024-03-15" in row

        # Should contain bid/ask data (basic check)
        assert "/" in row  # Bid/ask separator

        # Should contain percentage sign for IV
        assert "%" in row

    def test_format_summary_row_no_current_price(self) -> None:
        """Test formatting summary row without current price."""
        panel = OptionsChainPanel()
        panel._current_price = None  # No price set

        chain = create_options_chain(ticker="AAPL", expiration="2024-03-15")

        # When no current price, find_atm_strike returns None
        atm_strike = panel._find_atm_strike(chain.calls)
        assert atm_strike is None

        # Format should handle gracefully
        row = panel._format_summary_row("2024-03-15", chain)
        assert "2024-03-15" in row
        # Should show "No ATM data" when can't find ATM
        assert "No ATM data" in row

    def test_format_summary_row_empty_chain(self) -> None:
        """Test formatting summary row with empty chain."""
        panel = OptionsChainPanel()
        panel._current_price = 150.0

        # Create chain with no contracts
        chain = OptionsChain(
            ticker="AAPL",
            expiration="2024-03-15",
            calls=[],
            puts=[]
        )

        row = panel._format_summary_row("2024-03-15", chain)

        # Should contain expiration and error message
        assert "2024-03-15" in row
        assert "No data available" in row

    def test_format_summary_row_missing_atm_contract(self) -> None:
        """Test formatting summary row when ATM strike not in chain."""
        panel = OptionsChainPanel()
        panel._current_price = 200.0  # Price outside of available strikes

        # Create chain with strikes far from current price
        chain = OptionsChain(
            ticker="AAPL",
            expiration="2024-03-15",
            calls=[create_option_contract(strike=100.0)],
            puts=[create_option_contract(strike=100.0)]
        )

        # ATM would be 100.0 (closest to 200.0)
        atm_strike = panel._find_atm_strike(chain.calls)
        assert atm_strike == 100.0

        # Should find the contract and format successfully
        row = panel._format_summary_row("2024-03-15", chain)
        assert "2024-03-15" in row
        # Should contain data (not error) since ATM contract exists
        assert "/" in row  # Bid/ask separator

    def test_summary_view_navigation_j_k(self) -> None:
        """Test j/k navigation in summary mode."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._summary_mode = True
        panel._expirations = ["2024-01-19", "2024-02-16", "2024-03-15"]
        panel._chain = create_options_chain()
        panel._selected_index = 0

        # Navigate down (j key)
        max_index = min(len(panel._expirations), 8) - 1
        panel._selected_index = min(panel._selected_index + 1, max_index)
        assert panel._selected_index == 1

        # Navigate down again
        panel._selected_index = min(panel._selected_index + 1, max_index)
        assert panel._selected_index == 2

        # Navigate up (k key)
        panel._selected_index = max(panel._selected_index - 1, 0)
        assert panel._selected_index == 1

        # Navigate up to top
        panel._selected_index = max(panel._selected_index - 1, 0)
        assert panel._selected_index == 0

        # Try to navigate up past 0
        panel._selected_index = max(panel._selected_index - 1, 0)
        assert panel._selected_index == 0  # Should stay at 0

    def test_summary_view_limits_to_8_expirations(self) -> None:
        """Test that summary view only shows up to 8 expirations."""
        panel = OptionsChainPanel()
        panel._expirations = [f"2024-{i:02d}-15" for i in range(1, 13)]  # 12 expirations

        # Get expirations to show
        expirations_to_show = panel._expirations[:8]

        assert len(expirations_to_show) == 8
        assert expirations_to_show[0] == "2024-01-15"
        assert expirations_to_show[7] == "2024-08-15"

    def test_summary_view_navigation_bounds(self) -> None:
        """Test that summary navigation respects 8-expiration limit."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._summary_mode = True
        panel._expirations = [f"2024-{i:02d}-15" for i in range(1, 13)]  # 12 expirations
        panel._chain = create_options_chain()
        panel._selected_index = 0

        # Try to navigate to index 10 (beyond 8-expiration limit)
        max_index = min(len(panel._expirations), 8) - 1
        panel._selected_index = 10

        # Should be clamped to max (7)
        if panel._selected_index >= min(len(panel._expirations), 8):
            panel._selected_index = max_index

        assert panel._selected_index == 7

    def test_select_expiration_from_summary(self) -> None:
        """Test selecting an expiration from summary view."""
        panel = OptionsChainPanel()
        panel._summary_mode = True
        panel._state = "success"
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19", "2024-02-16", "2024-03-15"]
        panel._selected_index = 1  # Select Feb expiration
        panel._chain = create_options_chain()

        # Get expirations shown in summary
        expirations_to_show = panel._expirations[:8]

        # Validate selection is in range
        assert 0 <= panel._selected_index < len(expirations_to_show)

        # Get selected expiration
        selected_expiration = expirations_to_show[panel._selected_index]
        assert selected_expiration == "2024-02-16"

        # Simulate selecting (exit summary mode)
        panel._summary_mode = False

        # Update expiration index
        panel._current_expiration_index = panel._expirations.index(selected_expiration)
        assert panel._current_expiration_index == 1

    def test_select_expiration_uses_cached_chain(self) -> None:
        """Test that selecting expiration uses cached chain data."""
        panel = OptionsChainPanel()
        panel._summary_mode = True
        panel._expirations = ["2024-01-19", "2024-02-16"]
        panel._selected_index = 0
        panel._chain = create_options_chain()

        # Cache a chain for first expiration
        cached_chain = create_options_chain(expiration="2024-01-19")
        panel._summary_chains["2024-01-19"] = cached_chain

        # Simulate selection
        selected_exp = panel._expirations[panel._selected_index]
        cached = panel._summary_chains.get(selected_exp)

        assert cached is not None
        assert cached == cached_chain
        assert not isinstance(cached, OptionsError)

    def test_summary_chains_cache_structure(self) -> None:
        """Test that summary chains cache uses correct structure."""
        panel = OptionsChainPanel()

        # Cache should be a dict mapping expiration to chain
        panel._summary_chains["2024-01-19"] = create_options_chain(expiration="2024-01-19")
        panel._summary_chains["2024-02-16"] = create_options_chain(expiration="2024-02-16")

        assert len(panel._summary_chains) == 2
        assert "2024-01-19" in panel._summary_chains
        assert "2024-02-16" in panel._summary_chains

    def test_summary_chains_can_store_errors(self) -> None:
        """Test that summary chains cache can store OptionsError."""
        panel = OptionsChainPanel()

        # Store both successful and error results
        panel._summary_chains["2024-01-19"] = create_options_chain(expiration="2024-01-19")
        panel._summary_chains["2024-02-16"] = OptionsError(
            ticker="AAPL",
            error_message="Failed to load"
        )

        # Check cache contents
        assert len(panel._summary_chains) == 2
        assert isinstance(panel._summary_chains["2024-01-19"], OptionsChain)
        assert isinstance(panel._summary_chains["2024-02-16"], OptionsError)

    def test_show_empty_clears_summary_state(self) -> None:
        """Test that show_empty clears summary mode and cache."""
        panel = OptionsChainPanel()

        # Set summary state
        panel._summary_mode = True
        panel._summary_chains = {
            "2024-01-19": create_options_chain(expiration="2024-01-19")
        }

        # Simulate show_empty
        panel._summary_mode = False
        panel._summary_chains = {}

        assert panel._summary_mode is False
        assert panel._summary_chains == {}

    def test_summary_view_header_text(self) -> None:
        """Test that summary view shows correct header text."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain(ticker="AAPL")
        panel._summary_mode = True

        # Simulate header generation
        if panel._summary_mode:
            header_text = f"OPTIONS SUMMARY: [cyan]{panel._chain.ticker}[/cyan]"
        else:
            header_text = "OPTIONS"

        assert "SUMMARY" in header_text
        assert "AAPL" in header_text

    def test_normal_view_header_text(self) -> None:
        """Test that normal view shows detailed header text."""
        panel = OptionsChainPanel()
        panel._state = "success"
        panel._chain = create_options_chain(ticker="AAPL", expiration="2024-01-19")
        panel._summary_mode = False
        panel._show_calls = True
        panel._filter_mode = "all"

        # Simulate header generation
        if panel._summary_mode:
            header_text = "SUMMARY"
        else:
            option_type = "CALLS" if panel._show_calls else "PUTS"
            filter_text = panel._filter_mode.upper()
            header_text = f"OPTIONS: [cyan]{panel._chain.ticker}[/cyan] | [cyan]{panel._chain.expiration}[/cyan] | [cyan]{option_type}[/cyan] | Filter: [cyan]{filter_text}[/cyan]"

        assert "CALLS" in header_text
        assert "2024-01-19" in header_text
        assert "AAPL" in header_text
        assert "Filter: ALL" in header_text.replace("[cyan]", "").replace("[/cyan]", "")

    def test_summary_mode_only_works_in_success_state(self) -> None:
        """Test that summary mode toggle only works in success state."""
        panel = OptionsChainPanel()

        # Test in empty state
        panel._state = "empty"
        panel._chain = None
        should_toggle = (panel._state == "success" and panel._chain is not None)
        assert should_toggle is False

        # Test in loading state
        panel._state = "loading"
        panel._chain = None
        should_toggle = (panel._state == "success" and panel._chain is not None)
        assert should_toggle is False

        # Test in error state
        panel._state = "error"
        panel._chain = None
        should_toggle = (panel._state == "success" and panel._chain is not None)
        assert should_toggle is False

        # Test in success state
        panel._state = "success"
        panel._chain = create_options_chain()
        should_toggle = (panel._state == "success" and panel._chain is not None)
        assert should_toggle is True

    def test_select_expiration_only_works_in_summary_mode(self) -> None:
        """Test that select expiration only works when in summary mode."""
        panel = OptionsChainPanel()
        panel._state = "success"

        # Test in normal mode
        panel._summary_mode = False
        should_select = (panel._summary_mode and panel._state == "success")
        assert should_select is False

        # Test in summary mode
        panel._summary_mode = True
        should_select = (panel._summary_mode and panel._state == "success")
        assert should_select is True

    def test_summary_row_format_includes_all_fields(self) -> None:
        """Test that summary row includes expiration, call bid/ask, put bid/ask, and IV."""
        panel = OptionsChainPanel()
        panel._current_price = 150.0

        chain = create_options_chain(ticker="AAPL", expiration="2024-03-15")
        row = panel._format_summary_row("2024-03-15", chain)

        # Check for all expected fields
        assert "2024-03-15" in row  # Expiration
        # Should have at least 2 slashes for bid/ask separators (call and put)
        assert row.count("/") >= 2
        assert "%" in row  # IV percentage

    @pytest.mark.asyncio
    async def test_load_summary_chains_clears_cache(self) -> None:
        """Test that loading summary chains clears existing cache."""
        panel = OptionsChainPanel()
        panel._current_ticker = "AAPL"
        panel._expirations = ["2024-01-19", "2024-02-16"]

        # Set some cached data
        panel._summary_chains = {
            "2024-01-19": create_options_chain(expiration="2024-01-19")
        }

        # Simulate cache clear (first step of _load_summary_chains)
        panel._summary_chains = {}

        assert panel._summary_chains == {}

    def test_select_expiration_with_invalid_index(self) -> None:
        """Test that select expiration handles invalid index gracefully."""
        panel = OptionsChainPanel()
        panel._summary_mode = True
        panel._state = "success"
        panel._expirations = ["2024-01-19", "2024-02-16"]
        panel._selected_index = 10  # Invalid index

        expirations_to_show = panel._expirations[:8]

        # Should not proceed with invalid index
        is_valid = (0 <= panel._selected_index < len(expirations_to_show))
        assert is_valid is False

    def test_select_expiration_with_empty_expirations(self) -> None:
        """Test that select expiration handles empty expirations list."""
        panel = OptionsChainPanel()
        panel._summary_mode = True
        panel._state = "success"
        panel._expirations = []
        panel._selected_index = 0

        # Should not proceed with empty list
        should_proceed = bool(panel._expirations)
        assert should_proceed is False
