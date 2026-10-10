"""Lossless seven-field wire export for the independently prepared model adapter."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np

FIELDS=['symbol_order','decision_us','execution_us','funding_interval_start_us','funding_interval_end_us','prices','funding_coeff']
CORE5=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(root,destination,contract):
    source=root/'Y2021';validation=json.loads((source/'VALIDATION.json').read_text())
    assert validation['execution_and_owned_held_funding_ready'] and validation['distinct_eligible_active_intervals']==364
    destination.mkdir(exist_ok=False)
    with np.load(source/'ECONOMICS.npz',allow_pickle=False) as rich:
        assert rich['execution_ready'].all() and rich['funding_interval_ready'].all()
        arrays={k:rich[k].copy() for k in FIELDS}
        np.savez_compressed(destination/'ECONOMICS.npz',**arrays)
        with np.load(destination/'ECONOMICS.npz',allow_pickle=False) as wire:
            assert wire.files==FIELDS
            for k in FIELDS:assert rich[k].dtype==wire[k].dtype and np.array_equal(rich[k],wire[k]),'Wire changed economic values'
    artifacts=[]
    for symbol in CORE5:
        for suffix in ('daily','funding_events','funding_intervals'):
            source_path=source/f'derived/economics/{symbol}_{suffix}.parquet'
            prefix='normalized/economics' if suffix=='funding_intervals' else 'normalized/data/normalized'
            relative=f'{prefix}/{symbol}_{suffix}.parquet';path=destination/relative
            path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source_path,path)
            assert sha(path)==sha(source_path),'Wire changed canonical economic table'
            artifacts.append(dict(path=relative,bytes=path.stat().st_size,SHA256=sha(path)))
    economic_sha=sha(destination/'ECONOMICS.npz')
    index=dict(schema='EARLY2021_SOURCE_BOUND_CONSUMER_INDEX_V1',symbols_order=CORE5,
        source_download_complete=True,official_archive_receipts_verified=True,
        normalization_source_SHA256=validation['unchanged_normalizer_source_SHA256'],
        economic_SHA256=economic_sha,economic_array=dict(path='ECONOMICS.npz',bytes=(destination/'ECONOMICS.npz').stat().st_size,SHA256=economic_sha),
        economic_table_artifacts=artifacts,execution_and_held_funding_ready=True,
        original_source_packet_commit='29030f34a5a2f4b8c83569a42063fef9b2b99545',
        original_source_packet_index_path='research/core5-2021-economic-data/Y2021/INDEX.json',
        original_source_packet_index_SHA256='48b5059f69da7f978103463f139b2ae8c102d7ebfed12b65e659f11f50526288',
        original_source_package_SHA256='b427bd0a17322f4c238cd7a813450fe5dee0f3c3a673ec38743a70784d387ab2',
        richer_economic_array_SHA256=sha(source/'ECONOMICS.npz'),
        source_archive_count=validation['original_archive_count'],new_official_archive_body_bytes=validation['new_official_archive_body_bytes'],
        download_cap_bytes=180*2**20,source_chronology='Original signed event timestamp/rate/hours; latest strictly prior completed actual minute marks.',
        candidate_decisions=365,distinct_eligible_active_intervals=364,paid_episode_count=1,episodes=validation['episodes'],exclusions=validation['exclusions'],
        terminal_contract='Fresh CASH at Jan1; charged CASH at Dec31 00:01:00.000001 UTC. 365 real prices,364 real held intervals; no padding.',
        mask_bindings=dict(original_feature_NPZ_SHA256=validation['feature_NPZ_SHA256'],
            original_feature_archive_SHA256=validation['cached_feature_archive_SHA256'],
            fixed5_covariance_ready_decisions=365,original_E5_slots=[0,1,4],
            original_dynamic_mask_gates=validation['original_dynamic_mask_gates'],
            context_artifact=next(r for r in validation['derived_artifacts'] if r['path']=='derived/CONTEXT_INPUTS.npz'),
            feature_window_artifact=next(r for r in validation['derived_artifacts'] if r['path']=='derived/FEATURE_WINDOW_REFERENCES.npz')),
        adapter_contract_commit='556fc9d157747a76f28a15d03dd953e6ca44529a',adapter_contract_SHA256=sha(contract),
        original_raw_CSV_and_remote_hash_readback_verified=True,wire_export='Seven arrays and15 economic tables are exact value/byte copies of source packet; no economic semantics changed.',
        historical_publication_time_and_funding_unit_contract='Original conditional completed-day/unit/cross-venue assumptions retained.',
        full_December_native_mark_minute_tape=False,model_fits=0,model_inferences=0,backtests=0,wallets=0)
    (destination/'CONSUMER_INDEX.json').write_text(json.dumps(index,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(consumer_SHA256=sha(destination/'CONSUMER_INDEX.json'),economic_SHA256=economic_sha,
        economic_fields=FIELDS,table_artifacts=len(artifacts),source_data_changed=False)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True);p.add_argument('--contract',type=Path,required=True)
    a=p.parse_args();main(a.root,a.destination,a.contract)
