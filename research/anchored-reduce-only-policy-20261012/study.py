"""Two single-day suffixes from a genuine saved complete scheduler state."""
import argparse,gc,gzip,hashlib,importlib.util,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'research/cs-hold-continuous-assembly-20261012'))
from driver import native,b,save,sha,source_window,SYMBOLS
spec=importlib.util.spec_from_file_location('anchored_codec',ROOT/'research/cs-dual-speed-ranking-20261012/archive.py');codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
from rules import quantity_gate
ARMS=('DEFAULT','EXEMPT_PROXY_V1');BOUNDARY=native.utc('2021-05-02');PARENT='5191aeddd5d9fa1a68a29f1812a95692e3095cbd';PREFIX='research/cs-hold-continuous-assembly-20261012/result/P1/'
def verify():
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def parent():
    index=json.loads(b.git('show',PARENT+':'+PREFIX+'INDEX.json'));raw=b''
    for r in index['parts']:
        x=b.git('show',PARENT+':'+PREFIX+r['file']);assert len(x)==r['bytes'] and hashlib.sha256(x).hexdigest()==r['SHA256'];raw+=x
    assert hashlib.sha256(raw).hexdigest()==index['packet_SHA256'];z=zipfile.ZipFile(io.BytesIO(raw));assert z.testzip() is None
    for r in index['members']:
        x=z.read(r['name']);assert len(x)==r['bytes'] and hashlib.sha256(x).hexdigest()==r['SHA256']
    return z,index
def anchor(state,z,index):
    raw=(HERE/'input/ANCHOR.json.gz').read_bytes();s=json.loads(gzip.decompress(raw));assert s['state']['rows_written']==43200 and s['state']['cursor']==native.utc('2021-05-01') and s['account']['closing_min_notional_exempt'] is False
    final=json.loads(z.read('ACCOUNT.json'));assert s['account']['trades']==[r for r in final['trades'] if r['event_us']<=s['account']['clock_us']];chunks=[]
    for r in index['lossless_chunks'][:30]:
        p=state/Path(r['original']).name;codec.decode_chunk(z.read(r['encoded']),p,r['original_SHA256'])
        with np.load(p,allow_pickle=False) as a:chunks.append(a['minute_chunk'])
    s['minute_chunks']=chunks;assert sum(map(len,chunks))==43200;return s,final
def run(state,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source;verify();state.mkdir();began=time.monotonic();z,index=parent();snap,original=anchor(state,z,index);win=source_window('P1',Path('/workspace/cs-continuous-state/SOURCE_RECOVERED'));reports={}
    ref=index['lossless_chunks'][30];expected_path=state/'OBSERVED_DAY31.npz';codec.decode_chunk(z.read(ref['encoded']),expected_path,ref['original_SHA256'])
    with np.load(expected_path,allow_pickle=False) as a:expected=a['minute_chunk']
    for arm in ARMS:
        sim=native.NativeDailySimulator.from_snapshot(snap,win);before=sim.account.snapshot();oldhash=sim.state_hash();oldnav=sim.account.nav();activation=dict(contract_id='ORIGINAL_FALSE' if arm=='DEFAULT' else 'ANCHORED_CLOSE_NOTIONAL_EXEMPT_PROXY_V1',at_us=sim.cursor,validated_original_state_hash=oldhash,original_account_SHA256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),old_contract=sim.account.contract_metadata())
        if arm=='EXEMPT_PROXY_V1':sim.account.closing_min_notional_exempt=True
        activation['new_contract']=sim.account.contract_metadata();n=len(sim.account.trades);sim.advance_day();assert sim.cursor==BOUNDARY and sim.stop is None and sim.rows_written==44640
        if arm=='DEFAULT':
            np.testing.assert_array_equal(sim.minute_chunks[-1].view(np.uint64),expected.view(np.uint64))
            for k in ('trades','funding','rejections','breaches'):
                current=sim.result()[k];assert current==[r for r in original[k] if r.get('event_us',r.get('signal_us',0))<=BOUNDARY],k
        path=state/arm;path.mkdir();case=sim.result();saved=native.save_case(case,path/'account');summary=saved['summary'];_,q=native.episodes(case['trades'],SYMBOLS)
        for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav());suffix=case['minute'].tail(1440);suffix.write_parquet(path/'SUFFIX.parquet');np.savez_compressed(path/'DAY31.npz',minute_chunk=sim.minute_chunks[-1]);save(path/'MINUTE_NUMERIC.json',codec.minute_fingerprint(case['minute']));view=codec.native # Alias is originalnative, not altered.
        from state_io import split_snapshot
        raw=json.dumps(split_snapshot(sim),sort_keys=True,separators=(',',':'),allow_nan=False).encode();(path/'STATE.json.gz').write_bytes(gzip.compress(raw,mtime=0));save(path/'ACTIVATION.json',activation);body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts());save(path/'ACCOUNT.json',body)
        new=sim.account.trades[n:];eth=[r for r in new if r['symbol']=='ETHUSDT' and r['leg']=='CLOSE'];report=dict(global_calendar_incomplete_not_cash_return=True,common_slice=['2021-05-01','2021-05-02'],marked_NAV_change_from_anchor_USDT=str(sim.account.nav()-oldnav),ETH_quantity_before=str(before['positions']['ETHUSDT']['quantity']),ETH_quantity_after=str(sim.account.positions['ETHUSDT'].quantity),ETH_paid_close_legs=eth,source_default_day31_parity='EXACT_BITS_AND_JOURNAL_PREFIX' if arm=='DEFAULT' else 'DIFFERENT_NAMED_FUTURE_CLOSE_CONTRACT',state_hash=sim.state_hash(),summary=summary,independent_decimal_NAV_bridge=finance,current_native_quantity_gate=quantity_gate(sim.account.positions['ETHUSDT'].quantity,None),native_filter_certificate=False);save(path/'RESULT.json',report);reports[arm]=report;del sim,case,saved,suffix;gc.collect();assert time.monotonic()-began<120;print('ACTUAL_ONE_DAY_ANCHORED_POLICY',arm,'ETHcloselegs',len(eth),'NAV',summary['NAV'],flush=True)
    save(state/'RESULT.json',dict(status='COMPLETE_CONDITIONAL_ONE_DAY_EXIT_POLICY_SENSITIVITY_NOT_NATIVE_CERTIFIED',source_commit=source,arms=reports,new_full_year_wallets=0,restored_suffix_continuations=2,new_fits=0,market_provider_downloads=0,rule_current_symbol_parameters='UNKNOWN_BYBIT_COUNTRY_BLOCK_NO_BYPASS',seconds=time.monotonic()-began));print('ANCHORED_PAIR_COMPLETE',time.monotonic()-began,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.source_commit)
