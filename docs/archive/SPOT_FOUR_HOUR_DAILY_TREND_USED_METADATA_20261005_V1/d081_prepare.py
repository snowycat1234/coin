import json,hashlib,subprocess,os
from pathlib import Path
from quant.paths import ROOT
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
p=read(ROOT/'protocols/SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1.json')
p.update(experiment_id='D081_SPOT_FOUR_HOUR_DAILY_TREND',module='D081',
 parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 recipe='HALF_HOLD10_EXIT10_4H_DAILY_TREND',
 question='Does a completed daily SMA200 entry filter improve net/cost and risk versus the fixed4h blend?',
 hypothesis='The4h SMA200 trend gate is relatively short; a fixed daily macro entry gate may avoid costly participation in weak macro trends. Cost concentration motivates the question, does not prove it.',
 comparison='Single factor: entry trend SMA200 uses daily instead4h candles. Same4h prior20 entry channel/exit10/R20, HOLD10 daily carried, 4h refresh,30daily covariance,303 dates/Spot input/cost/10k/caps. Saved unfiltered4h primary, originaldailyblend/H8 additional. No matched actual risk claim.',
 stop_rule='One fixed daily macro entry filter, two complete wallets. Source/clock/daily context/target/account/caps disagreement stops. Missing component mismatch stops. No period grid, duplicate cost deletion, new data/API/fit or risk increase.',
 success_decision='Adopt development filtered4h only if marked net improves at both costs AND daily volatility/minuteMDD do not worsen versus unfiltered4h; originaldailyblend/H8 still reported. Otherwise retain originaldaily research configuration. No investment certification.',
 trend_filter_interval_minutes=1440)
control=ROOT/'reports/fast_research/SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1.json'
p['spot_control']=dict(path=str(control),sha256=sha(control))
daily=ROOT/'reports/fast_research/SPOT_DEFENSIVE_BLEND_20261005_V1.json'
p['hold_reference']=p['economic_reference']
p['economic_reference']=dict(path=str(daily),sha256=sha(daily))
p['source_hashes']={n:sha(ROOT/n) for n in p['source_hashes']}
p['source_hashes']['tests/test_four_hour_daily_trend_filter.py']=sha(ROOT/'tests/test_four_hour_daily_trend_filter.py')
p['budget']['saved_controls']=6
path=ROOT/'protocols/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json'
with path.open('x') as f:json.dump(p,f,indent=2);f.write('\n')
print(json.dumps({'status':'BEFORE_MARKET_RESULTS_FROZEN','protocol_sha256':sha(path),'task_id':os.environ['COIN_TASK_ID']}))
