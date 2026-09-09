"""Connected components of positive content relationships only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

from intelligence.deduplication.normalize import Identity, PreparedArticle, stable_hash


@dataclass(frozen=True)
class DuplicateGroup:
    group_id: str
    canonical: Identity
    members: tuple[Identity, ...]


def canonical_key(record: PreparedArticle) -> tuple:
    """Established publication first, earliest UTC time, more body words, ID.

    No trust lookup or changing registry state; missing publication sorts last.
    Canonical is a representative, not a claim of truth or source authority.
    """
    published = record.article.normalized_published_at
    return (published is None, published or datetime.max.replace(tzinfo=timezone.utc),
            -record.body_words, record.identity)


def build_groups(records: Mapping[Identity, PreparedArticle],
                 edges: Iterable[tuple[Identity, Identity]], *,
                 cleaning_version: str, dedup_version: str) -> list[DuplicateGroup]:
    parent: dict[Identity, Identity] = {}

    def find(node):
        parent.setdefault(node, node)
        while node != parent[node]:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in edges:
        if a not in records or b not in records or a == b:
            continue
        x, y = find(a), find(b)
        parent[max(x, y)] = min(x, y)
    components: dict[Identity, list[Identity]] = {}
    for node in sorted(parent):
        components.setdefault(find(node), []).append(node)
    groups = []
    for members in components.values():
        ordered = tuple(sorted(members))
        canonical = min(ordered, key=lambda key: canonical_key(records[key]))
        group_id = stable_hash([cleaning_version, dedup_version, ordered])
        groups.append(DuplicateGroup(group_id, canonical, ordered))
    return sorted(groups, key=lambda group: group.group_id)
