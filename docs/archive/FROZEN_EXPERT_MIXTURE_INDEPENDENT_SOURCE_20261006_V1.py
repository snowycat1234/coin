"""Scalar full-target identity and fixed weight reconstruction from source."""
import json,os
from pathlib import Path
from datetime import UTC,datetime
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha
review='reports/FROZEN_EXPERT_MIXTURE_REVIEW_20261006_V1.json';r=json.loads((ROOT/review).read_bytes())
di=json.loads((ROOT/r['oracle_diagnostic_reference']['path']).read_bytes())
sources={}
for entry in di['library']:
    v=entry['artifacts']['targets.parquet'];assert sha(v['path'])==v['sha256']
    f=pl.read_parquet(v['path']);sources[entry['expert'],entry['unit']]={(row['available_us'],row['symbol']):row for row in f.iter_rows(named=True)}
start=1640995200000000;day=86_400_000_000;max_error=0.;witnesses=[]
for ref in r['producers']:
    assert sha(ROOT/ref['path'])==ref['sha256'];producer=json.loads((ROOT/ref['path']).read_bytes())
    for case in producer['cases']:
        family=case['strategy'];unit=case['unit'];target=case['artifacts']['targets.parquet']
        assert sha(target['path'])==target['sha256'];f=pl.read_parquet(target['path']);assert f.height==730
        seg=next(v for v in di['results'] if v['unit']==unit)['oracle_variants']['TARGET_DISTANCE_SWITCH_COST_13_5BP']['segments']
        ordinal=0;switches=0;previous=None
        for row in f.sort('available_us').iter_rows(named=True):
            assert row['symbol']=='BTCUSDT' and row['available_us']==start+ordinal*day
            if family=='ORACLE60D':
                choice=seg[ordinal//60]['expert'];blend={choice:1.}
                if previous is not None and choice!=previous:switches+=1
                previous=choice
            elif family=='EQUAL_EXPERTS':blend={n:1/8 for n in di['protocol']['experts']}
            elif family=='STATIC_DIRECTION3':blend={'SMA200_SIGNED':.5,'HOLD':.25,'CASH':.25}
            else:raise AssertionError(family)
            assert sum(blend.values())==1 and all(v>=0 for v in blend.values())
            for column in ('target_weight','raw_signed_target'):
                expected=sum(weight*sources[name,unit][row['available_us'],'BTCUSDT'][column] for name,weight in blend.items())
                error=abs(row[column]-expected);max_error=max(max_error,error);assert error<1e-12
            assert abs(row['target_weight'])<=.3+1e-12;ordinal+=1
        meta=case['artifacts']['target_meta.json'];assert sha(meta['path'])==meta['sha256'];m=json.loads(Path(meta['path']).read_bytes())
        assert m['future_winner_used']==(family=='ORACLE60D') and m['shadow_cost_surcharge_not_applied_actual_fills_costed_once']
        assert not m['original_expert_parameters_changed'] and not m['static_weights_optimized']
        if family=='ORACLE60D':assert switches==next(v for v in di['results'] if v['unit']==unit)['oracle_variants']['TARGET_DISTANCE_SWITCH_COST_13_5BP']['switches']
        # Independent journal verification has already checked all NAV and fee
        # events. This independent check covers actual portfolio intent inputs.
        s=case['summary'];fees=case['artifacts']['trades.parquet'];assert sha(fees['path'])==fees['sha256']
        trades=pl.read_parquet(fees['path']);assert abs(trades['fee_USDT_mid'].sum()-s['fees_USDT'])<1e-7
        witnesses.append(dict(id=case['id'],full730d_target_reference='PASS',future_informed=family=='ORACLE60D',switches=switches,actual_fees_once_USDT=s['fees_USDT']))
assert len(witnesses)==6
out=dict(status='PASS_INDEPENDENT_FULL730D_MIXTURE_INTENTS_AND_FEE_JOURNAL_IDENTITY',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    input=dict(path=review,sha256=sha(ROOT/review)),witnesses=witnesses,maximum_target_error=max_error,new_accounts=0,models_fit=0,
    scope='Independent scalar frozen weight and per-unit winner-path reconstruction against published target artifacts; recorded fee sum checked. Original Decimal minute journal NAV/wallet audit retained. Does not certify causal oracle or investment.',created_utc=datetime.now(UTC).isoformat())
with (ROOT/'reports/FROZEN_EXPERT_MIXTURE_INDEPENDENT_20261006_V1.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(dict(status=out['status'],maximum_target_error=max_error)))
