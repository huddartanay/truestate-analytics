"""Stable signatures for immutable input cohorts, without full SQL row copies."""

import hashlib
import json


def _sql_value(value):
    # SQLite may contain malformed BLOBs in TEXT columns. Their typed signature
    # must remain stable so row validation can isolate them after snapshotting.
    if isinstance(value, bytes):
        return {'sqlite_blob_hex': value.hex()}
    raise TypeError('Unsupported SQLite value')


def cleaned_signature(conn, cleaning_version: str) -> str:
    digest = hashlib.sha256()
    for row in conn.execute('SELECT * FROM cleaned_articles WHERE cleaning_version=? ORDER BY article_id,raw_hash',
                            (cleaning_version,)):
        digest.update(json.dumps(dict(row),sort_keys=True,ensure_ascii=True,separators=(',', ':'),default=_sql_value).encode())
        digest.update(b'\n')
    return digest.hexdigest()
