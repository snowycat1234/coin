"""Read-only closed backups and exact partial artifacts before independent recovery."""
import json, shutil, sqlite3, subprocess, time
from datetime import UTC, datetime
from pathlib import Path
from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.microstructure import read_microstructure_status
from quant.collector_public_v3 import read_public_v3_status
from quant.research_fast.dataset import file_sha

out=STATE/'v7-runtime-preservation-20261002-v3';out.mkdir()
def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False)
def active():
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():continue
        try:
            command=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode()
            if any(token in command for token in (' -m quant.microstructure --run',' -m quant.collector_public_v3 --run','python scripts/research_v7/screen_family_models.py --fold','python scripts/research_v7/fetch_monthly_v2.py --market')):
                result.append({'pid':int(path.name),'command':command})
        except (OSError,UnicodeError):pass
    return result
assert not active(),active()
saved=[]
paths=list((STATE/'v7-runtime-preservation-20261002-v1').glob('*new.*.log'))
paths += [STATE/'v7-family-screen-20261002-v2/queue.log',ROOT/'reports/fast_research/V7_MONTHLY_PERP_ETHUSDT_202510_V2.json']
paths += list((STATE/'v7-family-screen-20261002-v2/fold-A').glob('*.json'))
for index,path in enumerate(paths):
    target=out/f'{index:02d}-{path.name}';shutil.copyfile(path,target)
    assert file_sha(path)==file_sha(target)
    saved.append({'source':str(path),'saved':str(target),'sha256':file_sha(target),'bytes':target.stat().st_size})
backups=[]
for name in ('microstructure.sqlite3','collector_public_v3.sqlite3'):
    source=sqlite3.connect(f'file:{STATE/name}?mode=ro',uri=True);target=out/name
    destination=sqlite3.connect(target)
    try:
        source.backup(destination,pages=256);assert destination.execute('PRAGMA quick_check').fetchall()==[('ok',)]
        destination.commit()
    finally:source.close();destination.close()
    backups.append({'path':str(target),'sha256':file_sha(target),'bytes':target.stat().st_size,'closed':True,'quick_check':'ok'})
micro=read_microstructure_status();public=read_public_v3_status()
old=json.loads((ROOT/'reports/fast_research/V7_PUBLIC_COLLECTOR_RECOVERY_20261002_V1.json').read_text())
assert micro['binding']==old['microstructure']['binding']
assert micro['binding']['implementation_sha256']==file_sha(ROOT/'src/quant/microstructure.py')
assert public['contract']==old['public_v3']['contract'] and public['stored_source_matches_current']
logs=(STATE/'v7-runtime-preservation-20261002-v1/microstructure-new.stderr.log').read_text()
assert 'Receipt clock incident requires restart' in logs
fold=STATE/'v7-family-screen-20261002-v2/fold-A'
assert not any((fold/name).exists() for name in ('RIDGE-1-5m','XGB-S-5m','TCN-S-5m','COMPLETE.json'))
partial={str(path.relative_to(fold)):{'sha256':file_sha(path),'bytes':path.stat().st_size} for path in fold.rglob('*') if path.is_file()}
archive=STATE/'v7-monthly-perp-ethusdt-202510-v2/ETHUSDT-aggTrades-2025-10.zip'
monthly=json.loads((ROOT/'reports/fast_research/V7_MONTHLY_PERP_ETHUSDT_202510_V2.json').read_text())
assert monthly['completed_days']==30 and monthly['status']=='MONTHLY_V7_RUNNING_UNACCEPTED'
for entry in monthly['daily']:
    assert file_sha(Path(entry['path']))==entry['sha256']
    manifest=json.loads(Path(entry['path']).read_text())
    assert file_sha(Path(manifest['feature_path']))==entry['parquet_sha256']
ledger=disk.check(1_000_000_000)
receipt={'status':'PRESERVED_INTERRUPTED_COLLECTORS_AND_ZERO_FIT_RESEARCH',
    'created_utc':datetime.now(UTC).isoformat(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'resources':resources.status(),'disk':ledger,'saved_files':saved,'closed_backups':backups,
    'microstructure_before':micro,'public_before':public,
    'L1_exit_cause':'Verified Receipt clock incident requires restart; frozen guard correctly stopped.',
    'environment_interruption':'Distro init and all previous task PIDs disappeared; trigger not established; no OOM attribution.',
    'research_partial_artifacts':partial,'model_fits_before_interruption':0,'new_OOS_results_before_interruption':0,
    'unfinished_monthly_days':30,'unaccepted_archive_sha256':file_sha(archive),'unaccepted_archive_bytes':archive.stat().st_size,
    'old_frozen_sources_unchanged':True,'source_version_switch':False,'healthy_gap_splicing':False,
    'locked_consumed':False,'orders_sent':0,'gpu_hours':0}
save(out/'PRESERVATION.json',receipt)
report=ROOT/'reports/fast_research/V7_RUNTIME_INTERRUPTION_PRESERVATION_20261002_V3.json'
save(report,{**receipt,'preservation_path':str(out/'PRESERVATION.json'),'preservation_sha256':file_sha(out/'PRESERVATION.json')})
print(json.dumps({'status':receipt['status'],'model_fits':0,'preserved_monthly_days':30,'disk_total_bytes':ledger['total_bytes']}),flush=True)
