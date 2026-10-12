import json, hashlib
from pathlib import Path
root=Path('/workspace/coin-tail-risk');here=root/'research/portfolio-risk-budget-20261012'
old=json.loads((root/'research/quantity-grid-sensitivity-20261012/PROTOCOL.json').read_text())
P=dict(experiment='FIXED10_CAUSAL_PORTFOLIO_RISK_BUDGET_CAP_CONSTRAINED',scientific_attempts=1,annual_risk_budget=.10,
 hypothesis='The old mixed portfolio had a lower joint forecast risk. Apply the same fixed10percent budget separately to CS, HOLD and the fixed half mixture, without changing their relative directions. Test paid economics under original safety caps; increasing mixture exposure alone is not predictive alpha.',
 allocation='Use exact original CS_MATCHED/VOL_MATCHED and STATIC50=.5CS+.5HOLD. For each arm and date use original30 completed SIMPLE daily returns, np.cov(ddof1)*365; sigma=sqrt(w@C@w). Desiredscale=.10/sigma; uniformcapscale=min(.3/maxabs(w),.6/sumabs(w)); factor=min(desiredscale,uniformcapscale). No per-leg clipping/redistribution or future realized-vol normalization. Intrinsic zero intent remains cash, nonzero degenerate risk stops. Report each unmet target/cap and cross-arm forecast mismatch. Fixed nominal budget does not guarantee common achieved forecast sigma when caps bind; forecast matching does not imply equal realized risk.',
 clock='Daily close_available_us <= decision_us, original completed-close chronology; 31 completed prices give30 returns. First execution remains original later minute. No funding/mark/arrival authority upgraded. No full-period outcomes read in allocation; historical risk is a rolling deterministic statistic, not fitted model parameters.',
 targets=old['targets'],quantity_profile=old['quantity_profile'],quantity_baseline_commit='098fc5ecb7db63eb568706d087a2b18d2b038339',
 risk_source=dict(path='research/monetary-policy-information-20261012/input/INPUTS.npz',SHA256='e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4',allowed_fields=['close_available_us','close'],forbidden='outcome/label/return/state/teacher'),
 windows=old['windows'],account='Exact existing QuantityGridAccount from inception: profile94b2238, closing notional exemption, fees5.5/spread4/slip4 bps eachside, RAW_AS_FRACTION funding1, original minute capacity/mask/risk/MMR/terminal. Shared10k, isolated1x/no topup, asset.3/gross.6. No financial methods rewritten.',
 roles='Two alreadyseen development windows, independently fresh10k per arm. No stitching or pristineOOS/paper-exact claim. Six prior quantity baseline wallets REUSED; none risk-consistent unless entire generated target arrays are exactly unchanged. Skip any such exact unchanged arm, otherwise at most6 new wallets; never rerun old paths.',
 dedup='Old CS/HOLD match to min(.10,original sigmas); old fixed mixture no re-upscale, hence lower joint sigma. Unified Closing and coarse versions keep those targets. HRP commonrisk is January2022 HRP/IVOL/IVAR/default; EG BTC experts. No equivalent full456/365 three-arm portfolio risk target identified.',
 gates=old['gates'],bootstrap=old['bootstrap'],
 comparison='Report raw net, paid status, fees/execution/funding, gross/net, realized vol/DD/worst30, forecast targetmet/capshortfalls. Same fixed nominal budget is constrained comparison, never claim equal achieved risk on cap-shortfall dates or equal realized risk. BothSTATIC50 path gates required; no winner switching or outcome retune.',
 budget=dict(threads=1,AS=4000000000,RSS_stop=2000000000,host_stop=8000000000,GPU=0,swap=0,disk_reserve=16106127360,wallet_seconds=600,new_wallets=6,STATE_case_bytes=180000000,STATE_module_bytes=650000000,published_total_bytes=500000000,fits=0,normalizer_fits=0,provider_downloads=0,old_wallet_reruns=0),
 publication='Code/protocol/tests normal push+remote first. Then prepare causal targets and push. Serial one-account execution/compact snapshot/full original journals/minute bits, public packet and cold proof before next case/window. Original state remains: existing column transpose-copy codec stores every36 native values;37th clock reconstructed exactly. Original standard NPZ byteSHAs checked on recovery, Parquet containers not created. This is storage only and never changes financial state. Keep old originals; remove only verified own transport/cold duplicate caches. No price source re-upload.',
 preserve=old['preserve'])
for key,W in P['windows'].items():
 W['quantity_baseline_prefix']='research/quantity-grid-sensitivity-20261012/summary/'+key
 W['existing_risk_path']='research/cs-hold-continuous-assembly-20261012/input/'+key+'_RISK.json'
 W['existing_risk_SHA256']=hashlib.sha256((root/W['existing_risk_path']).read_bytes()).hexdigest()
(here/'PROTOCOL.json').write_text(json.dumps(P,sort_keys=True,indent=2)+'\n')
(here/'evidence').mkdir(exist_ok=True)
files=[]
for line in (root/'research/quantity-grid-sensitivity-20261012/SOURCE_SHA256.txt').read_text().splitlines():
 _,p=line.split(maxsplit=1);files.append(p)
files += ['research/quantity-grid-sensitivity-20261012/driver.py','research/quantity-grid-sensitivity-20261012/grid_account.py','research/cs-continuous-economics-20261012/state_io.py','research/cs-continuous-economics-20261012/persistence.py','research/cs-hold-continuous-assembly-20261012/input/P1_RISK.json','research/cs-hold-continuous-assembly-20261012/input/P2_RISK.json']
files += [str(p.relative_to(root)) for p in here.glob('*.py')]+['research/portfolio-risk-budget-20261012/PROTOCOL.json','research/portfolio-risk-budget-20261012/reproduce.sh']
files=list(dict.fromkeys(files))
(here/'SOURCE_SHA256.txt').write_text(''.join(hashlib.sha256((root/p).read_bytes()).hexdigest()+'  '+p+'\n' for p in files))
print('FROZEN_SOURCES',len(files),'wallets0,targets0,scientificattempt1')
