"""Use the already-frozen 60-minute exit API on one genuine annual account."""
import argparse,gzip,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from driver import HERE,ROOT,Closing,native,SYMBOLS,sha,save,verify,load,b
TERMINAL=ROOT/'research/terminal-readiness-2025-20261012'

def original_api():
 # Explicit module binding avoids the unrelated generic common.py imports.
 sys.modules['common']=load('common',TERMINAL/'common.py')
 return load('unchanged_high_reference_terminal_api',TERMINAL/'extend.py')

def run(state,annual,science):
 assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==science;verify()
 for line in (TERMINAL/'FINANCIAL_SHA256.txt').read_text().splitlines():h,p=line.split(maxsplit=1);assert sha(ROOT/p)==h,p
 result=json.loads((annual/'RESULT.json').read_text());binding=json.loads((annual/'BINDING.json').read_text());ptr=json.loads((annual/'recovery/POINTER.json').read_text());assert ptr['binding']==binding and result['year']==binding['year']=='Y2025' and result['summary']['completed_minutes']==525600
 p=annual/'recovery'/ptr['snapshot_path'];assert sha(p)==ptr['snapshot_SHA256'];snap=json.loads(gzip.decompress(p.read_bytes()));api=original_api();assert snap['state']['cursor']==snap['account']['clock_us']==api.START and snap['state']['stop'] is None
 account=Closing.from_snapshot(snap['account']);assert account.snapshot()==snap['account']
 for k,v in account.summary().items():assert result['summary'][k]==v,k
 assert not result['summary']['terminal_cash_realized'],'Already-flat accounts need no tail fork'
 state.mkdir(parents=True);began=time.monotonic();src=json.loads((TERMINAL/'source/SOURCE_INDEX.json').read_text());assert sha(TERMINAL/'source/INPUTS.npz')==src['INPUTS_SHA256'] and sha(TERMINAL/'source/EVENTS.json')==src['EVENTS_SHA256']
 with np.load(TERMINAL/'source/INPUTS.npz',allow_pickle=False) as z:
  times=z['times'];assert tuple(z['symbol_order'])==SYMBOLS;np.testing.assert_array_equal(times,np.arange(api.START,api.END,api.MINUTE));market={s:{k:z[s+'_'+k] for k in ('open','close','quote_volume','mark')} for s in SYMBOLS}
 def rows():
  for i,at in enumerate(times):yield int(at),{s:{k:float(v[i]) for k,v in fields.items()} for s,fields in market.items()}
 events=json.loads((TERMINAL/'source/EVENTS.json').read_text());r=api.extend(account,rows(),events,snap['state']['previous_quote'],'TERMINAL60_2026JAN1_HIGH_REFERENCE2025')
 raw=json.dumps(account.snapshot(),sort_keys=True,separators=(',',':'),allow_nan=False).encode();p=state/'FINAL_ACCOUNT.json.gz';p.write_bytes(gzip.compress(raw,mtime=0))
 _,q=native.episodes(account.trades,SYMBOLS)
 for s in SYMBOLS:assert q[s]==account.positions[s].quantity
 prices={s:float(account.marks[s][-1]['price']) for s in SYMBOLS};finance=native.nav_bridge(account.trades,account.funding,q,prices,account.nav())
 base=json.loads((TERMINAL/'evidence/ACTUAL_RESULT.json').read_text())['cases']['STATIC50'];assert base['paid_flat']
 r.update(year='Y2025',science_source_commit=science,parent_science_source_commit=binding['science_source_commit'],parent_genuine_state_hash=ptr['state_hash'],parent_snapshot_SHA256=ptr['snapshot_SHA256'],original_annual_RESULT_SHA256=sha(annual/'RESULT.json'),original_annual_ACCOUNT_SHA256=sha(annual/'ACCOUNT.json'),final_snapshot_SHA256=sha(p),final_account_state_SHA256=hashlib.sha256(raw).hexdigest(),source_INPUTS_SHA256=sha(TERMINAL/'source/INPUTS.npz'),source_EVENTS_SHA256=sha(TERMINAL/'source/EVENTS.json'),inventory_NAV_audit='PASS',independent_decimal_NAV_bridge=finance,reused_STATIC50_extended_paid_net=base['extended_paid_total_net_USDT'],extended_paid_net_increment_over_STATIC50=r['extended_paid_total_net_USDT']-base['extended_paid_total_net_USDT'] if r['paid_flat'] else None,original_annual_daily_path_and_CI_unchanged=True,new_short_tail_forks=1,annual_wallet_replays=0,new_fits=0,provider_downloads=0,seconds=time.monotonic()-began)
 assert sha(annual/'RESULT.json')==r['original_annual_RESULT_SHA256'] and sha(annual/'ACCOUNT.json')==r['original_annual_ACCOUNT_SHA256'];save(state/'TAIL.json',r);print('HIGH_REFERENCE_ACTUAL_EXIT',r['status'],r['minutes'],r['extended_paid_total_net_USDT'],r['extended_paid_net_increment_over_STATIC50'],flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--annual',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.annual,a.source_commit)
