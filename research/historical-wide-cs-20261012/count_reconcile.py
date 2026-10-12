"""Exact original-object set reconciliation; no price/body or new source reads."""
import argparse,hashlib,json,subprocess
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];COMMIT='b00183d550fde638978ab476f319af8f8ce1fef2'
def run(state):
 assert not state.exists();state.mkdir(parents=True);proof={}
 def read(name):
  raw=subprocess.check_output(['git','show',COMMIT+':reports/fast_research/'+name],cwd=ROOT);proof[name]=dict(bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest());return json.loads(raw)
 inventory=read('MULTI_ASSET_HISTORICAL_INVENTORY_20261004_V2.json');pool=read('MULTI_ASSET_POINT_IN_TIME_POOL_20261004_V2.json');a=set(inventory['symbols']);b={r['symbol'] for r in pool['july_ranked_candidates']};u=pool['unknown_candidates'];c={r['symbol'] for r in u};j={r['symbol'] for r in u if r['phase']=='JULY_RANK'};q={r['symbol'] for r in u if r['phase']=='QUALIFICATION'}
 assert len(a)==len(inventory['symbols'])==880 and len(b)==len(pool['july_ranked_candidates'])==279 and len(c)==len(u)==603 and len(j)==601 and len(q)==2 and b&c==q=={'NOTUSDT','ZROUSDT'} and not b&j and b|c==a
 out=dict(status='PASS_EXACT_ORIGINAL_880_279_603_STAGE_OVERLAP',source_commit=COMMIT,sources=proof,historical_folders_unique=880,July_rankable_unique=279,July_UNKNOWN_unique=601,qualification_UNKNOWN_unique=2,total_UNKNOWN_unique=603,rank_UNKNOWN_intersection=sorted(b&c),union_unique=len(b|c),equation='279+603-2=880',UNKNOWN_does_not_mean_nontradable=True,UNKNOWN_phase_reasons=[dict(symbol=r['symbol'],phase=r['phase'],reason=r['reason']) for r in u if r['phase']=='QUALIFICATION' or '404' not in r['reason']],current_exchangeInfo_used=False,new_downloads=0,new_fits=0,new_wallets=0)
 (state/'RECONCILIATION.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print('ACTUAL_ORIGINAL_COUNT_RECONCILIATION_PASS',out['equation'],out['rank_UNKNOWN_intersection'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);a=p.parse_args();run(a.state)
