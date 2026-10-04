"""Recorded same-weight decision proves a spurious quantity-roundtrip reduction."""
from decimal import Decimal as D,localcontext
import hashlib,json,os
from pathlib import Path
import polars as pl
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
a=json.loads((ROOT/'reports/fast_research/TURTLE_NO_ADD_SINGLE_LAYER_303D_20261004_V1.json').read_bytes());case=a['cases'][0]
def payload(name):
    p=Path(case['artifacts'][name]['path']);assert p.is_relative_to(STATE) and sha(p)==case['artifacts'][name]['sha256'];return p
meta=json.loads(payload('target_meta.json').read_bytes());stamp=1730145600000000
receipt=[r for r in meta['decision_receipts'] if r['decision_us']==stamp];assert len(receipt)==1
targets=pl.read_parquet(payload('targets.parquet')).filter(pl.col('available_us')==stamp).to_dicts()
assert len(targets)==2 and all(r['target_weight']==r['raw_signed_target'] for r in targets)
assert receipt[0]['unscaled_signed_covariance_annual_vol']<.10
assert max(abs(r['raw_signed_target']) for r in targets)<.3 and sum(abs(r['raw_signed_target']) for r in targets)<.6
intent=[r for r in meta['journal'] if r.get('event')=='INTENT_SUBMITTED' and r.get('id')=='BTCUSDT:RISK_REDUCTION:175'];assert len(intent)==1
q=D(str(next(r['actual_quantity_at_decision'] for r in targets if r['symbol']=='BTCUSDT')))
target=D(intent[0]['target_quantity'])
with localcontext() as ctx:
    ctx.prec=40;bounded=target/D('.99');tiny=q-bounded
    assert D(0)<tiny<D('1e-16') and abs(target/q-D('.99'))<D('1e-16')
bridge=ROOT/'scripts/investment/turtle_perpetual_bridge.py'
assert sha(bridge)=='9e35d22fcfc827812941d02daeeeb8d0bead398ca4eed46193eb97234cb2041e'
r=dict(status='CONFIRMED_D060_SAME_WEIGHT_DECIMAL_ROUNDTRIP_SPURIOUS_RISK_REDUCTION',task_id=os.environ['COIN_TASK_ID'],
    source_sha256=sha(Path(__file__)),bridge_sha256=sha(bridge),failed_actual_sha256=sha(ROOT/'reports/fast_research/TURTLE_NO_ADD_SINGLE_LAYER_303D_20261004_V1.json'),
    decision_us=stamp,recorded_risk_receipt=receipt[0],recorded_target_rows=targets,recorded_intent=intent[0],
    q=str(q),reconstructed_bounded_quantity_before_buffer=str(bounded),quantity_roundtrip_shortfall=str(tiny),
    risk_weights_unchanged=True,all_risk_thresholds_below_declared_limits=True,
    conclusion='Unchanged float risk weights reconstructed to a slightly smaller Decimal inventory, triggering an unjustified 1% reduction buffer. Capacity rejection is correct; its risk intent is spurious.',
    complete_strategy_intents_independently_rebuilt=False,accounting_invalidated=False,
    prior_Turtle_investment_interpretation_requires_corrected_scheduling=True,
    market_accounts=0,financial_calls=0,full_source_QA=0,locked_consumed=False,full_period_net_delta='NOT_EVALUABLE')
out=ROOT/'reports/fast_research/TURTLE_NO_ADD_RISK_ROUNDTRIP_COUNTEREXAMPLE_20261004_V1.json'
with out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(dict(status=r['status'],shortfall=str(tiny),unchanged_weights=True)),flush=True)
