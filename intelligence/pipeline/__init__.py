"""
Background ingestion pipeline for the intelligence layer.

Stage 4 provides only the fetcher: RSS URL from the verified registry →
raw article records on disk and sightings in SQLite. No cleaning, no
deduplication engine, no LLM. Invoke as:

    python -m intelligence.pipeline.run --fetch-only
"""
