"""Offline, non-destructive Stage 7 article-content duplicate detection."""

from intelligence.deduplication.compare import compare
from intelligence.deduplication.normalize import prepare

__all__ = ["compare", "prepare"]
