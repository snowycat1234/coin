"""Snapshot and rehash v2 evidence into new external STATE without modifying v2."""
import argparse,gzip,hashlib,json,os,subprocess,time
from collections import Counter
from pathlib import Path
from modules.transformer_v2.train import atomic,sha

def seal(paths):
    return [dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(set(map(Path,paths)))]

def verify(entries):
    for e in entries:
        if sha(e['path'])!=e['sha256']:raise ValueError('Protected evidence changed: '+e['path'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--v2-state',required=True);p.add_argument('--v2-repo',required=True);p.add_argument('--complete-run',required=True);a=p.parse_args()
    state=Path(a.state);old=Path(a.v2_state);repo=Path(a.v2_repo);state.mkdir(exist_ok=True)
    assert state.resolve()!=old.resolve() and not state.resolve().is_relative_to(old.resolve())
    assert not (state/'PHASE0_V2_PRESERVATION.json').exists(),'Do not overwrite a preservation receipt'
    started=time.time();head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    assert head=='0350589199d4566ac519b0e581ff86eb065ba934' and not subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True)
    cases=json.loads((old/'NATIVE_DEV_RESULTS.json').read_text());assert cases['status']=='COMPLETE' and len(cases['cases'])==720 and not cases['errors']
    legacy=json.loads(Path(a.complete_run,'NATIVE_RESULTS.json').read_text())
    controls=[c for c in legacy['cases'] if c['model'] in ('BASE_CASH','BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3','TRANSFORMER_SHARED','PER_ASSET_XGB')]
    assert len(controls)==72
    paths=[p for p in old.rglob('*') if p.is_file()]+[p for p in (repo/'reports/transformer_v2').rglob('*') if p.is_file()]
    for c in controls:
        paths.extend(Path(e['path']) for e in c['artifacts'].values());paths.extend([Path(c['summary_path']),Path(c['independent_audit_path'])])
    entries=[]
    for i,p in enumerate(sorted(set(paths)),1):
        entries.extend(seal([p]))
        if i%100==0:atomic(state/'progress.json',dict(stage='PHASE0_PROTECTED_V2_SHA',current=i,total=len(set(paths)),pid=os.getpid(),updated_at=time.time()))
    manifest=state/'V2_PROTECTED_FILES.json.gz'
    with gzip.open(manifest,'wt',encoding='utf-8') as f:json.dump(entries,f,separators=(',',':'))
    reasons=[]
    for c in cases['cases']:
        if c['economic_calendar_complete']:continue
        s=c['summary'];reasons.append(dict(task_id=c['task']['id'],completion=s['completion'],account_status=s['account_status'],
                                          stop_us=s['stop_us'],completed_minutes=s['completed_minutes'],required_minutes=s['required_minutes'],
                                          halt_witness=s.get('halt_witness'),summary_sha256=c['summary_sha256']))
    assert len(reasons)==111
    atomic(state/'V2_INCOMPLETE_REASONS.json',dict(rows=reasons,counts=dict(Counter(r['account_status'] for r in reasons))))
    fits=json.loads((old/'FIT_PROGRESS.json').read_text());final=json.loads((old/'FINAL_FITS.json').read_text())
    assert fits['completed']==120 and final['completed']==24
    exposure=json.loads((old/'DEV_EXPOSURE_RESULTS.json').read_text());oracle=json.loads((old/'DEV_ORACLE_RESULTS.json').read_text())
    assert len(exposure['rows'])==36 and len(oracle['rows'])==36
    result=dict(status='V2_PRESERVED_AND_REHASHED',v2_HEAD=head,protocol_sha256=sha(repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'),
                started_at=started,finished_at=time.time(),protected_files=len(entries),protected_bytes=sum(e['bytes'] for e in entries),manifest_sha256=sha(manifest),
                CUDA_development_fits=120,final_fits=24,native_tasks=720,reused_controls=72,exposure_controls=36,corrected_oracle_cases=36,
                incomplete_accounts=111,incomplete_reason_sha256=sha(state/'V2_INCOMPLETE_REASONS.json'),locked_N_E_sha256=sha(old/'TRANSFORMER_V2_LOCKED_RESULTS.json'),
                raw_locked_status=json.loads((old/'TRANSFORMER_V2_LOCKED_RESULTS.json').read_text())['status'],v2_modified=False)
    atomic(state/'PHASE0_V2_PRESERVATION.json',result);atomic(state/'progress.json',dict(stage='PHASE0_COMPLETE',current=len(entries),total=len(entries)))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
