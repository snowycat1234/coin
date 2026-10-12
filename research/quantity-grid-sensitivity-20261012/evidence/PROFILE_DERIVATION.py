import hashlib,json
from decimal import Decimal as D,localcontext
from pathlib import Path
import numpy as np
root=Path('/workspace/coin-tail-risk');here=root/'research/quantity-grid-sensitivity-20261012'
cube=root/'research/monetary-policy-information-20261012/input/INPUTS.npz'
assert hashlib.sha256(cube.read_bytes()).hexdigest()=='e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4'
cut=1617235200000000
with np.load(cube,allow_pickle=False) as z:
 t=z['close_available_us'];p=z['close'];k=np.flatnonzero(t<cut)[-1];at=int(t[k]);price=p[k]
symbols=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
assert at==1617148800000000 and np.isfinite(price).all() and (price>0).all()
with localcontext() as ctx:
 ctx.prec=40;anchor=D('.001')*D(str(price[0]));rows={}
 for s,v in zip(symbols,price,strict=True):
  q=anchor/D(str(v));step=D(1)
  while step>q:step/=10
  while step*10<=q:step*=10
  rows[s]=dict(quantity_step=str(step),min_quantity_assumption=str(step),min_notional='10',reference_price=str(v),reference_lot_notional=str(step*D(str(v))),native_filters_certified=False)
profile=dict(name='BTC_DOCUMENT_EXAMPLE_ANCHORED_EQUAL_QUOTE_DECADE_SENSITIVITY',source_rule='Current official Bybit help BTC minimum .001 example only; step=minQty is an explicit research assumption. Unknown other asset specs derived by largest decimal power not exceeding BTC-example lot notional at strict preP1 price. Not a historical/current exchange instrument table.',official_reference='https://www.bybit.com/en/help-center/article/Futures-Trading-Rules',official_document_update='2026-07-03',official_read_UTC_date='2026-10-12',price_source_SHA256=hashlib.sha256(cube.read_bytes()).hexdigest(),price_available_us=at,first_experiment_start_us=cut,anchor_BTC_quantity='.001',anchor_quote_notional=str(anchor),derivation='q_s=10**floor(log10((.001*P_BTC)/P_s)), implemented by exact Decimal comparisons. MinQty=step; one frozen table for both P1 and P2, zero outcome/return inputs.',rows=rows,native_certified=False,historical_certified=False)
(here/'QUANTITY_PROFILE.json').write_text(json.dumps(profile,sort_keys=True,indent=2)+'\n')
old=json.loads((root/'research/unified-closing-exempt-economics-20261012/PROTOCOL.json').read_text())
old.update(experiment='ONE_FACTOR_PER_SYMBOL_QUANTITY_GRID_SENSITIVITY',hypothesis='An explicit coarse integer-lot minimum profile changes executable intents, actual exposures, terminal feasibility and paid economics relative to the six exact previously observed fine-step accounts; no expected sign or outcome selection.',account='Existing Closing semantics/cost/funding/caps/MMR/10k/one-way isolated1x/no-topup/native318a/same targets/source/paidterminal unchanged. Only instrument quantity_step/minQty=step assumption differs, through existing InstrumentProfile and integer-lot floor. QuantityGridAccount adds frozen identity validation only, inherits all financial methods.',quantity_profile=dict(path=str((here/'QUANTITY_PROFILE.json').relative_to(root)),SHA256=hashlib.sha256((here/'QUANTITY_PROFILE.json').read_bytes()).hexdigest()),comparison='New same-calendar coarse case versus corresponding exact fine-step Closing case fca3aafd REUSED; full-calendar differences descriptive with changed realized exposure/turnover. Partial paths never compared as full income. Withincoarse STATIC50 control comparisons retained, no joint-risk alpha or oracle.',roles='At most6 new coarse-profile fresh10k wallets and6fine-profile cases REUSED from fca3aafd; two separate seen windows, no returns stitching or profile selection.',dedup='Existing next_mechanism_history_review no matching coarse-profile sixwallet found. OldD048/Turtle exactweight-to-quantity fixtures or synthetic profile tests are different. No official saved CORE5 perpetual specs; oldBybit public API403 and currentETH403 not retried; P03 spot snapshot body not recovered and wrong product.')
for key,w in old['windows'].items():w['fine_step_baseline_prefix']=f'research/unified-closing-exempt-economics-20261012/summary/{key}'
(here/'PROTOCOL.json').write_text(json.dumps(old,sort_keys=True,indent=2)+'\n')
print(json.dumps(profile,indent=2))
