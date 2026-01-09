"""Unit tests for article_reader service."""

import pytest
import respx
from httpx import Response, TimeoutException

from viper.services.article_reader import (
    ArticleError,
    ArticleResult,
    _extract_article_sync,
    clear_article_cache,
    fetch_article,
)


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Clear cache before each test to ensure isolation."""
    clear_article_cache()


# Sample HTML for testing
SAMPLE_HTML = """
<html>
<head><title>Test Article Title</title></head>
<body>
<article>
<h1>Test Article Title</h1>
<p class="author">By John Doe</p>
<time datetime="2024-01-15">January 15, 2024</time>
<p>This is the first paragraph of the article content. It contains useful information.</p>
<p>This is the second paragraph with more details and context about the topic.</p>
<p>This is the third paragraph that concludes the main points of the article.</p>
</article>
<nav>Navigation links that should be stripped</nav>
<div class="ads">Advertisement content that should be removed</div>
</body>
</html>
"""

PAYWALL_HTML = """
<html>
<body>
<article>
<h1>Premium Article</h1>
<p>This article is for subscribers only. Subscribe to read more.</p>
</article>
</body>
</html>
"""

EMPTY_HTML = """
<html>
<head><title>Empty Page</title></head>
<body>
</body>
</html>
"""

MINIMAL_HTML = """
<html>
<body>
<nav>Navigation only</nav>
<footer>Footer only</footer>
</body>
</html>
"""


class TestArticleResultDataclass:
    """Test ArticleResult dataclass."""

    def test_article_result_creation(self) -> None:
        """Test creating ArticleResult with all fields."""
        result = ArticleResult(
            title="Test Title",
            content="Test content goes here.",
            author="Jane Smith",
            date="2024-01-15",
            source_url="https://example.com/article",
            word_count=4,
        )

        assert result.title == "Test Title"
        assert result.content == "Test content goes here."
        assert result.author == "Jane Smith"
        assert result.date == "2024-01-15"
        assert result.source_url == "https://example.com/article"
        assert result.word_count == 4

    def test_article_result_frozen(self) -> None:
        """Test that ArticleResult is immutable (frozen)."""
        result = ArticleResult(
            title="Test",
            content="Content",
            author="Author",
            date="2024-01-15",
            source_url="https://example.com",
            word_count=1,
        )

        with pytest.raises(AttributeError):
            result.title = "New Title"  # type: ignore


class TestArticleErrorDataclass:
    """Test ArticleError dataclass."""

    def test_article_error_creation(self) -> None:
        """Test creating ArticleError with all fields."""
        error = ArticleError(
            error_type="timeout",
            error_message="Request timed out",
            source_url="https://example.com/article",
            should_retry=True,
        )

        assert error.error_type == "timeout"
        assert error.error_message == "Request timed out"
        assert error.source_url == "https://example.com/article"
        assert error.should_retry is True

    def test_article_error_frozen(self) -> None:
        """Test that ArticleError is immutable (frozen)."""
        error = ArticleError(
            error_type="network",
            error_message="Network error",
            source_url="https://example.com",
            should_retry=False,
        )

        with pytest.raises(AttributeError):
            error.error_type = "timeout"  # type: ignore


class TestExtractArticleSync:
    """Test synchronous article extraction logic."""

    def test_extract_article_basic(self) -> None:
        """Test basic article extraction from HTML."""
        result = _extract_article_sync(SAMPLE_HTML, "https://example.com/article")

        assert result is not None
        assert isinstance(result, ArticleResult)
        assert result.source_url == "https://example.com/article"
        assert len(result.content) > 0
        assert result.word_count > 0
        # Content should not contain navigation or ads
        assert "Navigation links" not in result.content
        assert "Advertisement" not in result.content

    def test_extract_article_empty_content(self) -> None:
        """Test extraction returns None when no content found."""
        result = _extract_article_sync(EMPTY_HTML, "https://example.com/empty")
        assert result is None

    def test_extract_article_very_short_content(self) -> None:
        """Test extraction handles suspiciously short content (possible paywall)."""
        result = _extract_article_sync(PAYWALL_HTML, "https://example.com/paywall")

        # Should still extract even if short (user will see it's paywalled)
        if result is not None:
            assert result.word_count < 50  # Very short content
            assert len(result.content) < 200

    def test_extract_article_minimal_content(self) -> None:
        """Test extraction with minimal HTML (nav/footer only)."""
        result = _extract_article_sync(MINIMAL_HTML, "https://example.com/minimal")

        # Trafilatura may extract nav text or return None
        # Either is acceptable behavior
        if result is not None:
            assert result.word_count > 0


class TestFetchArticle:
    """Test async fetch_article function."""

    @pytest.mark.asyncio
    async def test_fetch_article_success(self, respx_mock: respx.MockRouter) -> None:
        """Test successful article fetch and extraction."""
        url = "https://example.com/article"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        result = await fetch_article(url)

        assert isinstance(result, ArticleResult)
        assert result.source_url == url
        assert len(result.content) > 0
        assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_fetch_article_timeout(self, respx_mock: respx.MockRouter) -> None:
        """Test timeout error handling."""
        url = "https://example.com/slow"
        respx_mock.get(url).mock(side_effect=TimeoutException("Timeout"))

        result = await fetch_article(url, timeout=5)

        assert isinstance(result, ArticleError)
        assert result.error_type == "timeout"
        assert "timed out" in result.error_message.lower()
        assert result.should_retry is True

    @pytest.mark.asyncio
    async def test_fetch_article_404(self, respx_mock: respx.MockRouter) -> None:
        """Test 404 error handling."""
        url = "https://example.com/missing"
        respx_mock.get(url).mock(return_value=Response(404, text="Not Found"))

        result = await fetch_article(url)

        assert isinstance(result, ArticleError)
        assert result.error_type == "http_error"
        assert "404" in result.error_message
        assert result.should_retry is False

    @pytest.mark.asyncio
    async def test_fetch_article_403(self, respx_mock: respx.MockRouter) -> None:
        """Test 403 forbidden error handling."""
        url = "https://example.com/forbidden"
        respx_mock.get(url).mock(return_value=Response(403, text="Forbidden"))

        result = await fetch_article(url)

        assert isinstance(result, ArticleError)
        assert result.error_type == "http_error"
        assert "403" in result.error_message
        assert result.should_retry is False

    @pytest.mark.asyncio
    async def test_fetch_article_500(self, respx_mock: respx.MockRouter) -> None:
        """Test 500 server error handling (should retry)."""
        url = "https://example.com/error"
        respx_mock.get(url).mock(return_value=Response(500, text="Server Error"))

        result = await fetch_article(url)

        assert isinstance(result, ArticleError)
        assert result.error_type == "http_error"
        assert "500" in result.error_message
        assert result.should_retry is True  # Server errors are retryable

    @pytest.mark.asyncio
    async def test_fetch_article_extraction_failure(self, respx_mock: respx.MockRouter) -> None:
        """Test extraction failure when no content can be extracted."""
        url = "https://example.com/empty"
        # Truly empty HTML - no body content at all
        truly_empty = "<html><head></head><body></body></html>"
        respx_mock.get(url).mock(return_value=Response(200, text=truly_empty))

        result = await fetch_article(url)

        assert isinstance(result, ArticleError)
        assert result.error_type == "extraction"
        assert "extract" in result.error_message.lower()
        assert result.should_retry is False


class TestArticleCaching:
    """Test article caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_stores_successful_result(self, respx_mock: respx.MockRouter) -> None:
        """Test that successful results are cached."""
        url = "https://example.com/article"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        # First fetch - should hit network
        result1 = await fetch_article(url, use_cache=True)
        assert isinstance(result1, ArticleResult)

        # Second fetch - should use cache (no network call)
        result2 = await fetch_article(url, use_cache=True)
        assert isinstance(result2, ArticleResult)
        assert result2 is result1  # Same object from cache

    @pytest.mark.asyncio
    async def test_cache_not_used_when_disabled(self, respx_mock: respx.MockRouter) -> None:
        """Test that cache can be bypassed."""
        url = "https://example.com/article"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        result1 = await fetch_article(url, use_cache=False)
        assert isinstance(result1, ArticleResult)

        result2 = await fetch_article(url, use_cache=False)
        assert isinstance(result2, ArticleResult)
        # Should be different objects (not cached)
        assert result2 is not result1

    @pytest.mark.asyncio
    async def test_cache_different_urls(self, respx_mock: respx.MockRouter) -> None:
        """Test that different URLs are cached separately."""
        url1 = "https://example.com/article1"
        url2 = "https://example.com/article2"

        respx_mock.get(url1).mock(return_value=Response(200, text=SAMPLE_HTML))
        respx_mock.get(url2).mock(return_value=Response(200, text=SAMPLE_HTML))

        result1 = await fetch_article(url1)
        result2 = await fetch_article(url2)

        assert isinstance(result1, ArticleResult)
        assert isinstance(result2, ArticleResult)
        assert result1.source_url == url1
        assert result2.source_url == url2
        assert result1 is not result2

    @pytest.mark.asyncio
    async def test_cache_clear(self, respx_mock: respx.MockRouter) -> None:
        """Test manual cache clearing."""
        url = "https://example.com/article"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        result1 = await fetch_article(url)
        assert isinstance(result1, ArticleResult)

        # Clear cache
        clear_article_cache()

        # Should fetch again after clearing
        result2 = await fetch_article(url)
        assert isinstance(result2, ArticleResult)
        assert result2 is not result1  # Different object (re-fetched)

    @pytest.mark.asyncio
    async def test_cache_does_not_store_errors(self, respx_mock: respx.MockRouter) -> None:
        """Test that errors are not cached."""
        url = "https://example.com/error"
        respx_mock.get(url).mock(return_value=Response(404, text="Not Found"))

        result1 = await fetch_article(url)
        assert isinstance(result1, ArticleError)

        result2 = await fetch_article(url)
        assert isinstance(result2, ArticleError)
        # Errors are not cached, so should be different objects
        assert result2 is not result1


class TestUserAgentAndRedirects:
    """Test HTTP client configuration."""

    @pytest.mark.asyncio
    async def test_fetch_uses_realistic_user_agent(self, respx_mock: respx.MockRouter) -> None:
        """Test that a realistic User-Agent is sent."""
        url = "https://example.com/article"

        # Capture the request to verify headers
        route = respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        await fetch_article(url)

        # Verify User-Agent was sent
        assert route.called
        request = route.calls.last.request
        assert "User-Agent" in request.headers
        user_agent = request.headers["User-Agent"]
        assert "Mozilla" in user_agent  # Should look like a browser

    @pytest.mark.asyncio
    async def test_fetch_follows_redirects(self, respx_mock: respx.MockRouter) -> None:
        """Test that redirects are followed."""
        original_url = "https://example.com/redirect"
        final_url = "https://example.com/article"

        respx_mock.get(original_url).mock(
            return_value=Response(301, headers={"Location": final_url})
        )
        respx_mock.get(final_url).mock(return_value=Response(200, text=SAMPLE_HTML))

        result = await fetch_article(original_url)

        assert isinstance(result, ArticleResult)
        # Note: source_url will be the original URL passed to fetch_article
        assert result.source_url == original_url


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    @pytest.mark.asyncio
    async def test_fetch_article_with_custom_timeout(self, respx_mock: respx.MockRouter) -> None:
        """Test that custom timeout is respected."""
        url = "https://example.com/article"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        result = await fetch_article(url, timeout=20)

        assert isinstance(result, ArticleResult)

    @pytest.mark.asyncio
    async def test_fetch_article_url_with_query_params(self, respx_mock: respx.MockRouter) -> None:
        """Test URL with query parameters."""
        url = "https://example.com/article?id=123&source=rss"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        result = await fetch_article(url)

        assert isinstance(result, ArticleResult)
        assert result.source_url == url

    @pytest.mark.asyncio
    async def test_fetch_article_url_with_fragment(self, respx_mock: respx.MockRouter) -> None:
        """Test URL with fragment."""
        url = "https://example.com/article#section2"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        result = await fetch_article(url)

        assert isinstance(result, ArticleResult)


class TestPaywallDetection:
    """Test paywall detection functionality."""

    @pytest.mark.asyncio
    async def test_paywall_detection_with_subscribe_keyword(self, respx_mock: respx.MockRouter) -> None:
        """Test that short content with 'subscribe' keyword is detected as paywall."""
        url = "https://example.com/paywall"
        paywall_html = """
        <html><body><article>
        <h1>Premium Article</h1>
        <p>Subscribe to read this premium content.</p>
        </article></body></html>
        """
        respx_mock.get(url).mock(return_value=Response(200, text=paywall_html))

        result = await fetch_article(url)

        # Should fail extraction due to paywall detection
        assert isinstance(result, ArticleError)
        assert result.error_type == "extraction"

    @pytest.mark.asyncio
    async def test_paywall_detection_with_subscription_keyword(self, respx_mock: respx.MockRouter) -> None:
        """Test that short content with 'subscription' keyword is detected as paywall."""
        url = "https://example.com/paywall"
        paywall_html = """
        <html><body><article>
        <h1>Members Only</h1>
        <p>This requires a subscription to view.</p>
        </article></body></html>
        """
        respx_mock.get(url).mock(return_value=Response(200, text=paywall_html))

        result = await fetch_article(url)

        assert isinstance(result, ArticleError)
        assert result.error_type == "extraction"

    @pytest.mark.asyncio
    async def test_paywall_detection_with_members_only(self, respx_mock: respx.MockRouter) -> None:
        """Test that short content with 'members only' keyword is detected as paywall."""
        url = "https://example.com/paywall"
        paywall_html = """
        <html><body><article>
        <h1>Exclusive Content</h1>
        <p>This is for members only. Sign up to continue reading.</p>
        </article></body></html>
        """
        respx_mock.get(url).mock(return_value=Response(200, text=paywall_html))

        result = await fetch_article(url)

        assert isinstance(result, ArticleError)
        assert result.error_type == "extraction"

    @pytest.mark.asyncio
    async def test_short_article_without_paywall_keywords_succeeds(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test that short content WITHOUT paywall keywords is allowed."""
        url = "https://example.com/short"
        # Short but legitimate content (no paywall keywords)
        short_html = """
        <html><body><article>
        <h1>Brief Update</h1>
        <p>Market closes up 2% today on strong earnings reports from tech sector.</p>
        </article></body></html>
        """
        respx_mock.get(url).mock(return_value=Response(200, text=short_html))

        result = await fetch_article(url)

        # Should succeed - short but no paywall keywords
        assert isinstance(result, ArticleResult)
        assert result.word_count < 200  # Verify it's actually short
        assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_long_article_with_subscribe_keyword_succeeds(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test that LONG content with 'subscribe' keyword is allowed (e.g., newsletter signup at end)."""
        url = "https://example.com/article"
        # Long legitimate article that mentions subscribe at the bottom
        long_html = """
        <html><body><article>
        <h1>Market Analysis</h1>
        <p>""" + " ".join(["This is a detailed analysis of market trends."] * 50) + """</p>
        <p>Subscribe to our newsletter for more insights.</p>
        </article></body></html>
        """
        respx_mock.get(url).mock(return_value=Response(200, text=long_html))

        result = await fetch_article(url)

        # Should succeed - long content with subscribe is OK (newsletter CTA)
        assert isinstance(result, ArticleResult)
        assert result.word_count > 200  # Verify it's actually long


class TestCacheExpiration:
    """Test cache expiration behavior."""

    @pytest.mark.asyncio
    async def test_cache_expiration(self, respx_mock: respx.MockRouter) -> None:
        """Test that cache expires after TTL."""
        import time
        from datetime import timedelta
        from viper.services.article_reader import _article_cache, _CACHE_TTL_SECONDS

        url = "https://example.com/article"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        # First fetch - should cache
        result1 = await fetch_article(url)
        assert isinstance(result1, ArticleResult)

        # Manually expire the cache by modifying timestamp
        from datetime import datetime
        if url in _article_cache:
            # Set timestamp to past (beyond TTL)
            expired_time = datetime.now() - timedelta(seconds=_CACHE_TTL_SECONDS + 1)
            _article_cache[url] = (expired_time, _article_cache[url][1])

        # Second fetch - should re-fetch due to expiration
        result2 = await fetch_article(url)
        assert isinstance(result2, ArticleResult)
        assert result2 is not result1  # Different object (re-fetched)

    @pytest.mark.asyncio
    async def test_cache_hit_within_ttl(self, respx_mock: respx.MockRouter) -> None:
        """Test that cache returns same object within TTL."""
        url = "https://example.com/article"
        respx_mock.get(url).mock(return_value=Response(200, text=SAMPLE_HTML))

        # First fetch
        result1 = await fetch_article(url)
        assert isinstance(result1, ArticleResult)

        # Second fetch immediately (within TTL)
        result2 = await fetch_article(url)
        assert isinstance(result2, ArticleResult)
        assert result2 is result1  # Same object from cache
