"""Owned local pipeline runs and conservative stale-run reconciliation.

An exclusive advisory pipeline lock is held for the whole run. Once acquired,
no other cooperating process can still own that pipeline. Only old RUNNING rows
registered under this protocol are reconciled; legacy unowned rows are left
alone because their liveness cannot be established safely. SIGKILL releases
the OS lock, not Python cleanup. No PID-reuse assumptions or heartbeat expiry.
"""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from intelligence import config as cfg
from intelligence.errors import OperationLockError
from intelligence.db.locking import advisory_lock

_TABLES = {'clean': 'cleaning_run_log', 'dedupe': 'dedup_run_log', 'relevance': 'relevance_run_log', 'uae_relevance': 'uae_relevance_run_log', 'entities': 'entity_extraction_run_log', 'events': 'event_run_log', 'metrics': 'metric_run_log', 'intelligence': 'intelligence_run_log'}


@dataclass
class RunLease:
    pipeline: str
    token: str
    database: str
    active: bool = True

    def check(self):
        if not self.active or self.database != str(cfg.DB_PATH.resolve()):
            raise OperationLockError('Run ownership is not active for this database')


@contextmanager
def pipeline_guard(pipeline: str):
    if pipeline not in _TABLES:
        raise OperationLockError('Unknown operational pipeline')
    database = cfg.DB_PATH.resolve()
    path = database.parent / f'.{database.name}.{pipeline}.lock'
    with advisory_lock(path):
        lease = RunLease(pipeline, str(uuid.uuid4()), str(database))
        try:
            yield lease
        finally:
            lease.active = False


def register_run(conn, lease: RunLease, run_id: str, started_at: str, *, since=None):
    lease.check()
    conn.execute('INSERT INTO pipeline_run_owners VALUES (?,?,?,?,?,NULL)',
                 (lease.pipeline, run_id, lease.token, started_at, since))


def reconcile_stale_runs(conn, lease: RunLease, *, now: datetime | None = None) -> int:
    lease.check()
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise OperationLockError('Recovery time must be timezone-aware')
    table = _TABLES[lease.pipeline]  # Internal allowlist, never user SQL.
    count = 0
    with conn:
        rows = conn.execute(
            f"SELECT r.run_id,r.started_at,r.error_count,r.errors_json FROM {table} r "
            "JOIN pipeline_run_owners o ON o.run_id=r.run_id "
            "WHERE o.pipeline=? AND r.status='RUNNING'", (lease.pipeline,),
        ).fetchall()
        for row in rows:
            try:
                started = datetime.fromisoformat(row['started_at'])
                if started.utcoffset() is None or (now-started).total_seconds() < cfg.STALE_RUN_SECONDS:
                    continue
                errors = json.loads(row['errors_json'])
                if not isinstance(errors, list):
                    errors = []
            except (ValueError, TypeError):
                continue
            errors = errors[:99] + [{'type':'AbortedRun','reason':'Owner lock released before finalization'}]
            conn.execute(
                f"UPDATE {table} SET status='FAILED',completed_at=?,duration_ms=?,error_count=?,"
                "error_type='AbortedRun',error_message='Stale owned run reconciled after lock recovery',"
                "errors_json=? WHERE run_id=? AND status='RUNNING'",
                (now.isoformat(),int((now-started).total_seconds()*1000),row['error_count']+1,
                 json.dumps(errors,sort_keys=True),row['run_id']),
            )
            count += 1
    return count
