"""Narrow public source-body audit; no new market-data provider request."""
import argparse
import importlib.util
import inspect
import io
import json
import math
from pathlib import Path
import sys
import time
import zipfile

import pandas as pd
import pyarrow.parquet as pq
from quant.perpetual_account import USDTLinearPerpetualAccount
from bridge import pair_events

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'research/core5-continuous-risk600-20261011'))
sys.path.insert(0,str(ROOT/'research/native-mark-inputs-20261011'))
from prepare import git,digest,save,SYMBOLS
from economic_readiness import funding_readiness


def require(v,msg):
    if not bool(v):raise ValueError(msg)


def run(state,source,expected=None):
    require(not state.exists() and state.resolve().is_relative_to(Path('/workspace')),'Fresh STATE')
    require(not git('status','--porcelain'),'Clean publishedsource')
    if expected is None:require(git('rev-parse','HEAD').decode().strip()==source,'Exactsource')
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        sha,p=line.split(maxsplit=1);require(digest((ROOT/p).read_bytes())==sha,'SourceSHA '+p)
    state.mkdir();began=time.monotonic()
    spec=importlib.util.spec_from_file_location('original_source',ROOT/'research/short-funding-residual-20261011/experiment.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);raw=m.source_archive(ROOT,state)
    events=[];schema=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        for s in SYMBOLS:
            name=f'source_tables_not_model_inputs/economics/{s}_funding_events.parquet';b=z.read(name)
            require(digest(b)==members[name]['SHA256'],'Originalfundingmemberidentity')
            names=pq.read_schema(io.BytesIO(b)).names
            columns=['calc_time_ms','last_funding_rate','funding_interval_hours','past_mark_price','past_mark_available_us']
            f=pq.read_table(io.BytesIO(b),columns=columns,filters=[('calc_time_ms','>=',1664582400000),('calc_time_ms','<',1664845200000)]).to_pandas()
            require(len(f)==10,'ActualOct1three days plusOct4firsthour10events perasset')
            for r in f.itertuples(index=False):events.append(dict(symbol=s,calc_time_ms=int(r.calc_time_ms),
                last_funding_rate=str(r.last_funding_rate),reported_interval_hours=float(r.funding_interval_hours),
                past_mark_price=float(r.past_mark_price) if pd.notna(r.past_mark_price) and math.isfinite(r.past_mark_price) else None,
                past_mark_available_us=int(r.past_mark_available_us) if pd.notna(r.past_mark_available_us) else None))
            schema.append(dict(symbol=s,member=name,member_SHA256=digest(b),column_names=names,events=len(f),
                associated_charge_mark_saved=('markPrice' in names or 'charge_mark_price' in names)))
    events.sort(key=lambda r:(r['calc_time_ms'],r['symbol']));paired,proof=pair_events(events,None)
    for row,event in zip(paired,events):
        readiness=funding_readiness(dict(symbol=event['symbol'],event_us=event['calc_time_ms']*1000,raw_rate=event['last_funding_rate']),
            venue='Binance',product='USD_M_LINEAR_USDT_PERPETUAL')
        row.update(past_minute_mark_price=event['past_mark_price'],past_minute_mark_available_us=event['past_mark_available_us'],
            charge_mark_readiness=readiness['charge_mark'],unit_readiness=readiness['raw_unit'])
        past=event['past_mark_available_us']
        row['past_minute_proxy_status']=('UNKNOWN_SAVED_PROXY' if past is None or event['past_mark_price'] is None else
            'PAST_PROXY_ONLY_NOT_CHARGE_MARK' if past<event['calc_time_ms']*1000 else 'BLOCKED_NOT_STRICTLY_PAST_SOURCE_PROXY')
        row['past_proxy_age_us']=None if past is None else event['calc_time_ms']*1000-past
    pd.DataFrame(paired).to_csv(state/'EXACT_EVENT_RECOVERY_MATRIX.csv',index=False)
    signature=str(inspect.signature(USDTLinearPerpetualAccount.apply_funding))
    report=dict(status='BLOCKED_EXACT_CHARGE_SOURCE_BODY_AND_UNIT_AUTHORITY',source_commit=source,
        archive_source=m.SOURCE_COMMIT,archive_SHA256=m.ARCHIVE_SHA,member_schemas=schema,
        actual_funding_events=len(events),exact_associated_charge_marks_present=sum(r['associated_charge_mark_saved'] for r in schema),
        missing_saved_past_proxy_events=sum(r['past_minute_proxy_status']=='UNKNOWN_SAVED_PROXY' for r in paired),
        source_pairing=proof,legacy_kernel_funding_signature=signature,exact_charge_mark_hook='NOT_AVAILABLE_IN_CURRENT_KERNEL',
        modern_API_price_field='markPrice_associated_with_funding_fee_charge_DOCUMENTED_NOT_FETCHED',
        historical_rate_time_mapping='UNKNOWN_NO_NEAREST_JOIN',raw_unit_authority='UNKNOWN_NOT_GUESSED',
        no_minute_price_substitution=True,no_wallet_or_oldPnL_mutation=True,old_selector_four_FAILs_unchanged=True,
        models_fit=0,wallets=0,new_provider_requests=0,new_provider_downloads=0,
        matrix_SHA256=digest((state/'EXACT_EVENT_RECOVERY_MATRIX.csv').read_bytes()))
    save(state/'RESULT.json',report)
    if expected:
        old=json.loads(git('show',expected+':research/funding-charge-evidence-20261011/result/RESULT.json'))
        require(old==report,'Exactprovider gap/source/schema readiness restoration')
        require(digest(git('show',expected+':research/funding-charge-evidence-20261011/result/EXACT_EVENT_RECOVERY_MATRIX.csv'))==report['matrix_SHA256'],'Exactevent matrixbytes')
        save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_FUNDING_EVENT_RECOVERY_GAP_RESTORE',artifact_commit=expected,
            models_fit=0,wallets=0,new_provider_requests=0,elapsed_seconds=time.monotonic()-began))
    save(state/'TIMING.json',dict(elapsed_seconds=time.monotonic()-began));require(time.monotonic()-began<60,'Frozen60s budget')
    print(json.dumps({k:report[k] for k in ('status','actual_funding_events','exact_associated_charge_marks_present','exact_charge_mark_hook','new_provider_requests')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit')
    a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
