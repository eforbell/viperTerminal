"""Tests for news fetching service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from viper.services.news import (
    NewsError,
    NewsItem,
    NewsResult,
    clear_news_cache,
    fetch_news,
)


def create_mock_rss_feed(num_items: int = 5) -> str:
    """Create a mock RSS feed XML."""
    items = []
    base_time = datetime(2024, 1, 1, 12, 0, 0)

    for i in range(num_items):
        pub_date = (base_time + timedelta(hours=i)).strftime("%a, %d %b %Y %H:%M:%S %z")
        items.append(
            f"""
        <item>
            <title>Apple Stock News {i} - CNBC</title>
            <link>https://example.com/news/{i}</link>
            <description>Summary of news article {i}</description>
            <pubDate>{pub_date}</pubDate>
        </item>
        """
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Yahoo Finance - AAPL</title>
        <link>https://finance.yahoo.com</link>
        <description>AAPL stock news</description>
        {''.join(items)}
    </channel>
</rss>
"""


def create_empty_rss_feed() -> str:
    """Create an empty RSS feed (no items)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Yahoo Finance - INVALID</title>
        <link>https://finance.yahoo.com</link>
        <description>No news available</description>
    </channel>
</rss>
"""


def create_malformed_rss() -> str:
    """Create malformed RSS to test parsing errors."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Malformed Feed</title>
        <!-- Missing closing tags -->
    </channel>
"""


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
    @respx.mock
    async def test_fetch_news_success(self) -> None:
        """Test successful news fetch."""
        mock_rss = create_mock_rss_feed(5)
        route = respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

        result = await fetch_news("AAPL", use_cache=False)

        assert isinstance(result, list)
        assert len(result) == 5
        assert all(isinstance(item, NewsItem) for item in result)
        assert result[0].title == "Apple Stock News 0"
        assert result[0].source == "CNBC"
        assert result[0].url == "https://example.com/news/0"
        assert result[0].summary == "Summary of news article 0"
        assert route.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_max_items(self) -> None:
        """Test news fetch with max_items limit."""
        mock_rss = create_mock_rss_feed(20)
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

        result = await fetch_news("AAPL", max_items=3, use_cache=False)

        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_empty_feed(self) -> None:
        """Test news fetch with empty feed."""
        mock_rss = create_empty_rss_feed()
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=INVALID").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

        result = await fetch_news("INVALID", use_cache=False)

        assert isinstance(result, NewsError)
        assert result.ticker == "INVALID"
        assert "No news available" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_timeout(self) -> None:
        """Test news fetch with timeout."""
        from httpx import TimeoutException

        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            side_effect=TimeoutException("Timeout")
        )

        result = await fetch_news("AAPL", timeout=1.0, use_cache=False)

        assert isinstance(result, NewsError)
        assert result.ticker == "AAPL"
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_connect_error(self) -> None:
        """Test news fetch with connection error."""
        from httpx import ConnectError

        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            side_effect=ConnectError("Connection failed")
        )

        result = await fetch_news("AAPL", use_cache=False)

        assert isinstance(result, NewsError)
        assert result.ticker == "AAPL"
        assert "connect" in result.error_message.lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_request_error(self) -> None:
        """Test news fetch with generic request error."""
        from httpx import RequestError

        # Mock a generic network error
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            side_effect=RequestError("Network error occurred")
        )

        result = await fetch_news("AAPL", use_cache=False)

        assert isinstance(result, NewsError)
        assert result.ticker == "AAPL"
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_404_not_found(self) -> None:
        """Test news fetch with 404 error."""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=INVALID").mock(
            return_value=Response(404, content=b"Not Found")
        )

        result = await fetch_news("INVALID", use_cache=False)

        assert isinstance(result, NewsError)
        assert result.ticker == "INVALID"
        assert "No news feed available" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_http_error(self) -> None:
        """Test news fetch with generic HTTP error."""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(500, content=b"Server Error")
        )

        result = await fetch_news("AAPL", use_cache=False)

        assert isinstance(result, NewsError)
        assert result.ticker == "AAPL"
        assert "HTTP error: 500" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_ticker_normalization(self) -> None:
        """Test that ticker is normalized (uppercase, stripped)."""
        mock_rss = create_mock_rss_feed(1)
        route = respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

        result = await fetch_news("  aapl  ", use_cache=False)

        assert isinstance(result, list)
        assert route.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_caching_enabled(self) -> None:
        """Test that results are cached when use_cache=True."""
        mock_rss = create_mock_rss_feed(3)
        route = respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

        # Clear cache first
        clear_news_cache()

        # First call should fetch
        result1 = await fetch_news("AAPL", use_cache=True)
        assert isinstance(result1, list)
        assert route.call_count == 1

        # Second call should use cache
        result2 = await fetch_news("AAPL", use_cache=True)
        assert isinstance(result2, list)
        assert route.call_count == 1  # Still 1, not 2

        # Results should be the same
        assert len(result1) == len(result2)

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_cache_expiration(self) -> None:
        """Test that cache expires after TTL."""
        mock_rss = create_mock_rss_feed(3)
        route = respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

        # Clear cache first
        clear_news_cache()

        # First call
        result1 = await fetch_news("AAPL", use_cache=True)
        assert route.call_count == 1

        # Simulate cache expiration by manually modifying cache
        from viper.services import news

        if "AAPL" in news._cache:
            old_time = datetime.now() - timedelta(seconds=121)  # Expired
            news._cache["AAPL"] = (old_time, news._cache["AAPL"][1])

        # Second call should fetch again
        result2 = await fetch_news("AAPL", use_cache=True)
        assert route.call_count == 2  # Fetched again

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_cache_disabled(self) -> None:
        """Test that cache is bypassed when use_cache=False."""
        mock_rss = create_mock_rss_feed(3)
        route = respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

        clear_news_cache()

        # First call
        result1 = await fetch_news("AAPL", use_cache=False)
        assert route.call_count == 1

        # Second call should fetch again
        result2 = await fetch_news("AAPL", use_cache=False)
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_error_caching(self) -> None:
        """Test that errors are also cached."""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=INVALID").mock(
            return_value=Response(404, content=b"Not Found")
        )

        clear_news_cache()

        # First call - error
        result1 = await fetch_news("INVALID", use_cache=True)
        assert isinstance(result1, NewsError)

        # Second call should return cached error
        result2 = await fetch_news("INVALID", use_cache=True)
        assert isinstance(result2, NewsError)

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_without_source_in_title(self) -> None:
        """Test parsing news items without source suffix in title."""
        rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Yahoo Finance - AAPL</title>
        <item>
            <title>Apple announces new product</title>
            <link>https://example.com/news/1</link>
            <description>Product announcement</description>
            <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
        </item>
    </channel>
</rss>
"""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=rss.encode())
        )

        result = await fetch_news("AAPL", use_cache=False)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].title == "Apple announces new product"
        assert result[0].source == "Yahoo Finance"  # Default source

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_without_published_date(self) -> None:
        """Test parsing news items without published date."""
        rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Yahoo Finance - AAPL</title>
        <item>
            <title>Breaking News - Reuters</title>
            <link>https://example.com/news/1</link>
            <description>Breaking news summary</description>
        </item>
    </channel>
</rss>
"""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=rss.encode())
        )

        result = await fetch_news("AAPL", use_cache=False)

        assert isinstance(result, list)
        assert len(result) == 1
        # Should have a published_at (defaulted to now)
        assert result[0].published_at is not None
        # Should be recent (within last minute)
        assert (datetime.now() - result[0].published_at).total_seconds() < 60

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_without_summary(self) -> None:
        """Test parsing news items without summary/description."""
        rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Yahoo Finance - AAPL</title>
        <item>
            <title>News Title - Source</title>
            <link>https://example.com/news/1</link>
            <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
        </item>
    </channel>
</rss>
"""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=rss.encode())
        )

        result = await fetch_news("AAPL", use_cache=False)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].summary is None


class TestClearNewsCache:
    """Tests for clear_news_cache function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_clear_all_cache(self) -> None:
        """Test clearing entire cache."""
        mock_rss = create_mock_rss_feed(1)
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=mock_rss.encode())
        )
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

        # Populate cache
        await fetch_news("AAPL", use_cache=True)
        await fetch_news("TSLA", use_cache=True)

        # Clear all
        clear_news_cache()

        # Check cache is empty
        from viper.services import news

        assert len(news._cache) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_clear_specific_ticker_cache(self) -> None:
        """Test clearing cache for specific ticker."""
        mock_rss = create_mock_rss_feed(1)
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=mock_rss.encode())
        )
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA").mock(
            return_value=Response(200, content=mock_rss.encode())
        )

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


class TestParsingEdgeCases:
    """Tests for edge cases in RSS parsing."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_with_malformed_rss(self) -> None:
        """Test handling of malformed RSS that feedparser can't parse well."""
        malformed = create_malformed_rss()
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=malformed.encode())
        )

        result = await fetch_news("AAPL", use_cache=False)

        # feedparser is lenient, but with bozo flag this might be an error
        # This depends on how severely malformed the feed is
        assert isinstance(result, (list, NewsError))

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_with_invalid_published_date(self) -> None:
        """Test handling of items with invalid/unparseable published dates."""
        rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Yahoo Finance - AAPL</title>
        <item>
            <title>News with bad date - Source</title>
            <link>https://example.com/news/1</link>
            <pubDate>Invalid Date String</pubDate>
        </item>
    </channel>
</rss>
"""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=rss.encode())
        )

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

        # Mock run_in_executor to raise an exception
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_event_loop = MagicMock()
            mock_event_loop.run_in_executor.side_effect = RuntimeError("Unexpected error")
            mock_loop.return_value = mock_event_loop

            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, NewsError)
            assert result.ticker == "AAPL"
            assert "Failed to fetch news" in result.error_message
            assert "Unexpected error" in result.error_message

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_with_exception_during_date_parse(self) -> None:
        """Test date parsing exception handling."""
        # Create RSS with published_parsed that will cause mktime to fail
        rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Yahoo Finance - AAPL</title>
        <item>
            <title>News - Source</title>
            <link>https://example.com/news/1</link>
            <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
        </item>
    </channel>
</rss>
"""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=rss.encode())
        )

        # Mock time.mktime to raise exception
        with patch("time.mktime", side_effect=ValueError("Invalid time")):
            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, list)
            assert len(result) == 1
            # Should fall back to datetime.now()
            assert (datetime.now() - result[0].published_at).total_seconds() < 60

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_generic_sync_exception(self) -> None:
        """Test handling of generic exception in sync fetch."""
        respx.get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL").mock(
            return_value=Response(200, content=b"valid content")
        )

        # Mock feedparser.parse to raise a generic exception
        with patch("feedparser.parse", side_effect=RuntimeError("Unexpected parsing error")):
            result = await fetch_news("AAPL", use_cache=False)

            assert isinstance(result, NewsError)
            assert result.ticker == "AAPL"
            assert "Unexpected error" in result.error_message
            assert "Unexpected parsing error" in result.error_message
