"""News fetching service using yfinance built-in news attribute.

This module fetches news using the yfinance Ticker.news attribute, which provides
rich news data directly without requiring RSS parsing or external API keys.

Data source: yfinance Ticker.news (Yahoo Finance news API)
Structure: List of dicts with content.title, content.summary, content.pubDate, etc.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import yfinance as yf  # type: ignore[import-untyped]


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
    Fetch news for the given ticker using yfinance.

    Args:
        ticker: Stock/crypto ticker symbol (e.g., 'AAPL', 'BTC-USD')
        timeout: Maximum time to wait for response in seconds (unused, for compatibility)
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

    # Fetch news in executor (yfinance is blocking)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            _fetch_news_sync,
            ticker,
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


def _fetch_news_sync(ticker: str, max_items: int) -> NewsResult:
    """
    Synchronous news fetch using yfinance Ticker.news attribute.

    Args:
        ticker: Stock/crypto ticker symbol
        max_items: Maximum number of news items to return

    Returns:
        List of NewsItem on success, NewsError on failure
    """
    try:
        # Create yfinance Ticker object
        ticker_obj = yf.Ticker(ticker)

        # Fetch news using .news attribute
        news_data: list[dict[str, Any]] = ticker_obj.news

        # If no news available
        if not news_data:
            return NewsError(ticker=ticker, error_message="No news available")

        # Extract news items
        items: list[NewsItem] = []
        for news_item in news_data[:max_items]:
            try:
                # Validate that we have a "content" key - skip if not
                if "content" not in news_item or not isinstance(news_item["content"], dict):
                    continue

                content = news_item["content"]

                # Extract title from content.title - require it to be valid
                title = content.get("title")
                if not title or not isinstance(title, str):
                    continue

                # Extract summary from content.summary
                summary = content.get("summary")
                if summary is not None and not isinstance(summary, str):
                    summary = None

                # Extract URL from content.previewUrl or content.canonicalUrl.url
                url = content.get("previewUrl")
                if not url:
                    canonical_url = content.get("canonicalUrl")
                    if isinstance(canonical_url, dict):
                        url = canonical_url.get("url", "")
                    else:
                        url = ""
                if not isinstance(url, str):
                    url = ""

                # Extract source from content.provider.displayName
                source = "Yahoo Finance"  # Default
                provider = content.get("provider")
                if isinstance(provider, dict):
                    display_name = provider.get("displayName")
                    if isinstance(display_name, str):
                        source = display_name

                # Extract and parse published date from content.pubDate
                pub_date_str = content.get("pubDate")
                published_at = datetime.now()  # Default to now
                if pub_date_str and isinstance(pub_date_str, str):
                    try:
                        # Parse ISO format string (e.g., "2024-01-15T10:30:00Z")
                        published_at = datetime.fromisoformat(
                            pub_date_str.replace("Z", "+00:00")
                        )
                    except Exception:
                        # If parsing fails, use current time
                        published_at = datetime.now()

                items.append(
                    NewsItem(
                        title=title,
                        source=source,
                        url=url,
                        published_at=published_at,
                        summary=summary,
                    )
                )
            except Exception:
                # Skip malformed news items
                continue

        # If no valid items after parsing
        if not items:
            return NewsError(ticker=ticker, error_message="No news available")

        return items

    except Exception as e:
        return NewsError(ticker=ticker, error_message=f"Unexpected error: {str(e)}")


def _safe_get_nested(
    data: dict[str, Any], keys: list[str], default: Any = None
) -> Any:
    """
    Safely navigate nested dictionary structure.

    Args:
        data: Dictionary to navigate
        keys: List of keys to traverse
        default: Default value if key path doesn't exist

    Returns:
        Value at key path or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


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
