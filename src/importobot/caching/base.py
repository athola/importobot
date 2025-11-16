"""Defines base cache abstractions and policies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class EvictionPolicy(Enum):
    """Enumerates available cache eviction strategies."""

    LRU = "lru"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass(frozen=True)
class CacheConfig:
    """Represents a unified cache configuration."""

    max_size: int = 1000
    ttl_seconds: float | None = None
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    max_content_size_bytes: int = 50000
    enable_telemetry: bool = True


class CacheStrategy(ABC, Generic[K, V]):
    """Abstract base class for all cache implementations."""

    @abstractmethod
    def get(self, key: K) -> V | None:
        """Retrieve a value by its key."""

    @abstractmethod
    def set(self, key: K, value: V) -> None:
        """Store a value associated with a key."""

    @abstractmethod
    def delete(self, key: K) -> None:
        """Remove an entry from the cache."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Retrieve cache statistics."""

    def contains(self, key: K) -> bool:
        """Check if a key exists in the cache."""
        return self.get(key) is not None


__all__ = ["CacheConfig", "CacheStrategy", "EvictionPolicy"]
