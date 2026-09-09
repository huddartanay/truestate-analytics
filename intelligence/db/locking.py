"""Bounded POSIX advisory locks for cooperating local processes.

Lock files are persistent coordination objects: never unlink them on release.
Unlinking would let another process lock a different inode at the same path.
Unsupported platforms fail closed; no claim of distributed/NFS locking safety.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

from intelligence import config as cfg
from intelligence.errors import OperationLockError


@contextmanager
def bounded_thread_lock(lock):
    if not lock.acquire(timeout=cfg.OPERATION_LOCK_TIMEOUT_SECONDS):
        raise OperationLockError('Timed out waiting for the thread append lock')
    try:
        yield
    finally:
        lock.release()


@contextmanager
def advisory_lock(path: Path, *, timeout: float | None = None):
    try:
        import fcntl
    except ImportError as exc:
        raise OperationLockError('POSIX advisory locks are required on this platform') from exc
    timeout = cfg.OPERATION_LOCK_TIMEOUT_SECONDS if timeout is None else timeout
    if timeout < 0:
        raise OperationLockError('Lock timeout must be nonnegative')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise OperationLockError('Timed out waiting for an operational lock') from None
                time.sleep(min(.025, max(0, deadline - time.monotonic())))
        # Exceptions from the protected operation retain their original type.
        yield
    finally:
        if fd is not None:
            os.close(fd)  # Closing releases the lock, including after exceptions.
