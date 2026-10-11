"""One fixed January source bridge inspection, including the real MarketTape.

No targets, account, forward labels, inference, funding charge or trading result.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np
from mark_bars import source_bars,day_block,legacy_projection,exact_boundary,DAY
from economic_readiness import funding_readiness,risk_rule_readiness

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
MARK='research/core5-continuous-mark-20261011/'
TRADE='research/core5-continuous-risk600-20261011/'
PREFIX='research/native-mark-inputs-20261011/'
sys.path.insert(0,str(ROOT/MARK))
from mark_source import SourceReader,bind_current,configure,inventories,complete_month,git,digest,save,SYMBOLS
from prepare import decoded_month


def certificate(commit,prefix,phase):
    base=prefix+'phases/'+phase+'/'
    cold=json.loads(git('show',commit+':'+base+'PUBLIC_RESTORE.json'))
    artifact=cold['artifact_commit']
    iraw=git('show',artifact+':'+base+'SOURCE_INDEX.json')
    raw=git('show',artifact+':'+base+'RECOVERY.json')
    index=json.loads(iraw)
    assert digest(iraw)==cold['source_index_SHA256'] and digest(raw)==index['proof_SHA256']
    assert cold['fits']==cold['wallets']==cold['provider_downloads']==cold['original_STATE_open_attempts']==0
    return bind_current(json.loads(raw),artifact),dict(artifact_commit=artifact,index_SHA256=digest(iraw),proof_SHA256=digest(raw))


def vector_sha(arrays):
    h=hashlib.sha256()
    for name,a in arrays:
        h.update(name.encode()+b'\0'+str(a.dtype).encode()+b'\0'+str(a.shape).encode()+b'\0')
        h.update(a.tobytes(order='C'))
    return h.hexdigest()


def run(state,source,expected_commit=None):
    assert state.resolve().is_relative_to(Path('/workspace')) and not state.exists()
    assert not git('status','--porcelain')
    if expected_commit is None:assert git('rev-parse','HEAD').decode().strip()==source
    protocol=json.loads((HERE/'PROTOCOL.json').read_text())
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        sha,p=line.split(maxsplit=1)
        assert digest(git('show',source+':'+p))==digest((ROOT/p).read_bytes())==sha,p
    state.mkdir();configure(state,'Q12022');start=time.monotonic();blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=str(Path(args[0]).absolute())
            if p.startswith(('/workspace/mark-continuous-state/','/workspace/core5-continuous-risk-state/','/workspace/native-mark-inspection-state/')) and not Path(p).is_relative_to(state):
                blocked.append(p);raise RuntimeError('Original preparation/inspection STATE forbidden')
    sys.addaudithook(audit)
    def bounded():
        assert time.monotonic()-start<600 and shutil.disk_usage(state).free>=16106127360
        assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<1000000000
    tradeproof,tcert=certificate(protocol['trade_source_commit'],TRADE,'Q12022')
    markproof,mcert=certificate(protocol['mark_source_commit'],MARK,'Q12022')
    assert tradeproof['phase']==markproof['phase']=='Q12022'
    coverage=json.loads(git('show',protocol['mark_source_commit']+':'+MARK+'result/COVERAGE.json'))
    assert coverage['remaining_missing_minutes']==27 and not coverage['full_minute_continuity']
    inv,_,_,_=inventories();reader=SourceReader(inv,state,local=False)
    from modules.collector_research.pipeline.normalize import month_limits
    left,right=month_limits(2022,1);trade={};mark={};source_records=[]
    for s in SYMBOLS:
        tr=next(r for r in tradeproof['sources'] if r['source']['symbol']==s and r['source']['month']=='2022-01')
        mr=next(r for r in markproof['sources'] if r['source']['symbol']==s and r['source']['month']=='2022-01')
        tf,te=decoded_month(reader,tr['source'],left,right)
        mf,me=complete_month(reader,mr['source'],left,right)
        assert te['CRC'] and me['CRC'] and te['exact_complete_grid'] and me['exact_complete_grid']
        assert len(tf)==len(mf)==44640
        trade[s]=source_bars(tf,tr['source'],'klines');mark[s]=source_bars(mf,mr['source'],'markPriceKlines')
        source_records.append(dict(symbol=s,trade_ZIP_SHA256=tr['source']['ZIP_SHA256'],mark_ZIP_SHA256=mr['source']['ZIP_SHA256'],
            trade_official_URL=tr['source']['official_URL'],mark_official_URL=mr['source']['official_URL'],
            actual_trade_minutes=len(tf),actual_mark_minutes=len(mf),reused_first_boundary_certificate=True))
        print('DUAL_SOURCE_VERIFIED',s,'2022-01',len(tf),len(mf),flush=True);bounded()
    reader.close()
    from scripts.investment.resumable_perpetual import MarketTape
    def blocks():
        for at in range(left*1000,right*1000,DAY):yield legacy_projection(day_block(SYMBOLS,trade,mark,at))
    tape=MarketTape(dict(start=left*1000,end=right*1000,minute_blocks=blocks),SYMBOLS)
    day_receipts=[];prior_checks=0;vector_arrays=[];wicks={}
    for at in range(left*1000,right*1000,DAY):
        block=day_block(SYMBOLS,trade,mark,at);rows=tape.day(at)
        np.testing.assert_array_equal(np.asarray([r[0] for r in rows]),block['times'])
        for s in SYMBOLS:
            for k,v in block['market'][s].items():
                actual=np.asarray([row[s][k] for _,row in rows])
                np.testing.assert_array_equal(actual,v)
            sidecar=block['mark_sidecars'][s]
            for k,v in sidecar['mark_ohlc'].items():
                keep=(mark[s].open_us>=at)&(mark[s].open_us<at+DAY)
                np.testing.assert_array_equal(v,mark[s].values[k][keep])
            assert np.all(sidecar['available_us']==block['times']+60_000_000)
            if at>left*1000:
                exact_boundary(mark[s],at);exact_boundary(trade[s],at);prior_checks+=2
        vectors=[('times',block['times'])]
        for s in SYMBOLS:
            vectors += [(s+'/legacy/'+k,v) for k,v in block['market'][s].items()]
            vectors += [(s+'/mark/'+k,v) for k,v in block['mark_sidecars'][s]['mark_ohlc'].items()]
            vectors += [(s+'/'+k,block['mark_sidecars'][s][k]) for k in ('open_us','close_us','available_us')]
        day_receipts.append(dict(day_open_us=at,asset_minutes=7200,source_and_actual_MarketTape_vectors_SHA256=vector_sha(vectors)))
        bounded()
    for s in SYMBOLS:
        vector_arrays += [(s+'/trade/'+k,v) for k,v in trade[s].values.items()]
        vector_arrays += [(s+'/mark/'+k,v) for k,v in mark[s].values.items()]
        wicks[s]=dict(mark_high_above_close_minutes=int((mark[s].values['high']>mark[s].values['close']).sum()),
                      mark_low_below_close_minutes=int((mark[s].values['low']<mark[s].values['close']).sum()))
    economic=dict(funding=funding_readiness(None,venue='BINANCE',product='USD_M_PERPETUAL'),
        risk=risk_rule_readiness({},event_us=left*1000,venue='BINANCE',product='USD_M_PERPETUAL'),
        venue_execution='BLOCKED_BINANCE_PRICE_BYBIT_FEE_PROXY_NOT_NATIVE',arrival='BLOCKED_UNKNOWN_HISTORICAL_ARRIVAL',
        current_kernel_charge_hook='STRICTLY_PAST_COMPLETED_MARK_CONDITIONAL_ONLY; no exact event-price interface',
        current_kernel_risk_rule='Default/declaredMMR is not effective historical tiers or close-fee reserve certification',
        funding_event_source_status='NO_BOUND_EVENT_UNIT_AND_CHARGE_POINT_CONTRACT',wallet_status='NOT_RUN')
    assert not blocked
    report=dict(status='PASS_REAL_JANUARY_DUAL_BAR_TO_MARKET_TAPE_INPUT',source_commit=source,
        protocol_SHA256=digest((HERE/'PROTOCOL.json').read_bytes()),trade_source=tcert,mark_source=mcert,
        source_records=source_records,symbol_order=list(SYMBOLS),observed_trade_minutes=223200,observed_mark_minutes=223200,
        completed_calendar_days=31,day_receipts=day_receipts,actual_legacy_reader_vectors_exact=True,
        mark_OHLC_sidecars_and_completion_clock_exact=True,intraminute_order='UNKNOWN',extreme_event_us='UNKNOWN',
        intra_January_actual_previous_source_boundary_checks=prior_checks,source_vector_SHA256=vector_sha(vector_arrays),
        observed_mark_ranges=wicks,source_slice_status='SOURCE_BAR_READY',global_mark_source_status='SOURCE_GAPPED',
        global_remaining_mark_holes=27,global_complete_joint_risk_dates=696,economic_readiness=economic,
        actual_funding_events_consumed=0,held_quantity_or_account_created=False,source_inspection_attempts=1,
        fits=0,forward_labels=0,targets=0,wallets=0,provider_downloads=0,original_STATE_open_attempts=0,
        data_role='Previouslyseenhistoricalsourceverification; no newOOS or economicresult',
        random_seed='NOT_APPLICABLE_DETERMINISTIC_SOURCE_ADAPTER',
        runtime=dict(python=sys.version.split()[0],numpy=np.__version__,pandas=importlib.metadata.version('pandas'),polars=importlib.metadata.version('polars')))
    if expected_commit:
        expected=json.loads(git('show',expected_commit+':'+PREFIX+'result/INSPECTION.json'))
        original={k:v for k,v in expected.items() if k!='elapsed_seconds'}
        assert original==report,'Public source bridge vectors/receipts/status must restore exactly'
        save(state/'PUBLIC_RESTORE.json',dict(status='PASS_PUBLIC_NATIVE_INPUT_RESTORE',artifact_commit=expected_commit,
            original_scientific_source=source,inspection_report_SHA256=digest(git('show',expected_commit+':'+PREFIX+'result/INSPECTION.json')),
            every_source_vector_day_receipt_and_economic_block_exact=True,original_STATE_open_attempts=0,
            provider_downloads=0,new_scientific_attempts=0,fits=0,wallets=0,elapsed_seconds=time.monotonic()-start))
    report['elapsed_seconds']=time.monotonic()-start;save(state/'INSPECTION.json',report)
    print(json.dumps({k:report[k] for k in ('status','completed_calendar_days','observed_trade_minutes','observed_mark_minutes',
        'global_mark_source_status','global_remaining_mark_holes','source_vector_SHA256','wallets','elapsed_seconds')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
