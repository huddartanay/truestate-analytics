"""Portable real-production bundles. No acquisition, inference or remote writes.

The trusted publisher attests provenance; hashes detect transfer corruption, not
an administrator forging receipts. Originals are never edited. Only raw-pointer
representation changes in deployment copies; logical records and IDs survive.
"""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import tarfile
import tempfile
import uuid

from intelligence import config as cfg
from intelligence.production.store import (ProductionUnavailable, digest, inspect_database,
                                          load_build, readonly, VERSIONS)

FORMAT = 'truestate-portable-production-v1'
SERVING = 'production-serving.tar.gz'
HISTORY = 'production-publisher-state.tar.gz'
INDEX = 'production-release.json'
MAX_BYTES = 512 * 1024 * 1024
MAX_FILES = 20000
HEX = re.compile(r'[0-9a-f]{64}')
PARTITION = re.compile(r'\d{4}-\d{2}-\d{2}(?:\.\d+)?\.jsonl')


def fail(code):
    raise ProductionUnavailable(code)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def portable_bytes(data):
    # Check actual exported bytes, including SQLite free pages after VACUUM.
    if re.search(rb'/Users/|/home/|/private/(?:tmp|var)/|\b[A-Za-z]:[\\/]|sk-or-v1-', data):
        fail('NON_PORTABLE_OR_SECRET_BYTES')


def relative_name(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or str(p) != name:
        fail('UNSAFE_MEMBER')
    return p


def raw_name(value):
    # Existing Stage 5 resolves relative paths under RAW_ARTICLES_DIR already.
    # Accept legacy absolute pointers only at export, extracting a strictly
    # validated partition name; the raw record identity is checked separately.
    name = value.rsplit('/raw_articles/', 1)[-1] if '/raw_articles/' in value else value
    if not PARTITION.fullmatch(name):
        fail('NON_PORTABLE_RAW_POINTER')
    return name


def backup(source, destination):
    with readonly(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        dst.execute('PRAGMA journal_mode=DELETE')


def normalize_database(source, destination):
    backup(source, destination)
    with sqlite3.connect(destination) as db:
        for (value,) in db.execute('SELECT DISTINCT raw_jsonl_path FROM article_sightings').fetchall():
            db.execute('UPDATE article_sightings SET raw_jsonl_path=? WHERE raw_jsonl_path=?',
                       (raw_name(value), value))
        db.commit()
        db.execute('VACUUM')  # Remove old absolute strings from free pages too.
    portable_bytes(Path(destination).read_bytes())


def validate_database(path, manifest):
    if not HEX.fullmatch(manifest.get('sha256', '')) or digest(path) != manifest['sha256']:
        fail('ARTIFACT_HASH_MISMATCH')
    if manifest.get('portable_contract') != FORMAT or manifest.get('schema_version') != cfg.SCHEMA_VERSION:
        fail('UNSUPPORTED_PORTABLE_VERSION')
    stamp = datetime.fromisoformat(manifest['completed_at'])
    if stamp.utcoffset() is None:
        fail('INVALID_FRESHNESS')
    portable_bytes(Path(path).read_bytes())
    with readonly(path) as db:
        if db.execute('PRAGMA integrity_check').fetchall()[0][0] != 'ok':
            fail('SQLITE_INTEGRITY')
        if db.execute('PRAGMA foreign_key_check').fetchone():
            fail('SQLITE_FOREIGN_KEY')
        for row in db.execute('SELECT source_id,article_id,raw_hash,raw_jsonl_path FROM article_sightings'):
            if not re.fullmatch('[0-9a-f]{40}',row['article_id']) or not HEX.fullmatch(row['raw_hash']):
                fail('FIXTURE_IDENTITY')
            if row['raw_jsonl_path'] != raw_name(row['raw_jsonl_path']):
                fail('ABSOLUTE_RAW_POINTER')
    return inspect_database(path, manifest)


def portable_manifest(original, path):
    return {**original, 'sha256': digest(path), 'portable_contract': FORMAT,
            'schema_version': cfg.SCHEMA_VERSION,
            'origin_sha256': original.get('origin_sha256', original['sha256'])}


def validate_serving(root):
    build = load_build(root)
    manifest = json.loads((build.path.parent / 'manifest.json').read_text())
    return validate_database(build.path, manifest)


def validate_history(root):
    root = Path(root)
    build = validate_serving(root)
    manifest = json.loads((root / 'history.json').read_text())
    work = root / 'work' / 'intelligence.db'
    history_build = validate_database(work, manifest)
    if (history_build.build_id, history_build.completed_at) != (build.build_id, build.completed_at):
        fail('HISTORY_BUILD_MISMATCH')
    ledger = json.loads((root / 'receipts.json').read_text())
    if sorted(ledger.values(), key=lambda r:r['source_id']) != sorted(manifest['receipts'], key=lambda r:r['source_id']):
        fail('HISTORY_RECEIPTS_MISMATCH')
    serving_manifest = json.loads((build.path.parent / 'manifest.json').read_text())
    if serving_manifest['receipts'] != manifest['receipts']:
        fail('SERVING_HISTORY_RECEIPTS_MISMATCH')
    from intelligence.schemas import RawArticleRecord
    raw = root / 'work' / 'raw_articles'
    records = {}
    for path in sorted(raw.glob('*.jsonl')):
        if path.is_symlink() or not PARTITION.fullmatch(path.name): fail('UNSAFE_RAW_ARCHIVE')
        data = path.read_bytes(); portable_bytes(data)
        records[path.name] = [RawArticleRecord.model_validate_json(line) for line in data.splitlines()]
    seen = set()
    with readonly(work) as db:
        for row in db.execute('SELECT * FROM article_sightings'):
            name = raw_name(row['raw_jsonl_path']); line = row['raw_jsonl_line']
            if name not in records or line < 1 or line > len(records[name]): fail('MISSING_RAW_HISTORY')
            rec = records[name][line-1]
            if (rec.source_id, rec.article_id, rec.raw_hash) != (row['source_id'], row['article_id'], row['raw_hash']):
                fail('RAW_IDENTITY_MISMATCH')
            if [rec.article_id,rec.raw_hash] not in ledger.get(rec.source_id,{}).get('article_identities',[]):
                fail('UNATTESTED_HISTORY')
            seen.add((name,line))
    # No unattested scratch or hidden fixture records can ride in the archive.
    if seen != {(name,i+1) for name,values in records.items() for i in range(len(values))}:
        fail('UNREFERENCED_RAW_HISTORY')
    return history_build


def allowed_member(name, kind):
    if name in ('current.json',): return True
    if re.fullmatch(r'builds/[0-9a-f]{64}/(?:manifest.json|intelligence.db)',name): return True
    return kind == 'history' and (name in ('history.json','receipts.json','work/intelligence.db') or
        name.startswith('work/raw_articles/') and PARTITION.fullmatch(name.removeprefix('work/raw_articles/')) is not None)


def pack_directory(root, target, kind):
    root = Path(root)
    entries = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink(): fail('LINK_REJECTED')
        if not path.is_file(): continue
        name = path.relative_to(root).as_posix()
        if not allowed_member(name,kind): fail('UNEXPECTED_EXPORT_FILE')
        data = path.read_bytes(); portable_bytes(data)
        entries[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    if len(entries)>MAX_FILES or sum(x['bytes'] for x in entries.values())>MAX_BYTES:fail('BUNDLE_TOO_LARGE')
    meta = json.dumps({'contract':FORMAT,'kind':kind,'files':entries},sort_keys=True).encode()
    with tarfile.open(target,'w:gz',format=tarfile.USTAR_FORMAT) as tar:
        for name,data in [('bundle.json',meta)] + [(n,(root/n).read_bytes()) for n in entries]:
            info = tarfile.TarInfo(name); info.size=len(data); info.mode=0o600; info.mtime=0
            tar.addfile(info,io.BytesIO(data))


def unpack(archive, destination, expected_sha, kind):
    archive=Path(archive); destination=Path(destination)
    if not HEX.fullmatch(expected_sha) or archive.stat().st_size>MAX_BYTES or digest(archive)!=expected_sha:
        fail('BUNDLE_HASH_MISMATCH')
    destination.mkdir(parents=True,exist_ok=False)
    files={}; total=0
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            relative_name(member.name)
            if not member.isfile() or member.name in files or len(files)>=MAX_FILES or member.size<0:
                fail('UNSAFE_ARCHIVE')
            total+=member.size
            if total>MAX_BYTES: fail('BUNDLE_TOO_LARGE')
            if member.name!='bundle.json' and not allowed_member(member.name,kind):fail('UNEXPECTED_MEMBER')
            stream=tar.extractfile(member); data=stream.read(member.size+1)
            if len(data)!=member.size:fail('TRUNCATED_MEMBER')
            portable_bytes(data); files[member.name]=data
    meta=json.loads(files.pop('bundle.json'))
    if meta.get('contract')!=FORMAT or meta.get('kind')!=kind or set(meta['files'])!=set(files):
        fail('BUNDLE_MANIFEST_MISMATCH')
    for name,data in files.items():
        if meta['files'][name]!={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}:
            fail('MEMBER_HASH_MISMATCH')
        path=destination/name; path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    build=validate_serving(destination)
    required={'current.json','builds/'+build.sha256+'/intelligence.db','builds/'+build.sha256+'/manifest.json'}
    if kind=='history':
        required.update({'history.json','receipts.json','work/intelligence.db'})
        required.update(n for n in files if n.startswith('work/raw_articles/'))
        validate_history(destination)
    if set(files)!=required:fail('UNEXPECTED_BUNDLE_CONTENTS')


def package(root, output):
    """Export copies only. Caller holds publisher lock; output must be absent."""
    root=Path(root); output=Path(output)
    original=load_build(root)
    original_manifest=json.loads((original.path.parent/'manifest.json').read_text())
    with tempfile.TemporaryDirectory(prefix='truestate-export-') as tmp:
        temp=Path(tmp); serving=temp/'serving'; serving.mkdir()
        portable=temp/'portable.db'; normalize_database(original.path,portable)
        manifest=portable_manifest(original_manifest,portable)
        dest=serving/'builds'/manifest['sha256']; dest.mkdir(parents=True)
        portable.replace(dest/'intelligence.db');write_json(dest/'manifest.json',manifest)
        write_json(serving/'current.json',{'artifact':manifest['sha256']})
        validate_serving(serving)
        history=temp/'history';shutil.copytree(serving,history)
        (history/'work').mkdir(); normalize_database(root/'work/intelligence.db',history/'work/intelligence.db')
        work_manifest=portable_manifest(original_manifest,history/'work/intelligence.db')
        write_json(history/'history.json',work_manifest)
        shutil.copy2(root/'receipts.json',history/'receipts.json')
        raw=history/'work/raw_articles';raw.mkdir()
        with readonly(history/'work/intelligence.db') as db:
            for (name,) in db.execute('SELECT DISTINCT raw_jsonl_path FROM article_sightings'):
                source=root/'work/raw_articles'/raw_name(name)
                if source.is_symlink():fail('RAW_LINK_REJECTED')
                shutil.copy2(source,raw/name)
        validate_history(history)
        prepared=temp/'release';prepared.mkdir()
        pack_directory(serving,prepared/SERVING,'serving');pack_directory(history,prepared/HISTORY,'history')
        index={'contract':FORMAT,'data_class':'PRODUCTION','status':'COMPLETE','build_id':original.build_id,
            'completed_at':original.completed_at,'artifact_sha256':manifest['sha256'],
            'assets':{n:{'sha256':digest(prepared/n),'bytes':(prepared/n).stat().st_size} for n in (SERVING,HISTORY)}}
        write_json(prepared/INDEX,index)
        output.parent.mkdir(parents=True,exist_ok=True)
        # Copy to a sibling then rename; never expose a partial local release.
        staging=output.with_name(output.name+'.'+uuid.uuid4().hex+'.tmp')
        shutil.copytree(prepared,staging)
        if output.exists(): shutil.rmtree(staging); fail('RELEASE_ALREADY_EXISTS')
        os.rename(staging,output)
    return index


def read_index(directory):
    value=json.loads((Path(directory)/INDEX).read_text())
    if value.get('contract')!=FORMAT or value.get('data_class')!='PRODUCTION' or value.get('status')!='COMPLETE':
        fail('INVALID_RELEASE_INDEX')
    if set(value.get('assets',{}))!={SERVING,HISTORY} or not HEX.fullmatch(value.get('artifact_sha256','')):
        fail('INVALID_RELEASE_ASSETS')
    for name,entry in value['assets'].items():
        if not HEX.fullmatch(entry.get('sha256','')) or not 0<entry.get('bytes',0)<=MAX_BYTES:fail('INVALID_ASSET_HASH')
    return value


def check_index_build(index,build):
    if (index['artifact_sha256'],index['build_id'],index['completed_at']) != (build.sha256,build.build_id,build.completed_at):
        fail('INDEX_BUILD_MISMATCH')


def restore_history(release, destination):
    destination=Path(destination);index=read_index(release)
    if destination.exists():fail('RESTORE_REQUIRES_EMPTY_DESTINATION')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent,prefix='.restore-') as temp:
        staged=Path(temp)/'state';unpack(Path(release)/HISTORY,staged,index['assets'][HISTORY]['sha256'],'history')
        check_index_build(index,validate_serving(staged))
        os.rename(staged,destination)
    return validate_history(destination)


def materialize(release, root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);index=read_index(release)
    with tempfile.TemporaryDirectory(dir=root,prefix='.materialize-') as temp:
        staged=Path(temp)/'serving';unpack(Path(release)/SERVING,staged,index['assets'][SERVING]['sha256'],'serving')
        build=validate_serving(staged);check_index_build(index,build)
        dest=root/'builds'/build.sha256;dest.parent.mkdir(exist_ok=True)
        if dest.exists():
            validate_database(dest/'intelligence.db',json.loads((dest/'manifest.json').read_text()))
        else:os.rename(build.path.parent,dest)
        pending=root/('current.'+uuid.uuid4().hex+'.tmp')
        write_json(pending,{'artifact':build.sha256});os.replace(pending,root/'current.json')
    return validate_serving(root)
