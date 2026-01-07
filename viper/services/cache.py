"""Generic in-memory cache with TTL (time-to-live) support."""

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with value and timestamp."""

    value: T
    timestamp: datetime


class TTLCache(Generic[T]):
    """Thread-safe in-memory cache with TTL expiration.

    This cache stores values with a time-to-live (TTL) and automatically
    expires entries that are older than the TTL when accessed.
    """

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: Time-to-live in seconds for cache entries (default: 60).
        """
        self._ttl = timedelta(seconds=ttl_seconds)
        self._cache: dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> T | None:
        """Get a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value if present and not expired, None otherwise.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            # Check if entry has expired
            if datetime.now() - entry.timestamp > self._ttl:
                # Remove expired entry
                del self._cache[key]
                return None

            return entry.value

    def set(self, key: str, value: T) -> None:
        """Set a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
        """
        with self._lock:
            self._cache[key] = CacheEntry(value=value, timestamp=datetime.now())

    def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: The cache key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()

    def has(self, key: str) -> bool:
        """Check if a key exists and is not expired.

        Args:
            key: The cache key to check.

        Returns:
            True if the key exists and is not expired.
        """
        return self.get(key) is not None

    def size(self) -> int:
        """Get the number of entries in the cache (including expired).

        Returns:
            Number of entries in the cache.
        """
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key
                for key, entry in self._cache.items()
                if now - entry.timestamp > self._ttl
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


# Pre-configured cache instances for different data types
# Historical data cache - 5 minutes TTL
historical_data_cache: TTLCache[Any] = TTLCache(ttl_seconds=300.0)

# News cache - 2 minutes TTL
news_cache: TTLCache[Any] = TTLCache(ttl_seconds=120.0)

# Quote cache - 30 seconds TTL
quote_cache: TTLCache[Any] = TTLCache(ttl_seconds=30.0)


def clear_ticker_caches(ticker: str) -> None:
    """Clear all caches for a specific ticker.

    Args:
        ticker: The ticker symbol to clear from all caches.
    """
    ticker_upper = ticker.upper()
    historical_data_cache.delete(ticker_upper)
    news_cache.delete(ticker_upper)
    quote_cache.delete(ticker_upper)


def clear_all_caches() -> None:
    """Clear all caches completely."""
    historical_data_cache.clear()
    news_cache.clear()
    quote_cache.clear()
