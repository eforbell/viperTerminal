"""Tests for news fetching service."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from viper.services.news import (
    NewsError,
    NewsItem,
    NewsResult,
    clear_news_cache,
    fetch_news,
)


def create_mock_yfinance_news(num_items: int = 5) -> list[dict[str, Any]]:
    """Create mock yfinance news data structure."""
    items = []
    base_time = datetime(2024, 1, 1, 12, 0, 0)

    for i in range(num_items):
        pub_date = (base_time + timedelta(hours=i)).isoformat() + "Z"
        items.append(
            {
                "content": {
                    "title": f"Apple Stock News {i}",
                    "summary": f"Summary of news article {i}",
                    "pubDate": pub_date,
                    "provider": {"displayName": "CNBC"},
                    "previewUrl": f"https://example.com/news/{i}",
                }
            }
        )

    return items


class TestNewsItem:
    """Tests for NewsItem dataclass."""

    def test_news_item_creation(self) -> None:
        """Test NewsItem dataclass instantiation."""
        now = datetime.now()
        item = NewsItem(
            title="Test News",
            source="CNBC",
            url="https://example.com",
            published_at=now,
            summary="Test summary",
        )
        assert item.title == "Test News"
        assert item.source == "CNBC"
        assert item.url == "https://example.com"
        assert item.published_at == now
        assert item.summary == "Test summary"

    def test_news_item_without_summary(self) -> None:
        """Test NewsItem with optional summary."""
        now = datetime.now()
        item = NewsItem(
            title="Test News",
            source="CNBC",
            url="https://example.com",
            published_at=now,
        )
        assert item.summary is None


class TestNewsError:
    """Tests for NewsError dataclass."""

    def test_news_error_creation(self) -> None:
        """Test NewsError dataclass instantiation."""
        error = NewsError(ticker="AAPL", error_message="Failed to fetch news")
        assert error.ticker == "AAPL"
        assert error.error_message == "Failed to fetch news"


class TestFetchNews:
    """Tests for fetch_news function."""

    @pytest.mark.asyncio
    async def test_fetch_news_success(self) -> None:
        """Test successful news fetch."""
        mock_news = create_mock_yfinance_news(5)

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, list)
            assert len(result) == 5
            assert all(isinstance(item, NewsItem) for item in result)
            assert result[0].title == "Apple Stock News 0"
            assert result[0].source == "CNBC"
            assert result[0].url == "https://example.com/news/0"
            assert result[0].summary == "Summary of news article 0"
            mock_ticker_class.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_fetch_news_max_items(self) -> None:
        """Test news fetch with max_items limit."""
        mock_news = create_mock_yfinance_news(20)

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("AAPL", max_items=3, use_cache=False)

            assert isinstance(result, list)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_fetch_news_empty_feed(self) -> None:
        """Test news fetch with empty news list."""
        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = []
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("INVALID", use_cache=False)

            assert isinstance(result, NewsError)
            assert result.ticker == "INVALID"
            assert "No news available" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_news_ticker_normalization(self) -> None:
        """Test that ticker is normalized (uppercase, stripped)."""
        mock_news = create_mock_yfinance_news(1)

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("  aapl  ", use_cache=False)

            assert isinstance(result, list)
            mock_ticker_class.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_fetch_news_caching_enabled(self) -> None:
        """Test that results are cached when use_cache=True."""
        mock_news = create_mock_yfinance_news(3)

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            # Clear cache first
            clear_news_cache()

            # First call should fetch
            result1 = await fetch_news("AAPL", use_cache=True)
            assert isinstance(result1, list)
            assert mock_ticker_class.call_count == 1

            # Second call should use cache
            result2 = await fetch_news("AAPL", use_cache=True)
            assert isinstance(result2, list)
            assert mock_ticker_class.call_count == 1  # Still 1, not 2

            # Results should be the same
            assert len(result1) == len(result2)

    @pytest.mark.asyncio
    async def test_fetch_news_cache_expiration(self) -> None:
        """Test that cache expires after TTL."""
        mock_news = create_mock_yfinance_news(3)

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            # Clear cache first
            clear_news_cache()

            # First call
            result1 = await fetch_news("AAPL", use_cache=True)
            assert mock_ticker_class.call_count == 1

            # Simulate cache expiration by manually modifying cache
            from viper.services import news

            if "AAPL" in news._cache:
                old_time = datetime.now() - timedelta(seconds=121)  # Expired
                news._cache["AAPL"] = (old_time, news._cache["AAPL"][1])

            # Second call should fetch again
            result2 = await fetch_news("AAPL", use_cache=True)
            assert mock_ticker_class.call_count == 2  # Fetched again

    @pytest.mark.asyncio
    async def test_fetch_news_cache_disabled(self) -> None:
        """Test that cache is bypassed when use_cache=False."""
        mock_news = create_mock_yfinance_news(3)

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            clear_news_cache()

            # First call
            result1 = await fetch_news("AAPL", use_cache=False)
            assert mock_ticker_class.call_count == 1

            # Second call should fetch again
            result2 = await fetch_news("AAPL", use_cache=False)
            assert mock_ticker_class.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_news_error_caching(self) -> None:
        """Test that errors are also cached."""
        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = []
            mock_ticker_class.return_value = mock_ticker

            clear_news_cache()

            # First call - error
            result1 = await fetch_news("INVALID", use_cache=True)
            assert isinstance(result1, NewsError)

            # Second call should return cached error
            result2 = await fetch_news("INVALID", use_cache=True)
            assert isinstance(result2, NewsError)
            assert mock_ticker_class.call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_fetch_news_without_summary(self) -> None:
        """Test parsing news items without summary."""
        mock_news = [
            {
                "content": {
                    "title": "News Title",
                    "pubDate": "2024-01-01T12:00:00Z",
                    "provider": {"displayName": "Source"},
                    "previewUrl": "https://example.com/news/1",
                }
            }
        ]

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].summary is None

    @pytest.mark.asyncio
    async def test_fetch_news_without_published_date(self) -> None:
        """Test parsing news items without published date."""
        mock_news = [
            {
                "content": {
                    "title": "Breaking News",
                    "summary": "Breaking news summary",
                    "provider": {"displayName": "Reuters"},
                    "previewUrl": "https://example.com/news/1",
                }
            }
        ]

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, list)
            assert len(result) == 1
            # Should have a published_at (defaulted to now)
            assert result[0].published_at is not None
            # Should be recent (within last minute)
            assert (datetime.now() - result[0].published_at).total_seconds() < 60

    @pytest.mark.asyncio
    async def test_fetch_news_with_canonicalUrl(self) -> None:
        """Test URL extraction from canonicalUrl when previewUrl is missing."""
        mock_news = [
            {
                "content": {
                    "title": "News with canonical URL",
                    "summary": "Test summary",
                    "pubDate": "2024-01-01T12:00:00Z",
                    "provider": {"displayName": "CNBC"},
                    "canonicalUrl": {"url": "https://canonical.example.com"},
                }
            }
        ]

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].url == "https://canonical.example.com"

    @pytest.mark.asyncio
    async def test_fetch_news_malformed_item(self) -> None:
        """Test handling of malformed news items (should skip them)."""
        mock_news = [
            {
                "content": {
                    "title": "Good News",
                    "summary": "Valid summary",
                    "pubDate": "2024-01-01T12:00:00Z",
                    "provider": {"displayName": "CNBC"},
                    "previewUrl": "https://example.com/news/1",
                }
            },
            {"malformed": "item"},  # Malformed item
            {
                "content": {
                    "title": "Another Good News",
                    "summary": "Another valid summary",
                    "pubDate": "2024-01-01T13:00:00Z",
                    "provider": {"displayName": "Reuters"},
                    "previewUrl": "https://example.com/news/2",
                }
            },
        ]

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, list)
            assert len(result) == 2  # Malformed item skipped
            assert result[0].title == "Good News"
            assert result[1].title == "Another Good News"

    @pytest.mark.asyncio
    async def test_fetch_news_all_malformed(self) -> None:
        """Test when all news items are malformed."""
        mock_news = [
            {"malformed": "item1"},
            {"bad": "item2"},
        ]

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, NewsError)
            assert result.ticker == "AAPL"
            assert "No news available" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_news_invalid_published_date(self) -> None:
        """Test handling of invalid/unparseable published dates."""
        mock_news = [
            {
                "content": {
                    "title": "News with bad date",
                    "summary": "Test summary",
                    "pubDate": "Invalid Date String",
                    "provider": {"displayName": "Source"},
                    "previewUrl": "https://example.com/news/1",
                }
            }
        ]

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, list)
            assert len(result) == 1
            # Should default to current time
            assert result[0].published_at is not None
            assert (datetime.now() - result[0].published_at).total_seconds() < 60

    @pytest.mark.asyncio
    async def test_fetch_news_generic_exception(self) -> None:
        """Test handling of unexpected exceptions during fetch."""
        clear_news_cache()

        with patch("yfinance.Ticker", side_effect=RuntimeError("Unexpected error")):
            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, NewsError)
            assert result.ticker == "AAPL"
            assert "Unexpected error" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_news_async_exception(self) -> None:
        """Test handling of exceptions in async wrapper."""
        clear_news_cache()

        # Mock run_in_executor to raise an exception
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_event_loop = MagicMock()
            mock_event_loop.run_in_executor.side_effect = RuntimeError("Async error")
            mock_loop.return_value = mock_event_loop

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, NewsError)
            assert result.ticker == "AAPL"
            assert "Failed to fetch news" in result.error_message
            assert "Async error" in result.error_message


class TestClearNewsCache:
    """Tests for clear_news_cache function."""

    @pytest.mark.asyncio
    async def test_clear_all_cache(self) -> None:
        """Test clearing entire cache."""
        mock_news = create_mock_yfinance_news(1)

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            # Populate cache
            await fetch_news("AAPL", use_cache=True)
            await fetch_news("TSLA", use_cache=True)

            # Clear all
            clear_news_cache()

            # Check cache is empty
            from viper.services import news

            assert len(news._cache) == 0

    @pytest.mark.asyncio
    async def test_clear_specific_ticker_cache(self) -> None:
        """Test clearing cache for specific ticker."""
        mock_news = create_mock_yfinance_news(1)

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.news = mock_news
            mock_ticker_class.return_value = mock_ticker

            # Populate cache
            await fetch_news("AAPL", use_cache=True)
            await fetch_news("TSLA", use_cache=True)

            # Clear only AAPL
            clear_news_cache("AAPL")

            # Check TSLA still in cache
            from viper.services import news

            assert "AAPL" not in news._cache
            assert "TSLA" in news._cache

    def test_clear_nonexistent_ticker(self) -> None:
        """Test clearing cache for ticker that doesn't exist."""
        clear_news_cache("NONEXISTENT")  # Should not raise error


class TestSafeGetNested:
    """Tests for _safe_get_nested helper function."""

    def test_safe_get_nested_success(self) -> None:
        """Test successful nested key access."""
        from viper.services.news import _safe_get_nested

        data = {"a": {"b": {"c": "value"}}}
        assert _safe_get_nested(data, ["a", "b", "c"]) == "value"

    def test_safe_get_nested_missing_key(self) -> None:
        """Test missing key returns default."""
        from viper.services.news import _safe_get_nested

        data = {"a": {"b": {}}}
        assert _safe_get_nested(data, ["a", "b", "c"], "default") == "default"

    def test_safe_get_nested_non_dict(self) -> None:
        """Test non-dict value returns default."""
        from viper.services.news import _safe_get_nested

        data = {"a": "not_a_dict"}
        assert _safe_get_nested(data, ["a", "b"], "default") == "default"

    def test_safe_get_nested_none_default(self) -> None:
        """Test None as default value."""
        from viper.services.news import _safe_get_nested

        data = {"a": {}}
        assert _safe_get_nested(data, ["a", "b"]) is None
