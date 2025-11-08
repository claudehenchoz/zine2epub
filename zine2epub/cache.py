"""Caching system for HTML content and images."""

import hashlib
from pathlib import Path
from typing import Optional


class Cache:
    """Simple file-based cache for web content."""

    def __init__(self, cache_dir: str = ".cache"):
        """Initialize cache with specified directory.

        Args:
            cache_dir: Directory to store cached files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from a URL.

        Args:
            url: The URL to generate a key for

        Returns:
            SHA256 hash of the URL
        """
        return hashlib.sha256(url.encode()).hexdigest()

    def _get_cache_path(self, key: str, extension: str = ".html") -> Path:
        """Get the cache file path for a given key.

        Args:
            key: The cache key
            extension: File extension for the cached content

        Returns:
            Path to the cache file
        """
        return self.cache_dir / f"{key}{extension}"

    def get(self, url: str, binary: bool = False) -> Optional[str | bytes]:
        """Retrieve cached content for a URL.

        Args:
            url: The URL to retrieve content for
            binary: Whether to read as binary (for images)

        Returns:
            Cached content if available, None otherwise
        """
        key = self._get_cache_key(url)
        extension = ".bin" if binary else ".html"
        cache_path = self._get_cache_path(key, extension)

        if not cache_path.exists():
            return None

        mode = "rb" if binary else "r"
        encoding = None if binary else "utf-8"

        try:
            with open(cache_path, mode, encoding=encoding) as f:
                return f.read()
        except Exception:
            return None

    def set(self, url: str, content: str | bytes, binary: bool = False) -> None:
        """Store content in cache for a URL.

        Args:
            url: The URL to cache content for
            content: The content to cache
            binary: Whether to write as binary (for images)
        """
        key = self._get_cache_key(url)
        extension = ".bin" if binary else ".html"
        cache_path = self._get_cache_path(key, extension)

        mode = "wb" if binary else "w"
        encoding = None if binary else "utf-8"

        try:
            with open(cache_path, mode, encoding=encoding) as f:
                f.write(content)
        except Exception:
            pass  # Silently fail on cache write errors


# Global cache instance
_cache = Cache()


def get_cache() -> Cache:
    """Get the global cache instance.

    Returns:
        The global Cache instance
    """
    return _cache
