"""Stable identities shared by event models and persistence; no I/O."""
import hashlib
import json

UPSTREAM_KEY = ('article_id', 'raw_hash', 'cleaning_version', 'dedup_version',
                'relevance_version', 'context_id', 'uae_relevance_version',
                'registry_version', 'entity_extraction_version', 'entity_registry_version')


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def result_id(extraction_id, version):
    return digest([extraction_id, version])


def event_id(result, kind, field, start, end, rule, direction, evidence, links):
    return digest([result, kind, field, start, end, rule, direction, evidence,
                   [(link.entity_id, link.mention_index) for link in links]])
