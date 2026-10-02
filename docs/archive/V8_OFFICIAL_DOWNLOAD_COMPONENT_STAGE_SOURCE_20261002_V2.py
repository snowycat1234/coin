"""Pinned official software via GitHub Contents API, preserving failed raw-host run."""
from datetime import UTC,datetime
import base64,hashlib,json,subprocess,sys
from pathlib import Path
import httpx

root=Path('/mnt/d/codex/coin')
sys.path.insert(0,str(root))
from scripts.research_v8.registry import FIELDS,append_event,canonical
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reports=root/'reports/fast_research'
prior_source=root/'.cache/v8_official_download_component_stage_20261002_v1.py'
failed={'status':'FAILED_PINNED_SOFTWARE_SOURCE_STAGE','actual_exit_code':1,'actual_session':80155,
 'observed_failure_utc':datetime.now(UTC).isoformat(),'reason':'httpx.ConnectTimeout: raw.githubusercontent.com TLS handshake timeout',
 'source_path':str(prior_source),'source_sha256':sha(prior_source),'state_directory':'/home/xflops/coin-state/v8-binance-official-component-20261002-v1',
 'archive_bodies_read':0,'fits':0,'source_acceptance':False,'preregistration_before_failed_preparation':'NONE_DO_NOT_RETROCLAIM_START'}
failed_path=reports/'V8_OFFICIAL_DOWNLOAD_COMPONENT_FAILED_20261002_V1.json'
with failed_path.open('x') as stream:json.dump(failed,stream,indent=2);stream.write('\n')
state=Path('/home/xflops/coin-state/v8-binance-official-component-20261002-v2')
assert not state.exists()
state.mkdir()
commit='f446ce3812bd4e5521f21faecd4ae3c6460e49fc'
proto={'scope':'Fetch two pinned official software files, no market archives','upstream_commit':commit,
       'files':['python/enums.py','python/utility.py'],'host':'api.github.com','source_sha256':sha(Path(__file__)),
       'max_file_bytes':64000,'software_mit_declared':True,'local_modifications':[]}
event=dict.fromkeys(FIELDS)
event.update(event_id='v8-official-software-stage-20261002-v2:start',event_type='OPERATIONAL_SOURCE_PREP_START',
 experiment_id='V8-OFFICIAL-SOFTWARE-STAGE-20261002-V2',git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_manifest_hash=sha(failed_path),protocol_hash=hashlib.sha256(canonical(proto)).hexdigest(),feature_set='NONE_SOFTWARE_SOURCE_ONLY',
 labels='NONE',model_family='NONE',hyperparameters=proto,seed=None,thresholds={'max_file_bytes':64000},cost_assumptions='NOT_APPLICABLE',
 all_folds='NO_MARKET_DATA',success_failure='START_BEFORE_SOURCE_ACCESS',reason_for_next_experiment='Official raw host timed out; exact same commit via official Contents API',
 result_influenced_later_choice='NETWORK_REACHABILITY_ONLY_NO_MODELS',fits=0)
append_event(root/'reports/experiment_registry.jsonl',dict(event,event_id='v8-official-software-stage-20261002-v1:failure',
 event_type='OPERATIONAL_SOURCE_PREP_RESULT',success_failure='FAILED_RAW_HOST_TLS_TIMEOUT',output_sha256=sha(failed_path),output_path=str(failed_path)))
started=append_event(root/'reports/experiment_registry.jsonl',event)
result={'status':'FAILED_PINNED_OFFICIAL_DOWNLOAD_COMPONENT_STAGE','created_utc':datetime.now(UTC).isoformat(),
 'repo':'https://github.com/binance/binance-public-data','commit':commit,'software_license':'MIT declared by upstream README; no standalone LICENSE',
 'data_terms_sha256':'dcf358e9d18f598a7a635fac80f6e643fa24a0e111a4d39bda47f1e246b31eb1',
 'use':'Unchanged official utility.download_file for fixed small funding/mark/index archives',
 'files':[],'local_modifications':[],'zip_bodies_read':0,'registration_start':started,'prior_failure_sha256':sha(failed_path)}
out=reports/'V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json'
try:
    with httpx.Client(timeout=30,follow_redirects=False) as client:
        for name in ('enums.py','utility.py'):
            url=f'https://api.github.com/repos/binance/binance-public-data/contents/python/{name}?ref={commit}'
            response=client.get(url)
            response.raise_for_status()
            assert len(response.content)<=100_000
            item=response.json()
            assert item['type']=='file' and item['path']==f'python/{name}' and item['encoding']=='base64'
            raw=base64.b64decode(item['content'])
            assert 0<len(raw)<=64_000 and len(raw)==item['size']
            blob_sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            assert blob_sha==item['sha'],'Official Git blob differs'
            compile(raw,str(state/name),'exec')
            with (state/name).open('xb') as stream:stream.write(raw)
            result['files'].append({'path':str(state/name),'url':url,'http_status':response.status_code,
                'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_blob_sha1':blob_sha})
    result['status']='PINNED_OFFICIAL_DOWNLOAD_COMPONENT_STAGED_NO_MARKET_DATA'
except Exception as error:
    result.update(error_type=type(error).__name__,reason=str(error)[:1024])
    raise
finally:
    with out.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    append_event(root/'reports/experiment_registry.jsonl',dict(event,event_id='v8-official-software-stage-20261002-v2:complete',
       event_type='OPERATIONAL_SOURCE_PREP_RESULT',success_failure=result['status'],output_sha256=sha(out),output_path=str(out)))
print(json.dumps(result))
