"""Source-admission capability: reject known incomplete native paths before wallets."""
import argparse,hashlib,json,subprocess,time,zipfile,sys,os
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def admission(missing,prior_denial,hashes_unchanged):
    if missing and hashes_unchanged:return dict(status='STOP_UNCHANGED_REQUIRED_NATIVE_MARK_GAPS',native_wallets_admitted=0,missing_mark_rows=missing,denied_API_retry_allowed=False,prior_denial=prior_denial,large_remaining_source_acquisition_admitted=False)
    if missing:return dict(status='UNKNOWN_ARCHIVE_CHANGED_NEEDS_BOUNDED_SOURCE_REVIEW',native_wallets_admitted=0,missing_mark_rows=missing,denied_API_retry_allowed=False,prior_denial=prior_denial,large_remaining_source_acquisition_admitted=False)
    return dict(status='SLICE_SOURCE_ONLY_READY_FULLYEAR_OTHER_SOURCES_NOT_CERTIFIED',native_wallets_admitted=0,denied_API_retry_allowed=False,prior_denial=prior_denial,large_remaining_source_acquisition_admitted=False)
def run(state,source,expected=None):
    assert not state.exists() and not git('status','--porcelain');P=json.loads((HERE/'PROTOCOL.json').read_text());start=time.monotonic()
    if not expected:assert git('rev-parse','HEAD').decode().strip()==source
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha((ROOT/p).read_bytes())==s,p
    state.mkdir();os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),WARMUP_START='2024-08-01',START_DATE='2024-08-01',END_DATE='2024-08-31',SYMBOLS=','.join(P['symbols']),MAX_ARCHIVE_MIB='8',MAX_UNCOMPRESSED_MIB='64',HTTP_RETRIES='0')
    from modules.collector_research.pipeline.download import parse_checksum,check_zip,session
    from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits
    base=P['july_data_base'];commit=P['july_data_commit'];index_raw=git('show',commit+':'+base+'INDEX.json');index=json.loads(index_raw);packet=state/'ORIGINALS.zip'
    with packet.open('xb') as f:
        for part in index['parts']:
            raw=git('show',commit+':'+base+part['name']);assert len(raw)==part['bytes'] and sha(raw)==part['SHA256'];f.write(raw)
    assert packet.stat().st_size==index['package_bytes'] and sha(packet.read_bytes())==index['package_SHA256'];members={r['name']:r for r in index['members']};records=[];checks=[];missing_total=0;connection=session() if not expected else None
    observed_checks=json.loads(git('show',expected+':'+str(HERE.relative_to(ROOT))+'/result/RESULT.json'))['official_checksum_probe'] if expected else None
    try:
        with zipfile.ZipFile(packet) as z:
            assert z.testzip() is None
            for s in P['symbols']:
                frames={}
                for stamp in ('2024-08','2024-08-12'):
                    name=f'raw/markPriceKlines/{s}/{s}-1m-{stamp}.zip';raw=z.read(name);check=z.read(name+'.CHECKSUM')
                    for n,b in [(name,raw),(name+'.CHECKSUM',check)]:assert len(b)==members[n]['bytes'] and sha(b)==members[n]['SHA256']
                    stem=name.split('/')[-1];old=parse_checksum(check.decode(),stem);assert sha(raw)==old;frequency='daily' if len(stamp)==10 else 'monthly';url=f'https://data.binance.vision/data/futures/um/{frequency}/markPriceKlines/{s}/1m/{stem}.CHECKSUM'
                    if expected:r=next(x for x in observed_checks if x['URL']==url);assert r['published_archive_SHA256']==old;checks.append(r)
                    else:
                        response=connection.get(url,timeout=(10,20));response.raise_for_status();assert len(response.content)<=4096;current=parse_checksum(response.text,stem);r=dict(URL=url,HTTP_status=response.status_code,published_archive_SHA256=old,current_official_SHA256=current,checksum_body_SHA256=sha(response.content),archive_unchanged=current==old);checks.append(r)
                    p=state/stem;p.write_bytes(raw);check_zip(p);left,right=month_limits(2024,8)
                    if frequency=='daily':left+=11*86400000;right=left+86400000
                    frame,dups=validate_price(numeric_csv(p),'markPriceKlines',left,right);assert dups==0;missing=np.setdiff1d(np.arange(left,right,60000,dtype=np.int64),frame.timestamp_ms.to_numpy());np.testing.assert_array_equal(missing,np.array(P['known_gap_open_ms'],np.int64));frames[frequency]=frame
                    records.append(dict(symbol=s,frequency=frequency,official_URL=url.removesuffix('.CHECKSUM'),source_member=name,original_SHA256=old,observed_rows=len(frame),missing_open_ms=missing.tolist(),CRC=True,all_source_numeric_vectors_SHA256=sha(frame.to_numpy().tobytes())));p.unlink();assert time.monotonic()-start<P['budget']['source_replay_seconds']
                month,day=frames['monthly'],frames['daily'];common=month[month.timestamp_ms.isin(day.timestamp_ms)].reset_index(drop=True);np.testing.assert_array_equal(common.to_numpy(),day.to_numpy());missing_total+=len(P['known_gap_open_ms']);print('ACTUAL2024_KNOWN_MARK_GAP_REPLAYED',s,len(month),len(day),'unfilled',2,flush=True)
        denial=json.loads((HERE/'evidence/PRIOR_API_REFUSAL.json').read_text())['api_probe']['http_code'];gate=admission(missing_total,denial,all(r['archive_unchanged'] for r in checks));report=dict(**gate,source_science_commit=source,published_source_commit=commit,source_index_SHA256=sha(index_raw),calendar=P['calendar'],records=records,official_checksum_probe=checks,provider_checksum_requests=0 if expected else len(checks),provider_archive_downloads=0,new_wallets=0,new_fits=0,old_wallet_reruns=0,full2024_results='NOT_RUN_NOT_SOURCE_READY',proxy_or_imputed_price_used=False)
        if expected:
            observed=json.loads(git('show',expected+':'+str(HERE.relative_to(ROOT))+'/result/RESULT.json'));observed['provider_checksum_requests']=0;assert report==observed;save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC2024_SOURCE_ADMISSION_ZERO_DOWNLOAD',artifact_commit=expected,observed_metadata_not_requeried=True,source_values_gap_vectors_gate_exact=True,new_provider_downloads=0,new_wallets=0,new_fits=0))
        save(state/'RESULT.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-start));print(json.dumps(dict(status=report['status'],missing_mark_rows=missing_total,provider_checksum_requests=report['provider_checksum_requests'],native_wallets_admitted=0),indent=2),flush=True)
    except Exception as e:
        save(state/'FAILED.json',dict(status='STOP_BOUNDED_SOURCE_ADMISSION',error=str(e),checksum_requests_completed=len(checks),HTTP_status=getattr(getattr(e,'response',None),'status_code',None),no_denied_API_retry=True,new_wallets=0,new_fits=0));raise
    finally:
        if connection:connection.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
