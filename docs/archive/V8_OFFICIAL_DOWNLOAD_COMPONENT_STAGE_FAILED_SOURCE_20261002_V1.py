"""Stage exactly two small pinned official software files on D-hosted STATE."""
from datetime import UTC,datetime
import hashlib,json
from pathlib import Path
import httpx

root=Path('/mnt/d/codex/coin')
state=Path('/home/xflops/coin-state/v8-binance-official-component-20261002-v1')
assert not state.exists()
state.mkdir()
commit='f446ce3812bd4e5521f21faecd4ae3c6460e49fc'
files=[]
with httpx.Client(timeout=30,follow_redirects=False) as client:
    for name in ('enums.py','utility.py'):
        url=f'https://raw.githubusercontent.com/binance/binance-public-data/{commit}/python/{name}'
        response=client.get(url)
        response.raise_for_status()
        raw=response.content
        assert 0<len(raw)<=64_000
        compile(raw,str(state/name),'exec')
        with (state/name).open('xb') as stream:stream.write(raw)
        files.append({'path':str(state/name),'url':url,'http_status':response.status_code,
                      'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
result={'status':'PINNED_OFFICIAL_DOWNLOAD_COMPONENT_STAGED_NO_MARKET_DATA',
        'created_utc':datetime.now(UTC).isoformat(),'repo':'https://github.com/binance/binance-public-data',
        'commit':commit,'software_license':'MIT declared by upstream README; no standalone LICENSE',
        'data_terms_sha256':'dcf358e9d18f598a7a635fac80f6e643fa24a0e111a4d39bda47f1e246b31eb1',
        'use':'Call official utility.download_file for fixed small funding/mark/index archives; no upstream modification',
        'files':files,'local_modifications':[],'zip_bodies_read':0}
out=root/'reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V1.json'
with out.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result))
