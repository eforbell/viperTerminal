"""Options chain panel widget for displaying options data."""

from typing import Literal, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator

from viper.services.options import (
    OptionContract,
    OptionsChain,
    OptionsError,
    fetch_option_chain,
    fetch_option_expirations,
)


class OptionsChainPanel(Widget):
    """Panel for displaying options chain data with navigation support."""

    # Make the panel focusable
    can_focus = True

    # Keyboard bindings for navigation - use priority=True so they work when focused
    BINDINGS = [
        Binding("j", "navigate_down", "Next", show=False, priority=True),
        Binding("k", "navigate_up", "Previous", show=False, priority=True),
        Binding("[", "prev_expiration", "Prev Expiry", show=False, priority=True),
        Binding("]", "next_expiration", "Next Expiry", show=False, priority=True),
        Binding("c", "show_calls", "Calls", show=False, priority=True),
        Binding("p", "show_puts", "Puts", show=False, priority=True),
        Binding("f", "cycle_filter", "Filter", show=False, priority=True),
        Binding("a", "jump_to_atm", "ATM", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    OptionsChainPanel {
        height: 100%;
        width: 100%;
        padding: 1 2;
    }

    OptionsChainPanel .panel-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    OptionsChainPanel .table-header {
        text-style: bold;
        color: #00ffff;
        margin-bottom: 1;
        margin-top: 1;
    }

    OptionsChainPanel .table-row {
        width: 100%;
        margin-bottom: 0;
    }

    OptionsChainPanel .selected {
        background: #003300;
    }

    OptionsChainPanel .itm {
        color: #00ff00;
    }

    OptionsChainPanel .otm {
        color: $text;
    }

    OptionsChainPanel .atm {
        color: #00ffff;
        text-style: bold;
    }

    OptionsChainPanel .empty-state {
        color: #666666;
        text-align: center;
        margin-top: 3;
    }

    OptionsChainPanel .error-state {
        color: #ff0000;
        text-align: center;
        margin-top: 3;
    }

    OptionsChainPanel .loading-container {
        align: center middle;
        height: 100%;
    }

    OptionsChainPanel VerticalScroll {
        height: 100%;
    }
    """

    def __init__(self) -> None:
        """Initialize the options chain panel."""
        super().__init__()
        self._state: str = "empty"
        self._current_ticker: Optional[str] = None
        self._expirations: list[str] = []
        self._current_expiration_index: int = 0
        self._chain: Optional[OptionsChain] = None
        self._show_calls: bool = True  # True = calls, False = puts
        self._selected_index: int = 0
        self._filter_mode: Literal["all", "itm", "otm"] = "all"
        self._current_price: Optional[float] = None  # Current stock/crypto price
        self._atm_strike: Optional[float] = None  # At-the-money strike price

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("", id="options-header", classes="panel-header", markup=True)
        yield VerticalScroll(id="options-content")

    def on_mount(self) -> None:
        """Initialize content when mounted."""
        self._rebuild_content()

    async def load_options(self, ticker: str, current_price: Optional[float] = None) -> None:
        """Load options for the given ticker.

        Args:
            ticker: The ticker symbol to fetch options for.
            current_price: Optional current stock/crypto price for ATM calculation.
        """
        # Update current ticker and price before fetch
        self._current_ticker = ticker
        self._current_price = current_price
        self._state = "loading"
        self._selected_index = 0
        self._expirations = []
        self._current_expiration_index = 0
        self._chain = None
        self._show_calls = True
        self._filter_mode = "all"  # Reset filter when loading new ticker
        self._atm_strike = None  # Reset ATM strike
        self._rebuild_content()

        # Fetch available expirations
        expirations_result = await fetch_option_expirations(ticker)

        # Check if ticker changed while fetching
        if self._current_ticker != ticker:
            return

        # Process result
        if isinstance(expirations_result, OptionsError):
            self._state = "error"
            self._rebuild_content()
            return

        # Store expirations and load first chain
        self._expirations = expirations_result
        if self._expirations:
            await self._load_chain(ticker, self._expirations[0])
        else:
            self._state = "error"
            self._rebuild_content()

    async def _load_chain(self, ticker: str, expiration: str) -> None:
        """Load option chain for the given ticker and expiration.

        Args:
            ticker: The ticker symbol.
            expiration: The expiration date in YYYY-MM-DD format.
        """
        self._state = "loading"
        self._rebuild_content()

        # Fetch chain data
        chain_result = await fetch_option_chain(ticker, expiration)

        # Check if ticker changed while fetching
        if self._current_ticker != ticker:
            return

        # Process result
        if isinstance(chain_result, OptionsError):
            self._state = "error"
            self._rebuild_content()
        else:
            self._state = "success"
            self._chain = chain_result
            self._selected_index = 0  # Reset selection on new chain
            self._rebuild_content()

    def show_empty(self) -> None:
        """Display empty state when no ticker is selected."""
        self._state = "empty"
        self._current_ticker = None
        self._expirations = []
        self._current_expiration_index = 0
        self._chain = None
        self._selected_index = 0
        self._show_calls = True
        self._filter_mode = "all"
        self._current_price = None
        self._atm_strike = None
        self._rebuild_content()

    def _find_atm_strike(self, contracts: list[OptionContract]) -> Optional[float]:
        """Find the at-the-money (ATM) strike price.

        The ATM strike is the strike closest to the current stock/crypto price.

        Args:
            contracts: List of option contracts to search.

        Returns:
            The ATM strike price, or None if no current price or no contracts.
        """
        if not self._current_price or not contracts:
            return None

        # Find strike with minimum distance to current price
        current_price = self._current_price  # Type narrowing for mypy
        atm_strike = min(contracts, key=lambda c: abs(c.strike - current_price))
        return atm_strike.strike

    def _rebuild_content(self) -> None:
        """Render the appropriate content based on current state."""
        # Update header
        header = self.query_one("#options-header", Label)
        if self._state == "success" and self._chain:
            option_type = "CALLS" if self._show_calls else "PUTS"
            filter_text = self._filter_mode.upper()
            header_text = f"OPTIONS: [cyan]{self._chain.ticker}[/cyan] | [cyan]{self._chain.expiration}[/cyan] | [cyan]{option_type}[/cyan] | Filter: [cyan]{filter_text}[/cyan]"
            header.update(header_text)
        else:
            header.update("OPTIONS")

        # Update content
        container = self.query_one("#options-content", VerticalScroll)
        container.remove_children()

        if self._state == "empty":
            container.mount(Label("No ticker selected", classes="empty-state"))
        elif self._state == "loading":
            # Create loading container with widgets to mount
            loading_indicator = LoadingIndicator()
            loading_label = Label(
                f"Loading options for {self._current_ticker}..."
                if self._current_ticker
                else "Loading..."
            )
            loading_container = Container(
                loading_indicator, loading_label, classes="loading-container"
            )
            container.mount(loading_container)
        elif self._state == "error":
            container.mount(
                Label(
                    f"No options available for {self._current_ticker}",
                    classes="error-state",
                )
            )
        elif self._state == "success":
            self._render_options_table(container)

    def _render_options_table(self, container: VerticalScroll) -> None:
        """Render the options table with current selection.

        Args:
            container: The container to mount widgets into.
        """
        if not self._chain:
            return

        # Get current contracts list (calls or puts)
        all_contracts = self._chain.calls if self._show_calls else self._chain.puts

        if not all_contracts:
            container.mount(
                Label(
                    f"No {'calls' if self._show_calls else 'puts'} available",
                    classes="error-state",
                )
            )
            return

        # Apply filter
        contracts = self._apply_filter(all_contracts)

        # Handle empty filter results
        if not contracts:
            container.mount(
                Label(
                    "No contracts match filter",
                    classes="error-state",
                )
            )
            return

        # Calculate ATM strike from all contracts (not filtered)
        self._atm_strike = self._find_atm_strike(all_contracts)

        # Clamp selected index to valid range
        if self._selected_index >= len(contracts):
            self._selected_index = len(contracts) - 1
        if self._selected_index < 0:
            self._selected_index = 0

        # Render table header
        header_text = "[cyan]Strike    Bid      Ask      Last     Vol      OI       IV     ITM[/cyan]"
        container.mount(Label(header_text, classes="table-header", markup=True))

        # Render table rows
        for i, contract in enumerate(contracts):
            is_selected = i == self._selected_index
            is_atm = self._atm_strike is not None and contract.strike == self._atm_strike

            # Format row data
            row_text = self._format_contract_row(contract, is_atm=is_atm)

            # Create row container with appropriate classes
            classes = "table-row"
            if is_selected:
                classes += " selected"
            if is_atm:
                classes += " atm"

            row_label = Label(row_text, classes=classes, markup=True)
            container.mount(row_label)

    def _apply_filter(self, contracts: list[OptionContract]) -> list[OptionContract]:
        """Apply the current filter mode to the list of contracts.

        Args:
            contracts: The full list of contracts to filter.

        Returns:
            Filtered list of contracts based on current filter mode.
        """
        if self._filter_mode == "all":
            return contracts
        elif self._filter_mode == "itm":
            return [c for c in contracts if c.in_the_money]
        elif self._filter_mode == "otm":
            return [c for c in contracts if not c.in_the_money]
        else:
            return contracts

    def _format_contract_row(self, contract: OptionContract, is_atm: bool = False) -> str:
        """Format an option contract as a table row.

        Args:
            contract: The option contract to format.
            is_atm: Whether this is the at-the-money strike.

        Returns:
            Formatted row string with Rich markup.
        """
        # Format strike (right-aligned in 8 chars)
        strike_str = f"{contract.strike:>8.2f}"

        # Format prices (right-aligned in 8 chars)
        bid_str = f"{contract.bid:>8.2f}"
        ask_str = f"{contract.ask:>8.2f}"
        last_str = f"{contract.last_price:>8.2f}"

        # Format volume and OI (right-aligned in 8 chars)
        vol_str = f"{contract.volume:>8,d}"
        oi_str = f"{contract.open_interest:>8,d}"

        # Format IV (right-aligned in 6 chars, percentage)
        iv_pct = contract.implied_volatility * 100
        iv_str = f"{iv_pct:>6.1f}%"

        # Format ITM indicator (centered in 4 chars)
        itm_str = " Y  " if contract.in_the_money else " N  "

        # Build the row string
        row = f"{strike_str} {bid_str} {ask_str} {last_str} {vol_str} {oi_str} {iv_str} {itm_str}"

        # Apply color based on ATM or ITM status
        if is_atm:
            # ATM strikes get cyan color (handled by CSS class)
            return row
        elif contract.in_the_money:
            # ITM contracts get green color
            return f"[green]{row}[/green]"
        else:
            # OTM contracts use default color
            return row

    def action_navigate_down(self) -> None:
        """Navigate down to the next option contract (j key)."""
        if self._state != "success" or not self._chain:
            return

        all_contracts = self._chain.calls if self._show_calls else self._chain.puts
        contracts = self._apply_filter(all_contracts)
        if not contracts:
            return

        # Move selection down
        self._selected_index = min(self._selected_index + 1, len(contracts) - 1)
        self._rebuild_content()

    def action_navigate_up(self) -> None:
        """Navigate up to the previous option contract (k key)."""
        if self._state != "success" or not self._chain:
            return

        all_contracts = self._chain.calls if self._show_calls else self._chain.puts
        contracts = self._apply_filter(all_contracts)
        if not contracts:
            return

        # Move selection up
        self._selected_index = max(self._selected_index - 1, 0)
        self._rebuild_content()

    def action_prev_expiration(self) -> None:
        """Navigate to the previous expiration date ([ key)."""
        if not self._current_ticker or not self._expirations:
            return

        # Move to previous expiration with wrap-around
        self._current_expiration_index = (
            self._current_expiration_index - 1
        ) % len(self._expirations)

        # Load the new chain
        expiration = self._expirations[self._current_expiration_index]
        self.run_worker(self._load_chain(self._current_ticker, expiration))

    def action_next_expiration(self) -> None:
        """Navigate to the next expiration date (] key)."""
        if not self._current_ticker or not self._expirations:
            return

        # Move to next expiration with wrap-around
        self._current_expiration_index = (
            self._current_expiration_index + 1
        ) % len(self._expirations)

        # Load the new chain
        expiration = self._expirations[self._current_expiration_index]
        self.run_worker(self._load_chain(self._current_ticker, expiration))

    def action_show_calls(self) -> None:
        """Switch to calls view (c key)."""
        if self._state != "success" or not self._chain:
            return

        # Only rebuild if we're not already showing calls
        if not self._show_calls:
            self._show_calls = True
            self._selected_index = 0  # Reset selection when switching
            self._rebuild_content()

    def action_show_puts(self) -> None:
        """Switch to puts view (p key)."""
        if self._state != "success" or not self._chain:
            return

        # Only rebuild if we're not already showing puts
        if self._show_calls:
            self._show_calls = False
            self._selected_index = 0  # Reset selection when switching
            self._rebuild_content()

    def action_cycle_filter(self) -> None:
        """Cycle through filter modes: all -> itm -> otm -> all (f key)."""
        if self._state != "success" or not self._chain:
            return

        # Cycle filter mode
        if self._filter_mode == "all":
            self._filter_mode = "itm"
        elif self._filter_mode == "itm":
            self._filter_mode = "otm"
        else:
            self._filter_mode = "all"

        # Reset selection when filter changes
        self._selected_index = 0
        self._rebuild_content()

    def action_jump_to_atm(self) -> None:
        """Jump to the at-the-money (ATM) strike (a key)."""
        if self._state != "success" or not self._chain:
            return

        # Check if we have a current price to calculate ATM
        if not self._current_price or not self._atm_strike:
            return

        # Get current contracts list and apply filter
        all_contracts = self._chain.calls if self._show_calls else self._chain.puts
        contracts = self._apply_filter(all_contracts)

        if not contracts:
            return

        # Find the ATM strike in the filtered list
        atm_index = None
        for i, contract in enumerate(contracts):
            if contract.strike == self._atm_strike:
                atm_index = i
                break

        # If ATM strike found in filtered list, jump to it
        if atm_index is not None:
            self._selected_index = atm_index
            self._rebuild_content()
        # Otherwise, ATM strike is filtered out - do nothing (graceful degradation)
