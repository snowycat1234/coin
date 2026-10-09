"""Small independent accounting/finite-difference audit; no optimizer or market reads."""
import argparse
import json
from decimal import Decimal, getcontext
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, request_loss_and_gradient_v2
from modules.temporal_two_expert.exact import load_prototype

getcontext().prec = 48
torch.set_num_threads(1)
D = lambda x: Decimal(str(float(x)))
ZERO = Decimal(0)
ONE = Decimal(1)


def scalar_targets(requests, contexts):
    prior = [ONE, ZERO, ZERO, ZERO, ZERO]
    result = []
    for index, (request, context) in enumerate(zip(requests, contexts, strict=True)):
        old, wanted = list(prior), list(map(D, request))
        for expert, eligible in enumerate(context.eligible):
            if not eligible:
                old[0] += old[expert]
                old[expert] = ZERO
                wanted[0] += wanted[expert]
                wanted[expert] = ZERO
        distance = sum(abs(b - a) for a, b in zip(old, wanted, strict=True))
        fraction = min(ONE, Decimal('.1') / distance) if distance else ONE
        prior = [a + fraction * (b - a) for a, b in zip(old, wanted, strict=True)]
        target = [sum(prior[k] * D(context.expert_targets[k, j]) for k in range(5))
                  for j in range(5)]
        result.append(target if index + 1 < len(requests) else [ZERO] * 5)
    return result


def decimal_path(targets, prices, funding):
    nav = Decimal(10000)
    carry = [ZERO] * 5
    path, utility, risk_events = [nav], ZERO, 0
    totals = dict(fees=ZERO, spread=ZERO, slippage=ZERO, funding=ZERO)
    for t, target in enumerate(targets):
        begin = nav
        p0, p1, f = list(map(D, prices[t])), list(map(D, prices[t + 1])), list(map(D, funding[t]))
        q = [Decimal('.99') * nav * w / p for w, p in zip(target, p0, strict=True)]

        def charge(new, old, mids):
            nonlocal nav
            for a, b, p in zip(new, old, mids, strict=True):
                delta = a - b
                # Direct adverse execution price and execution fee; no production cost helper.
                execution = p * (ONE + (ONE if delta > 0 else -ONE if delta < 0 else ZERO) * Decimal('.0008'))
                fee = abs(delta) * execution * Decimal('.00055')
                friction = abs(delta) * p * Decimal('.0004')
                nav -= fee + 2 * friction
                totals['fees'] += fee
                totals['spread'] += friction
                totals['slippage'] += friction

        charge(q, carry, p0)
        paid = -sum(a * b for a, b in zip(q, f, strict=True))
        totals['funding'] += paid
        nav += sum(a * (b - c) for a, b, c in zip(q, p1, p0, strict=True)) + paid
        notionals = [abs(a) * b for a, b in zip(q, p1, strict=True)]
        if max(notionals) > Decimal('.3') * nav + Decimal('1e-8') or sum(notionals) > Decimal('.6') * nav + Decimal('1e-8'):
            scale = min(ONE, Decimal('.297') * nav / max(notionals), Decimal('.594') * nav / sum(notionals))
            reduced = [a * scale for a in q]
            charge(reduced, q, p1)
            carry = reduced
            risk_events += 1
        else:
            carry = q
        ratio = nav / begin
        utility += ratio.ln() - Decimal(5) * min(ratio - ONE, ZERO) ** 2
        path.append(nav)
    return dict(nav=np.array(list(map(float, path))), utility=float(utility),
                risk_events=risk_events, **{k: float(v) for k, v in totals.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prototype', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prototype = load_prototype(args.prototype)
    rng = np.random.default_rng(94171)
    max_forward, max_gradient, checks, releases, reductions = 0., 0., 0, 0, 0
    for trial in range(12):
        n = 12
        logits = rng.normal(0, 1, (n, 3))
        def requests(z):
            scores = np.exp(z - z.max(1, keepdims=True))
            weights = scores / scores.sum(1, keepdims=True)
            full = np.zeros((n, 5)); full[:, [0, 1, 4]] = weights
            return full
        contexts = []
        for t in range(n):
            targets = np.zeros((5, 5))
            targets[1] = [.13, .10, .08, .05, .04]
            targets[4] = [-.12, .10, -.05, .04, .03]
            eligible = np.array([True, True, False, False, True])
            if t in (5, 9):
                eligible[1 if t == 5 else 4] = False
                releases += 1
            decision = int((20000 + t) * prototype.DAY_US)
            contexts.append(prototype.Context(decision, decision, targets, eligible,
                np.zeros((30, 5)), np.zeros(13), np.full(5, decision, np.int64)))
        prices = 100 * np.exp(np.cumsum(rng.normal(0, .03, (n + 1, 5)), axis=0))
        funding = rng.uniform(-.02, .02, (n, 5))
        e = SimpleNamespace(contexts=tuple(contexts), prices=prices, funding_coeff=funding)
        request = requests(logits)
        plan = BoundaryPlan.full_fill_diagnostic(n)
        loss, grad, actual = request_loss_and_gradient_v2(request, e, prototype, plan=plan)
        expected = decimal_path(scalar_targets(request, contexts), prices, funding)
        error = float(np.max(np.abs(actual['nav'].detach().numpy() - expected['nav'])))
        max_forward = max(max_forward, error)
        assert error < 2e-9
        assert abs(loss + expected['utility'] / n) < 2e-13
        for field in ('fees', 'spread', 'slippage', 'funding'):
            assert abs(float(actual[field].detach()) - expected[field]) < 2e-9
        for t in (0, 3, 5, 7, 9, 10):
            for k in range(3):
                step = 1e-5
                up, down = logits.copy(), logits.copy()
                up[t, k] += step; down[t, k] -= step
                plus = decimal_path(scalar_targets(requests(up), contexts), prices, funding)['utility']
                minus = decimal_path(scalar_targets(requests(down), contexts), prices, funding)['utility']
                numeric = -(plus - minus) / (2 * step * n)
                w = request[t, [0, 1, 4]]
                g = grad[t, [0, 1, 4]]
                analytic = w[k] * (g[k] - g @ w)
                difference = abs(numeric - analytic)
                max_gradient = max(max_gradient, difference)
                assert difference < 3e-9, (trial, t, k, numeric, analytic)
                checks += 1
    # Separate high-gross long and short cases exercise charged drift reductions.
    from modules.temporal_risk_proxy_v2.proxy import charged_boundary_path
    for side in (1, -1):
        target = np.array([[side * .118] * 5, [side * .08] * 5, [0.] * 5])
        prices = np.array([[100.] * 5, [120.] * 5, [118.] * 5, [117.] * 5])
        funding = np.tile([.011, -.006, .004, -.001, .003], (3, 1))
        actual = charged_boundary_path(torch.tensor(target, dtype=torch.float64), prices, funding,
                                      plan=BoundaryPlan.full_fill_diagnostic(3))
        expected = decimal_path([list(map(D, row)) for row in target], prices, funding)
        error = float(np.max(np.abs(actual['nav'].numpy() - expected['nav'])))
        max_forward = max(max_forward, error)
        assert error < 2e-9
        assert len(actual['risk_events']) == expected['risk_events'] > 0
        reductions += len(actual['risk_events'])
    result = dict(status='PASS', synthetic_wallets=14, request_logit_finite_differences=checks,
                  forced_availability_releases=releases, signed_drift_reductions=reductions,
                  max_Decimal_NAV_error_USDT=max_forward, max_gradient_absolute_error=max_gradient,
                  real_fits=0, native_backtests=0, market_reads=0)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
