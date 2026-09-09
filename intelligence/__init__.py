"""
UAE Real Estate Intelligence Layer.

This package is a sibling of `platform_core/` and `regions/`. It is
self-contained: nothing in `platform_core/` or `regions/` imports from here,
and deleting this package leaves the existing app running unchanged.

Stage 3 scope: RSS source registry only. No ingestion, no cleaning, no
deduplication, no LLM integration. See `intelligence/sources/registry.py`.
"""

__version__ = "0.1.0"
