"""First logged fullreduce request, fixed date, same original source/targets."""
import argparse,gc,gzip,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from study import HERE,ROOT,native,b,sha,save,source_window,SYMBOLS,parent,anchor,codec,verify
from state_io import split_snapshot
from rules import quantity_gate
def observed_prefix(sim,original,end):
    case=sim.result()
    for k in ('trades','funding','rejections','breaches'):assert case[k]==[r for r in original[k] if r.get('event_us',r.get('signal_us',0))<=end],k
def run(state,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source;verify();state.mkdir();began=time.monotonic();z,index=parent();snap,original=anchor(state,z,index);win=source_window('P1',Path('/workspace/cs-continuous-state/SOURCE_RECOVERED'))
    # Reuse the alreadyobserved/parity-validated DEFAULTMay2state, no repeatedMay1.
    r=index['lossless_chunks'][30];p=state/'ORIGINAL_DAY30.npz';codec.decode_chunk(z.read(r['encoded']),p,r['original_SHA256'])
    with np.load(p,allow_pickle=False) as a:prefix=snap['minute_chunks']+[a['minute_chunk']]
    snap=json.loads(gzip.decompress((HERE/'input/MAY2_REPRODUCED_STATE.json.gz').read_bytes()));assert snap['state']['rows_written']==44640 and snap['state']['cursor']==native.utc('2021-05-02') and snap['account']['closing_min_notional_exempt'] is False;snap['minute_chunks']=prefix;sim=native.NativeDailySimulator.from_snapshot(snap,win)
    # Necessary recovery days are exactoriginal chronology, not newparameters.
    for day in (31,):
        sim.advance_day();r=index['lossless_chunks'][day];p=state/f'ORIGINAL_DAY{day}.npz';codec.decode_chunk(z.read(r['encoded']),p,r['original_SHA256'])
        with np.load(p,allow_pickle=False) as a:np.testing.assert_array_equal(sim.minute_chunks[-1].view(np.uint64),a['minute_chunk'].view(np.uint64))
        observed_prefix(sim,original,sim.cursor)
    assert sim.cursor==native.utc('2021-05-03') and sim.account.status=='ACTIVE';snap=split_snapshot(sim);snap['minute_chunks']=sim.minute_chunks;save(state/'ANCHOR_RECOVERY.json',dict(status='PASS_EXACT_ORIGINAL_DAY30_31_FULL37BITS_JOURNAL_PREFIX',source_parent='5191aeddd5d9fa1a68a29f1812a95692e3095cbd',cursor=sim.cursor,state_hash=sim.state_hash(),reference_recovery_day_advances=1,new_year_wallets=0));del sim;gc.collect();reports={}
    ref=index['lossless_chunks'][32];p=state/'ORIGINAL_DAY32.npz';codec.decode_chunk(z.read(ref['encoded']),p,ref['original_SHA256'])
    with np.load(p,allow_pickle=False) as a:expected=a['minute_chunk']
    for arm in ('DEFAULT','EXEMPT_PROXY_V1'):
        sim=native.NativeDailySimulator.from_snapshot(snap,win);before=sim.account.snapshot();oldnav=sim.account.nav();n=len(sim.account.trades);activation=dict(at_us=sim.cursor,contract_id='ORIGINAL_FALSE' if arm=='DEFAULT' else 'ANCHORED_MAY3_CLOSE_MIN_NOTIONAL_EXEMPT_PROXY_V1',validated_original_state_hash=sim.state_hash(),old_contract=sim.account.contract_metadata())
        if arm!='DEFAULT':sim.account.closing_min_notional_exempt=True
        activation['new_contract']=sim.account.contract_metadata();sim.advance_day();assert sim.cursor==native.utc('2021-05-04') and sim.stop is None
        if arm=='DEFAULT':np.testing.assert_array_equal(sim.minute_chunks[-1].view(np.uint64),expected.view(np.uint64));observed_prefix(sim,original,sim.cursor)
        p=state/arm;p.mkdir();case=sim.result();saved=native.save_case(case,p/'account');summary=saved['summary'];_,q=native.episodes(case['trades'],SYMBOLS)
        for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav());save(p/'ACCOUNT.json',{**{k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')},'summary':summary,'targets':case['targets'].to_dicts()});save(p/'ACTIVATION.json',activation);np.savez_compressed(p/'DAY32.npz',minute_chunk=sim.minute_chunks[-1]);save(p/'MINUTE_NUMERIC.json',codec.minute_fingerprint(case['minute']));raw=json.dumps(split_snapshot(sim),sort_keys=True,separators=(',',':'),allow_nan=False).encode();(p/'STATE.json.gz').write_bytes(gzip.compress(raw,mtime=0));new=sim.account.trades[n:];eth=[r for r in new if r['symbol']=='ETHUSDT' and r['leg']=='CLOSE'];report=dict(common_slice=['2021-05-03','2021-05-04'],contract_sensitivity_only_not_native_certificate=True,globalcalendar_incomplete_not_income=True,anchor_ETH_quantity=before['positions']['ETHUSDT']['quantity'],ETH_paid_close_legs=eth,dayend_ETH_quantity=str(sim.account.positions['ETHUSDT'].quantity),day_marked_NAV_change=str(sim.account.nav()-oldnav),state_hash=sim.state_hash(),summary=summary,independent_decimal_NAV_bridge=finance,native_quantity_gate=quantity_gate('.00176847',None));save(p/'RESULT.json',report);reports[arm]=report;print('ACTUAL_FIRST_REDUCE_DAY',arm,'ETHpaidcloselegs',len(eth),'NAV',summary['NAV'],flush=True);del sim,case,saved;gc.collect();assert time.monotonic()-began<120
    save(state/'RESULT.json',dict(status='COMPLETE_FIRST_ACTUAL_REDUCE_REQUEST_DAY_POLICY_PAIR',source_commit=source,arms=reports,new_year_wallets=0,new_fits=0,market_provider_downloads=0,single_day_account_advances=3,reference_recovery_days=1,seconds=time.monotonic()-began));print('FIRST_REQUEST_PAIR_COMPLETE',time.monotonic()-began,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.source_commit)
