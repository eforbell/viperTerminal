"""MCP tool for fetching news."""

from viper.mcp.serializers import serialize_datetime
from viper.mcp.server import mcp
from viper.services.news import NewsError, NewsItem, fetch_news


@mcp.tool()
async def get_news(ticker: str, max_items: int = 10) -> dict[str, object]:
    """Get recent news headlines for a stock or cryptocurrency.

    Args:
        ticker: Ticker symbol, e.g. "AAPL", "BTC-USD"
        max_items: Maximum number of news items to return (default 10)

    Returns:
        List of news items with title, source, URL, and published date.
    """
    result = await fetch_news(ticker, max_items=max_items)

    if isinstance(result, NewsError):
        return {"error": result.error_message, "symbol": result.ticker}

    assert isinstance(result, list)
    items: list[dict[str, object]] = []
    for item in result:
        items.append({
            "title": item.title,
            "source": item.source,
            "url": item.url,
            "published_at": serialize_datetime(item.published_at),
            "summary": item.summary,
        })

    return {
        "symbol": ticker.upper().strip(),
        "count": len(items),
        "items": items,
    }
