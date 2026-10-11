"""Public-only cold restore and saved prediction replay; never train/refit.

The worker runs remote source bytes with a minimal PYTHONPATH in a fresh folder.
Python file opens outside that folder and the installed runtime are denied.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import urllib.request
import zipfile

BASE='research/slow-momentum-cpd-cost-data-repair-20261011'
SCRIPT=BASE+'/persistence/verify_public_models.py'
CONFIG_SHA='d54f4b20133bd281c04d1ae3eeb4f9f51a7de14d0d0cf54d439ff9f520aef891'
BUNDLE_SHA='eea641c4cc965ff3d04a93b7aa259874d81bd6cfa2d5711ac7f45dc74a7ab454'
OLD_FROZEN_SHA='8587adcb407ba7b55e66eed6e1d06596cbbcb1e743f5fe04a822b98eee6b4bd2'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def download(state,commit):
    began=time.monotonic();code=state/'code';receipts=[]
    def get(name,source_commit=commit,target=None,digest=None):
        url=f'https://raw.githubusercontent.com/snowycat1234/coin/{source_commit}/{name}'
        with urllib.request.urlopen(url,timeout=30) as r:
            if not r.url.startswith('https://raw.githubusercontent.com/snowycat1234/coin/'):
                raise ValueError('Unexpected public redirect')
            raw=r.read(2097153)
        if len(raw)>2097152 or (digest is not None and sha(raw)!=digest):
            raise ValueError('Public size/SHA mismatch: '+name)
        if target is not None:
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(raw)
        receipts.append(dict(url=url,sha256=sha(raw),bytes=len(raw),stored_as=str(target.relative_to(state)) if target else 'ASSEMBLY_ONLY'))
        return raw
    precheck=json.loads(get(BASE+'/persistence/PUBLICATION_PRECHECK.json',target=state/'PUBLICATION_PRECHECK.json'))
    if precheck['status']!='PASS' or precheck['bundle_sha256']!=BUNDLE_SHA or precheck['bundle_bytes']!=1067209:
        raise ValueError('Published model precheck mismatch')
    publication=json.loads(get(BASE+'/persistence/PUBLICATION_PROTOCOL.json',target=state/'PUBLICATION_PROTOCOL.json'))
    if publication['bundle_sha256']!=BUNDLE_SHA or publication['new_training_updates']!=0 or publication['new_GP_fits']!=0:
        raise ValueError('Published cold-restore scope differs')
    bundle=get(BASE+'/persistence/MODEL_STATE_RECOVERY.zip',target=state/'MODEL_STATE_RECOVERY.zip',digest=BUNDLE_SHA)
    index=json.loads(get(BASE+'/results/MODEL_STATE_RECOVERY_INDEX.json',target=state/'MODEL_STATE_RECOVERY_INDEX.json'))
    with zipfile.ZipFile(io.BytesIO(bundle)) as z:
        if len(z.namelist())!=33 or len(set(z.namelist()))!=33 or z.testzip() is not None:
            raise ValueError('Bundle count/duplicate/CRC mismatch')
        if json.loads(z.read('MODEL_STATE_RECOVERY_INDEX.json'))['files']!=index['files']:
            raise ValueError('Internal/public index mismatch')
        for name,v in index['files'].items():
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:
                raise ValueError('Unsafe archive path')
            raw=z.read(name)
            if sha(raw)!=v['sha256'] or len(raw)!=v['bytes']:raise ValueError('Member SHA mismatch')
            dest=state/'restored'/name;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as f:f.write(raw)
    config_raw=get(BASE+'/CONFIG.json',target=code/BASE/'CONFIG.json',digest=CONFIG_SHA)
    config=json.loads(config_raw)
    for name,h in config['source_files'].items():get(name,target=code/name,digest=h)
    for name in ('modules/slow_momentum_cpd/__init__.py','modules/collector_research/__init__.py','modules/collector_research/pipeline/__init__.py'):
        get(name,target=code/name,digest=publication['package_init_sha256'][name])
    get(SCRIPT,target=code/SCRIPT,digest=publication['verification_script_sha256'])
    for name,h in config['prefit_artifacts'].items():get(BASE+'/prefit/'+name,target=code/BASE/'prefit'/name,digest=h)
    original='research/slow-momentum-cpd-20261011/'
    protocol=json.loads(get(original+'PROTOCOL.json',target=code/original/'PROTOCOL.json'))
    get(original+'results/FROZEN_TRAINING.json',target=code/original/'results/FROZEN_TRAINING.json',digest=OLD_FROZEN_SHA)
    mse=json.loads(get(original+'results/RESULT.json',target=code/original/'results/RESULT.json'))
    get(original+'results/PREDICTIONS.csv',target=code/original/'results/PREDICTIONS.csv',digest=mse['prediction_sha256'])
    gross='research/slow-momentum-cpd-sharpe-20261011/'
    old_result=json.loads(get(gross+'results/RESULT.json',target=code/gross/'results/RESULT.json'))
    get(gross+'results/POSITIONS.csv',target=code/gross/'results/POSITIONS.csv',digest=old_result['positions_sha256'])
    source=protocol['source'];parts=[]
    for part in source['parts']:
        raw=get(source['base']+part['file'],source_commit=source['commit'],digest=part['sha256'])
        if len(raw)!=part['bytes']:raise ValueError('Public price part size differs')
        parts.append(raw)
    raw=b''.join(parts)
    if sha(raw)!=source['archive_sha256']:raise ValueError('Public price archive differs')
    (state/'source/features.zip').write_bytes(raw)
    owned=sum(p.stat().st_size for p in state.rglob('*') if p.is_file())
    if owned>10485760:raise ValueError('10MiB cold restore output stop')
    save(state/'REMOTE_DOWNLOAD.json',dict(status='PASS',commit=commit,receipts=receipts,
        network_bytes=sum(r['bytes'] for r in receipts),owned_bytes=owned,bundle_sha256=BUNDLE_SHA,
        restored_payloads=32,legacy_STATE_reads=0,market_provider_downloads=0,seconds=time.monotonic()-began))
    print(f'REMOTE_RESTORE payloads=32 checkpoints=18 network_files={len(receipts)} bytes={sum(r["bytes"] for r in receipts)}',flush=True)
    env={'PYTHONPATH':str(code),'PYTHONDONTWRITEBYTECODE':'1','CUDA_VISIBLE_DEVICES':'',
         'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','POLARS_MAX_THREADS':'1'}
    subprocess.run([sys.executable,str(code/SCRIPT),'--worker','--state',str(state),'--commit',commit],cwd=code,env=env,check=True)


def worker(state,commit):
    began=time.monotonic();runtime=Path(sys.prefix).resolve();denied=[];workspace_opens=set()
    def audit_open(event,args):
        if event!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
        path=Path(os.fsdecode(args[0])).resolve()
        if path.is_relative_to(Path('/workspace')):
            workspace_opens.add(str(path))
            if not path.is_relative_to(state) and not path.is_relative_to(runtime):
                denied.append(str(path));raise RuntimeError('Cold worker forbids existing workspace source/data/state reads')
    sys.addaudithook(audit_open)
    import importlib.metadata
    import numpy as np
    import torch
    from modules.slow_momentum_cpd import core,run,sharpe,cost_training,repaired_data
    for module in (core,run,sharpe,cost_training,repaired_data):
        if not Path(module.__file__).resolve().is_relative_to(state/'code'):
            raise ValueError('Cold worker imported a nonremote model source')
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    code=state/'code';config=json.loads((code/BASE/'CONFIG.json').read_text())
    for name,h in config['source_files'].items():
        if sha((code/name).read_bytes())!=h:raise ValueError('Downloaded code identity differs')
    for name,h in config['prefit_artifacts'].items():
        if sha((code/BASE/'prefit'/name).read_bytes())!=h:raise ValueError('Downloaded frozen identity differs')
    original=code/'research/slow-momentum-cpd-20261011'
    protocol=json.loads((original/'PROTOCOL.json').read_text())
    available,close,_=run.load_close(state/'source/features.zip',protocol)
    old_frozen=json.loads((original/'results/FROZEN_TRAINING.json').read_text())
    repair=json.loads((code/BASE/'prefit/DATA_REPAIR.json').read_text())
    new_frozen=json.loads((code/BASE/'prefit/FROZEN_TRAINING.json').read_text())
    if new_frozen['data_repair_sha256']!=config['prefit_artifacts']['DATA_REPAIR.json']:
        raise ValueError('Repair/refreeze binding differs')
    old_data=repaired_data.prepared(available,close,old_frozen)
    new_data=repaired_data.prepared(available,repaired_data.apply_patch(available,close,repair['records']),new_frozen)
    model_info=json.loads((state/'PUBLICATION_PRECHECK.json').read_text())
    loaded={};models=[]
    with torch.inference_mode():
        for record in model_info['checkpoints']:
            name=record['file'];path=state/'restored'/name
            if sha(path.read_bytes())!=record['sha256']:raise ValueError('Cold checkpoint identity differs')
            cp=torch.load(path,map_location='cpu',weights_only=True)
            family='mse256' if name.startswith('slow-momentum-state/') else 'gross1024' if name.startswith('slow-momentum-sharpe-state/') else 'cost64'
            arm='trend_cpd' if 'trend_cpd' in path.name else 'trend';seed=cp['seed']
            model=run.TrendLSTM() if family=='mse256' else sharpe.PositionLSTM()
            model.load_state_dict(cp['model'],strict=True);model.eval()
            if any(not torch.isfinite(p).all() for p in model.parameters()):raise ValueError('Nonfinite restored parameter')
            ages=sorted({int(v['step']) for v in cp['optimizer']['state'].values()})
            if ages!=record['adam_ages'] or cp['updates']!=record['updates']:raise ValueError('Restored optimizer ages differ')
            if family=='cost64':
                r=json.loads((state/'restored/slow-momentum-cost-repaired-state/RESULT.json').read_text())
                if cp['config_sha256']!=CONFIG_SHA or cp['source_commit']!=r['source_commit'] or cp['training_identity']!=r['training_identity']:
                    raise ValueError('Cost checkpoint source/config identity differs')
            loaded[(family,arm,seed)]=model
            models.append(dict(file=name,sha256=record['sha256'],model_class=record['model_class'],seed=seed,updates=cp['updates'],adam_ages=ages,strict_load='PASS'))
        if len(loaded)!=18:raise ValueError('Unexpected cold model axis')
        groups=[('mse256',original/'results/PREDICTIONS.csv',old_data),
                ('gross1024',code/'research/slow-momentum-cpd-sharpe-20261011/results/POSITIONS.csv',old_data),
                ('cost64',state/'restored/slow-momentum-cost-repaired-state/POSITIONS.csv',new_data)]
        replays=[];scalar_count=0;max_error=0.
        for family,path,data in groups:
            records=list(csv.DictReader(path.open()));features,inputs,returns,vol=data
            if len(records)!=(2209 if family=='mse256' else 2415):raise ValueError('Saved forecast coverage differs')
            for start,end in protocol['validation']:
                subset=[r for r in records if r['block']==start]
                if family=='mse256':
                    rows=core.sample_index(features,returns,vol,available,run.utc_us(start),run.utc_us(end))
                    clock_to_row={int(v):k for k,v in enumerate(available)}
                    expected_rows=np.asarray([(clock_to_row[int(r['available_us'])],core.SYMBOLS.index(r['symbol'])) for r in subset])
                    np.testing.assert_array_equal(rows,expected_rows)
                    x=run.sequences(inputs,rows);ep=None
                else:
                    ep=cost_training.build_episode(available,features,inputs,returns,vol,start,end);x=ep['x']
                    if len(subset)!=len(ep['clock'])*5:raise ValueError('Saved position/calendar coverage differs')
                    for k,row in enumerate(subset):
                        t,a=divmod(k,5)
                        if row['symbol']!=core.SYMBOLS[a] or int(row['available_us'])!=ep['clock'][t] or int(row['eligible'])!=int(ep['mask'][t,a]):
                            raise ValueError('Saved symbol/clock/causal mask differs')
                if any(int(r['label_end_us'])!=int(r['available_us'])+core.DAY_US or int(r['label_end_us'])>=run.utc_us(end) for r in subset):
                    raise ValueError('Saved label maturity differs')
                for arm in ('trend','trend_cpd'):
                    for seed in (2001,2002,2003):
                        model=loaded[(family,arm,seed)];arm_x=cost_training.arm_inputs(x,arm)
                        if family=='cost64':values=cost_training.model_outputs(model,arm_x,128).numpy().astype(float)
                        else:values=run.predict(model,arm_x)
                        column=('cpd' if arm=='trend_cpd' else 'trend')+f'_seed{seed}' if family=='mse256' else arm+f'_seed{seed}'
                        expected=np.asarray([float(r[column]) for r in subset])
                        if ep is not None:
                            actual=np.zeros(ep['mask'].shape);actual[ep['mask']]=values;actual=actual.ravel()
                        else:actual=values
                        error=float(np.abs(actual-expected).max());max_error=max(max_error,error)
                        if error>1e-12:raise ValueError('Cold saved prediction replay differs')
                        replays.append(dict(family=family,arm=arm,seed=seed,block=start,prediction_scalars=len(expected),max_absolute_residual=error,bit_identical=bool(np.array_equal(actual,expected))))
                        scalar_count+=len(expected)
                print(f'COLD_SAVED_REPLAY {family} {start} 6/6 models',flush=True)
    if denied:raise ValueError('Cold worker attempted a forbidden workspace read')
    report=dict(status='PASS',public_commit=commit,bundle_sha256=BUNDLE_SHA,checkpoint_loads=18,checkpoints=models,
        saved_model_block_replays=len(replays),prediction_scalars=scalar_count,replays=replays,max_saved_prediction_residual=max_error,
        all_saved_prediction_vectors_bit_identical=all(r['bit_identical'] for r in replays),legacy_workspace_read_attempts=denied,
        python_open_hook='Existing /workspace sources/data/STATE denied; only fresh cold directory and installed interpreter runtime allowed',
        framework=dict(Python=sys.version,**{n:importlib.metadata.version(n) for n in ('torch','numpy','scipy','pyarrow','pandas','polars')}),
        new_training_updates=0,new_GP_fits=0,new_scaler_fits=0,new_wallets=0,new_scientific_validation_queries=0,
        audit_inference_scope='54 same saved-policy block replays across MSE256/gross1024/cost64; not new recipe scores or training',
        cold_scope='Code,models,prices,frozenparameters and savedforecasts recovered from public immutable Git URLs; existing installed Python/runtime only, not cleanOS/packageinstallation verification',
        seconds=time.monotonic()-began)
    save(state/'COLD_MODEL_REPLAY.json',report)
    print(json.dumps(dict(status='PASS',checkpoint_loads=18,saved_model_block_replays=len(replays),prediction_scalars=scalar_count,max_residual=max_error,bit_identical=report['all_saved_prediction_vectors_bit_identical'],new_updates=0,legacy_reads=0)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--worker',action='store_true')
    a=p.parse_args();state=a.state.resolve()
    if not state.is_relative_to(Path('/workspace')):raise ValueError('Fresh cold directory must be under /workspace')
    if a.worker:worker(state,a.commit)
    else:
        if (state/'code').exists() or (state/'MODEL_STATE_RECOVERY.zip').exists():raise FileExistsError('No cold restore overwrite/implicit retry')
        state.mkdir(parents=True,exist_ok=True);(state/'source').mkdir(exist_ok=True);download(state,a.commit)
