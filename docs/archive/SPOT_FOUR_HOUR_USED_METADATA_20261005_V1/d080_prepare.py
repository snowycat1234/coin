import json,hashlib,subprocess,os
from pathlib import Path
from quant.paths import ROOT
from scripts.research_v8.registry import FIELDS,append_event
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
p=read(ROOT/'protocols/SPOT_DISCRETIONARY_BAND50_20261005_V1.json')
p.update(experiment_id='D080_SPOT_FOUR_HOUR_DAILY_RISK',module='D080',
 parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 recipe='HALF_HOLD10_EXIT10_4H',discretionary_rebalance_min_notional=0,
 question='Does one fixed four-hour Donchian horizon and combined target cadence improve same Spot daily defensive recipe economics using unchanged daily risk?',
 hypothesis='Faster completed-bar trend participation may change timing losses; test one fixed horizon with actual incremental cost/risk, not threshold grid.',
 comparison='Same303 days/Spot prices/fees/10k/caps. HOLD10 daily target forward-carried; Donchian20/SMA200/exit10/reentry20 interpreted in4h bars. Entire combined wallet refreshed4h; both signal horizon and execution cadence change. Not signal-only or matched-risk alpha.',
 stop_rule='One4h recipe, two wallets. Source/cadence/warmup/causal/account/caps mismatch stops. Component eligibility disagreement fails closed. No horizon grid/no new data/API/fits/no free liquidation.',
 success_decision='Adopt development challenger only if marked net exceeds daily blend at both costs and daily realized volatility and minute drawdown do not worsen; otherwise retain daily blend. No native or investment certification.',
 signal_interval_minutes=240,risk_interval_minutes=1440,hold_interval_minutes=1440)
p.pop('band_policy');p['source_hashes']={n:sha(ROOT/n) for n in p['source_hashes']}
p['source_hashes']['tests/test_four_hour_signal_daily_risk.py']=sha(ROOT/'tests/test_four_hour_signal_daily_risk.py')
path=ROOT/'protocols/SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1.json'
with path.open('x') as f:json.dump(p,f,indent=2);f.write('\n')
print(json.dumps({'status':'BEFORE_MARKET_RESULTS_FROZEN','protocol_sha256':sha(path),'task_id':os.environ['COIN_TASK_ID']}))
