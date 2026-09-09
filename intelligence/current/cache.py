"""15-minute validated cache; isolated Stage 4–13 job, per-source rate guards.

Neither Streamlit nor its answer workers mutate pipeline configuration. The
private publisher workspace and receipts persist to honor registry intervals.
Only a separately gated, nonempty immutable build becomes the cache pointer.
"""
import json
import re
import sqlite3
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from intelligence.production.store import ROOT,load_build,inspect_database,digest

TTL=900
VERSION='current-rss-v1'
_LOCK=threading.Lock()

def root_path():
    return ROOT/'data/current_intelligence'

def read(root):
    try:
        meta=json.loads((root/'cache.json').read_text())
        if meta['version']!=VERSION or not re.fullmatch('[0-9a-f]{64}',meta['artifact']):return None
        path=root/'publisher/builds'/meta['artifact']/'intelligence.db'
        manifest=json.loads(path.with_name('manifest.json').read_text())
        if digest(path)!=meta['artifact']:return None
        build=inspect_database(path,manifest)
        if build.article_count<1:return None
        return build,meta
    except (OSError,ValueError,KeyError,sqlite3.Error):return None

def atomic(path,value):
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.current-')
    with os.fdopen(fd,'w') as f:json.dump(value,f,sort_keys=True)
    os.replace(name,path)

def refresh(root):
    env=os.environ.copy();env.pop('OPENROUTER_API_KEY',None)
    env['PYTHONDONTWRITEBYTECODE']='1'
    # No credential reaches RSS acquisition, and stdout never becomes UI text.
    if sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>256*1024*1024:
        raise ValueError('CURRENT_STORAGE_LIMIT')
    result=subprocess.run([sys.executable,'-m','intelligence.current.refresh_worker',str(root)],
        cwd=ROOT,env=env,capture_output=True,text=True,timeout=300)
    if result.returncode:raise ValueError('CURRENT_REFRESH_FAILED')
    value=json.loads(result.stdout)
    if value.get('status')!='PASS':raise ValueError('CURRENT_REFRESH_FAILED')
    return value['metadata']

def ensure(root=None,*,now=None,runner=None):
    import fcntl
    root=Path(root or root_path());root.mkdir(parents=True,exist_ok=True)
    stamp=time.time() if now is None else now
    current=read(root)
    def due():
        try:return stamp-json.loads((root/'attempt.json').read_text())['checked_at']>=TTL
        except (OSError,ValueError,KeyError):return True
    if not due():return current
    if not _LOCK.acquire(blocking=False):return current
    try:
        with (root/'.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return current
            current=read(root)
            if not due():return current
            # Bounded failure cooldown prevents every session retrying the feeds.
            atomic(root/'attempt.json',{'checked_at':stamp,'status':'REFRESHING'})
            try:
                meta=(runner or refresh)(root)
                build=load_build(root/'publisher')
                if build.article_count<1 or meta.get('artifact')!=build.sha256 or meta.get('version')!=VERSION or meta.get('build_id')!=build.build_id or meta.get('article_count')!=build.article_count:raise ValueError('EMPTY_OR_INVALID_CURRENT_BUILD')
                atomic(root/'cache.json',meta)
                atomic(root/'attempt.json',{'checked_at':stamp,'status':'PASS'})
                return read(root)
            except Exception:
                atomic(root/'attempt.json',{'checked_at':stamp,'status':'FAILED_PREVIOUS_CACHE_RETAINED'})
                return current
    finally:_LOCK.release()
