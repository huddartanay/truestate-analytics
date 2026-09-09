"""Administrative release job: restore before refresh; publish only on success.

No bootstrap from fixtures/empty history. The first release must be exported
from the reviewed existing real checkpoint and separately published by its
operator. This command runs only after explicit workflow activation.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from intelligence.production.artifacts import (package, restore_history, fail,
                                              read_index, INDEX)
from intelligence.production.releases import GitHubReleases, REPOSITORY
from intelligence.production.store import ProductionUnavailable


def controlled_refresh(root):
    env=os.environ.copy()
    for key in ('OPENROUTER_API_KEY','GITHUB_TOKEN','GH_TOKEN'):env.pop(key,None)
    env['TRUESTATE_PRODUCTION_ROOT']=str(Path(root).resolve())
    env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run([sys.executable,'-m','intelligence.production.refresh'],env=env,
                          capture_output=True,text=True,timeout=1500)
    if result.returncode:fail('REFRESH_FAILED_PREVIOUS_RELEASE_RETAINED')
    reports=list((Path(root)/'runs').glob('*/fetch.json'))
    if len(reports)!=1:fail('MISSING_REFRESH_REPORT')
    fetched=json.loads(reports[0].read_text())
    results=fetched.get('results',[])
    from intelligence.sources.registry import enabled_sources
    if {x['source_id'] for x in results}!={s.source_id for s in enabled_sources()}:
        fail('INCOMPLETE_REGISTERED_FETCH')
    if any(x['status'] not in ('SUCCESS','NOT_MODIFIED','SKIPPED_RATE_LIMIT') for x in results):
        fail('RSS_FAILED_PREVIOUS_RELEASE_RETAINED')


def run_job(source, workspace, *, refresh=controlled_refresh, publish=None):
    workspace=Path(workspace);workspace.mkdir(parents=True,exist_ok=False)
    candidates=source.candidates()
    if not candidates:fail('VERIFIED_BOOTSTRAP_REQUIRED')
    # Do not silently restore older publisher history after corruption.
    release=source.download(candidates[0],workspace/'download',history=True)
    restore_history(release,workspace/'state')
    refresh(workspace/'state')
    output=workspace/'release';index=package(workspace/'state',output)
    if publish:publish(output)
    return index


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=('scheduled','export'))
    parser.add_argument('--root',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();os.environ.pop('OPENROUTER_API_KEY',None)
    try:
        if args.operation=='export':
            if args.root is None or args.output is None:fail('ROOT_AND_OUTPUT_REQUIRED')
            from intelligence.db.locking import advisory_lock
            with advisory_lock(args.root/'.refresh.lock'):result=package(args.root,args.output)
        else:
            if os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY or os.environ.get('GITHUB_REF')!='refs/heads/main':
                fail('UNAPPROVED_WORKFLOW_TARGET')
            if os.environ.get('GITHUB_EVENT_NAME') not in ('schedule','workflow_dispatch'):fail('UNAPPROVED_TRIGGER')
            source=GitHubReleases()
            def publish(path):
                return source.publish(path,commit=os.environ.get('GITHUB_SHA',''),run_id=os.environ.get('GITHUB_RUN_ID',''),token=os.environ.get('GITHUB_TOKEN',''))
            with tempfile.TemporaryDirectory(prefix='truestate-runner-') as temp:
                result=run_job(source,Path(temp)/'job',publish=publish)
        print(json.dumps({'status':'COMPLETE','build_id':result['build_id']}))
        return 0
    except Exception as exc:
        code=str(exc) if isinstance(exc,ProductionUnavailable) else 'LOCAL_OPERATION_FAILED'
        print(json.dumps({'status':'FAILED_PREVIOUS_RELEASE_PRESERVED','code':code}))
        return 1


if __name__=='__main__':raise SystemExit(main())
