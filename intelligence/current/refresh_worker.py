"""Disposable acquisition process; reuses production functions without duplication."""
from contextlib import redirect_stdout
import io,json,os,sys
from pathlib import Path
from intelligence.production.refresh import run
from intelligence.production.store import load_build,readonly
from intelligence.sources.registry import enabled_sources
from intelligence.current.cache import VERSION

def main(root):
    os.environ.pop('OPENROUTER_API_KEY',None)
    publisher=Path(root)/'publisher';publisher.mkdir(parents=True,exist_ok=True)
    # Existing refresh stages, source failures and receipts remain in local runs.
    with redirect_stdout(io.StringIO()):run(publisher)
    build=load_build(publisher)
    if not build.article_count:raise ValueError('EMPTY_COHORT')
    manifest=json.loads(build.path.with_name('manifest.json').read_text())
    report=publisher/manifest['run_directory']
    fetched=json.loads((report/'fetch.json').read_text())
    stages=json.loads((report/'pipeline.json').read_text())
    results=fetched['results']
    with readonly(build.path) as db:
        counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('article_sightings','real_estate_relevance','uae_real_estate_relevance','intelligence_events','intelligence_observations')}
        re_count=db.execute('SELECT count(*) FROM real_estate_relevance WHERE is_real_estate_relevant=1').fetchone()[0]
        uae_count=db.execute('SELECT count(*) FROM uae_real_estate_relevance WHERE is_uae_real_estate_relevant=1').fetchone()[0]
    meta=dict(version=VERSION,artifact=build.sha256,build_id=build.build_id,
        fetched_at=fetched['started_at'],processed_at=build.completed_at,
        sources_attempted=sum(r['status']!='SKIPPED_RATE_LIMIT' for r in results),
        sources_successful=sum(r['status']=='SUCCESS' for r in results),
        items_fetched=sum(r['entries_seen'] for r in results),article_count=build.article_count,
        real_estate_relevant_count=re_count,uae_relevant_count=uae_count,
        counts=counts,source_results=[{k:r.get(k) for k in ('source_id','status','entries_seen','entries_new','http_status')} for r in results],
        registry=[s.model_dump(mode='json') for s in enabled_sources()],
        pipeline=[{'stage':s['stage'],'status':s['status']} for s in stages])
    return {'status':'PASS','metadata':meta}

if __name__=='__main__':
    try:result=main(Path(sys.argv[1]))
    except Exception:result={'status':'FAILED'}
    print(json.dumps(result));raise SystemExit(result['status']!='PASS')
