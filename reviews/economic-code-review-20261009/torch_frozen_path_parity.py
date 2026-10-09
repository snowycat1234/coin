"""Torch/reference parity on two exported requests; no model or native wallet run."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import torch

from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, request_loss_and_gradient_v2
from modules.temporal_two_expert.exact import load_prototype, sha


def imported(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('requests-root', 'fragment', 'prototype', 'reference', 'native-helper', 'results', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    assert sha(args.fragment) == 'c13de3125698f1fc350d1435453cbb6e33b7d5873537d7f859c1570344f081bc'
    assert sha(args.reference) == '2327fc143824b99a4359580054a9f52b090fa7bbb0022f7c8f029086e1dd7062'
    assert sha(args.native_helper) == '61a38b3432b8df39d87ac873fe375ee0bf57827a9ceb94b70e20a7156362e63c'
    imported('native61', args.native_helper)
    reference = imported('independent_v2_same_path_reference', args.reference)
    prototype = load_prototype(args.prototype)
    with np.load(args.fragment, allow_pickle=False) as z:
        a = {k: z[k].copy() for k in z.files}
    contexts = []
    for i, d in enumerate(a['decision_us']):
        targets = np.zeros((5, 5))
        eligible = np.zeros(5, dtype=bool)
        targets[[0, 1, 4]] = a['expert_targets'][i, [0, 1, 4]]
        eligible[[0, 1, 4]] = a['expert_eligible'][i, [0, 1, 4]]
        contexts.append(prototype.Context(int(d), int(d), targets, eligible,
            a['past_returns30'][i], a['market_state13'][i], a['target_available_us'][i]))
    episode = SimpleNamespace(contexts=tuple(contexts), prices=a['prices'], funding_coeff=a['funding_coeff'])
    saved = json.loads(args.results.read_text())
    arms = {}
    identities = {
        'V2_GRU64_NO_CASH': 'ab7fe0400dec7908b11de314e4372e058ccaf85b54b482d662175ee9eb6489ac',
        'V2_LATEST_MLP_NO_CASH': '383dcebd34b62f6f6b9f73527cc7b41c6018b698d39c2038e7ee633d05bf72a2',
    }
    for name, identity in identities.items():
        file = args.requests_root / name / 'REQUESTS.npz'
        assert sha(file) == identity
        with np.load(file, allow_pickle=False) as z:
            requests = z['desired_expert_budget'].copy()
            np.testing.assert_array_equal(z['decision_us'], a['decision_us'])
        targets, _ = prototype.mapped_path(requests, contexts)
        target_sha = hashlib.sha256(targets.tobytes()).hexdigest()
        registered = saved['accounts'][name]['same_path_v2_proxy']
        assert target_sha == registered['exact_saved_native_target_bytes_SHA256']
        expected = reference.boundary_reference(targets, a['prices'], a['funding_coeff'])
        loss, gradient, actual = request_loss_and_gradient_v2(
            requests, episode, prototype, plan=BoundaryPlan.full_fill_diagnostic(61))
        nav_error = float(np.max(np.abs(actual['nav'].detach().numpy() - expected['nav'])))
        utility_error = abs(float(actual['utility_sum'].detach()) - expected['utility_sum'])
        assert nav_error < 3e-9 and utility_error < 1e-12
        assert abs(loss + expected['utility_sum'] / 61) < 2e-14
        assert abs(float(actual['net_PnL'].detach()) - registered['proxy_net_PnL_USDT']) < 3e-9
        scalar_errors = {field: abs(float(actual[field].detach()) - expected[field])
                         for field in ('fees', 'spread', 'slippage', 'funding', 'charged_reduction_cost')}
        assert max(scalar_errors.values()) < 3e-9
        assert len(actual['risk_events']) == len(expected['risk_events'])
        fd_error, logit_error = 0., 0.
        for t in range(60):
            epsilon = min(1e-5, float(requests[t, [1, 4]].min()) / 4)
            assert epsilon > 0
            utilities = []
            for direction in (1, -1):
                perturbed = requests.copy()
                perturbed[t, 1] += direction * epsilon
                perturbed[t, 4] -= direction * epsilon
                path, _ = prototype.mapped_path(perturbed, contexts)
                report = reference.boundary_reference(path, a['prices'], a['funding_coeff'])
                assert len(report['risk_events']) == len(expected['risk_events'])
                utilities.append(report['utility_sum'])
            numeric = -(utilities[0] - utilities[1]) / (2 * epsilon * 61)
            analytic = gradient[t, 1] - gradient[t, 4]
            fd_error = max(fd_error, abs(numeric - analytic))
            assert abs(numeric - analytic) < 5e-8, (name, t, epsilon, numeric, analytic)
            # The neural pair uses a sigmoid logit. Its constant-size step avoids
            # cancellation from tiny legal simplex perturbations near saturation.
            logit = np.log(requests[t, 4] / requests[t, 1])
            utilities = []
            for direction in (1, -1):
                perturbed = requests.copy()
                w = 1 / (1 + np.exp(-(logit + direction * 1e-4)))
                perturbed[t, 1], perturbed[t, 4] = 1 - w, w
                path, _ = prototype.mapped_path(perturbed, contexts)
                report = reference.boundary_reference(path, a['prices'], a['funding_coeff'])
                assert len(report['risk_events']) == len(expected['risk_events'])
                utilities.append(report['utility_sum'])
            numeric = -(utilities[0] - utilities[1]) / (2e-4 * 61)
            analytic = requests[t, 1] * requests[t, 4] * (gradient[t, 4] - gradient[t, 1])
            logit_error = max(logit_error, abs(numeric - analytic))
            assert abs(numeric - analytic) < 2e-10, (name, t, numeric, analytic)
        arms[name] = dict(
            request_SHA256=identity, targets_SHA256=target_sha,
            Torch_net_PnL_USDT=float(actual['net_PnL'].detach()),
            NumPy_reference_net_PnL_USDT=float(expected['nav'][-1] - 10000),
            native_net_PnL_USDT=saved['accounts'][name]['net_PnL_USDT'],
            maximum_NAV_error_USDT=nav_error, utility_sum_absolute_error=utility_error,
            scalar_absolute_errors=scalar_errors, risk_events=len(actual['risk_events']),
            finite_differences=60, maximum_request_gradient_absolute_error=fd_error,
            sigmoid_logit_finite_differences=60, maximum_logit_gradient_absolute_error=logit_error,
            terminal_cash_realized=actual['terminal_cash_realized'])
    report = dict(status='PASS_TORCH_VS_INDEPENDENT_NUMPY_ON_EXACT_SAVED_NATIVE_TARGET_BYTES',
        exported_requests_commit='2bf2dc03e1ca3f0594b7b15dcff0cdb5651c5f1d',
        native_reference_commit='6cd153bb57ca3e238ac207124ca5ec45f2ec02bd',
        reference_SHA256=sha(args.reference), arms=arms,
        model_loads=0, model_fits=0, historical_native_wallets=0, journal_downloads=0)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
