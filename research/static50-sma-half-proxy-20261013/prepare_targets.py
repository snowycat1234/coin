"""Prepare frozen historical saved-target combination; never runs economics."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from core import (YEARS, SYMBOLS, SOURCE_HASHES, INDEX_SHA256, INPUT_HASHES,
                  calendar, load_originals, mix_arrays, read_npz, save_npz, sha256, write_json)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_SOURCES = ROOT.parent.parent / 'coin_strong_candidates_20261013'
DEFAULT_INPUTS = ROOT.parent / 'inputs'
PROTOCOL_SHA256 = 'ea74b7f8b876993d84951e5a8e2f9e03e8384b6546b0f28f7e984a0fe084032f'


def check_execution_inputs(path, year):
    if sha256(path) != INPUT_HASHES[year]:
        raise ValueError('Original owned execution inputs SHA mismatch')
    d = read_npz(path)
    if not np.array_equal(d['decision_us'], calendar(year)) or tuple(d['symbol_order']) != SYMBOLS:
        raise ValueError('Execution calendar/order differs')
    for key in ('p0','p1','funding_per_unit','owned_interval_valid'):
        if d[key].shape != (365,5): raise ValueError('Owned execution shape differs: '+key)
    if (not d['owned_interval_valid'].all() or not np.isfinite(d['p0']).all()
            or not np.isfinite(d['p1']).all() or not np.isfinite(d['funding_per_unit']).all()
            or np.min(d['p0']) <= 0 or np.min(d['p1']) <= 0
            or not np.array_equal(d['p1'][:-1], d['p0'][1:])):
        raise ValueError('Complete owned execution and terminal inputs required')
    return d


def run(source_root=DEFAULT_SOURCES, input_root=DEFAULT_INPUTS):
    if sha256(HERE / 'PROTOCOL.json') != PROTOCOL_SHA256:
        raise ValueError('Preregistered protocol changed')
    output = HERE / 'targets'
    if any(output.iterdir()):
        raise ValueError('Prepared targets already exist; never overwrite')
    prepared = {}
    for year in YEARS:
        source = load_originals(source_root, year)
        execution = check_execution_inputs(Path(input_root)/f'Y{year}.npz', year)
        static = source['STATIC50']['STATIC50']
        sma = source['SMA200']['SMA200_10PCT']
        c = source['STATIC50']['annual_covariance']
        mix, proof = mix_arrays(static, sma, c)
        if not np.array_equal(mix, .5*static + .5*sma):
            raise ValueError('Target matrix is not literal half-sum')
        if not np.array_equal(source['STATIC50']['decision_us'], source['SMA200']['decision_us']) or not np.array_equal(execution['decision_us'],source['STATIC50']['decision_us']):
            raise ValueError('Source/execution decisions not aligned')
        prepared[year] = dict(packet=dict(decision_us=calendar(year),symbol_order=np.asarray(SYMBOLS),
                                          annual_covariance=c,STATIC50=static,SMA200=sma,COMBINED=mix),proof=proof)
    files={}
    for year in YEARS:
        path=output/f'Y{year}.npz'
        save_npz(path,**prepared[year]['packet'])
        replay=read_npz(path)
        for key, value in prepared[year]['packet'].items():
            if not np.array_equal(replay[key], value): raise ValueError('Saved target replay differs')
        proofpath=output/f'Y{year}_PROOF.json'
        write_json(proofpath,dict(year=year,days=365,source_files={f'{kind}_Y{year}.npz':SOURCE_HASHES[f'{kind}_Y{year}.npz'] for kind in ('STATIC50','SMA200')},
                                  mix_exact=True, no_post_mix_rescale=True, rows=prepared[year]['proof']))
        files[str(path.relative_to(HERE))] = sha256(path)
        files[str(proofpath.relative_to(HERE))] = sha256(proofpath)
    manifest=dict(status='PREPARED_UNSCORED',protocol_SHA256=PROTOCOL_SHA256,
                  core_SHA256=sha256(HERE/'core.py'),prepare_SHA256=sha256(HERE/'prepare_targets.py'),
                  sources_index_SHA256=INDEX_SHA256,original_source_hashes=SOURCE_HASHES,
                  execution_input_hashes={str(k):v for k,v in INPUT_HASHES.items()},
                  target_files=files,economic_runs_started=False)
    write_json(HERE/'TARGETS_MANIFEST.json',manifest)
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources',type=Path,default=DEFAULT_SOURCES)
    parser.add_argument('--execution-inputs',type=Path,default=DEFAULT_INPUTS)
    args=parser.parse_args()
    print(json.dumps(run(args.sources,args.execution_inputs),sort_keys=True))
