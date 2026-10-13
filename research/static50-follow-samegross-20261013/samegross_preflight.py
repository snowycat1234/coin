"""Zero-wallet gate for all three years; no favorable-year bypass."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from samegross_freeze import verify

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REVIEWED=verify()
BINDINGS_SHA256=REVIEWED['files_SHA256']['CASE_BINDINGS.json']
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def bindings():
    verify()
    p=HERE/'CASE_BINDINGS.json'
    if sha(p)!=BINDINGS_SHA256: raise ValueError('Frozen six-case plan changed')
    b=json.loads(p.read_text())
    if (b['case_count']!=6 or b['modes']!=['ORIGINAL']
            or b['new_historical_wallets_executed']!=0 or b['wallets_to_rerun']!=0):
        raise ValueError('Only fixed six new fine ORIGINAL wallets permitted')
    return b

def check(full_source=True):
    import numpy as np
    from same_gross_targets import ARMS,SYMBOLS,DAY,common_gross
    from original_follow_adapter import original
    b=bindings(); gate_path=HERE/'source_audit/SOURCE_GATE.json'
    gate=json.loads(gate_path.read_text())
    if (sha(gate_path)!=b['source_gate_SHA256']
            or gate['status']!='PASS_REAL_CORE5_2024_OHLC_SOURCE_GATE'
            or gate['warmup_complete_days']!=31 or gate['evaluation_decisions']!=366
            or gate['evaluation_trade_minutes_per_asset']!=527040
            or gate['completed_daily_close_cells_bit_matching_STATIC50']!=1985
            or gate['new_market_provider_downloads']!=0 or gate['new_historical_wallets']!=0):
        raise ValueError('SOURCE_STOP: full real 2024 + December warmup gate required')
    if {(c['year'],c['arm']) for c in b['cases']}!={(y,a) for y in (2023,2024,2025) for a in ARMS}:
        raise ValueError('Fixed complete three-year/two-arm plan changed')
    dataset=ROOT/gate['dataset_locator']
    if sha(dataset)!=b['source_dataset_SHA256'] or sha(dataset)!=gate['dataset_SHA256']:
        raise ValueError('SOURCE_STOP: actual source artifact changed')
    # Formula parity on this exact source, not economic replay.
    with np.load(dataset,allow_pickle=False) as a:
        d=np.arange(1704067200000000,1735689600000000,DAY,dtype=np.int64)
        f2024,_=original().targets(a['available_us'],a['high'],a['low'],a['close'],a['ready'],a['risk_t'],a['risk_p'],d)
    for c in b['cases']:
        if c['protective_enabled'] is not False: raise ValueError('Protective policy must be off')
        for locator,expected in [(c['source_index_local_locator'],c['source_index_SHA256']),
                                 (c['target_archive_local_locator'],c['target_archive_SHA256'])]:
            if sha(ROOT/locator)!=expected: raise ValueError('Input identity changed: '+locator)
        old=c['original_STATIC50']
        if sha(ROOT/old['target_archive_local_locator'])!=old['target_archive_SHA256']:
            raise ValueError('Original S archive changed')
        with np.load(ROOT/old['target_archive_local_locator'],allow_pickle=False) as a:
            old_s=a['STATIC50'].copy(); old_d=a['decision_us'].copy()
        with np.load(ROOT/c['target_archive_local_locator'],allow_pickle=False) as a:
            clocks=a['decision_us']; np.testing.assert_array_equal(clocks,np.arange(*c['calendar'],DAY,dtype=np.int64))
            if tuple(a['symbol_order'])!=SYMBOLS: raise ValueError('CORE5 order changed')
            np.testing.assert_array_equal(a['STATIC50'],old_s);np.testing.assert_array_equal(clocks,old_d)
            if c['year']==2024: np.testing.assert_array_equal(a['FOLLOW'],f2024['FOLLOW'])
            else:
                f=c['FOLLOW'];p=ROOT/f['local_locator']
                if sha(p)!=f['archive_SHA256']: raise ValueError('Saved F archive changed')
                with np.load(p,allow_pickle=False) as q:
                    np.testing.assert_array_equal(clocks,q['decision_us']);np.testing.assert_array_equal(a['FOLLOW'],q['FOLLOW'])
            r=common_gross(clocks,SYMBOLS,a['STATIC50'],clocks,SYMBOLS,a['FOLLOW'])
            for k,w in r.items(): np.testing.assert_array_equal(a[k],w)
            w=a[c['arm']]
            if (w.dtype.str!=c['target_dtype'] or list(w.shape)!=c['target_shape']
                    or hashlib.sha256(w.tobytes()).hexdigest()!=c['target_array_SHA256']):
                raise ValueError('New target matrix identity changed')
        for rec in c['reused_original_STATIC50_fine_comparator'].values():
            if sha(ROOT/rec['local_locator'])!=rec['SHA256']: raise ValueError('Saved original S comparator changed')
    if full_source:
        # Existing exact read-only source admission validates every original
        # month/event/daily source and the unchanged ten-cell 2024 mark overlay.
        folder=ROOT/'coin_quantity_resolution_20261013'
        sys.path.insert(0,str(folder))
        spec=importlib.util.spec_from_file_location('frozen_fine_readonly_preflight',folder/'preflight.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        m.check(full_source=True)
    return {'status':'PASS_SIX_FINE_CASES_SOURCE_AND_TARGET_IDENTITY_ZERO_HISTORY',
            'planned_new_fine_wallets':6,'historical_wallets_started':0,
            'old_wallets_rerun':0,'protective_enabled':False,
            'full_source_checked':full_source,'parent_GO_required':True,
            'independent_exact_byte_review_required':True}
