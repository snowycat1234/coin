"""Exact funding-event/associated-mark pairing, never a bar-price fallback."""
from decimal import Decimal
import hashlib
import json


def number(x):
    d=Decimal(str(x))
    if not d.is_finite():raise ValueError('Finite provider source number required')
    return d


def response_records(body):
    if body is None:return {},None
    raw=json.loads(body)
    if not isinstance(raw,list):raise ValueError('Explicit stored officialhistory response array required')
    rows={}
    for row in raw:
        if not all(k in row for k in ('symbol','fundingTime','fundingRate','markPrice')):
            raise ValueError('Associatedcharge mark isrequired; no minute-price fallback')
        if type(row['fundingTime']) is not int or row['fundingTime']<0 or not row['symbol']:
            raise ValueError('Exactprovider symbol andinteger millisecond clock required')
        if row.get('rateType','Regular')!='Regular':raise ValueError('Specialfunding schema isoutside thiscryptoarchive bridge')
        value=(number(row['fundingRate']),number(row['markPrice']))
        if value[1]<=0:raise ValueError('Positive associatedcharge mark required')
        key=(row['symbol'],row['fundingTime'])
        if key in rows and rows[key]!=value:raise ValueError('Conflicting officialrate/charge point forexactevent')
        rows[key]=value
    return rows,hashlib.sha256(body).hexdigest()


def pair_events(events,body=None):
    records,response_sha=response_records(body);out=[];used=set()
    for event in events:
        key=(event['symbol'],event['calc_time_ms']);raw=number(event['last_funding_rate'])
        row=dict(symbol=key[0],calc_time_ms=key[1],event_us=key[1]*1000,raw_rate_decimal=str(raw),
            provider_response_SHA256=response_sha,raw_unit_authority='UNKNOWN',historical_publication_authority='UNKNOWN')
        if key not in records:
            row.update(status='BLOCKED_NO_EXACT_ASSOCIATED_CHARGE_MARK_RESPONSE',charge_mark_price=None,
                old_past_mark_substituted=False)
        else:
            rate,price=records[key]
            if rate!=raw:raise ValueError('Exactevent rawrateconflict; no implicitpercent/fraction conversion')
            row.update(status='PAIRED_NUMERIC_SOURCE_ONLY_AUTHORITY_STILL_UNKNOWN',charge_mark_price=str(price),
                old_past_mark_substituted=False);used.add(key)
        out.append(row)
    return out,dict(provider_response_SHA256=response_sha,paired_events=len(used),unmatched_provider_events=len(set(records)-used),
        exact_time_join=True,nearest_time_or_minute_floor=False,unit_inferred=False,native_funding_certified=False)
