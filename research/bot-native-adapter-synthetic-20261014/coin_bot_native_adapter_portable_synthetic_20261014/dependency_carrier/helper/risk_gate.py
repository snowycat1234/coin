"""Fail-closed intent envelopes and ex-post paired-risk gates, not risk proofs."""
from dataclasses import dataclass
from collections.abc import Mapping
from decimal import Decimal
from itertools import product
from math import ceil, isfinite, sqrt
from statistics import stdev
from grid_policy import CORE5


@dataclass(frozen=True)
class Envelope:
    gross_cap: float = .60
    asset_cap: float = .30
    annual_vol_cap: float = .10
    leverage: float = 1.
    initial_capital: float = 10000.


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reasons: tuple
    worst_reserved_gross: float | None = None
    worst_reserved_abs_net: float | None = None
    worst_reserved_sigma: float | None = None
    math_valid: bool = False
    status: str = "NOT_CERTIFIED_NEEDS_NATIVE_BINDING"


def vector(xs):
    raw=tuple(xs)
    if any(isinstance(x,bool) or not isinstance(x,(int,float,Decimal)) for x in raw):
        raise ValueError("numeric values required; boolean/string values forbidden")
    v = tuple(float(x) for x in raw)
    if len(v) != len(CORE5) or any(not isfinite(x) for x in v):
        raise ValueError("five finite CORE5 values required")
    return v


def sigma(weights, cov):
    return sqrt(max(0., sum(weights[i]*cov[i][j]*weights[j]
                           for i in range(5) for j in range(5))))


def check_covariance(cov):
    # Symmetric positive definite is sufficient and fails closed for singular
    # matrices in this tiny stdlib-only skeleton; original covariance may be
    # PSD/singular and needs its reviewed numerical implementation at integration.
    c = tuple(vector(row) for row in cov)
    if len(c) != 5 or any(abs(c[i][j]-c[j][i]) > 1e-12
                          for i in range(5) for j in range(5)):
        raise ValueError("finite symmetric annual covariance required")
    l = [[0.]*5 for _ in range(5)]
    for i in range(5):
        for j in range(i+1):
            x = c[i][j]-sum(l[i][k]*l[j][k] for k in range(j))
            if i == j:
                if x <= 0:
                    raise ValueError("positive definite covariance required; otherwise inconclusive")
                l[i][j] = sqrt(x)
            else:
                l[i][j] = x/l[j][j]
    return c


def assess_intent_envelope(*, original_weights, retained_legs, grid_owned_weight,
                           grid_unfilled_buy_weight, annual_covariance,
                           previous_quote_volume, requested_notional,
                           free_cash, reserved_cash, valuation_nav, envelope=Envelope()):
    """Validate every vertex of outstanding-fill intervals jointly with base legs.

    Retained legs are supplied separately. Their absolute notionals count toward
    gross and per-asset risk even if signed holdings cancel in a one-way target.
    Grid inventory already owned is distinct from UNFILLED buy reservations.
    Prices/NAV must be contemporaneous actual marks; capacities cover all sleeves
    jointly. This cannot certify future gaps, liquidation or execution feasibility.
    """
    try:
        baseline = vector(original_weights)
        legs = tuple(vector(x) for x in retained_legs)
        owned, buys = vector(grid_owned_weight), vector(grid_unfilled_buy_weight)
        cov = check_covariance(annual_covariance)
        quote, request = vector(previous_quote_volume), vector(requested_notional)
        if any(x < 0 for x in (*owned, *buys, *quote, *request)):
            raise ValueError("nonnegative grid/capacity values required")
        if (any(isinstance(x,bool) or not isinstance(x,(int,float,Decimal))
                for x in (valuation_nav,free_cash,reserved_cash))
                or type(envelope) is not Envelope
                or any(isinstance(getattr(envelope,k),bool) for k in envelope.__dataclass_fields__)
                or not isfinite(valuation_nav) or valuation_nav <= 0 or envelope != Envelope() or not isfinite(free_cash) or not isfinite(reserved_cash)
                or free_cash < 0 or reserved_cash < 0):
            raise ValueError("unchanged canonical capital/leverage/caps and finite cash required")
    except (TypeError, ValueError, ZeroDivisionError) as e:
        return RiskDecision(False, ("INCONCLUSIVE_INPUT:"+str(e),))
    reasons = set()
    retained_net=tuple(sum(l[i] for l in legs) for i in range(5))
    expected=(baseline[0]-.10*max(0.,baseline[0]),*baseline[1:])
    if any(abs(retained_net[i]-expected[i]) > 1e-12 for i in range(5)):
        reasons.add("ORIGINAL_REPLACEMENT_LINEAGE_MISMATCH")
    if reserved_cash+1e-9 < sum(buys)*valuation_nav*1.00135044:
        reasons.add("GRID_BUY_RESERVATION_NOTIONAL_UNFUNDED")
    if any(request[i]+1e-9 < buys[i]*valuation_nav for i in range(5)):
        reasons.add("OUTSTANDING_BUY_NOTIONAL_UNBOUND")
    if reserved_cash > free_cash:
        reasons.add("SHARED_CASH_RESERVATION_EXCEEDS_FREE_CASH")
    if any(request[i] > .001*quote[i]+1e-9 for i in range(5)):
        reasons.add("SHARED_PRIOR_MINUTE_CAPACITY")
    base_gross = sum(abs(x) for x in baseline)
    base_net = abs(sum(baseline))
    base_sigma = sigma(baseline, cov)
    fixed_abs = tuple(sum(abs(l[i]) for l in legs)+owned[i] for i in range(5))
    fixed_net = tuple(sum(l[i] for l in legs)+owned[i] for i in range(5))
    gross_max, net_max, sigma_max = 0., 0., 0.
    for filled in product((0, 1), repeat=5):
        absolute = tuple(fixed_abs[i]+filled[i]*buys[i] for i in range(5))
        net = tuple(fixed_net[i]+filled[i]*buys[i] for i in range(5))
        gross, abs_net, vol = sum(absolute), abs(sum(net)), sigma(net, cov)
        gross_max, net_max, sigma_max = max(gross_max,gross),max(net_max,abs_net),max(sigma_max,vol)
        if gross > min(envelope.gross_cap, base_gross)+1e-12:
            reasons.add("GROSS_CAP_OR_BASELINE_ENVELOPE")
        if any(absolute[i] > min(envelope.asset_cap,abs(baseline[i]))+1e-12 for i in range(5)):
            reasons.add("ASSET_CAP_OR_BASELINE_ENVELOPE")
        if abs_net > base_net+1e-12:
            reasons.add("ABS_NET_BASELINE_ENVELOPE")
        if vol > min(envelope.annual_vol_cap,base_sigma)+1e-12:
            reasons.add("CAUSAL_VOL_BASELINE_ENVELOPE")
    return RiskDecision(False, tuple(sorted(reasons|{"NEEDS_NATIVE_BINDING"})),
                        gross_max, net_max, sigma_max, not reasons,
                        "MATH_FAIL" if reasons else "NOT_CERTIFIED_NEEDS_NATIVE_BINDING")


REQUIRED_METRICS = ("minute_mdd", "daily_annual_vol", "daily_es95_loss", "worst_30d_loss",
                    "max_gross", "mean_gross", "max_abs_net", "max_asset_gross",
                    "halt_count", "ruin_count", "residual_notional", "unfilled_risk_count")
REQUIRED_CONTRACT = ("initial_capital", "leverage", "no_topup", "cost_id", "fee_bps",
                     "spread_bps", "slippage_bps", "participation", "quantity_step",
                     "funding_convention", "terminal_opens", "symbols", "clock_identity",
                     "calendar_identity", "source_identity", "target_lineage", "hard_risk_identity")
CANONICAL_CONTRACT = {"initial_capital":10000., "leverage":1., "no_topup":True,
    "cost_id":"BASE27", "fee_bps":5.5, "spread_bps":4., "slippage_bps":4.,
    "participation":.001, "quantity_step":"0.00000001",
    "funding_convention":"RAW_FRACTION_SCALE1_CONDITIONAL", "terminal_opens":60,
    "symbols":CORE5}


def certify_risk_match(control, candidate):
    """No pass from target caps. Full original-engine journals are mandatory.

    Each annual/arm comparison stands alone and includes all fixed cases. A
    financial halt or a missing/minute-incomplete/marked-only ledger is never
    rewritten as a full-year cash return. Strict nonincrease is chosen in advance.
    """
    reasons = []
    if (not isinstance(control,Mapping) or not isinstance(candidate,Mapping)
            or any(not isinstance(a.get("metrics"),Mapping)
                   or not isinstance(a.get("contract"),Mapping) for a in (control,candidate))):
        return {"status":"INCONCLUSIVE", "reasons":["INVALID_REPORT_SCHEMA"]}
    for arm in (control, candidate):
        if arm.get("evidence_origin") != "ORIGINAL_NATIVE_ENGINE_COMPLETE_LEDGER":
            reasons.append("INCONCLUSIVE_NATIVE_LEDGER_REQUIRED")
        if arm.get("complete_calendar") is not True or arm.get("paid_flat") is not True:
            reasons.append("INCONCLUSIVE_COMPLETE_PAID_FLAT_REQUIRED")
        if any(k not in arm.get("metrics", {}) for k in REQUIRED_METRICS):
            reasons.append("INCONCLUSIVE_METRIC_MISSING")
        if any(k not in arm.get("contract", {}) for k in REQUIRED_CONTRACT):
            reasons.append("INCONCLUSIVE_CONTRACT_MISSING")
    if reasons:
        return {"status":"INCONCLUSIVE", "reasons":sorted(set(reasons))}
    for arm in (control, candidate):
        if (arm["contract"].get("no_topup") is not True
                or any(isinstance(arm["contract"][k],bool) for k in
                       ("initial_capital","leverage","fee_bps","spread_bps","slippage_bps","participation","terminal_opens"))
                or any(arm["contract"][k] != v for k,v in CANONICAL_CONTRACT.items())):
            reasons.append("NONCANONICAL_CAPITAL_PRODUCT_EXECUTION_CONTRACT")
        if any(type(arm["contract"][k]) is not str or not arm["contract"][k].strip()
               for k in ("clock_identity","calendar_identity","source_identity","target_lineage","hard_risk_identity")):
            reasons.append("INCONCLUSIVE_IDENTITY_MISSING")
    if "INCONCLUSIVE_IDENTITY_MISSING" in reasons:
        return {"status":"INCONCLUSIVE", "reasons":sorted(set(reasons))}
    if any(control["contract"][k] != candidate["contract"][k] for k in REQUIRED_CONTRACT):
        reasons.append("UNMATCHED_EXECUTION_OR_CAPITAL_CONTRACT")
    c, n = control["metrics"], candidate["metrics"]
    if any(not isinstance(n[k],(int,float)) or isinstance(n[k],bool) or not isfinite(n[k])
           or not isinstance(c[k],(int,float)) or isinstance(c[k],bool) or not isfinite(c[k])
           or min(c[k],n[k]) < 0 for k in REQUIRED_METRICS):
        return {"status":"INCONCLUSIVE", "reasons":["INVALID_METRICS"]}
    for key in REQUIRED_METRICS:
        if n[key] > c[key]+1e-12:
            reasons.append("WORSE_"+key.upper())
    if n["max_gross"] > .60+1e-12 or n["max_asset_gross"] > .30+1e-12:
        reasons.append("ACTUAL_EXPOSURE_CAP_BREACH")
    if n["daily_annual_vol"] > .10+1e-12:
        reasons.append("ACTUAL_VOL_CAP_BREACH")
    if any(n[k] != 0 for k in ("halt_count","ruin_count","residual_notional","unfilled_risk_count")):
        reasons.append("HALT_RUIN_RESIDUAL_OR_UNFILLED_RISK")
    return {"status":"FAIL" if reasons else "NOT_CERTIFIED_NEEDS_NATIVE_BINDING",
            "metric_gate":"FAIL" if reasons else "NONINCREASE_ON_SUPPLIED_NUMBERS_ONLY",
            "reasons":sorted(set(reasons or ["NEEDS_NATIVE_BINDING"])),
            "native_snapshot_verified":False, "not_a_future_risk_guarantee":True}


def path_metrics(nav):
    """Descriptive generated DAILY path only; minute DD needs minute native NAV."""
    raw=tuple(nav)
    if any(isinstance(x,bool) or not isinstance(x,(int,float,Decimal)) for x in raw):
        raise ValueError("numeric NAV required; booleans forbidden")
    nav = tuple(float(x) for x in raw)
    if len(nav) < 32 or any(not isfinite(x) or x <= 0 for x in nav):
        raise ValueError("at least 32 positive complete daily values required")
    returns = [b/a-1 for a,b in zip(nav,nav[1:])]
    peak, mdd = nav[0],0.
    for n in nav:
        peak=max(peak,n);mdd=max(mdd,1-n/peak)
    losses=sorted((max(0.,-x) for x in returns),reverse=True)
    k=max(1,ceil(.05*len(losses)))
    worst30=max(0.,max(1-nav[i+30]/nav[i] for i in range(len(nav)-30)))
    return {"daily_observed_mdd":mdd,"daily_annual_vol":stdev(returns)*sqrt(365),
            "daily_es95_loss":sum(losses[:k])/k,"worst_30d_loss":worst30}
