"""Restore public original audit columns/models and rerun independent cash checks.

No fitting, simulator, account import, provider data download or prior STATE read.
Existing interpreter/dependencies are reused; not a new-machine install test.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import urllib.request
import zipfile
import numpy as np
import polars as pl

PREFIX='research/btc-beta-residual-cs-20261011/'
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--commit',required=True)
    parser.add_argument('--state',type=Path,required=True)
    a=parser.parse_args()
    if len(a.commit)!=40 or any(c not in '0123456789abcdef' for c in a.commit):
        raise ValueError('Exact public immutable commit')
    state=a.state.resolve()
    if not state.is_relative_to(Path('/workspace')):raise ValueError('Fresh task STATE')
    root=state/'verification';root.mkdir()
    files=[]
    def fetch(name):
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+a.commit+'/'+name,timeout=40).read()
        path=root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(raw)
        files.append(dict(path=name,bytes=len(raw),SHA256=sha(raw)))
        return raw
    binding=json.loads(fetch(PREFIX+'PERSISTENCE_BINDING.json'))
    for name,digest in binding['files'].items():
        if sha(fetch(name))!=digest:raise ValueError('Remote frozen code/model/summary SHA: '+name)
    source=json.loads((root/PREFIX/'SOURCE_BINDING.json').read_bytes())
    if sha((root/'scripts/investment/audit_shared_direction.py').read_bytes())!=source['financial_source_sha256']['scripts/investment/audit_shared_direction.py']:
        raise ValueError('Mature independent auditor source')
    index=json.loads((root/PREFIX/'wallet-artifacts/INDEX.json').read_bytes())
    packet=state/'AUDIT_WALLETS.zip'
    h=hashlib.sha256()
    with packet.open('xb') as f:
        for i,part in enumerate(index['parts']):
            raw=fetch(PREFIX+'wallet-artifacts/'+part['name'])
            if len(raw)!=part['bytes'] or sha(raw)!=part['SHA256']:raise ValueError('Public result part SHA')
            h.update(raw);f.write(raw)
            if (i+1)%6==0:print('Public artifact parts',i+1,'/',len(index['parts']),flush=True)
    if packet.stat().st_size!=index['packet_bytes'] or h.hexdigest()!=index['packet_SHA256']:
        raise ValueError('Public result archive SHA')
    with zipfile.ZipFile(packet) as z:
        if z.testzip() is not None or set(z.namelist())!=set(m['name'] for m in index['members']):
            raise ValueError('Artifact membership/CRC')
        for m in index['members']:
            raw=z.read(m['name'])
            if len(raw)!=m['bytes'] or sha(raw)!=m['SHA256']:raise ValueError('Public artifact member SHA')
    forbidden=(Path('/workspace/coin-btc-beta-residual'),Path('/workspace/btc-beta-residual-state'),
               Path('/workspace/short-funding-residual-state'))
    blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            path=Path(args[0]).resolve()
            if any(path.is_relative_to(p) for p in forbidden):
                blocked.append(str(path));raise PermissionError('Cold verification forbids prior workspace/STATE reads')
    sys.addaudithook(audit)
    sys.path.insert(0,str(root))
    sys.path.insert(0,str(root/PREFIX))
    codec=importlib.import_module('persist_wallets')
    from modules.transformer_v3.isolated_audit import verify
    from scripts.investment import audit_shared_direction as cash_audit
    if not Path(codec.__file__).resolve().is_relative_to(root) or not Path(cash_audit.__file__).resolve().is_relative_to(root):
        raise ValueError('Restored source only')
    output=codec.restore(packet,state/'restored-wallets')
    cases=[]
    max_pair_error=0.
    daily={}
    for directory in sorted(p for p in output.iterdir() if p.is_dir()):
        summary=json.loads((directory/'summary.json').read_bytes())
        observed=verify(directory,SYMBOLS,summary['unit_scenario']['scale'])
        original=json.loads((directory/'INDEPENDENT_AUDIT.json').read_bytes())
        if observed!=original:raise ValueError('Recovered independent audit differs from saved original')
        cases.append(dict(case=directory.name,rows=observed['minutes'],status=observed['status'],
                          maximum_NAV_error_USDT=observed['maximum_NAV_error_USDT'],
                          terminal_cash=observed['terminal_cash_realized'],liquidations=summary['liquidation_count']))
        frame=pl.read_parquet(directory/'daily_nav.parquet')
        daily[directory.name]=np.diff(np.r_[10000.,frame['nav'].to_numpy()])
    result=json.loads((output/'RESULT.json').read_bytes())
    joined=np.column_stack([daily['residual_'+name]-daily['raw_'+name] for name in ('RAW_AS_FRACTION','RAW_AS_PERCENT')])
    rng=np.random.default_rng(811084)
    indices=((rng.integers(0,63,size=(1000,5))[:,:,None]+np.arange(14))%63).reshape(1000,70)[:,:63]
    bootstrap=np.quantile(joined[indices].sum(axis=1),[.025,.975],axis=0).T
    max_bootstrap_error=0.
    for pair,name in zip(result['pairs'],('RAW_AS_FRACTION','RAW_AS_PERCENT')):
        observed=float((daily['residual_'+name]-daily['raw_'+name]).sum())
        max_pair_error=max(max_pair_error,abs(observed-pair['paired_net_increment_USDT']))
    if max_pair_error>1e-9:raise ValueError('Recovered paired UTC NAV increments')
    for i,pair in enumerate(result['pairs']):
        max_bootstrap_error=max(max_bootstrap_error,float(np.max(np.abs(bootstrap[i]-np.asarray(pair['conditional_14day_joint_bootstrap_net_increment_95_USDT'])))))
    if max_bootstrap_error>1e-9:raise ValueError('Independent recovered joint bootstrap')
    targets=np.load(root/PREFIX/'diagnostic/SAVED_TARGETS.npz',allow_pickle=False)
    if targets['raw'].shape!=(365,5) or targets['residual'].shape!=(365,5):raise ValueError('Public saved target model shape')
    report=dict(status='PASS_PUBLIC_ARTIFACT_RECOVERY_AND_INDEPENDENT_CASH_AUDIT',commit=a.commit,
                parts=len(index['parts']),packet_SHA256=h.hexdigest(),files=files,cases=cases,
                maximum_paired_increment_error_USDT=max_pair_error,restored_causal_target_values=365*5*2,
                maximum_bootstrap_endpoint_error_USDT=max_bootstrap_error,
                source_workspace_or_STATE_read_attempts=blocked,additional_fits=0,wallet_reruns=0,
                scope='17 original audit columns byte-exact after decoding; original full37column Parquet byte restoration not claimed. Runtime dependencies already installed.')
    with (state/'COMPLETION.json').open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({k:report[k] for k in ('status','commit','parts','maximum_paired_increment_error_USDT','source_workspace_or_STATE_read_attempts','wallet_reruns')},indent=2),flush=True)


if __name__=='__main__':main()
