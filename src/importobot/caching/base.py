"""Base cache abstractions and policies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class EvictionPolicy(Enum):
    """Cache eviction strategies."""

    LRU = "lru"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass(frozen=True)
class CacheConfig:
    """Unified cache configuration."""

    max_size: int = 1000
    ttl_seconds: float | None = None
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    max_content_size_bytes: int = 50000
    enable_telemetry: bool = True


class CacheStrategy(ABC, Generic[K, V]):
    """Abstract base for all cache implementations."""

    @abstractmethod
    def get(self, key: K) -> V | None:
        """Retrieve value by key."""

    @abstractmethod
    def set(self, key: K, value: V) -> None:
        """Store value with key."""

    @abstractmethod
    def delete(self, key: K) -> None:
        """Remove entry from cache."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""

    def contains(self, key: K) -> bool:
        """Check if key exists in cache."""
        return self.get(key) is not None


__all__ = ["CacheConfig", "CacheStrategy", "EvictionPolicy"]
