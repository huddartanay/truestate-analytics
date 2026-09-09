"""Only attested, coherent, immutable real-RSS artifacts may serve the website.

The publisher is a trusted administrative job. An artifact hash detects corruption,
not a malicious administrator. Write access to production storage is privileged.
No fixture loader, schema migration or ingestion is imported by this reader.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit
from intelligence import config as cfg
from intelligence.sources.registry import enabled_sources

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = ROOT / 'data/production_intelligence'
CONTRACT = 'stage18-production-v1'
VERSIONS = ('cleaning_version','dedup_version','relevance_version','uae_relevance_version',
    'registry_version','entity_extraction_version','entity_registry_version',
    'event_extraction_version','metric_extraction_version','intelligence_build_version',
    'market_movement_version','ranking_version')

class ProductionUnavailable(ValueError):
    """Safe code only; never include raw database or provider exceptions."""

@dataclass(frozen=True)
class Build:
    path: Path
    build_id: str
    completed_at: str
    sha256: str
    article_count: int

def production_root():
    return Path(os.environ.get('TRUESTATE_PRODUCTION_ROOT', str(DEFAULT_ROOT))).expanduser().resolve()

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):h.update(block)
    return h.hexdigest()

def safe_url(url):
    if not isinstance(url,str) or any(c in url for c in '\r\n<>\\') or any(ord(c)<32 for c in url):return None
    try:
        p=urlsplit(url);host=(p.hostname or '').lower();port=p.port
    except ValueError:return None
    if p.scheme not in ('https','http') or not host or p.username or p.password or port not in (None,80,443):return None
    if host in ('localhost','example.com','example.org','example.net') or host.endswith(('.test','.invalid','.localhost')):return None
    if re.fullmatch(r'[\d.:]+',host):return None
    return url

def publisher_url(source,url):
    if not safe_url(url):return False
    host=urlsplit(url).hostname.lower()
    feedhost=urlsplit(str(source.rss_url)).hostname.lower().removeprefix('www.')
    roots=('bbc.co.uk','bbc.com') if feedhost=='feeds.bbci.co.uk' else (feedhost,)
    return any(host==r or host.endswith('.'+r) for r in roots)

@contextmanager
def readonly(path):
    conn=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    try:yield conn
    finally:conn.close()

def inspect_database(path,manifest):
    if manifest.get('contract')!=CONTRACT or manifest.get('data_class')!='PRODUCTION':raise ProductionUnavailable('NOT_PRODUCTION')
    if manifest.get('status')!='COMPLETE' or manifest.get('coherent') is not True:raise ProductionUnavailable('INCOMPLETE')
    registry={s.source_id:s for s in enabled_sources()}
    receipts=manifest.get('receipts',[])
    accepted={r['source_id']:r for r in receipts if r.get('status')=='SUCCESS' and r.get('publisher_verified') is True}
    if not accepted:raise ProductionUnavailable('NO_REAL_INGESTION')
    for sid,r in accepted.items():
        s=registry.get(sid)
        if s is None or r.get('feed_url')!=str(s.rss_url) or not re.fullmatch('[0-9a-f]{64}',r.get('body_sha256','')):raise ProductionUnavailable('REGISTRY_MISMATCH')
    with readonly(path) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():raise ProductionUnavailable('INCOHERENT_DATABASE')
        stamp=db.execute('SELECT * FROM production_build_classification').fetchone()
        if not stamp or stamp['data_class']!='PRODUCTION' or stamp['contract']!=CONTRACT or stamp['build_id']!=manifest['build_id']:raise ProductionUnavailable('CLASSIFICATION_MISMATCH')
        current=db.execute("SELECT build_id FROM intelligence_current WHERE channel='CURRENT'").fetchone()
        if not current or current[0]!=manifest['build_id']:raise ProductionUnavailable('BUILD_MISMATCH')
        run=db.execute("SELECT * FROM intelligence_run_log WHERE build_id=? AND status='SUCCESS' AND completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 1",(current[0],)).fetchone()
        if not run or run['completed_at']!=manifest['completed_at'] or run['failed_count'] or run['error_count']:raise ProductionUnavailable('INCOMPLETE_BUILD')
        if any(run[k]!=getattr(cfg,k.upper()) for k in VERSIONS):raise ProductionUnavailable('UNSUPPORTED_VERSION')
        articles=db.execute('SELECT * FROM intelligence_articles WHERE build_id=?',(current[0],)).fetchall()
        for a in articles:
            s=registry.get(a['source_id'])
            if s is None or s.source_id not in accepted or a['rss_url']!=str(s.rss_url) or a['source_name']!=s.source_name or not publisher_url(s,a['article_url']):raise ProductionUnavailable('NON_PRODUCTION_SOURCE')
        # Validate ALL raw sightings, including rejected articles, against this real
        # fetch receipt. A renamed fixture DB cannot be published by a label alone.
        for row in db.execute('SELECT source_id,article_id,raw_hash FROM article_sightings'):
            receipt=accepted.get(row['source_id'],{})
            if [row['article_id'],row['raw_hash']] not in receipt.get('article_identities',[]):raise ProductionUnavailable('UNATTESTED_RAW_INPUT')
        if len(articles)!=manifest.get('article_count'):raise ProductionUnavailable('COUNT_MISMATCH')
    return Build(Path(path).resolve(),manifest['build_id'],manifest['completed_at'],manifest['sha256'],len(articles))

def load_build(root=None):
    root=Path(root or production_root()).resolve()
    try:
        pointer=json.loads((root/'current.json').read_text())
        version=pointer['artifact']
        if not re.fullmatch('[0-9a-f]{64}',version):raise ProductionUnavailable('INVALID_POINTER')
        directory=root/'builds'/version
        manifest=json.loads((directory/'manifest.json').read_text())
        path=directory/'intelligence.db'
        if path.is_symlink() or directory.is_symlink() or manifest['sha256']!=digest(path):raise ProductionUnavailable('ARTIFACT_CHANGED')
        return inspect_database(path,manifest)
    except ProductionUnavailable:raise
    except Exception:raise ProductionUnavailable('PRODUCTION_DATA_UNAVAILABLE') from None
