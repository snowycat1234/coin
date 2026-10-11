"""Separate declared source contracts for exact historical economic inputs.

Valid metadata is necessary, not a substitute for verifying its authority body.
These functions perform no wallet mutation and accept no bar-price fallback.
"""
from decimal import Decimal
import re


def number(x):
    v=Decimal(str(x))
    if not v.is_finite():raise ValueError('Finite economic source number required')
    return v


def applies(a,symbol):
    return bool(a and (a.get('symbol')==symbol or
        isinstance(a.get('symbols'),(list,tuple)) and symbol in a['symbols']))


def authority(a,event,venue,product,symbol):
    return bool(a and a.get('status')=='VERIFIED_HISTORICAL_AUTHORITY' and
        re.fullmatch('[a-f0-9]{64}',a.get('SHA256','')) and a.get('venue')==venue and a.get('product')==product and
        applies(a,symbol) and
        type(a.get('effective_from_us')) is int and type(a.get('effective_to_us')) is int and
        a['effective_from_us']<=event<a['effective_to_us'])


def funding_readiness(event,*,venue,product):
    if event is None:
        return dict(raw_unit='BLOCKED_UNKNOWN_UNIT_AUTHORITY',charge_mark='BLOCKED_NEEDS_EXACT_CHARGE_MARK',
            rate_fraction=None,source_status='EXACT_FUNDING_BLOCKED',authority_body_verification_required=True,wallet_status='NOT_RUN')
    raw=number(event['raw_rate']);at=event['event_us'];symbol=event['symbol']
    if type(at) is not int or not symbol:raise ValueError('Exact funding symbol/event clock required')
    unit=event.get('raw_unit')
    unit_ok=unit in ('FRACTION','PERCENT') and authority(event.get('unit_authority'),at,venue,product,symbol)
    point=event.get('charge_mark') or {}
    point_ok=(point.get('kind')=='EXACT_FUNDING_CHARGE_MARK' and point.get('symbol')==symbol and
        point.get('event_us')==at and point.get('venue')==venue and point.get('product')==product and
        authority(point.get('authority'),at,venue,product,symbol))
    if point_ok:point_ok=number(point['price'])>0
    return dict(raw_unit='DECLARED_AUTHORITY_BOUND' if unit_ok else 'BLOCKED_UNKNOWN_UNIT_AUTHORITY',
        charge_mark='DECLARED_EXACT_EVENT_SOURCE' if point_ok else 'BLOCKED_NEEDS_EXACT_CHARGE_MARK',
        rate_fraction=str(raw if unit=='FRACTION' else raw/100) if unit_ok else None,
        source_status='DECLARED_FUNDING_CONTRACT_COMPLETE' if unit_ok and point_ok else 'EXACT_FUNDING_BLOCKED',
        authority_body_verification_required=True,wallet_status='NOT_RUN')


def unique_funding_events(events):
    seen={}
    for event in events:
        key=(event['symbol'],event['event_us'])
        if key in seen and seen[key]!=event:raise ValueError('Conflicting exact funding point or unit for same event')
        seen[key]=event
    return tuple(seen.values())


def risk_rule_readiness(rule,*,symbol,event_us,venue,product):
    bound=bool(rule.get('version') and applies(rule,symbol) and authority(rule.get('authority'),event_us,venue,product,symbol))
    tiers=rule.get('tiers') or [];valid=bound and bool(tiers);prior=Decimal(0);prior_mmr=Decimal(0);prior_mm=Decimal(0)
    for tier in tiers:
        maximum=number(tier['max_notional_USDT']);mmr=number(tier['MMR']);mmd=number(tier['MMD_USDT'])
        lower_mm=prior*mmr-mmd
        valid=valid and maximum>prior and 0<mmr<1 and mmr>=prior_mmr and mmd>=0 and lower_mm>=prior_mm
        prior=maximum;prior_mmr=mmr;prior_mm=maximum*mmr-mmd
    fee=rule.get('close_fee') or {}
    fee_ok=bool(applies(fee,symbol) and fee.get('reserve_formula') and fee.get('release_rule') and fee.get('version') and
                authority(fee.get('authority'),event_us,venue,product,symbol))
    return dict(historical_tiers='DECLARED_EFFECTIVE_RULE' if valid else 'BLOCKED_NO_HISTORICAL_EFFECTIVE_TIERS',
        close_fee_reserve='DECLARED_RESERVE_RELEASE_CONTRACT' if fee_ok else 'BLOCKED_NO_HISTORICAL_CLOSE_FEE_CONTRACT',
        source_status='DECLARED_RISK_CONTRACT_COMPLETE' if valid and fee_ok else 'HISTORICAL_NATIVE_LIQUIDATION_BLOCKED',
        authority_body_verification_required=True,wallet_status='NOT_RUN')
