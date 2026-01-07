"""Tests for the cache service."""

import threading
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from viper.services.cache import (
    CacheEntry,
    TTLCache,
    clear_all_caches,
    clear_ticker_caches,
    historical_data_cache,
    news_cache,
    quote_cache,
)


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_cache_entry_creation(self) -> None:
        """Test creating a cache entry."""
        now = datetime.now()
        entry: CacheEntry[str] = CacheEntry(value="test_value", timestamp=now)
        assert entry.value == "test_value"
        assert entry.timestamp == now

    def test_cache_entry_with_complex_type(self) -> None:
        """Test cache entry with complex types."""
        data = {"key": "value", "list": [1, 2, 3]}
        entry: CacheEntry[dict[str, object]] = CacheEntry(
            value=data, timestamp=datetime.now()
        )
        assert entry.value == data


class TestTTLCacheBasics:
    """Test basic TTLCache operations."""

    def test_cache_initialization(self) -> None:
        """Test cache initializes correctly."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        assert cache.size() == 0

    def test_cache_set_and_get(self) -> None:
        """Test setting and getting values."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        cache.set("key1", "value1")
        
        result = cache.get("key1")
        assert result == "value1"

    def test_cache_get_nonexistent(self) -> None:
        """Test getting a nonexistent key returns None."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_has_existing_key(self) -> None:
        """Test has() returns True for existing key."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        cache.set("key1", "value1")
        assert cache.has("key1") is True

    def test_cache_has_nonexistent_key(self) -> None:
        """Test has() returns False for nonexistent key."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        assert cache.has("nonexistent") is False

    def test_cache_delete_existing(self) -> None:
        """Test deleting an existing key."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        cache.set("key1", "value1")
        
        result = cache.delete("key1")
        assert result is True
        assert cache.get("key1") is None

    def test_cache_delete_nonexistent(self) -> None:
        """Test deleting a nonexistent key returns False."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        result = cache.delete("nonexistent")
        assert result is False

    def test_cache_clear(self) -> None:
        """Test clearing the cache."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_size(self) -> None:
        """Test cache size tracking."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        assert cache.size() == 0
        
        cache.set("key1", "value1")
        assert cache.size() == 1
        
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.delete("key1")
        assert cache.size() == 1

    def test_cache_overwrite_value(self) -> None:
        """Test overwriting an existing value."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        
        assert cache.get("key1") == "value2"
        assert cache.size() == 1


class TestTTLCacheExpiration:
    """Test TTL expiration behavior."""

    def test_cache_expires_old_entries(self) -> None:
        """Test that old entries are expired on get."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=0.1)  # 100ms TTL
        cache.set("key1", "value1")
        
        # Value should be available immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Value should be expired
        assert cache.get("key1") is None

    def test_cache_has_respects_ttl(self) -> None:
        """Test that has() respects TTL."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=0.1)
        cache.set("key1", "value1")
        
        assert cache.has("key1") is True
        
        time.sleep(0.15)
        
        assert cache.has("key1") is False

    def test_cleanup_expired(self) -> None:
        """Test cleanup_expired removes old entries."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=0.1)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        time.sleep(0.15)
        
        # Add a fresh entry
        cache.set("key3", "value3")
        
        removed = cache.cleanup_expired()
        
        assert removed == 2
        assert cache.size() == 1
        assert cache.get("key3") == "value3"

    def test_cleanup_expired_empty_cache(self) -> None:
        """Test cleanup on empty cache."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=60.0)
        removed = cache.cleanup_expired()
        assert removed == 0

    def test_refresh_entry_extends_ttl(self) -> None:
        """Test that re-setting extends TTL."""
        cache: TTLCache[str] = TTLCache(ttl_seconds=0.2)
        cache.set("key1", "value1")
        
        time.sleep(0.1)
        
        # Re-set the value to refresh TTL
        cache.set("key1", "updated")
        
        time.sleep(0.15)
        
        # Should still be valid because we refreshed
        assert cache.get("key1") == "updated"


class TestTTLCacheThreadSafety:
    """Test thread safety of TTLCache."""

    def test_concurrent_reads(self) -> None:
        """Test concurrent read operations."""
        cache: TTLCache[int] = TTLCache(ttl_seconds=60.0)
        cache.set("key1", 42)
        
        results: list[int | None] = []
        
        def read_value() -> None:
            for _ in range(100):
                result = cache.get("key1")
                results.append(result)
        
        threads = [threading.Thread(target=read_value) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All reads should succeed
        assert all(r == 42 for r in results)

    def test_concurrent_writes(self) -> None:
        """Test concurrent write operations."""
        cache: TTLCache[int] = TTLCache(ttl_seconds=60.0)
        
        def write_values(start: int) -> None:
            for i in range(100):
                cache.set(f"key{start + i}", start + i)
        
        threads = [
            threading.Thread(target=write_values, args=(i * 100,))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All writes should succeed
        assert cache.size() == 500

    def test_concurrent_read_write(self) -> None:
        """Test concurrent read and write operations."""
        cache: TTLCache[int] = TTLCache(ttl_seconds=60.0)
        errors: list[Exception] = []
        
        def read_loop() -> None:
            try:
                for _ in range(100):
                    cache.get("key1")
            except Exception as e:
                errors.append(e)
        
        def write_loop() -> None:
            try:
                for i in range(100):
                    cache.set("key1", i)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=read_loop),
            threading.Thread(target=write_loop),
            threading.Thread(target=read_loop),
            threading.Thread(target=write_loop),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0


class TestPreConfiguredCaches:
    """Test pre-configured cache instances."""

    def test_historical_data_cache_exists(self) -> None:
        """Test historical data cache is configured."""
        assert historical_data_cache is not None
        # TTL should be 5 minutes (300 seconds)
        assert historical_data_cache._ttl == timedelta(seconds=300.0)

    def test_news_cache_exists(self) -> None:
        """Test news cache is configured."""
        assert news_cache is not None
        # TTL should be 2 minutes (120 seconds)
        assert news_cache._ttl == timedelta(seconds=120.0)

    def test_quote_cache_exists(self) -> None:
        """Test quote cache is configured."""
        assert quote_cache is not None
        # TTL should be 30 seconds
        assert quote_cache._ttl == timedelta(seconds=30.0)


class TestCacheHelpers:
    """Test cache helper functions."""

    def test_clear_ticker_caches(self) -> None:
        """Test clearing caches for a specific ticker."""
        # Set up data in all caches
        historical_data_cache.set("AAPL", {"data": "historical"})
        news_cache.set("AAPL", {"data": "news"})
        quote_cache.set("AAPL", {"data": "quote"})
        
        # Also set other tickers
        historical_data_cache.set("MSFT", {"data": "msft"})
        
        # Clear AAPL from all caches
        clear_ticker_caches("AAPL")
        
        # AAPL should be gone from all caches
        assert historical_data_cache.get("AAPL") is None
        assert news_cache.get("AAPL") is None
        assert quote_cache.get("AAPL") is None
        
        # MSFT should still exist
        assert historical_data_cache.get("MSFT") == {"data": "msft"}

    def test_clear_ticker_caches_case_insensitive(self) -> None:
        """Test clearing caches handles case properly."""
        historical_data_cache.set("AAPL", {"data": "test"})
        
        # Clear with lowercase should still work (normalized to uppercase)
        clear_ticker_caches("aapl")
        
        assert historical_data_cache.get("AAPL") is None

    def test_clear_all_caches(self) -> None:
        """Test clearing all caches."""
        # Set up data in all caches
        historical_data_cache.set("AAPL", {"data": "historical"})
        historical_data_cache.set("MSFT", {"data": "historical2"})
        news_cache.set("AAPL", {"data": "news"})
        quote_cache.set("AAPL", {"data": "quote"})
        
        # Clear all
        clear_all_caches()
        
        # All caches should be empty
        assert historical_data_cache.size() == 0
        assert news_cache.size() == 0
        assert quote_cache.size() == 0


class TestCacheWithComplexTypes:
    """Test cache with various data types."""

    def test_cache_list_values(self) -> None:
        """Test caching list values."""
        cache: TTLCache[list[int]] = TTLCache(ttl_seconds=60.0)
        cache.set("numbers", [1, 2, 3, 4, 5])
        
        result = cache.get("numbers")
        assert result == [1, 2, 3, 4, 5]

    def test_cache_dict_values(self) -> None:
        """Test caching dict values."""
        cache: TTLCache[dict[str, str]] = TTLCache(ttl_seconds=60.0)
        cache.set("config", {"host": "localhost", "port": "8080"})
        
        result = cache.get("config")
        assert result == {"host": "localhost", "port": "8080"}

    def test_cache_none_value(self) -> None:
        """Test caching None values (edge case)."""
        cache: TTLCache[None] = TTLCache(ttl_seconds=60.0)
        cache.set("null_key", None)
        
        # get() returns None for both "not found" and "value is None"
        # Use has() to distinguish
        # Note: This is a known limitation - None values are ambiguous
        result = cache.get("null_key")
        assert result is None
