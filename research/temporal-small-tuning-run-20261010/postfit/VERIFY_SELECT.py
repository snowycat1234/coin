"""Read-only source-bound six-fit verification and exact reviewed tie selection.

No inference, objective rollout, gradient, optimizer update, or reserved-data read.
Keep outside frozen modules; all fitting sources retain their original identities.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from modules.temporal_small_tuning.checkpoint import binding_for, load, optimizer_for
from modules.temporal_small_tuning.protocol import plan, sources, task
from modules.temporal_two_expert.checkpoint import _atomic_json, _rng_state
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import DAY_US, Standardizer, array_digest, digest
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_episode_weighting_v2.stage import tree_identity


def number(a, b, atol=2e-12):
    if not np.isclose(a, b, rtol=0, atol=atol):
        raise ValueError(f"Independent metric mismatch: {a} != {b}")


def nav_metrics(nav, metrics, n):
    if not np.isfinite(nav).all() or np.any(nav <= 0) or nav[0] != 10000:
        raise ValueError("Finite positive full-wallet NAV with fresh10k required")
    ret = nav[1:] / nav[:-1] - 1
    utility = np.log(nav[1:] / nav[:-1]).sum() - 5 * np.minimum(ret, 0).dot(np.minimum(ret, 0))
    number(nav[-1] - 10000, metrics["net_PnL"])
    number(np.max(1 - nav / np.maximum.accumulate(nav)), metrics["maximum_drawdown"])
    number(utility, metrics["utility_sum"])
    number(-utility / n, metrics["mean_loss"])
    if not metrics["paid_terminal_flat"] or type(metrics["risk_events"]) is not int or metrics["risk_events"] < 0:
        raise ValueError("Paid terminal close and recorded risk-event count required")


def rank(candidates):
    top = max(r["mean_utility_excess"] for r in candidates)
    tied = [r for r in candidates if top-r["mean_utility_excess"] <= 1e-5]
    worst = max(r["worst_utility_excess"] for r in tied)
    # PLAN: tolerance only on mean; exact worst-fold max then fixed candidate order.
    return next(r for r in tied if r["worst_utility_excess"] == worst)


def extension_archive(output, rows):
    path = output / "RUNTIME_EXTENSION_5400.json"
    if not path.exists():
        return dict(applied=False)
    from RUNTIME_EXTENSION import (
        AUTH_COMMIT, AUTH_PUBLIC_PATH, LIMITS, overlay_sources,
        verify_permission, verify_prepared,
    )
    public = Path('/workspace/coin-temporal/research/temporal-small-tuning-run-20261010')
    permission = verify_permission(public/'RUNTIME_EXTENSION_AUTHORIZATION.json',AUTH_COMMIT,AUTH_PUBLIC_PATH)
    prepared = verify_prepared(Path(__file__).parent/'RUNTIME_EXTENSION_PREPARED.json','cb3f8dce53b735581b3c8e87bed3bc3ee0b70a56','research/temporal-small-tuning-run-20261010/runtime-extension/RUNTIME_EXTENSION_PREPARED.json',permission)
    runtime = json.loads(path.read_text())
    archive = output/'RUNTIME_5400_ORIGINALS'
    if runtime != json.loads((archive/'RECEIPT.json').read_text()) or runtime['permission'] != permission or runtime['prepared_receipt'] != prepared or runtime['limits'] != LIMITS or runtime['overlay_sources'] != overlay_sources() or runtime['added_fits'] != 0 or runtime['added_optimizer_updates'] != 0:
        raise ValueError('Exact published unchanged guard-only continuation required')
    for name, record in runtime['original_controller_files'].items():
        p = archive/name
        if sha(p) != record['SHA256'] or p.stat().st_size != record['bytes']:
            raise ValueError('Original controller archive differs')
    checks = []
    for transition in runtime['tasks']:
        task_id = transition['task_id']; backup = archive/task_id; live = output/task_id
        for name, record in transition['archived_files'].items():
            p = backup/name
            if sha(p) != record['SHA256'] or p.stat().st_size != record['bytes']:
                raise ValueError('Original fit archive differs')
            if name.startswith('RESOURCE_SLICE_') or name == 'RUN.json':
                if p.read_bytes() != (live/name).read_bytes():
                    raise ValueError('Earlier resource clock or fitting binding changed')
        before, resumed = transition['previous_pointer'], transition['resumed_pointer']
        if transition['added_optimizer_updates'] != 0 or before['step'] != resumed['step'] or before['model_identity'] != resumed['model_identity'] or before != json.loads((backup/'latest.json').read_text()):
            raise ValueError('Continuation metadata transition changed updates/model identity')
        old = torch.load(backup/before['file'],map_location='cpu',weights_only=True)
        identity = dict(model=digest(dict(contract=old['binding']['specification']['model_contract'],arrays={k:array_digest(v.detach().cpu().numpy()) for k,v in old['model'].items()})),optimizer=tree_identity(old['optimizer']),RNG=tree_identity(old['rng']),training=old['training'])
        if identity != transition['preserved_state_identity'] or identity['model'] != before['model_identity'] or old['step'] != before['step']:
            raise ValueError('Archived original model/Adam/RNG identity differs')
        resources = [json.loads(p.read_text()) for p in sorted(backup.glob('RESOURCE_SLICE_*.json'))]
        if len(resources) != transition['prior_slice_count'] or sum(r['elapsed_seconds'] for r in resources) != transition['prior_resource_seconds']:
            raise ValueError('Earlier cumulative resource clock was reset')
        row = next(r for r in rows if r['task_id'] == task_id)
        resume = [s for s in row['slices'] if s['resumed_update'] == resumed['step'] and s['checkpoint_SHA256'] == resumed['SHA256'] and s['all_RNG_identity'] == identity['RNG']]
        if len(resume) != 1:
            raise ValueError('Exact same-fit checkpoint/RNG continuation not confirmed')
        checks.append(dict(task_id=task_id,resumed_update=resumed['step'],original_model_Adam_RNG_verified=True,earlier_resource_clocks_preserved=True,additional_metadata_optimizer_updates=0))
    return dict(applied=True,guards_only=True,added_fits=0,archives_verified=checks)


def verify(output):
    ready = json.loads((output / "READY.json").read_text())
    if ready["sources"] != sources():
        raise ValueError("All77 original fitting-source identities required")
    receipt, rows = [], []
    for settings in plan()["actual_fit_tasks"]:
        task_id = settings["task_id"]
        folder = output / task_id
        terminal = json.loads((folder / "TERMINAL.json").read_text())
        if terminal["settings"] != task(task_id) or terminal["task_id"] != task_id:
            raise ValueError("Exactly approved fold/candidate settings required")
        if terminal["actual_active_training_dates"] != settings["eligible_dates"]:
            raise ValueError("Exact653/744active-date folds required")
        if terminal["status"] not in {
            "EARLY_STOP_RULE", "UPDATE_CAP_NOT_CONVERGENCE", "CUMULATIVE_RESOURCE_CAP"
        } or terminal["best"] is None or terminal["failure"] is not None:
            raise ValueError("All six admissible terminal fit results required")
        with np.load(folder / "SCALER.npz", allow_pickle=False) as z:
            meta = json.loads((folder / "SCALER.json").read_text())
            scaler = Standardizer(z["mean"], z["scale"], z["count"], meta["provenance"])
        if scaler.identity != meta["identity"]:
            raise ValueError("Exact train-only scaler required")
        model, _ = initialize(scaler)
        binding = json.loads((folder / "RUN.json").read_text())
        if binding != binding_for(model, binding["specification"]["data_split_identity"], settings):
            raise ValueError("Original fresh/source/data/optimizer binding required")
        optimizer = optimizer_for(model, settings)
        initial, _ = load(folder, model, optimizer, binding, name="INITIAL.json")
        r = ready["tasks"][task_id]
        if initial["step"] != 0 or optimizer.state or parameter_identity(model) != r["raw_parameter_identity"] or tree_identity(_rng_state()) != r["all_RNG_identity"]:
            raise ValueError("Matched fresh step0 model/emptyAdam/allRNG required")
        saved, p = load(folder, model, optimizer, binding)
        h = saved["trainer_state"]
        if terminal["latest"] != p or terminal["completed_updates"] != saved["step"] or terminal["optimizer_all_parameter_ages"] != saved["step"] or h["status"] != terminal["status"]:
            raise ValueError("Terminal/checkpoint/status/update ages differ")
        if terminal["validation"] != h["validation"] or terminal["best"] != h["best"] or terminal["slices"] != h["slices"]:
            raise ValueError("Terminal history differs from durable source-bound snapshot")
        if terminal["reserve_read"] or terminal["native_wallets"] or model.parameter_count != 13699:
            raise ValueError("Frozen non-native/no-reserve13699 contract required")
        with np.load(folder / "CONTROL_NAV.npz", allow_pickle=False) as z:
            d = z["decision_us"]
            if d.shape != (63,) or not np.all(np.diff(d) == DAY_US):
                raise ValueError("Unspliced63decision/62active development chronology required")
            for name, metrics in h["controls"].items():
                nav_metrics(z[name], metrics, 63)
        best, stale, expected_stop = None, 0, None
        checked = []
        for v in h["validation"]:
            if v["step"] != plan()["selection"]["checkpoints"][len(checked)] or v["step"] > saved["step"]:
                raise ValueError("Ordered scheduled validation checkpoints required")
            j = folder / f"VALIDATION_{v['step']:04d}.json"
            a = folder / f"VALIDATION_{v['step']:04d}.npz"
            if json.loads(j.read_text()) != v or v["controls"] != h["controls"] or not v["deterministic_eval"] or v["reserve_read"]:
                raise ValueError("Original deterministic validation receipt required")
            with np.load(a, allow_pickle=False) as z:
                request, nav = z["requests"], z["nav"]
                if not np.array_equal(z["decision_us"], d) or request.shape != (63, 6) or nav.shape != (64,):
                    raise ValueError("Original full chronological development path required")
                if not np.isfinite(request).all() or np.any(request < 0) or np.any(request > 1) or np.any(request[:, [2,3]] != 0) or not np.allclose(request.sum(1), 1, rtol=0, atol=1e-12):
                    raise ValueError("Finite canonical masked simplex required")
                if not np.allclose(request.mean(0), v["metrics"]["requests_mean"], rtol=0, atol=1e-12):
                    raise ValueError("Recorded mean request differs")
                nav_metrics(nav, v["metrics"], 63)
            number(v["utility_excess"], v["metrics"]["utility_sum"]-h["controls"]["FROZEN_VOL"]["utility_sum"])
            number(v["primary_PnL_excess"], v["metrics"]["net_PnL"]-h["controls"]["FROZEN_VOL"]["net_PnL"])
            improvement = float("inf") if best is None else v["utility_excess"]-best["utility_excess"]
            stale = 0 if improvement > 1e-5 else stale+1
            if best is None or v["utility_excess"] > best["utility_excess"]:
                best = v
            if v["step"] >= 512 and stale >= 3:
                if expected_stop is not None:
                    raise ValueError("Evaluation continued after frozen early stop")
                expected_stop = v["step"]
            checked.append(dict(step=v["step"], json_SHA256=sha(j), npz_SHA256=sha(a)))
        if best != h["best"] or stale != h["stale_checks"]:
            raise ValueError("Independent best/stale replay differs")
        if terminal["status"] == "EARLY_STOP_RULE" and expected_stop != saved["step"]:
            raise ValueError("Incorrect frozen early stop")
        if terminal["status"] == "UPDATE_CAP_NOT_CONVERGENCE" and (saved["step"] != 1024 or expected_stop is not None):
            raise ValueError("Incorrect1024cap status")
        if terminal["status"] == "CUMULATIVE_RESOURCE_CAP":
            proof = folder / "CAP_FINALIZATION.json"
            if not proof.exists() or json.loads(proof.read_text())["additional_optimizer_updates"] != 0:
                raise ValueError("Explicit zero-update resource-cap finalization proof required")
            cap = json.loads(proof.read_text())
            original = folder / cap["original_body_archive"]
            if sha(original) != cap["previous_latest"]["SHA256"] or cap["latest"] != p:
                raise ValueError("Exact original capped snapshot bytes required")
            old = torch.load(original,map_location="cpu",weights_only=True)
            if old["binding"] != binding or old["step"] != saved["step"] or any(tree_identity(old[k]) != tree_identity(saved[k]) for k in ("model","optimizer","rng")) or old["training"] != saved["training"]:
                raise ValueError("Cap finalization changed completed model/Adam/RNG state")
        best_state, bp = load(folder, model, optimizer, binding, name="BEST.json")
        if bp["step"] != best["step"] or bp["model_identity"] != best["model_identity"] or best_state["trainer_state"]["best"] != best:
            raise ValueError("BEST pointer/weights/validation identity differs")
        snapshots = dict(initial=r["initial_pointer"], latest=p, best=bp)
        if saved["step"] >= 512:
            _, mp = load(folder, model, optimizer, binding, name="MATCHED512.json")
            if mp["step"] != 512 or mp["model_identity"] != next(v["model_identity"] for v in h["validation"] if v["step"] == 512):
                raise ValueError("Matched512 snapshot differs")
            snapshots["matched512"] = mp
        resources = [json.loads(q.read_text()) for q in sorted(folder.glob("RESOURCE_SLICE_*.json"))]
        receipt.append(dict(task_id=task_id, completed_updates=saved["step"], status=terminal["status"], parameters=13699, snapshots=snapshots, validations=checked, guard_elapsed_seconds=sum(z["elapsed_seconds"] for z in resources), resource_slices=resources, exact_resume_slices=h["slices"]))
        rows.append(terminal)
    candidates = []
    for name in plan()["candidate_settings"]:
        pairs = [r for r in rows if r["settings"]["candidate"] == name]
        if len(pairs) != 2:
            raise ValueError("Both frozen folds required for every candidate")
        scores = [r["best"]["utility_excess"] for r in pairs]
        candidates.append(dict(candidate=name, mean_utility_excess=float(np.mean(scores)), worst_utility_excess=min(scores), best_updates=[r["best"]["step"] for r in pairs], folds={r["settings"]["fold"]:r["best"] for r in pairs}))
    selected = rank(candidates)
    result = dict(status="SIX_FITS_COMPLETE_VERIFIED_REVIEWED_SELECTION_RESERVE_NOT_READ", candidates=candidates, selected=selected, selected_settings=plan()["candidate_settings"][selected["candidate"]], later_full773_refit_steps=max(256,int(np.floor(np.median(selected["best_updates"])))), later_full773_refit="NOT_RUN", actual_fits=6, total_completed_updates=sum(r["completed_updates"] for r in rows), all_fit_results=rows, reserve_results_read=False, no_convergence_claim=True, no_promotion=True, exact_worst_fold_tie_break=True)
    verification = dict(status="PASS", source_count=len(sources()), fitting_sources_unchanged=True, fits=receipt, runtime_extension=extension_archive(output,rows), independent_NAV_metric_checks=True, all_Adam_parameter_ages_verified=True, matched_fresh_initialization_verified=True, scheduled_early_stop_replayed=True, canonical_output_mask_verified=True, optimizer_updates=0, model_inferences=0, wallet_rollouts=0, reserve_read=False, script_SHA256=sha(Path(__file__)), selected=result["selected"], later_full773_refit_steps=result["later_full773_refit_steps"])
    _atomic_json(output / "VERIFIED_RESULT.json", result)
    _atomic_json(output / "VERIFICATION.json", verification)
    return dict(status="PASS", selected=selected["candidate"], later_full773_refit_steps=result["later_full773_refit_steps"], actual_updates=result["total_completed_updates"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    print(json.dumps(verify(args.output),allow_nan=False))
