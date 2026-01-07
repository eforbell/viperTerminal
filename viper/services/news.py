"""News fetching service using Yahoo Finance RSS feeds."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import feedparser  # type: ignore[import-untyped]
import httpx


@dataclass
class NewsItem:
    """A single news item."""

    title: str
    source: str
    url: str
    published_at: datetime
    summary: Optional[str] = None


@dataclass
class NewsError:
    """Error result from news fetch."""

    ticker: str
    error_message: str


# Type alias for result
NewsResult = list[NewsItem] | NewsError

# Cache dictionary: ticker -> (timestamp, NewsResult)
_cache: dict[str, tuple[datetime, NewsResult]] = {}
_CACHE_TTL_SECONDS = 120  # 2 minutes


async def fetch_news(
    ticker: str,
    timeout: float = 10.0,
    max_items: int = 10,
    use_cache: bool = True,
) -> NewsResult:
    """
    Fetch news for the given ticker from Yahoo Finance RSS.

    Args:
        ticker: Stock/crypto ticker symbol (e.g., 'AAPL', 'BTC')
        timeout: Maximum time to wait for response in seconds
        max_items: Maximum number of news items to return
        use_cache: Whether to use cached results if available

    Returns:
        List of NewsItem on success, NewsError on failure

    Note:
        Results are cached for 2 minutes to reduce API calls.
        Network errors are handled gracefully.
    """
    ticker = ticker.upper().strip()

    # Check cache
    if use_cache and ticker in _cache:
        cached_time, cached_result = _cache[ticker]
        if datetime.now() - cached_time < timedelta(seconds=_CACHE_TTL_SECONDS):
            return cached_result

    # Fetch news in executor (feedparser is blocking)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            _fetch_news_sync,
            ticker,
            timeout,
            max_items,
        )
        # Cache result
        _cache[ticker] = (datetime.now(), result)
        return result
    except Exception as e:
        error_result = NewsError(
            ticker=ticker, error_message=f"Failed to fetch news: {str(e)}"
        )
        _cache[ticker] = (datetime.now(), error_result)
        return error_result


def _fetch_news_sync(ticker: str, timeout: float, max_items: int) -> NewsResult:
    """
    Synchronous news fetch using feedparser and httpx.

    Args:
        ticker: Stock/crypto ticker symbol
        timeout: Maximum time to wait for response in seconds
        max_items: Maximum number of news items to return

    Returns:
        List of NewsItem on success, NewsError on failure
    """
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"

    try:
        # Fetch RSS feed
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()

        # Parse RSS feed
        feed = feedparser.parse(response.content)

        # Check for parsing errors
        if feed.bozo and isinstance(feed.get("bozo_exception"), Exception):
            return NewsError(
                ticker=ticker,
                error_message=f"Failed to parse RSS feed: {feed.bozo_exception}",
            )

        # Extract news items
        items: list[NewsItem] = []
        for entry in feed.entries[:max_items]:
            # Parse published date
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    # Convert time.struct_time to datetime
                    import time

                    published_at = datetime.fromtimestamp(
                        time.mktime(entry.published_parsed)
                    )
                except Exception:
                    published_at = datetime.now()
            else:
                published_at = datetime.now()

            # Extract summary
            summary = None
            if hasattr(entry, "summary") and entry.summary:
                summary = entry.summary

            # Extract source (usually in title after '-')
            source = "Yahoo Finance"
            title = entry.title if hasattr(entry, "title") else "No title"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    source = parts[1].strip()

            items.append(
                NewsItem(
                    title=title,
                    source=source,
                    url=entry.link if hasattr(entry, "link") else "",
                    published_at=published_at,
                    summary=summary,
                )
            )

        # If no items, return error
        if not items:
            return NewsError(ticker=ticker, error_message="No news available")

        return items

    except httpx.TimeoutException:
        return NewsError(ticker=ticker, error_message="Request timed out")
    except httpx.ConnectError:
        return NewsError(ticker=ticker, error_message="Failed to connect to news server")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return NewsError(ticker=ticker, error_message="No news feed available")
        return NewsError(
            ticker=ticker, error_message=f"HTTP error: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        return NewsError(ticker=ticker, error_message=f"Network error: {str(e)}")
    except Exception as e:
        return NewsError(ticker=ticker, error_message=f"Unexpected error: {str(e)}")


def clear_news_cache(ticker: Optional[str] = None) -> None:
    """
    Clear the news cache.

    Args:
        ticker: If provided, clear only for that ticker. Otherwise clear all.
    """
    global _cache
    if ticker is None:
        _cache.clear()
    else:
        _cache.pop(ticker.upper().strip(), None)
