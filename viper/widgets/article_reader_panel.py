"""Article reader panel widget for displaying news article content in-app.

This module provides a full-screen reader panel that displays extracted article
content in a clean, readable format. It supports scrolling, loading states, error
handling, and fallback to browser.
"""

import webbrowser
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator, Static

from viper.services.article_reader import ArticleError, ArticleResult, fetch_article


class ArticleReaderPanel(Widget):
    """Full-screen panel for reading article content in terminal.

    Features:
    - Loading state with spinner while fetching
    - Clean article display with title, metadata, and content
    - Scrollable content with vim-style keybindings (j/k, PageUp/Down, Home/End)
    - Error state with fallback hints
    - Retry capability for failed fetches
    - Browser fallback option
    """

    # Custom events
    class CloseRequested(Message):
        """Event emitted when user closes the article reader."""

        pass

    class BrowserOpening(Message):
        """Event emitted when opening article in browser."""

        def __init__(self, url: str) -> None:
            """Initialize with URL being opened."""
            self.url = url
            super().__init__()

    # Make the panel focusable
    can_focus = True

    # Keyboard bindings
    BINDINGS = [
        Binding("escape", "close", "Close", show=False, priority=True),
        Binding("q", "close", "Close", show=False, priority=True),
        Binding("j", "scroll_down", "Scroll Down", show=False, priority=True),
        Binding("k", "scroll_up", "Scroll Up", show=False, priority=True),
        Binding("pagedown", "page_down", "Page Down", show=False, priority=True),
        Binding("pageup", "page_up", "Page Up", show=False, priority=True),
        Binding("home", "scroll_home", "Top", show=False, priority=True),
        Binding("end", "scroll_end", "Bottom", show=False, priority=True),
        Binding("o", "open_in_browser", "Open in Browser", show=False, priority=True),
        Binding("r", "retry_fetch", "Retry", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    ArticleReaderPanel {
        height: 100%;
        width: 100%;
        background: $background;
        padding: 0;
    }

    ArticleReaderPanel #article-container {
        height: 100%;
        width: 100%;
        background: $background;
    }

    ArticleReaderPanel .article-header {
        width: 100%;
        background: $panel;
        padding: 1 2;
        border-bottom: solid $accent;
    }

    ArticleReaderPanel .article-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    ArticleReaderPanel .article-meta {
        color: #666666;
        text-style: italic;
    }

    ArticleReaderPanel .article-content-scroll {
        height: 1fr;
        width: 100%;
        padding: 1 2;
    }

    ArticleReaderPanel .article-content {
        width: 100%;
        color: $text;
    }

    ArticleReaderPanel .article-footer-container {
        width: 100%;
        height: 3;
        background: $panel;
        padding: 1 2;
        border-top: solid $accent;
    }

    ArticleReaderPanel .footer-hint {
        color: #666666;
    }

    ArticleReaderPanel .loading-container {
        align: center middle;
        height: 100%;
    }

    ArticleReaderPanel .loading-message {
        color: $accent;
        text-align: center;
        margin-top: 1;
    }

    ArticleReaderPanel .error-container {
        align: center middle;
        height: 100%;
        padding: 2 4;
    }

    ArticleReaderPanel .error-title {
        color: #ff0000;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    ArticleReaderPanel .error-message {
        color: #ff6666;
        text-align: center;
        margin-bottom: 2;
    }

    ArticleReaderPanel .error-hint {
        color: #666666;
        text-align: center;
    }
    """

    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Initialize the article reader panel."""
        super().__init__(**kwargs)
        self._url: Optional[str] = None
        self._article_result: Optional[ArticleResult] = None
        self._article_error: Optional[ArticleError] = None
        self._scroll_container: Optional[VerticalScroll] = None

    def compose(self) -> ComposeResult:
        """Compose the article reader panel."""
        with Container(id="article-container"):
            # Will be populated dynamically based on state
            yield Container()

    async def show_article(self, url: str, use_cache: bool = True) -> None:
        """Fetch and display article from URL.

        Args:
            url: The article URL to fetch and display
            use_cache: Whether to use cached article (default True)
        """
        self._url = url
        self._article_result = None
        self._article_error = None

        # Show loading state
        self._render_loading_state()

        # Fetch article (retry bypasses cache)
        result = await fetch_article(url, use_cache=use_cache)

        if isinstance(result, ArticleResult):
            self._article_result = result
            self._render_article_content()
        else:
            self._article_error = result
            self._render_error_state()

    def _render_loading_state(self) -> None:
        """Render loading state with spinner."""
        container = self.query_one("#article-container", Container)
        container.remove_children()

        # Create loading container with children
        loading_container = Container(classes="loading-container")
        container.mount(loading_container)

        # Now mount children to the mounted container
        loading_container.mount(LoadingIndicator())
        loading_container.mount(
            Label("Fetching article...", classes="loading-message")
        )

    def _render_article_content(self) -> None:
        """Render article content (title, meta, body, footer)."""
        if not self._article_result:
            return

        article = self._article_result
        container = self.query_one("#article-container", Container)
        container.remove_children()

        # Calculate reading time (avg 200 words per minute)
        reading_time = max(1, article.word_count // 200)

        # Create header container (no ID to avoid duplicates on retry)
        header = Container(classes="article-header")

        # Create content scroll area
        scroll = VerticalScroll(classes="article-content-scroll")
        self._scroll_container = scroll

        # Create footer container
        footer = Container(classes="article-footer-container")

        # Mount all sections to main container first
        container.mount(header)
        container.mount(scroll)
        container.mount(footer)

        # Now populate header
        header.mount(Label(article.title, classes="article-title", markup=True))

        # Build metadata line
        meta_parts = []
        if article.author:
            meta_parts.append(f"By {article.author}")
        if article.date:
            meta_parts.append(article.date)
        meta_parts.append(f"{article.word_count} words")
        meta_parts.append(f"~{reading_time} min read")

        meta_text = " • ".join(meta_parts)
        header.mount(Label(meta_text, classes="article-meta", markup=True))

        # Populate scroll content - article body
        content_lines = article.content.split("\n")
        for line in content_lines:
            if line.strip():  # Non-empty line
                scroll.mount(Static(line, classes="article-content", markup=True))
            else:  # Empty line - add spacing
                scroll.mount(Static(" ", classes="article-content"))

        # Populate footer with keybinding hints
        footer.mount(
            Label(
                "[Esc/q] Close  [j/k] Scroll Line  [PgUp/PgDn] Scroll Page  [o] Open in Browser",
                classes="footer-hint",
                markup=True,
            )
        )

    def _render_error_state(self) -> None:
        """Render error state with helpful message."""
        if not self._article_error:
            return

        error = self._article_error
        container = self.query_one("#article-container", Container)
        container.remove_children()

        # Create error container
        error_container = Container(classes="error-container")
        container.mount(error_container)

        # Now mount children to the mounted container
        error_container.mount(
            Label("Failed to Load Article", classes="error-title", markup=True)
        )
        error_container.mount(
            Label(
                error.error_message,
                classes="error-message",
                markup=True,
            )
        )

        # Show appropriate hints based on error type
        hints = []
        if error.should_retry:
            hints.append("Press [green]r[/green] to retry")
        hints.append("Press [green]o[/green] to open in browser")
        hints.append("Press [green]Esc[/green] to go back")

        for hint in hints:
            error_container.mount(Label(hint, classes="error-hint", markup=True))

    # Action handlers
    def action_close(self) -> None:
        """Close the article reader and return to news list."""
        self.post_message(self.CloseRequested())

    def action_scroll_down(self) -> None:
        """Scroll content down by one line (vim j)."""
        if self._scroll_container:
            self._scroll_container.scroll_relative(y=1)

    def action_scroll_up(self) -> None:
        """Scroll content up by one line (vim k)."""
        if self._scroll_container:
            self._scroll_container.scroll_relative(y=-1)

    def action_page_down(self) -> None:
        """Scroll content down by one page."""
        if self._scroll_container:
            self._scroll_container.scroll_page_down()

    def action_page_up(self) -> None:
        """Scroll content up by one page."""
        if self._scroll_container:
            self._scroll_container.scroll_page_up()

    def action_scroll_home(self) -> None:
        """Scroll to top of content."""
        if self._scroll_container:
            self._scroll_container.scroll_home()

    def action_scroll_end(self) -> None:
        """Scroll to bottom of content."""
        if self._scroll_container:
            self._scroll_container.scroll_end()

    def action_open_in_browser(self) -> None:
        """Open article in browser as fallback."""
        if self._url:
            webbrowser.open(self._url)
            self.post_message(self.BrowserOpening(self._url))

    async def action_retry_fetch(self) -> None:
        """Retry fetching the article (for transient errors).

        Bypasses cache to force a fresh fetch.
        """
        if self._url:
            await self.show_article(self._url, use_cache=False)
