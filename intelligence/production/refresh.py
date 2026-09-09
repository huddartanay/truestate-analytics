"""Explicit administrative real-RSS refresh. Never imported by Streamlit.

Run from FULL CODE BASE: python3 -m intelligence.production.refresh
Only the existing enabled Stage 3 registry is accepted. No CLI source/URL override.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid
from urllib.request import build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.parse import urlsplit
from intelligence import config as cfg
from intelligence.production.store import CONTRACT,digest,inspect_database,production_root,publisher_url
from intelligence.sources.registry import all_sources, enabled_sources


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,default=str)+'\n')

def configure(work):
    cfg.DATA_DIR=work;cfg.DB_PATH=work/'intelligence.db'
    for key,folder in [('RAW_ARTICLES_DIR','raw_articles'),('LOGS_DIR','logs'),('PROMPTS_LOG_DIR','prompts_used'),('BACKUPS_DIR','backups')]:setattr(cfg,key,work/folder)
    cfg.ensure_data_dirs()

class RegistryRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urlsplit(newurl).scheme!='https' or urlsplit(req.full_url).hostname!=urlsplit(newurl).hostname:
            raise ValueError('CROSS_HOST_FEED_REDIRECT_REJECTED')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def run(root):
    from intelligence.pipeline import fetch
    from intelligence.db.connection import apply_schema
    from intelligence.pipeline.clean import run_cleaning
    from intelligence.pipeline.deduplicate import run_deduplication
    from intelligence.pipeline.relevance import run_relevance
    from intelligence.pipeline.uae_relevance import run_uae_relevance
    from intelligence.pipeline.entities import run_entities
    from intelligence.pipeline.events import run_events
    from intelligence.pipeline.metrics import run_metrics
    from intelligence.pipeline.intelligence import run_intelligence
    configure(root/'work');apply_schema()
    report_dir=root/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]);report_dir.mkdir(parents=True)
    registry=[s.model_dump(mode='json') for s in all_sources()]
    write_json(report_dir/'registry.json',registry)
    ledger_path=root/'receipts.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    source_index={str(s.rss_url):s for s in enabled_sources()}
    observed={}
    opener=build_opener(RegistryRedirect(),HTTPSHandler(context=fetch._SSL_CTX))
    # The Stage 4 parser, identity calculation and fetch orchestration remain
    # unchanged. Restrict redirect transport and attest the bytes it receives.
    fetch.urlopen=lambda request,timeout,context:opener.open(request,timeout=timeout)
    original=fetch._http_get
    def attest(url,**kwargs):
        source=source_index[url]
        status,body,headers=original(url,**kwargs)
        if status==200:
            feed=fetch._parse_feed(body)
            feedlink=feed.feed.get('link')
            if not publisher_url(source,feedlink):raise ValueError('FEED_PUBLISHER_MISMATCH')
            identities=[]
            for entry in feed.entries:
                identities.append([fetch.compute_article_id(source.source_id,entry),fetch.compute_raw_hash(entry)])
            observed[source.source_id]=dict(source_id=source.source_id,feed_url=url,
                feed_title=feed.feed.get('title',''),feed_link=feedlink,publisher_verified=True,
                body_sha256=hashlib.sha256(body).hexdigest(),article_identities=identities,status='SUCCESS')
        return status,body,headers
    fetch._http_get=attest
    fetched=fetch.fetch(list(enabled_sources()),max_concurrent=1)
    write_json(report_dir/'fetch.json',asdict(fetched))
    for result in fetched.results:
        print(json.dumps(dict(source=result.source_id,status=result.status,seen=result.entries_seen,new=result.entries_new,http_status=result.http_status)),flush=True)
        if result.status=='SUCCESS' and result.source_id in observed:
            record=observed[result.source_id]
            identities=ledger.get(result.source_id,{}).get('article_identities',[])+record['article_identities']
            record['article_identities']=[list(pair) for pair in sorted({tuple(pair) for pair in identities})]
            ledger[result.source_id]=record
    write_json(ledger_path,ledger)
    stages=[]
    for name,fn in [('cleaning',run_cleaning),('deduplication',run_deduplication),('relevance',run_relevance),('uae_relevance',run_uae_relevance),('entities',run_entities),('events',run_events),('metrics',run_metrics),('intelligence',run_intelligence)]:
        result=asdict(fn());stages.append(dict(stage=name,**result));write_json(report_dir/'pipeline.json',stages)
        print(json.dumps(dict(stage=name,status=result['status'])),flush=True)
        if result['status']!='SUCCESS':raise ValueError('PIPELINE_INCOMPLETE: '+name)
    final=stages[-1]
    with sqlite3.connect(cfg.DB_PATH) as db:
        db.execute('CREATE TABLE IF NOT EXISTS production_build_classification (build_id TEXT PRIMARY KEY, data_class TEXT NOT NULL, contract TEXT NOT NULL)')
        db.execute('DELETE FROM production_build_classification')
        db.execute('INSERT INTO production_build_classification VALUES (?,?,?)',(final['build_id'],'PRODUCTION',CONTRACT))
        db.commit()
        candidate=report_dir/'intelligence.db'
        with sqlite3.connect(candidate) as dest:db.backup(dest)
    sha=digest(candidate)
    with sqlite3.connect(candidate) as db:
        article_count=db.execute('SELECT count(*) FROM intelligence_articles WHERE build_id=?',(final['build_id'],)).fetchone()[0]
    manifest=dict(contract=CONTRACT,data_class='PRODUCTION',status='COMPLETE',coherent=True,
        build_id=final['build_id'],completed_at=final['completed_at'],sha256=sha,article_count=article_count,
        receipts=list(ledger.values()),run_directory=str(report_dir.relative_to(root)))
    write_json(report_dir/'manifest.json',manifest)
    inspect_database(candidate,manifest)
    destination=root/'builds'/sha;destination.mkdir(parents=True,exist_ok=False)
    candidate.replace(destination/'intelligence.db')
    write_json(destination/'manifest.json',manifest)
    # Publish only after the complete artifact passes the serving gate. Readers
    # resolve once, so a refresh never combines two generations.
    pending=root/('current.'+uuid.uuid4().hex+'.tmp')
    write_json(pending,{'artifact':sha});os.replace(pending,root/'current.json')
    print(json.dumps(dict(status='PRODUCTION_PUBLISHED',build_id=final['build_id'],articles=article_count,artifact=sha)),flush=True)
    return 0

def main():
    os.environ.pop('OPENROUTER_API_KEY',None)
    from intelligence.db.locking import advisory_lock
    root=production_root();root.mkdir(parents=True,exist_ok=True)
    with advisory_lock(root/'.refresh.lock'):
        try:return run(root)
        except Exception as exc:
            # Feed/pipeline reports retain diagnostics; never dump an environment.
            print(json.dumps({'status':'REFRESH_FAILED_PREVIOUS_PUBLICATION_PRESERVED','error_type':type(exc).__name__}),flush=True)
            return 1

if __name__=='__main__':raise SystemExit(main())
