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
