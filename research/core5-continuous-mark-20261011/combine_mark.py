"""Join six alreadypublished mark certificates and day features; no new source."""
import argparse
import io
import json
from pathlib import Path
import time
import numpy as np
from mark_source import ROOT,HERE,PREFIX,PHASES,SYMBOLS,SourceReader,bind_current,identity,git,digest,save
from join import assemble as assemble_trade


def validate_masks(full,missing):
    """A missing source minute invalidates that asset day's path statistics."""
    observed=full['observed_minutes'];n=len(full['available_us'])
    assert observed.shape==(n,5) and np.all(observed==1440-missing)
    previous=np.vstack([np.zeros((1,5),dtype=bool),np.isfinite(full['close'][:-1])])
    valid=(missing==0)&previous
    risk=('RV_1m','RV_5m','RSplus_1m','RSminus_1m','RSplus_5m','RSminus_5m','max_log_up','max_log_down')
    for k,v in full.items():
        if k=='available_us':continue
        assert v.shape==(n,5) and not np.isinf(v).any()
        if k in risk:np.testing.assert_array_equal(np.isfinite(v),valid)
        if k in ('high','low'):np.testing.assert_array_equal(np.isfinite(v),missing==0)
    return valid


def assemble(commit):
    arrays=[];phases=[];previous=None;minutes=0;newbytes=0;newarchives=0;added=0;common=0;gaps=[];originals={}
    for phase in PHASES:
        prefix=PREFIX+'phases/'+phase+'/'
        iraw=git('show',commit+':'+prefix+'SOURCE_INDEX.json');index=json.loads(iraw)
        raw=git('show',commit+':'+prefix+'RECOVERY.json');assert digest(raw)==index['proof_SHA256']
        craw=git('show',commit+':'+prefix+'PUBLIC_RESTORE.json');cold=json.loads(craw)
        wanted='PASS_PUBLIC_GAPPED_MARK_SOURCE_RESTORE' if phase=='Q32022' else 'PASS_PUBLIC_RAW_MARK_MINUTE_COLD_RESTORE'
        assert cold['status']==wanted
        assert cold['source_index_SHA256']==digest(iraw)
        assert cold['provider_downloads']==cold['original_STATE_open_attempts']==cold['fits']==cold['wallets']==0
        assert git('show',cold['artifact_commit']+':'+prefix+'SOURCE_INDEX.json')==iraw
        proof=bind_current(json.loads(raw),cold['artifact_commit'])
        assert proof['fits']==proof['wallets']==proof['labels_created']==0
        if previous is None:assert proof['previous_proof_SHA256'] is None
        else:
            assert proof['previous_proof_SHA256']==previous['raw_SHA256']
            month=f'{PHASES[phase][0][0]}-{PHASES[phase][0][1]:02d}'
            for s in SYMBOLS:
                row=next(r for r in proof['sources'] if r['source']['symbol']==s and r['source']['month']==month)
                assert row['past_boundary']==previous['proof']['end_boundaries'][s]
        for r in proof['sources']:
            identity(r['source'])
            for t in r.get('remaining_missing_open_ms',[]):
                gaps.append(dict(symbol=r['source']['symbol'],open_ms=t,source_ZIP_SHA256=r['source']['ZIP_SHA256']))
            for s in [r['source'],*r['source'].get('new_daily_repairs',[])]:
                if s['kind']=='NEW_PUBLIC_PARTS':originals[s['ZIP_SHA256']]=s
        row=index['artifacts']['DAILY.npz'];b=b''.join(SourceReader.part(cold['artifact_commit'],p) for p in row['parts'])
        assert digest(b)==row['SHA256'] and len(b)==row['bytes']
        with np.load(io.BytesIO(b),allow_pickle=False) as a:
            assert tuple(a['symbol_order'])==SYMBOLS
            arrays.append({k:a[k].copy() for k in a.files if k!='symbol_order'})
        minutes+=proof['actual_minutes'];newbytes+=proof['new_original_bytes'];newarchives+=index['original_new_source_count']
        added+=proof['official_daily_repairs_added'];common+=proof['official_daily_common_rows_verified']
        phases.append(dict(phase=phase,artifact_commit=cold['artifact_commit'],source_index_SHA256=digest(iraw),
            recovery_SHA256=digest(raw),cold_SHA256=digest(craw),calendar_days=proof['calendar_days'],
            valid_joint_days=proof['valid_joint_RV_days'],actual_minutes=proof['actual_minutes'],
            new_original_bytes=proof['new_original_bytes'],new_original_archives=index['original_new_source_count'],
            monthly_sources=len(proof['sources']),previous_month_raw_boundary_checks=cold['previous_month_raw_boundary_checks']))
        previous=dict(raw_SHA256=digest(raw),proof=proof)
    assert len({tuple(a) for a in arrays})==1
    full={k:np.concatenate([a[k] for a in arrays]) for k in arrays[0]}
    t=full['available_us'];assert len(t)==699 and np.all(np.diff(t)==86400000000)
    assert int(t[0])==1609545600000000 and int(t[-1])==1669852800000000
    missing=np.zeros((699,5),dtype=np.int64);lookup={int(v):i for i,v in enumerate(t)}
    assert len({(g['symbol'],g['open_ms']) for g in gaps})==len(gaps)
    for g in gaps:
        day_end=(g['open_ms']//86400000+1)*86400000000
        missing[lookup[day_end],SYMBOLS.index(g['symbol'])]+=1
    valid=validate_masks(full,missing)
    full['missing_minutes']=missing;full['complete_risk_mask']=valid
    assert minutes==int(full['observed_minutes'].sum())==5032800-len(gaps)
    monthly=sum(s['frequency']=='monthly' for s in originals.values())
    daily=sum(s['frequency']=='daily' for s in originals.values())
    assert sum(p['monthly_sources'] for p in phases)==115 and monthly==50
    assert newarchives==len(originals)==monthly+daily and newbytes<=100000000
    trade,tradeproof=assemble_trade('306b58c4a52035ac9f374de7c25d40dff22fb658')
    np.testing.assert_array_equal(full['available_us'],trade['available_us'])
    return full,dict(status='PASS_PUBLIC_MARK_SOURCE_WITH_EXPLICIT_GAPS',source_chain_commit=commit,
        phases=phases,source_calendar_dates=699,valid_boundary_dates=int(valid.all(1).sum()),
        full_minute_continuity=False,remaining_missing_minutes=len(gaps),missing_source_minutes=gaps,
        incomplete_source_days=[dict(day_end_available_us=int(t[i]),missing_by_symbol={s:int(missing[i,j]) for j,s in enumerate(SYMBOLS) if missing[i,j]}) for i in np.flatnonzero(missing.any(1))],
        feature_day_start='2021-01-02',feature_day_end='2022-11-30',
        domain='BinanceUSD-MmarkPriceKlines, separatefromtrade',actual_mark_minute_rows=minutes,
        monthly_originals=115,reused_monthly_originals=65,new_monthly_originals=monthly,new_daily_originals=daily,
        new_original_archives=newarchives,new_original_bytes=newbytes,
        daily_repair_added_minutes=added,daily_overlap_common_minutes_verified=common,
        calendar_and_asset_order_match_trade=True,trade_source_SHA=tradeproof['source_chain_commit'],
        first_unknown_prior_preserved=True,all_month_quarter_year_boundaries_source_backed=True,
        minuteclose_not_exact_charge_mark=True,funding_unit='UNKNOWN_AUTHORITY_NOT_CERTIFIED',
        exact_funding_charge_price='UNKNOWN',historical_native_risk_rule='UNKNOWN',arrival_clock='UNKNOWN',
        priceclock='Actualsourceopen_ms/close_ms; conservativenextminute/daycompletion availability',
        fits=0,wallets=0,labels_created=0,provider_downloads=0,original_STATE_open_attempts=0,
        scope='Six rawminute publiccold certificates verified and reused; this join readspublicdayfeature bytes/certificates, no freshCSVscan orincome result.')


def run(commit,output,expected=None):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists();output.mkdir()
    for line in (HERE/'COMBINE_GAPPED_SHA256.txt').read_text().splitlines():
        sha,p=line.split(maxsplit=1)
        assert digest(git('show',commit+':'+p))==digest((ROOT/p).read_bytes())==sha
    start=time.monotonic();full,proof=assemble(commit)
    np.savez_compressed(output/'MARK_DAILY_CONTINUOUS.npz',symbol_order=np.asarray(SYMBOLS),**full)
    if expected is not None:
        with np.load(expected,allow_pickle=False) as a:
            assert tuple(a['symbol_order'])==SYMBOLS
            for k,v in full.items():np.testing.assert_array_equal(v,a[k])
        assert expected.read_bytes()==(output/'MARK_DAILY_CONTINUOUS.npz').read_bytes()
        proof['public_combined_bytes_and_vectors_exact']=True
    proof['artifact_SHA256']=digest((output/'MARK_DAILY_CONTINUOUS.npz').read_bytes())
    proof['elapsed_seconds']=time.monotonic()-start
    save(output/'COVERAGE.json',proof)
    print(json.dumps({k:v for k,v in proof.items() if k!='phases'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected',type=Path);a=p.parse_args();run(a.commit,a.output,a.expected)
