"""Status bar widget showing connection state and last refresh time."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Static


class StatusBar(Static):
    """Status bar showing connection state and last refresh time."""

    def __init__(self) -> None:
        """Initialize the status bar."""
        super().__init__()
        self._connection_state = "Online"
        self._last_refresh: datetime | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the status bar."""
        with Horizontal():
            yield Label(id="connection-status")
            yield Label(id="last-refresh")

    def on_mount(self) -> None:
        """Update the display when mounted."""
        self._update_display()

    def set_online(self) -> None:
        """Set connection state to online."""
        self._connection_state = "Online"
        self._update_display()

    def set_offline(self) -> None:
        """Set connection state to offline."""
        self._connection_state = "Offline"
        self._update_display()

    def update_last_refresh(self) -> None:
        """Update the last refresh time to now."""
        self._last_refresh = datetime.now()
        self._update_display()

    def _update_display(self) -> None:
        """Update the status bar display."""
        try:
            connection_label = self.query_one("#connection-status", Label)
            refresh_label = self.query_one("#last-refresh", Label)

            # Update connection status
            connection_label.update(f"Status: {self._connection_state}")

            # Update last refresh time
            if self._last_refresh:
                time_str = self._last_refresh.strftime("%H:%M:%S")
                refresh_label.update(f"Last refresh: {time_str}")
            else:
                refresh_label.update("Last refresh: Never")

        except Exception:
            # Widgets not yet mounted - will be updated on_mount
            pass
