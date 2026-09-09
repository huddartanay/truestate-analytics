"""Fixed-repository release transport. Readers never receive a write token.

Only release assets in the approved repository are accepted. Downloads are
bounded, use HTTPS, and redirect solely to GitHub's asset hosts. API failures
are safe codes; request headers and provider bodies are never logged.
"""
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from intelligence.production.artifacts import (FORMAT, SERVING, HISTORY, INDEX,
    MAX_BYTES, digest, fail, read_index, unpack, validate_serving, check_index_build)

REPOSITORY = 'huddartanay/truestate-analytics'
PREFIX = 'truestate-intelligence-v1-'
API = 'https://api.github.com/repos/' + REPOSITORY
TAG = re.compile(PREFIX + r'\d{8}T\d{6}Z-[0-9a-f]{12}-[0-9]+')


class AssetRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed=urlsplit(newurl)
        if parsed.scheme!='https' or parsed.hostname not in ('github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'):
            fail('UNAPPROVED_REDIRECT')
        if parsed.username or parsed.password or parsed.port not in (None,443):fail('UNAPPROVED_REDIRECT')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):fail('API_REDIRECT_REJECTED')


def read_bytes(url, limit, *, api=False, method='GET', data=None, token=None, content_type=None):
    parsed=urlsplit(url)
    expected=('api.github.com','uploads.github.com') if api else ('github.com',)
    if parsed.scheme!='https' or parsed.hostname not in expected or parsed.username or parsed.password:
        fail('UNAPPROVED_ENDPOINT')
    headers={'User-Agent':'TruEstate-production-artifacts/1','Accept':'application/vnd.github+json' if api else 'application/octet-stream'}
    if api:headers['X-GitHub-Api-Version']='2022-11-28'
    if token:headers['Authorization']='Bearer '+token
    if content_type:headers['Content-Type']=content_type
    try:
        request=Request(url,data=data,headers=headers,method=method)
        with build_opener(NoRedirect() if api else AssetRedirect()).open(request,timeout=30) as response:
            if int(response.headers.get('Content-Length','0'))>limit:fail('TRANSFER_TOO_LARGE')
            payload=response.read(limit+1)
            if len(payload)>limit:fail('TRANSFER_TOO_LARGE')
            return payload
    except Exception:
        fail('RELEASE_TRANSFER_FAILED')


def api_json(path, *, method='GET', value=None, token=None):
    data=None if value is None else json.dumps(value).encode()
    return json.loads(read_bytes(API+path,4*1024*1024,api=True,method=method,data=data,
                                 token=token,content_type='application/json'))


class GitHubReleases:
    def __init__(self, tag=None):
        if tag is not None and not TAG.fullmatch(tag):fail('UNAPPROVED_ROLLBACK_TAG')
        self.tag=tag

    def candidates(self):
        if self.tag:
            release=api_json('/releases/tags/'+self.tag)
            if release.get('draft') or release.get('prerelease') or release.get('tag_name')!=self.tag:
                fail('UNPUBLISHED_ROLLBACK')
            return [release]
        # Production releases are published daily; bounded pagination tolerates
        # unrelated repository releases. Never use /releases/latest implicitly.
        rows=[]
        for page in range(1,4):
            batch=api_json('/releases?per_page=100&page='+str(page))
            rows.extend(r for r in batch if not r.get('draft') and not r.get('prerelease') and TAG.fullmatch(r.get('tag_name','')))
            if len(batch)<100:break
        return sorted(rows,key=lambda r:r['tag_name'],reverse=True)

    def download(self, release, destination, *, history=False):
        destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
        tag=release['tag_name']
        if not TAG.fullmatch(tag):fail('UNAPPROVED_TAG')
        assets={a['name']:a for a in release['assets']}
        if not {INDEX,SERVING,HISTORY}.issubset(assets):fail('INCOMPLETE_RELEASE')
        def get(name,limit):
            expected='https://github.com/'+REPOSITORY+'/releases/download/'+tag+'/'+name
            asset=assets[name]
            if asset.get('browser_download_url')!=expected or asset.get('state')!='uploaded' or not 0<asset.get('size',0)<=limit:
                fail('UNAPPROVED_ASSET')
            data=read_bytes(expected,limit)
            if len(data)!=asset['size']:fail('ASSET_LENGTH_MISMATCH')
            path=destination/name;path.write_bytes(data)
            remote_digest=asset.get('digest')
            if remote_digest and remote_digest!='sha256:'+digest(path):fail('GITHUB_ASSET_HASH_MISMATCH')
        get(INDEX,1024*1024);index=read_index(destination)
        for name in ((SERVING,HISTORY) if history else (SERVING,)):
            get(name,MAX_BYTES)
            if digest(destination/name)!=index['assets'][name]['sha256'] or (destination/name).stat().st_size!=index['assets'][name]['bytes']:
                fail('RELEASE_HASH_MISMATCH')
        return destination

    def publish(self, directory, *, commit, run_id, token):
        """Scheduler only: validate BOTH bundles before the first remote write.

        Drafts from interrupted uploads remain drafts. No existing release is
        overwritten/deleted, and no workflow is dispatched by this method.
        """
        if not token or not re.fullmatch('[0-9a-f]{40}',commit) or not re.fullmatch('[0-9]+',run_id):fail('INVALID_PUBLISH_CONTEXT')
        directory=Path(directory);index=read_index(directory)
        with tempfile.TemporaryDirectory(prefix='truestate-publish-check-') as temp:
            for name,kind in ((SERVING,'serving'),(HISTORY,'history')):
                dest=Path(temp)/kind;unpack(directory/name,dest,index['assets'][name]['sha256'],kind)
                check_index_build(index,validate_serving(dest))
        from datetime import datetime,timezone
        tag=PREFIX+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+index['artifact_sha256'][:12]+'-'+run_id
        draft=api_json('/releases',method='POST',token=token,value={
            'tag_name':tag,'target_commitish':commit,'name':tag,'draft':True,'prerelease':False,
            'body':'Verified real TruEstate production intelligence. Build '+index['build_id']})
        rid=draft['id']
        if not isinstance(rid,int):fail('INVALID_RELEASE_ID')
        for name in (SERVING,HISTORY,INDEX):
            data=(directory/name).read_bytes()
            uploaded=json.loads(read_bytes('https://uploads.github.com/repos/'+REPOSITORY+'/releases/'+str(rid)+'/assets?name='+name,
                1024*1024,api=True,method='POST',data=data,token=token,content_type='application/octet-stream'))
            if uploaded.get('state')!='uploaded' or uploaded.get('size')!=len(data) or uploaded.get('digest')!='sha256:'+digest(directory/name):
                fail('UPLOAD_VALIDATION_FAILED')
        api_json('/releases/'+str(rid),method='PATCH',token=token,value={'draft':False,'make_latest':'false'})
        return tag
