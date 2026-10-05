"""One read-only economic interpretation; no market replay or source copying."""
import json,hashlib,os
from pathlib import Path
import polars as pl
from quant.paths import ROOT,STATE
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
previous=json.loads((ROOT/'reports/SPOT_FOUR_HOUR_DAILY_TREND_ACCEPTED_20261005_V1.json').read_bytes())
batched=json.loads((ROOT/'reports/SPOT_FOUR_HOUR_DAILY_TREND_ACCEPTED_BATCH_20261005_V1.json').read_bytes())
for k in ('status','experiment_id','parent_commit','references','source_hashes','development_recipe_adopted','candidate','investment','long_term_APR','private_SHA_only','private_body_read','validator_source_sha256'):
    assert previous[k]==batched[k],k
v=json.loads((ROOT/'reports/fast_research/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json').read_bytes())
old=json.loads(Path(v['spot_control']['path']).read_bytes());assert sha(v['spot_control']['path'])==v['spot_control']['sha256']
source=STATE/'d081-spot-saved-diagnostics-20261005-v1/RESULT.json';d=json.loads(source.read_bytes());rows=[]
for case,control in zip(d['cases']['BLEND'],d['cases']['HOLD8'],strict=True):
    assets=[]
    for n,o in zip(case['assets'],control['assets'],strict=True):
        assert n['symbol']==o['symbol']
        assets.append(dict(symbol=n['symbol'],net_delta_USDT=n['net_USDT']-o['net_USDT'],
            gross_cost_addback_delta_USDT=n['gross_cost_addback_USDT']-o['gross_cost_addback_USDT'],
            cost_delta_USDT=(n['fees_USDT']+n['execution_USDT'])-(o['fees_USDT']+o['execution_USDT'])))
    rows.append(dict(id=case['id'],assets=assets))
prefix=True;hold_equal=True
for a,b in zip(v['target_meta']['risk'],old['target_meta']['risk'],strict=True):
    prefix=prefix and a['decision_us']==b['decision_us'] and a['symbol_order']==b['symbol_order'] and a['covariance_symbol_order']==b['covariance_symbol_order']
    hold_equal=hold_equal and a['component_HOLD_raw']==b['component_HOLD_raw'] and a['component_HOLD_target']==b['component_HOLD_target']
assert prefix and hold_equal
output=STATE/'d081-fast-workflow-saved-diagnosis-20261005-v1/RESULT.json';output.parent.mkdir()
with output.open('x') as f:json.dump(dict(status='PASS_SAVED_ASSET_ECONOMIC_BRIDGE_AND_UNCHANGED_HOLD',task_id=os.environ['COIN_TASK_ID'],
 input_sha256=sha(ROOT/'reports/fast_research/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json'),diagnostic_sha256=sha(source),assets=rows,
 complete_shared_clock_identity_equal=prefix,HOLD_targets_and_raw_equal=hold_equal,new_market_replays=0,
 optimized_and_original_acceptance_core_equal=True,
 scope='Actual shared wallet asset cashflow/inventory bridge; not attribution of entire trade PnL to signal reason or isolated component return.'),f,indent=2)
print(json.dumps(rows))
