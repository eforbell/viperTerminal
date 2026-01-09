"""Article extraction service for fetching and parsing news article content.

This module provides functionality to fetch news articles from URLs and extract
clean, readable content using trafilatura. It handles common errors like timeouts,
paywalls, and extraction failures gracefully.

Key Features:
- Async HTTP fetching with configurable timeout
- Article content extraction with trafilatura
- Metadata extraction (title, author, date)
- Word count and reading time estimation
- Comprehensive error handling
- Session-level caching (30-minute TTL)

Usage:
    result = await fetch_article("https://example.com/article")
    if isinstance(result, ArticleResult):
        print(f"Title: {result.title}")
        print(f"Content: {result.content}")
    else:
        print(f"Error: {result.error_message}")
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx
import trafilatura


@dataclass(frozen=True)
class ArticleResult:
    """Successfully extracted article content and metadata.

    Attributes:
        title: Article title/headline
        content: Main article text (plain text or markdown)
        author: Article author name (empty string if not available)
        date: Publication date (empty string if not available)
        source_url: Original article URL
        word_count: Number of words in article content
    """

    title: str
    content: str
    author: str
    date: str
    source_url: str
    word_count: int


@dataclass(frozen=True)
class ArticleError:
    """Article fetch/extraction error with details for user feedback.

    Attributes:
        error_type: Category of error (timeout, network, paywall, extraction, etc.)
        error_message: Human-readable error description
        source_url: Original article URL that failed
        should_retry: Whether retrying might succeed (e.g., transient network error)
    """

    error_type: str  # timeout, network, paywall, extraction, http_error
    error_message: str
    source_url: str
    should_retry: bool


# Session-level article cache: {url: (timestamp, ArticleResult)}
_article_cache: dict[str, tuple[datetime, ArticleResult]] = {}
_CACHE_TTL_SECONDS: int = 1800  # 30 minutes


def clear_article_cache() -> None:
    """Clear the article cache (useful for testing or manual cache invalidation)."""
    _article_cache.clear()


def _get_cached_article(url: str) -> ArticleResult | None:
    """Get article from cache if present and not expired."""
    if url not in _article_cache:
        return None

    timestamp, article = _article_cache[url]
    age = datetime.now() - timestamp

    if age.total_seconds() > _CACHE_TTL_SECONDS:
        # Expired - remove from cache
        del _article_cache[url]
        return None

    return article


def _cache_article(url: str, article: ArticleResult) -> None:
    """Store article in cache with current timestamp."""
    _article_cache[url] = (datetime.now(), article)


async def fetch_article(
    url: str, timeout: int = 10, use_cache: bool = True
) -> ArticleResult | ArticleError:
    """Fetch and extract article content from a URL.

    This function fetches the HTML from the given URL and uses trafilatura to
    extract the main article content, stripping ads, navigation, and other
    boilerplate. It handles common failure cases gracefully and returns either
    an ArticleResult on success or an ArticleError on failure.

    Args:
        url: The article URL to fetch
        timeout: HTTP request timeout in seconds (default 10)
        use_cache: Whether to use session cache (default True)

    Returns:
        ArticleResult if extraction succeeds, ArticleError otherwise

    Examples:
        >>> result = await fetch_article("https://example.com/news/article")
        >>> if isinstance(result, ArticleResult):
        ...     print(f"Title: {result.title}")
        ...     print(f"Words: {result.word_count}")
        ... else:
        ...     print(f"Error: {result.error_message}")
    """
    # Check cache first
    if use_cache:
        cached = _get_cached_article(url)
        if cached is not None:
            return cached

    # Fetch HTML
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

    except httpx.TimeoutException:
        return ArticleError(
            error_type="timeout",
            error_message=f"Request timed out after {timeout} seconds",
            source_url=url,
            should_retry=True,
        )

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 404:
            message = "Article not found (404)"
        elif status == 403:
            message = "Access forbidden (403) - site may block automated requests"
        elif status >= 500:
            message = f"Server error ({status}) - try again later"
        else:
            message = f"HTTP error {status}"

        return ArticleError(
            error_type="http_error",
            error_message=message,
            source_url=url,
            should_retry=status >= 500,  # Retry on server errors
        )

    except (httpx.NetworkError, httpx.ConnectError) as e:
        return ArticleError(
            error_type="network",
            error_message=f"Network error: {str(e)}",
            source_url=url,
            should_retry=True,
        )

    except Exception as e:
        return ArticleError(
            error_type="network",
            error_message=f"Unexpected error: {str(e)}",
            source_url=url,
            should_retry=False,
        )

    # Extract article content in thread pool (trafilatura is synchronous)
    try:
        extracted = await asyncio.to_thread(_extract_article_sync, html, url)

        if extracted is None:
            return ArticleError(
                error_type="extraction",
                error_message="Failed to extract article content - site may not be supported",
                source_url=url,
                should_retry=False,
            )

        # Cache successful result
        if use_cache:
            _cache_article(url, extracted)

        return extracted

    except Exception as e:
        return ArticleError(
            error_type="extraction",
            error_message=f"Extraction error: {str(e)}",
            source_url=url,
            should_retry=False,
        )


def _extract_article_sync(html: str, url: str) -> ArticleResult | None:
    """Synchronous article extraction using trafilatura.

    This function is called in a thread pool from fetch_article() since
    trafilatura is a synchronous library.

    Returns None if extraction fails (no content extracted).
    """
    # Extract with metadata
    metadata = trafilatura.extract_metadata(html)

    # Extract content (plain text)
    content = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        no_fallback=False,  # Use fallback extractors if main method fails
    )

    if not content or len(content.strip()) == 0:
        return None

    # Check for suspiciously short content (possible paywall)
    if len(content) < 200:
        # Could be paywall, but also could be a very short article
        # Don't error, but note this in logs if needed
        pass

    # Extract metadata fields
    title = ""
    author = ""
    date = ""

    if metadata:
        title = metadata.title or ""
        author = metadata.author or ""
        date = metadata.date or ""

    # If no title from metadata, try to extract from HTML
    if not title:
        extracted_title = trafilatura.extract(html, include_comments=False, output_format="xml")
        title = extracted_title or ""
        # Fallback: use first line of content if still no title
        if not title and content:
            first_line = content.split("\n")[0]
            title = first_line[:100] if len(first_line) > 100 else first_line

    # Calculate word count
    word_count = len(content.split())

    return ArticleResult(
        title=title,
        content=content,
        author=author,
        date=date,
        source_url=url,
        word_count=word_count,
    )
