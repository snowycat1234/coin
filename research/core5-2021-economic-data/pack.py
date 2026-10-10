"""Publish verified originals and compact 2021 economics in recoverable small parts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

PART=768*1024

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def main(root,destination,feature_index):
    source=root/'Y2021';validation=json.loads((source/'VALIDATION.json').read_text())
    raw=json.loads((source/'RAW_MANIFEST.json').read_text())
    assert validation['no_synthetic_observations'] and validation['no_date_selection_by_returns']
    assert validation['new_official_archive_body_bytes']<=180*2**20
    selected=[source/'RAW_MANIFEST.json',source/'VALIDATION.json',source/'EPISODES.json',source/'ECONOMICS.npz']
    for r in raw['records']:
        path=source/r['relative_raw_path']
        assert sha(path)==r['SHA256'] and path.stat().st_size==r['size']
        selected.extend([path,Path(str(path)+'.CHECKSUM')])
    for r in validation['derived_artifacts']:
        path=source/r['path'];assert sha(path)==r['SHA256']
        if path not in selected:selected.append(path)
    package=root/'Y2021-originals.zip';members=[]
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
        for path in sorted(selected):
            name=str(path.relative_to(source));info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_STORED;info.external_attr=0o100644<<16
            with path.open('rb') as body,z.open(info,'w') as out:shutil.copyfileobj(body,out,1048576)
            members.append(dict(name=name,bytes=path.stat().st_size,SHA256=sha(path)))
    target=destination/'Y2021';target.mkdir(exist_ok=False)
    parts=[]
    with package.open('rb') as f:
        i=0
        while b:=f.read(PART):
            name=f'originals.zip.part{i:04d}';(target/name).write_bytes(b)
            parts.append(dict(name=name,bytes=len(b),SHA256=hashlib.sha256(b).hexdigest()));i+=1
    cached=json.loads(feature_index.read_text())
    index=dict(schema='CORE5_FIXED2021_RECOVERABLE_ECONOMIC_PACKET_V1',status=validation['status'],
        fixed_calendar=['2021-01-01','2021-12-31'],candidate_actual_decisions=365,
        admitted_decisions=validation['admitted_decisions'],distinct_eligible_active_intervals=validation['distinct_eligible_active_intervals'],
        paid_episode_count=validation['paid_episode_count'],episodes=validation['episodes'],exclusions=validation['exclusions'],
        package_bytes=package.stat().st_size,package_SHA256=sha(package),maximum_part_bytes=PART,parts=parts,members=members,
        original_archive_count=raw['archive_count'],original_exchange_ZIPs_published_unchanged=True,
        new_official_archive_body_bytes=validation['new_official_archive_body_bytes'],provider_archive_body_cap_bytes=180*2**20,
        source_commit_binding='INDEX is consumed at its enclosing immutable Git commit; no moving-branch raw URLs required',
        economics_array_path='ECONOMICS.npz',context_inputs_path='derived/CONTEXT_INPUTS.npz',
        feature_window_references_path='derived/FEATURE_WINDOW_REFERENCES.npz',episodes_path='EPISODES.json',
        economics_schema=dict(prices=[365,5],funding_coeff=[364,5],symbol_order=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT'],
            held_intervals='(decision_i+60000001,decision_i+1+60000001]',funding_charge='-signed_quantity * funding_coeff',
            final_decision='Charged CASH; no last funding coefficient or extra price padding',
            adapter_requirement='Existing N+1 legacy loaders must explicitly adapt this unpadded contract; do not silently synthesize data'),
        CORE5_order=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT'],original_E5_slot_mapping=validation['original_E5_slot_mapping'],
        masks='Original dynamic per-asset/expert and per-feature/time masks. No ready256 or all64-complete gate. Complete fixed-five 30-return covariance remains required.',
        original_dynamic_mask_gates=validation['original_dynamic_mask_gates'],
        cached_inputs=dict(immutable_commit='e0d3400b23842f11f167a63e7d80856d76501de8',
            index_path='research/temporal-feature-data-20261009/INDEX.json',parts_prefix='research/temporal-feature-data-20261009/',
            archive_SHA256=validation['cached_feature_archive_SHA256'],archive_bytes=2246454,
            original_index=cached,source_member_bindings=validation['cached_source_bindings']),
        reused_December_marks='Cached actual event values verified by immutable table hash and strict prior clocks. Original Dec monthly ZIP source hashes retained by prior public receipt; raw Dec tape not reacquired or freshly CRC-verified.',
        full_native_minute_tape_complete=False,full_native_December_mark_tape_NOT_PUBLISHED=True,
        execution_and_owned_held_funding_ready=validation['execution_and_owned_held_funding_ready'],
        unchanged_normalizer_commit=validation['unchanged_normalizer_commit'],unchanged_normalizer_source_SHA256=validation['unchanged_normalizer_source_SHA256'],
        protocol_SHA256=validation['protocol_SHA256'],no_2020_new_decisions_or_body_acquisition=True,
        model_fits=0,model_inferences=0,backtests=0,wallets=0)
    (target/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
    print(json.dumps({k:index[k] for k in ['package_bytes','package_SHA256','distinct_eligible_active_intervals','admitted_decisions','paid_episode_count']}))
    print(json.dumps(dict(parts=len(parts),members=len(members))))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True);p.add_argument('--feature-index',type=Path,required=True)
    a=p.parse_args();main(a.root,a.destination,a.feature_index)
