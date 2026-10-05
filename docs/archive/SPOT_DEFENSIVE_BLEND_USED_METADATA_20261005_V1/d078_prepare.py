import hashlib,json,subprocess
from pathlib import Path
R=Path('/mnt/d/codex/coin')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='c7898815e8dacb7726627d6da6035afa4f32975e'
p=json.loads((R/'protocols/SPOT_PERPETUAL_PRODUCT_20261005_V1.json').read_bytes())
p.pop('perpetual_report')
p.update(experiment_id='D078_SPOT_FIXED_DEFENSIVE_BLEND',module='D078',recipe='HALF_HOLD10_EXIT10',annual_vol_target=.10,
    spot_control={'path':str(R/'reports/fast_research/SPOT_PERPETUAL_PRODUCT_20261005_V1.json'),
                  'sha256':sha(R/'reports/fast_research/SPOT_PERPETUAL_PRODUCT_20261005_V1.json')},
    hypothesis='Existing fixed defensive blend reduces drawdown on Spot; higher net is not required but report actual risk, costs and capital. No risk-matched alpha claim.',
    comparison='Same Spot input/cost/wallet/caps/full10k. Fixed .5 HOLD10 + .5 EXIT10/REENTRY20 after own component .10 past-cov scaling versus accepted HOLD8 .08. Different risk recipe, not single-factor signal or matched risk.',
    success_decision='Retain defensive challenger if non-dominated on net/vol/drawdown in both cost scenarios; no native/investment/APR. If dominated, pause tested recipe, preserve capability.',
    stop_rule='One fixed recipe, two wallets only. Source/cash/fee/target mismatch or observed caps breach fails. Keep residual, no free liquidation or grid.',
    budget={'actual_spot_wallets':2,'saved_spot_controls':2,'fits':0,'downloads':0,'API':0,'HPO':0,'wall_seconds':1800,'owned_bytes':100000000})
for n in ['scripts/investment/hold_donchian_blend_target.py','scripts/investment/donchian_daily_pool_target.py']:
    p['source_hashes'][n]=sha(R/n)
for n in p['source_hashes']:p['source_hashes'][n]=sha(R/n)
with (R/'protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json').open('x') as f:json.dump(p,f,indent=2);f.write('\n')
print(json.dumps({'status':'D078_PROTOCOL_FIXED_BEFORE_RESULTS','sha256':sha(R/'protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json')}))
