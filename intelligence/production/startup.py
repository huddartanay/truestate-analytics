"""Controlled artifact-only startup. No RSS, pipeline or model imports.

An advisory lock and disk timestamp survive Streamlit reruns/cache clears.
Downloads are attempted at most hourly per materialization root. Original local
production history is never a download destination in the hosted default.
"""
import json
import os
from pathlib import Path
import tempfile
import time
import uuid

from intelligence.production.artifacts import materialize, validate_serving, validate_database, write_json
from intelligence.production.store import ProductionUnavailable
from intelligence.production.releases import GitHubReleases

INTERVAL = 3600


def cache_root():
    return Path(os.environ.get('TRUESTATE_PRODUCTION_ROOT',str(Path(tempfile.gettempdir())/'truestate-production-cache'))).resolve()


def available(root):
    try:return validate_serving(root)
    except Exception:pass
    # Recover a previously validated portable generation if the pointer/current
    # file was lost or damaged. Never consider development databases.
    try:
        directories=sorted((Path(root)/'builds').iterdir(),key=lambda p:p.stat().st_mtime,reverse=True)
        for directory in directories[:10]:
            try:
                if directory.is_symlink() or not directory.is_dir():continue
                path=directory/'intelligence.db';meta=directory/'manifest.json'
                if path.is_symlink() or meta.is_symlink():continue
                manifest=json.loads(meta.read_text())
                if manifest['sha256']!=directory.name:continue
                build=validate_database(path,manifest)
                pending=Path(root)/('current.'+uuid.uuid4().hex+'.tmp')
                write_json(pending,{'artifact':build.sha256});os.replace(pending,Path(root)/'current.json')
                return build
            except Exception:continue
    except Exception:pass
    return None


def ensure_available(root=None, *, source=None, now=None):
    root=Path(root or cache_root());now=time.time() if now is None else now
    try:
        root.mkdir(parents=True,exist_ok=True)
        import fcntl
        with (root/'.materialization.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return available(root)
            prior=available(root)
            stamp=root/'.checked.json'
            try:last=float(json.loads(stamp.read_text())['checked_at'])
            except Exception:last=0
            if 0<=now-last<INTERVAL:return prior
            # Reserve this check before network access, including failures.
            write_json(stamp,{'checked_at':now})
            source=source or GitHubReleases(tag=os.environ.get('TRUESTATE_INTELLIGENCE_RELEASE_TAG'))
            try:candidates=source.candidates()
            except Exception:return prior
            # Warm cache keeps last valid on any newest-release failure; cold
            # startup may try up to three published candidates, never fixtures.
            for release in candidates[:1 if prior else 3]:
                try:
                    with tempfile.TemporaryDirectory(prefix='truestate-download-') as tmp:
                        downloaded=source.download(release,Path(tmp)/'release')
                        return materialize(downloaded,root)
                except Exception:continue
            return prior
    except Exception:return None


def initialize():
    """Called by the sole entry point; fail-safe even when storage is absent."""
    root=cache_root()
    os.environ['TRUESTATE_PRODUCTION_ROOT']=str(root)
    return ensure_available(root)
