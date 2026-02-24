"""Tests for MCP get_news tool."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from viper.mcp.tools.news import get_news
from viper.services.news import NewsError, NewsItem


class TestGetNews:
    """Tests for the get_news MCP tool."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Should return news items on success."""
        pub_date = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        with patch(
            "viper.mcp.tools.news.fetch_news", new_callable=AsyncMock
        ) as mock:
            mock.return_value = [
                NewsItem(
                    title="Apple reports record earnings",
                    source="Reuters",
                    url="https://example.com/article",
                    published_at=pub_date,
                    summary="Apple Inc. reported...",
                ),
            ]

            result = await get_news("AAPL")

            assert result["symbol"] == "AAPL"
            assert result["count"] == 1
            items = result["items"]
            assert isinstance(items, list)
            assert items[0]["title"] == "Apple reports record earnings"
            assert items[0]["source"] == "Reuters"
            assert items[0]["published_at"] == "2024-06-15T10:00:00+00:00"
            assert items[0]["summary"] == "Apple Inc. reported..."
            mock.assert_awaited_once_with("AAPL", max_items=10)

    @pytest.mark.asyncio
    async def test_custom_max_items(self) -> None:
        """Should pass max_items to the service."""
        with patch(
            "viper.mcp.tools.news.fetch_news", new_callable=AsyncMock
        ) as mock:
            mock.return_value = NewsError(ticker="AAPL", error_message="test")

            await get_news("AAPL", max_items=5)

            mock.assert_awaited_once_with("AAPL", max_items=5)

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        """Should return error dict on failure."""
        with patch(
            "viper.mcp.tools.news.fetch_news", new_callable=AsyncMock
        ) as mock:
            mock.return_value = NewsError(
                ticker="INVALID", error_message="No news available"
            )

            result = await get_news("INVALID")

            assert result["error"] == "No news available"
            assert result["symbol"] == "INVALID"
