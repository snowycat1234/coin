"""Read-only frozen-model input/gradient diagnosis; no fits or optimizer steps."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from modules.temporal_two_expert.feature_windows import load_feature_inputs, TRAINING_CUTOFF_US
from modules.temporal_two_expert.development_inputs import load_development_inputs
from modules.temporal_two_expert.inputs import FEATURE_NAMES, Standardizer, fit_standardizer
from modules.temporal_two_expert.model import Selector, predict_windows
from modules.temporal_two_expert.exact import load_prototype
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, request_loss_and_gradient_v2


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def summary(x):
    return dict(n=int(x.size), min=float(x.min()), median=float(np.median(x)),
                max=float(x.max()), mean=float(x.mean()), std=float(x.std()))


def gradient_summary(model):
    return {name: dict(norm=float(p.grad.norm()), max_abs=float(p.grad.abs().max()),
                      nonzero=int(torch.count_nonzero(p.grad)), size=p.numel())
            for name, p in model.named_parameters()}


def activation_stats(model, windows):
    collected = {k: [] for k in ('encoder_state', 'joint_preactivation', 'readout_logit')}
    handles = [model.encoder.register_forward_hook(
        lambda mod, ins, out: collected['encoder_state'].append(
            (out[1][0] if model.family == 'GRU64' else out).detach().numpy().ravel())),
        model.joint.register_forward_hook(lambda mod, ins, out:
            collected['joint_preactivation'].append(out.detach().numpy().ravel())),
        model.w_head.register_forward_hook(lambda mod, ins, out:
            collected['readout_logit'].append(out.detach().numpy().ravel()))]
    with torch.no_grad():
        requests = predict_windows(model, windows).numpy()
    for handle in handles:
        handle.remove()
    result = {}
    for key, parts in collected.items():
        x = np.concatenate(parts)
        result[key] = summary(x)
        result[key]['fraction_abs_over_3'] = float(np.mean(np.abs(x) > 3))
        if key == 'encoder_state':
            result[key]['fraction_abs_over_0_99'] = float(np.mean(np.abs(x) > .99))
    w = requests[:, 4]
    result['CS_weight'] = summary(w)
    result['CS_weight'].update(below_0_01=int(np.sum(w < .01)), above_0_99=int(np.sum(w > .99)),
                               sigmoid_derivative=summary(w * (1 - w)))
    return result, requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--requests-root', type=Path, required=True)
    parser.add_argument('--prototype', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    evidence = args.evidence
    source_root = Path(__import__('modules.temporal_two_expert.model', fromlist=['Selector']).__file__).resolve().parents[2]
    source_hashes = {name: sha(source_root / 'modules/temporal_two_expert' / name) for name in ('model.py', 'inputs.py', 'checkpoint.py')}
    assert source_hashes == {'model.py': '6ab473b139356c750457991961758bdd450e872d1779d58cfa7a9e09b50ef8a2',
        'inputs.py': 'e9b175aadede32539eefc25cc64c4d98964e7e2b166278f972c41f1dedcffcf5',
        'checkpoint.py': '2a12ed501542e31d3d1e5cf8020a901b2e79a241faa851ca40055fc904f0daef'}
    base = load_feature_inputs(evidence / 'CORE5_PRE_MAY2024.npz', evidence / 'FEATURE_MANIFEST.json')
    dev = load_development_inputs(base, evidence / 'DEV_FEATURES.npz', evidence / 'DEV_FEATURE_MANIFEST.json')
    economic = read_npz(evidence / 'TRAIN_ECONOMIC_CONTEXTS.npz')
    assert sha(evidence / 'TRAIN_ECONOMIC_CONTEXTS.npz') == '66c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676'
    episodes = [base.windows(economic['decision_us'][economic['episode_id'] == i])
                for i in np.unique(economic['episode_id'])]
    train_windows = base.windows(economic['decision_us'])
    dev_windows = dev.windows(dev.decision_us)
    provenance = json.loads((args.requests_root / 'V2_GRU64_NO_CASH' / 'RUN.json').read_text())['specification']['model_contract']['normalization_provenance']
    saved_scaler = read_npz(evidence / 'SCALER.npz')
    scaler = Standardizer(saved_scaler['mean'], saved_scaler['scale'], saved_scaler['count'], provenance)
    recomputed = fit_standardizer(episodes, training_cutoff_us=TRAINING_CUTOFF_US)
    assert recomputed.identity == scaler.identity
    rows = np.unique(np.concatenate([w.completed_us.ravel() for w in episodes]))
    train_rows = np.searchsorted(base.timeline.completed_us, rows)
    dev_rows = np.searchsorted(dev.timeline.completed_us, dev.decision_us)
    feature_stats = {}
    for j, name in enumerate(FEATURE_NAMES):
        stats = {}
        for role, timeline, indices in [('training_unique', base.timeline, train_rows), ('development_latest', dev.timeline, dev_rows)]:
            x = timeline.values[indices, :, j]
            valid = timeline.valid[indices, :, j]
            observed = x[valid].astype(np.float64)
            z = (observed - scaler.mean[j]) / scaler.scale[j]
            stats[role] = dict(valid=int(valid.sum()), total=int(valid.size), raw=summary(observed),
                               standardized=summary(z), max_abs_z=float(np.abs(z).max()),
                               fraction_abs_z_over_5=float(np.mean(np.abs(z) > 5)),
                               distinct_values=int(np.unique(observed).size))
            stats[role]['raw_quantiles'] = {str(q): float(np.quantile(observed, q)) for q in (.01, .05, .5, .95, .99)}
            coordinates = np.argwhere(valid)
            extremes = np.argsort(np.abs(z))[-3:][::-1]
            stats[role]['three_largest_abs_z'] = [dict(
                completed_us=int(timeline.completed_us[indices[coordinates[k, 0]]]),
                symbol=timeline.symbol_order[coordinates[k, 1]], raw=float(observed[k]),
                z=float(z[k]), share_role_squared_deviations=float(z[k] ** 2 / np.sum(z ** 2)))
                for k in extremes]
        feature_stats[name] = stats
    fragment = read_npz(evidence / 'H1_VALIDATE.npz')
    np.testing.assert_array_equal(fragment['decision_us'], dev.decision_us)
    prototype = load_prototype(args.prototype)
    contexts = []
    for i, clock in enumerate(fragment['decision_us']):
        targets = np.zeros((5, 5)); eligible = np.zeros(5, dtype=bool)
        targets[[0, 1, 4]] = fragment['expert_targets'][i, [0, 1, 4]]
        eligible[[0, 1, 4]] = fragment['expert_eligible'][i, [0, 1, 4]]
        contexts.append(prototype.Context(int(clock), int(clock), targets, eligible,
            fragment['past_returns30'][i], fragment['market_state13'][i], fragment['target_available_us'][i]))
    episode = SimpleNamespace(contexts=tuple(contexts), prices=fragment['prices'], funding_coeff=fragment['funding_coeff'])
    arms = {}
    for family in ('GRU64', 'LATEST_MLP'):
        name = 'V2_' + family + '_NO_CASH'; folder = args.requests_root / name
        manifest = json.loads((folder / 'MANIFEST.json').read_text())
        snapshot_file = folder / 'MODEL_ADAM_RNG.pt'
        assert sha(snapshot_file) == manifest['model_sha256']
        snapshot = torch.load(snapshot_file, weights_only=True, map_location='cpu')
        model = Selector(scaler, family=family, cash_enabled=False, zero_readout=True)
        model.load_state_dict(snapshot['model']); model.eval()
        assert model.contract == snapshot['binding']['specification']['model_contract']
        observed_shapes = []
        handle = model.encoder.register_forward_pre_hook(lambda mod, ins: observed_shapes.append(list(ins[0].shape)))
        dev_stats, requests = activation_stats(model, dev_windows)
        handle.remove()
        expected = read_npz(folder / 'REQUESTS.npz')['desired_expert_budget']
        np.testing.assert_array_equal(requests, expected)
        train_stats, _ = activation_stats(model, train_windows)
        loss, vjp, _ = request_loss_and_gradient_v2(requests, episode, prototype, plan=BoundaryPlan.full_fill_diagnostic(61))
        model.zero_grad(set_to_none=True)
        predicted = predict_windows(model, dev_windows)
        (predicted * torch.tensor(vjp)).sum().backward()
        gradients = gradient_summary(model)
        # Check neural VJP, including the encoder, against a read-only objective FD.
        fd = {}
        for parameter_name in ('encoder.weight_ih_l0' if family == 'GRU64' else 'encoder.0.weight', 'w_head.weight'):
            parameter = dict(model.named_parameters())[parameter_name]
            index = tuple(np.unravel_index(int(parameter.grad.abs().argmax()), tuple(parameter.shape)))
            analytic = float(parameter.grad[index]); original = float(parameter[index].detach()); eps = 1e-5
            objectives = []
            for sign in (1, -1):
                with torch.no_grad():
                    parameter[index] = original + sign * eps
                    out = predict_windows(model, dev_windows).numpy()
                objectives.append(request_loss_and_gradient_v2(out, episode, prototype, plan=BoundaryPlan.full_fill_diagnostic(61))[0])
            with torch.no_grad(): parameter[index] = original
            numeric = (objectives[0] - objectives[1]) / (2 * eps)
            assert abs(numeric - analytic) < 2e-9, (family, parameter_name, numeric, analytic)
            fd[parameter_name] = dict(index=[int(i) for i in index], analytic=analytic, finite_difference=numeric, absolute_error=abs(numeric - analytic))
        initial = Selector(scaler, family=family, cash_enabled=False, zero_readout=True); initial.eval()
        initial_requests = predict_windows(initial, dev_windows)
        (initial_requests * torch.tensor(vjp)).sum().backward()
        arms[name] = dict(snapshot_SHA256=sha(snapshot_file), parameter_count=model.parameter_count,
            encoder_input_shapes=observed_shapes, exact_export_reproduction=True,
            training_activations=train_stats, development_activations=dev_stats,
            development_objective_loss=loss, terminal_gradients=gradients,
            initial_zero_readout_gradients=gradient_summary(initial), parameter_finite_differences=fd,
            cumulative_Adam_step=snapshot['step'], terminal_status=manifest['terminal_training_status'])
    result = dict(status='PASS_READ_ONLY_INPUT_CONFIGURATION_DIAGNOSIS', source_commit='316423e2b4174bbf072814c1627861469a2e952b',
        snapshot_commit='2bf2dc03e1ca3f0594b7b15dcff0cdb5651c5f1d', source_SHA256=source_hashes,
        artifact_SHA256={p.name: sha(p) for p in [evidence / x for x in ('CORE5_PRE_MAY2024.npz', 'DEV_FEATURES.npz', 'SCALER.npz', 'TRAIN_ECONOMIC_CONTEXTS.npz')]},
        scaler_reproduction_identity=scaler.identity, scaler_provenance=provenance,
        train_window_count=len(train_windows.values), development_window_count=len(dev_windows.values),
        unique_training_rows=len(rows), latest_training_row_us=int(rows[-1]),
        training_economic_alignment=dict(
            maximum_target_available_minus_decision_us=int(np.max(economic['target_available_us'] - economic['decision_us'][:, None])),
            first_execution_minus_decision_us=summary(economic['start_execution_us'] - economic['decision_us']),
            last_training_outcome_available_us=int(economic['end_execution_us'].max()),
            maximum_feature_available_minus_completed_us=int(np.max(train_windows.available_us[train_windows.valid] - np.broadcast_to(train_windows.completed_us[..., None, None], train_windows.values.shape)[train_windows.valid]))),
        training_all64_CORE5_observed=int(train_windows.step_valid.all((1, 2)).sum()),
        development_all64_CORE5_observed=int(dev_windows.step_valid.all((1, 2)).sum()),
        all_training_feature_masks_true=bool(train_windows.valid.all()), all_development_feature_masks_true=bool(dev_windows.valid.all()),
        feature_stats=feature_stats, arms=arms, model_fits=0, optimizer_steps=0, historical_native_wallets=0)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('feature_stats', 'arms')}))
    for name, arm in arms.items():
        print(name, json.dumps({k: v for k, v in arm.items() if k not in ('initial_zero_readout_gradients', 'terminal_gradients', 'training_activations')}))


if __name__ == '__main__':
    main()
