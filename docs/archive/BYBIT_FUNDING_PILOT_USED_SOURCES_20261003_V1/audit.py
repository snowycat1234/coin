"""Independent fixed-day Bybit funding history bytes/schema evidence, no economics."""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, resource, sys, time
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
ROOT=Path('/mnt/d/codex/coin')
STATE=Path('/home/xflops/coin-state')
WORK=STATE/'test-bybit-funding-pilot-independent-audit-20261003-v1'
START_MS=1754006400000
END_EXCLUSIVE_MS=1754092800000
HOST='api.bybit.com'
API_PATH='/v5/market/funding/history'
SYMBOLS=('BTCUSDT','ETHUSDT')


def need(ok,message):
    if not ok: raise AssertionError(message)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path): return json.loads(Path(path).read_bytes())


def write_new(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')


def unique_object(pairs):
    value={}
    for key,item in pairs:
        need(key not in value,'Duplicate rawJSON key:'+key)
        value[key]=item
    return value


def reject_constant(value):
    raise AssertionError('Nonstandard JSON constant:'+value)


def strict_json(payload):
    need(isinstance(payload,bytes) and 0<len(payload)<=64000,'Empty/truncated/oversized rawbody')
    return json.loads(payload.decode('utf-8'),object_pairs_hook=unique_object,parse_constant=reject_constant)


def fixed_url(url,symbol,limit):
    parsed=urlsplit(url)
    need(parsed.scheme=='https' and parsed.hostname==HOST and parsed.port is None
         and parsed.path==API_PATH and not parsed.username and not parsed.password
         and not parsed.fragment,'One preregistered official HTTPS funding endpoint only')
    pairs=parse_qsl(parsed.query,keep_blank_values=True)
    need(len(pairs)==5 and len({k for k,v in pairs})==5,'No missing/duplicate/extra query fields')
    need(dict(pairs)=={'category':'linear','symbol':symbol,'startTime':str(START_MS),
         'endTime':str(END_EXCLUSIVE_MS-1),'limit':str(limit)},'Fixed historical day/category/symbol/ms only; never latest')


def validate_body(payload,symbol,limit=200):
    need(symbol in SYMBOLS and type(limit) is int and 1<=limit<=200,'Fixed requested symbol and documented cap')
    value=strict_json(payload)
    need(type(value) is dict and type(value.get('retCode')) is int and value['retCode']==0,
         'HTTP200 is not business success; boolean0/nonzero retCode forbidden')
    result=value.get('result')
    need(type(result) is dict and result.get('category')=='linear','Wrong/missing funding result category')
    rows=result.get('list')
    need(type(rows) is list and 0<len(rows)<limit,'Empty or saturated page cannot be accepted as untruncated small window')
    observed=[]
    for row in rows:
        need(type(row) is dict and row.get('symbol')==symbol,'Wrong/missing funding row symbol')
        timestamp=row.get('fundingRateTimestamp');raw=row.get('fundingRate')
        need(type(timestamp) is str and re.fullmatch(r'[0-9]+',timestamp) is not None,'Epoch milliseconds must be a string of ASCII integer digits')
        stamp=int(timestamp)
        need(START_MS<=stamp<END_EXCLUSIVE_MS,'Funding timestamp is not within the requested half-open UTC day; no rescale/filtering')
        need(type(raw) is str and re.fullmatch(r'[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',raw) is not None,
             'Funding rate must be an original numeric string')
        decimal=Decimal(raw)
        need(decimal.is_finite(),'Funding rate Decimal must be finite')
        observed.append({'symbol':symbol,'fundingRateTimestamp':timestamp,'timestamp_ms':stamp,
                         'fundingRate':raw,'decimal_raw_rate':str(decimal)})
    stamps=[row['timestamp_ms'] for row in observed]
    need(len(stamps)==len(set(stamps)),'Duplicate funding events forbidden')
    need(stamps==sorted(stamps) or stamps==sorted(stamps,reverse=True),'Unexpected response event ordering')
    return {'retCode':0,'category':'linear','symbol':symbol,'rows':len(rows),'events':observed,
            'response_below_preregistered_page_cap':True,'full_historical_retention_certified':False,
            'all_settled_events_for_day_certified':False,'8h_interval_assumed':False,
            'settlement_timeliness_or_signal_availability_certified':False,'rate_units_certified_by_parser':False}


def task_evidence(identity,expected_status,expected_exit):
    need(type(identity) is str and re.fullmatch(r'[0-9a-f]{32}',identity),'Actual task identity malformed')
    path=STATE/'task-progress'/('task-'+identity+'.json');value=load(path)
    need(value['id']==identity and value['status']==expected_status and value['exit_code']==expected_exit,
         'Actual wrapper status/exit differ from recorded pilot outcome')
    need(type(value.get('pid')) is int and type(value.get('start_ticks')) is int,'Actual process identity required')
    return dict(path=str(path),sha256=sha(path),**{k:value[k] for k in ('id','status','exit_code','pid','start_ticks')})

# Receipt/schema mapping will be completed from frozen pilot source and actual outputs.
# This prepared source and STATE fixtures have not read or queried any historical API data.