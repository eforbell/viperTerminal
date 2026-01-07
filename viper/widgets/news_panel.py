"""News panel widget for displaying news headlines for a ticker."""

import webbrowser
from datetime import datetime
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator

from viper.services.news import NewsError, NewsItem, NewsResult, fetch_news


class NewsPanel(Widget):
    """Panel for displaying news headlines with navigation support."""

    # Custom event for browser open notification
    class BrowserOpening(Message):
        """Event emitted when opening a URL in browser."""

        def __init__(self, url: str) -> None:
            """Initialize with URL being opened."""
            self.url = url
            super().__init__()

    # Make the panel focusable
    can_focus = True

    # Keyboard bindings for navigation - use priority=True so they work when focused
    BINDINGS = [
        Binding("j", "navigate_down", "Next", show=False, priority=True),
        Binding("k", "navigate_up", "Previous", show=False, priority=True),
        Binding("enter", "open_in_browser", "Open", show=False, priority=True),
        Binding("e", "toggle_expand", "Expand", show=False, priority=True),
        Binding("escape", "collapse", "Collapse", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    NewsPanel {
        height: 100%;
        width: 100%;
        padding: 1 2;
    }

    NewsPanel .panel-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    NewsPanel .news-item {
        width: 100%;
        margin-bottom: 1;
        padding: 0 1;
    }

    NewsPanel .news-headline {
        text-style: bold;
        color: $text;
    }

    NewsPanel .news-meta {
        color: #666666;
        text-style: italic;
    }

    NewsPanel .news-summary {
        color: #aaaaaa;
        margin-top: 1;
        padding: 0 1;
    }

    NewsPanel .selected {
        background: #003300;
    }

    NewsPanel .expanded {
        background: #002200;
        padding: 1;
    }

    NewsPanel .empty-state {
        color: #666666;
        text-align: center;
        margin-top: 3;
    }

    NewsPanel .error-state {
        color: #ff0000;
        text-align: center;
        margin-top: 3;
    }

    NewsPanel .loading-container {
        align: center middle;
        height: 100%;
    }

    NewsPanel VerticalScroll {
        height: 100%;
    }
    """

    def __init__(self, max_items: int = 10) -> None:
        """Initialize the news panel.

        Args:
            max_items: Maximum number of news items to display (default: 10).
        """
        super().__init__()
        self._max_items = max_items
        self._state: str = "empty"
        self._current_ticker: Optional[str] = None
        self._news_items: list[NewsItem] = []
        self._selected_index = 0
        self._expanded_index: int | None = None  # Index of expanded item, or None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("NEWS", classes="panel-header")
        yield VerticalScroll(id="news-content")

    async def load_news(self, ticker: str) -> None:
        """Load news for the given ticker.

        Args:
            ticker: The ticker symbol to fetch news for.
        """
        # Update current ticker before fetch
        self._current_ticker = ticker
        self._state = "loading"
        self._selected_index = 0
        self._expanded_index = None  # Reset expansion on new ticker
        self._render_content()

        # Fetch news
        result = await fetch_news(ticker, max_items=self._max_items)

        # Check if ticker changed while fetching
        if self._current_ticker != ticker:
            return

        # Process result
        if isinstance(result, NewsError):
            self._state = "error"
            self._news_items = []
            self._render_content()
        else:
            self._state = "success"
            self._news_items = result
            self._render_content()

    def show_empty(self) -> None:
        """Display empty state when no ticker is selected."""
        self._state = "empty"
        self._current_ticker = None
        self._news_items = []
        self._selected_index = 0
        self._expanded_index = None
        self._render_content()

    def _render_content(self) -> None:
        """Render the appropriate content based on current state."""
        container = self.query_one("#news-content", VerticalScroll)
        container.remove_children()

        if self._state == "empty":
            container.mount(Label("No ticker selected", classes="empty-state"))
        elif self._state == "loading":
            # Create loading container with widgets to mount
            loading_indicator = LoadingIndicator()
            loading_label = Label(
                f"Loading news for {self._current_ticker}..." if self._current_ticker else "Loading..."
            )
            loading_container = Container(
                loading_indicator, loading_label, classes="loading-container"
            )
            container.mount(loading_container)
        elif self._state == "error":
            container.mount(
                Label(f"No news available for {self._current_ticker}", classes="error-state")
            )
        elif self._state == "success":
            self._render_news_items(container)

    def _render_news_items(self, container: VerticalScroll) -> None:
        """Render the news items list with current selection.

        Args:
            container: The container to mount widgets into.
        """
        if not self._news_items:
            container.mount(
                Label(f"No news available for {self._current_ticker}", classes="error-state")
            )
            return

        # Clamp selected index to valid range
        if self._selected_index >= len(self._news_items):
            self._selected_index = len(self._news_items) - 1
        if self._selected_index < 0:
            self._selected_index = 0

        for i, item in enumerate(self._news_items):
            is_selected = i == self._selected_index
            is_expanded = i == self._expanded_index

            # Create news item container with appropriate classes
            classes = "news-item"
            if is_selected:
                classes += " selected"
            if is_expanded:
                classes += " expanded"

            item_container = Container(classes=classes)

            if is_expanded:
                # Expanded view: full headline + summary
                item_container.mount(Label(item.title, classes="news-headline"))
                relative_time = self._format_relative_time(item.published_at)
                meta = f"{item.source} • {relative_time}"
                item_container.mount(Label(meta, classes="news-meta"))

                # Show summary if available
                if item.summary:
                    item_container.mount(Label(item.summary, classes="news-summary"))
                else:
                    item_container.mount(
                        Label("[No summary available - press Enter to open in browser]",
                              classes="news-summary")
                    )
            else:
                # Compact view: truncated headline + meta
                headline = self._truncate_text(item.title, 80)
                relative_time = self._format_relative_time(item.published_at)
                meta = f"{item.source} • {relative_time}"
                item_container.mount(Label(headline, classes="news-headline"))
                item_container.mount(Label(meta, classes="news-meta"))

            container.mount(item_container)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis.

        Args:
            text: The text to truncate.
            max_length: Maximum length of the text.

        Returns:
            Truncated text with ellipsis if needed.
        """
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _format_relative_time(self, published_at: datetime) -> str:
        """Format a datetime as relative time (e.g., '2h ago', '1d ago').

        Args:
            published_at: The datetime to format.

        Returns:
            Formatted relative time string.
        """
        from datetime import timezone

        # Handle timezone-aware datetimes from yfinance
        if published_at.tzinfo is not None:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.now()
        delta = now - published_at

        # Calculate time units
        seconds = int(delta.total_seconds())
        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24

        if days > 0:
            return f"{days}d ago"
        elif hours > 0:
            return f"{hours}h ago"
        elif minutes > 0:
            return f"{minutes}m ago"
        else:
            return "just now"

    def action_navigate_down(self) -> None:
        """Navigate down to the next news item (j key)."""
        if not self._news_items:
            return

        # Move selection down
        self._selected_index = min(self._selected_index + 1, len(self._news_items) - 1)
        self._render_content()

    def action_navigate_up(self) -> None:
        """Navigate up to the previous news item (k key)."""
        if not self._news_items:
            return

        # Move selection up
        self._selected_index = max(self._selected_index - 1, 0)
        self._render_content()

    def get_selected_item(self) -> Optional[NewsItem]:
        """Get the currently selected news item.

        Returns:
            The selected NewsItem, or None if no item is selected.
        """
        if not self._news_items or self._selected_index >= len(self._news_items):
            return None
        return self._news_items[self._selected_index]

    def action_open_in_browser(self) -> None:
        """Open the selected news item in the default browser (Enter key)."""
        item = self.get_selected_item()
        if item and item.url:
            # Post notification event before opening
            self.post_message(self.BrowserOpening(item.url))
            # Open in browser
            webbrowser.open(item.url)

    def action_toggle_expand(self) -> None:
        """Toggle expansion of the selected news item (e key)."""
        if not self._news_items:
            return

        if self._expanded_index == self._selected_index:
            # Collapse if already expanded
            self._expanded_index = None
        else:
            # Expand the selected item
            self._expanded_index = self._selected_index

        self._render_content()

    def action_collapse(self) -> None:
        """Collapse any expanded news item (Escape key)."""
        if self._expanded_index is not None:
            self._expanded_index = None
            self._render_content()

    def is_expanded(self) -> bool:
        """Check if any item is currently expanded.

        Returns:
            True if an item is expanded, False otherwise.
        """
        return self._expanded_index is not None
