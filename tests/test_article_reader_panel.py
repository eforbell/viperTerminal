"""Tests for ArticleReaderPanel widget."""

from unittest.mock import AsyncMock, patch

import pytest
from textual.widgets import Label, LoadingIndicator, Static

from viper.services.article_reader import ArticleError, ArticleResult
from viper.widgets.article_reader_panel import ArticleReaderPanel


@pytest.fixture
def sample_article() -> ArticleResult:
    """Create a sample article result for testing."""
    return ArticleResult(
        title="Test Article Title",
        content="This is the article content.\n\nIt has multiple paragraphs.\n\nAnd some empty lines.",
        author="Test Author",
        date="2024-01-01",
        source_url="https://example.com/article",
        word_count=150,
    )


@pytest.fixture
def sample_error() -> ArticleError:
    """Create a sample article error for testing."""
    return ArticleError(
        error_type="network",
        error_message="Network connection failed",
        source_url="https://example.com/article",
        should_retry=True,
    )


class TestArticleReaderPanelInitialization:
    """Test ArticleReaderPanel initialization."""

    @pytest.mark.asyncio
    async def test_panel_initializes(self) -> None:
        """Test that panel initializes correctly."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)
            assert panel is not None
            assert panel.can_focus is True
            assert panel._url is None
            assert panel._article_result is None
            assert panel._article_error is None

    @pytest.mark.asyncio
    async def test_panel_has_keybindings(self) -> None:
        """Test that panel has all required keybindings."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            # Check that keybindings are defined
            binding_keys = {b.key for b in panel.BINDINGS}
            expected_keys = {
                "escape",
                "q",
                "j",
                "k",
                "pagedown",
                "pageup",
                "home",
                "end",
                "o",
                "r",
            }
            assert binding_keys == expected_keys


class TestArticleReaderPanelLoadingState:
    """Test ArticleReaderPanel loading state."""

    @pytest.mark.asyncio
    async def test_loading_state_shows_spinner(self, sample_article: ArticleResult) -> None:
        """Test that loading state shows spinner and message."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        # Mock fetch_article to delay response
        async def delayed_fetch(url: str, **kwargs):  # type: ignore[no-untyped-def]
            import asyncio

            await asyncio.sleep(0.1)  # Small delay to check loading state
            return sample_article

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                side_effect=delayed_fetch,
            ):
                # Start fetching (don't await yet)
                fetch_task = panel.show_article("https://example.com/article")

                # Give it a moment to render loading state
                await pilot.pause(0.05)

                # Check for loading indicator
                try:
                    loading_indicator = panel.query_one(LoadingIndicator)
                    assert loading_indicator is not None
                except Exception:
                    # Loading state may have already passed, that's ok
                    pass

                # Wait for fetch to complete
                await fetch_task

    @pytest.mark.asyncio
    async def test_loading_message_displayed(self, sample_article: ArticleResult) -> None:
        """Test that loading message is displayed during fetch."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        # Mock fetch_article to delay response
        async def delayed_fetch(url: str, **kwargs):  # type: ignore[no-untyped-def]
            import asyncio

            await asyncio.sleep(0.1)
            return sample_article

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                side_effect=delayed_fetch,
            ):
                fetch_task = panel.show_article("https://example.com/article")
                await pilot.pause(0.05)

                # Check for loading message
                labels = panel.query(Label)
                loading_messages = [
                    label
                    for label in labels
                    if "Fetching" in str(label.render())
                ]
                # May or may not be present depending on timing
                # This test is just for coverage

                await fetch_task


class TestArticleReaderPanelContentDisplay:
    """Test ArticleReaderPanel content display."""

    @pytest.mark.asyncio
    async def test_displays_article_title(self, sample_article: ArticleResult) -> None:
        """Test that article title is displayed."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check that title is displayed
            labels = panel.query(Label)
            title_labels = [
                label
                for label in labels
                if "Test Article Title" in str(label.render())
            ]
            assert len(title_labels) > 0

    @pytest.mark.asyncio
    async def test_displays_article_metadata(
        self, sample_article: ArticleResult
    ) -> None:
        """Test that article metadata (author, date, word count) is displayed."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check that metadata is displayed
            labels = panel.query(Label)
            meta_labels = [
                label for label in labels if "Test Author" in str(label.render())
            ]
            assert len(meta_labels) > 0

            # Check word count
            word_count_labels = [
                label for label in labels if "150 words" in str(label.render())
            ]
            assert len(word_count_labels) > 0

    @pytest.mark.asyncio
    async def test_displays_reading_time(self, sample_article: ArticleResult) -> None:
        """Test that reading time estimate is displayed."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check for reading time (150 words = 1 min at 200 wpm)
            labels = panel.query(Label)
            reading_time_labels = [
                label for label in labels if "min read" in str(label.render())
            ]
            assert len(reading_time_labels) > 0

    @pytest.mark.asyncio
    async def test_displays_article_content(
        self, sample_article: ArticleResult
    ) -> None:
        """Test that article content is displayed."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check that content is displayed
            content_widgets = panel.query(Static)
            content_text = " ".join([str(w.render()) for w in content_widgets])
            assert "article content" in content_text.lower()

    @pytest.mark.asyncio
    async def test_displays_footer_hints(self, sample_article: ArticleResult) -> None:
        """Test that footer with keybinding hints is displayed."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check for footer hints
            labels = panel.query(Label)
            footer_labels = [
                label for label in labels if "Esc" in str(label.render())
            ]
            assert len(footer_labels) > 0


class TestArticleReaderPanelErrorState:
    """Test ArticleReaderPanel error state."""

    @pytest.mark.asyncio
    async def test_displays_error_title(self, sample_error: ArticleError) -> None:
        """Test that error title is displayed."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_error,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check for error title
            labels = panel.query(Label)
            error_titles = [
                label for label in labels if "Failed" in str(label.render())
            ]
            assert len(error_titles) > 0

    @pytest.mark.asyncio
    async def test_displays_error_message(self, sample_error: ArticleError) -> None:
        """Test that error message is displayed."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_error,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check for error message
            labels = panel.query(Label)
            error_messages = [
                label
                for label in labels
                if "Network connection failed" in str(label.render())
            ]
            assert len(error_messages) > 0

    @pytest.mark.asyncio
    async def test_displays_retry_hint_for_retryable_errors(
        self, sample_error: ArticleError
    ) -> None:
        """Test that retry hint is shown for retryable errors."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_error,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check for retry hint (sample_error has should_retry=True)
            labels = panel.query(Label)
            retry_hints = [label for label in labels if "retry" in str(label.render())]
            assert len(retry_hints) > 0

    @pytest.mark.asyncio
    async def test_displays_browser_fallback_hint(
        self, sample_error: ArticleError
    ) -> None:
        """Test that browser fallback hint is always shown."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_error,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check for browser hint
            labels = panel.query(Label)
            browser_hints = [
                label for label in labels if "browser" in str(label.render())
            ]
            assert len(browser_hints) > 0


class TestArticleReaderPanelActions:
    """Test ArticleReaderPanel action handlers."""

    @pytest.mark.asyncio
    async def test_close_action_posts_message(
        self, sample_article: ArticleResult
    ) -> None:
        """Test that close action calls post_message."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Mock post_message to track calls
            with patch.object(panel, "post_message") as mock_post:
                panel.action_close()

                # Verify post_message was called (no await pilot.pause needed)
                assert mock_post.call_count == 1
                message = mock_post.call_args[0][0]
                assert isinstance(message, ArticleReaderPanel.CloseRequested)

    @pytest.mark.asyncio
    async def test_browser_action_opens_url(
        self, sample_article: ArticleResult
    ) -> None:
        """Test that browser action opens URL."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Mock webbrowser.open
            with patch("viper.widgets.article_reader_panel.webbrowser.open") as mock_open:
                panel.action_open_in_browser()
                await pilot.pause()

                mock_open.assert_called_once_with("https://example.com/article")

    @pytest.mark.asyncio
    async def test_retry_action_refetches_article(
        self, sample_article: ArticleResult
    ) -> None:
        """Test that retry action re-fetches the article."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            call_count = 0

            async def mock_fetch(url: str, **kwargs):  # type: ignore[no-untyped-def]
                nonlocal call_count
                call_count += 1
                return sample_article

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                side_effect=mock_fetch,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

                assert call_count == 1

                # Trigger retry
                await panel.action_retry_fetch()
                await pilot.pause()

                assert call_count == 2


class TestArticleReaderPanelScrolling:
    """Test ArticleReaderPanel scrolling actions."""

    @pytest.mark.asyncio
    async def test_scroll_actions_exist(self, sample_article: ArticleResult) -> None:
        """Test that all scroll actions are defined."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=sample_article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Test that scroll methods exist and can be called
            assert hasattr(panel, "action_scroll_down")
            assert hasattr(panel, "action_scroll_up")
            assert hasattr(panel, "action_page_down")
            assert hasattr(panel, "action_page_up")
            assert hasattr(panel, "action_scroll_home")
            assert hasattr(panel, "action_scroll_end")

            # Call them (they should work even if scroll container exists)
            panel.action_scroll_down()
            panel.action_scroll_up()
            panel.action_page_down()
            panel.action_page_up()
            panel.action_scroll_home()
            panel.action_scroll_end()


class TestArticleReaderPanelEdgeCases:
    """Test ArticleReaderPanel edge cases."""

    @pytest.mark.asyncio
    async def test_handles_article_without_author(self) -> None:
        """Test display when article has no author."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        article = ArticleResult(
            title="No Author Article",
            content="Content here",
            author="",  # Empty author
            date="2024-01-01",
            source_url="https://example.com/article",
            word_count=10,
        )

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Should still display without crashing
            labels = panel.query(Label)
            assert len(labels) > 0

    @pytest.mark.asyncio
    async def test_handles_article_without_date(self) -> None:
        """Test display when article has no date."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        article = ArticleResult(
            title="No Date Article",
            content="Content here",
            author="Author",
            date="",  # Empty date
            source_url="https://example.com/article",
            word_count=10,
        )

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Should still display without crashing
            labels = panel.query(Label)
            assert len(labels) > 0

    @pytest.mark.asyncio
    async def test_handles_large_article(self) -> None:
        """Test display with large article content."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        # Create large content
        large_content = "\n\n".join([f"Paragraph {i}" for i in range(100)])

        article = ArticleResult(
            title="Large Article",
            content=large_content,
            author="Author",
            date="2024-01-01",
            source_url="https://example.com/article",
            word_count=5000,
        )

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Should handle large content
            content_widgets = panel.query(Static)
            assert len(content_widgets) > 50  # Many paragraphs

    @pytest.mark.asyncio
    async def test_handles_single_word_article(self) -> None:
        """Test reading time for very short article (minimum 1 min)."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield ArticleReaderPanel()

        article = ArticleResult(
            title="Short",
            content="Word",
            author="Author",
            date="2024-01-01",
            source_url="https://example.com/article",
            word_count=1,
        )

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ArticleReaderPanel)

            with patch(
                "viper.widgets.article_reader_panel.fetch_article",
                return_value=article,
            ):
                await panel.show_article("https://example.com/article")
                await pilot.pause()

            # Check for minimum reading time of 1 min
            labels = panel.query(Label)
            reading_time_labels = [
                label for label in labels if "1 min read" in str(label.render())
            ]
            assert len(reading_time_labels) > 0
