"""Read-only terminal model/path receipt; no optimizer updates or native wallets."""

import hashlib, json, shutil, zipfile
from pathlib import Path
import numpy as np
import torch
from modules.temporal_two_expert.checkpoint import load_checkpoint, make_optimizer, model_identity
from modules.temporal_two_expert.comparison import ARMS, PROTOCOL
from modules.temporal_two_expert.exact import sha, request_loss_and_gradient
from modules.temporal_two_expert.inputs import Standardizer
from modules.temporal_two_expert.model import Selector, predict_windows
from modules.temporal_two_expert.training_packet import load_packet


def main():
    s = Path("/workspace/coin-state/work/temporal-two-expert-20261009")
    root = s / "four-fit"
    out = Path("research/temporal-four-fit-20261009/results")
    if out.exists():
        raise FileExistsError("Immutable new results destination required")
    barrier = json.loads((root / "ALL_FOUR_TERMINAL.json").read_text())
    original = json.loads((root / "DEVELOPMENT_RESULTS.json").read_text())
    train, dev, prototype, identity = load_packet(
        s / "FROZEN_PACKET.json",
        sha(s / "FROZEN_PACKET.json"),
        s / "recovery/source/modules/direct_path/prototype.py",
    )
    proof = json.loads((root / "SCALER.json").read_text())
    assert sha(root / "SCALER.npz") == proof["SHA256"]
    with np.load(root / "SCALER.npz", allow_pickle=False) as z:
        scaler = Standardizer(z["mean"], z["scale"], z["count"], proof["provenance"])
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    out.mkdir(parents=True)
    pack = s / "terminal-public-pack"
    pack.mkdir()
    arrays = {}
    reports = {}
    snapshots = {}
    for family, cash in ARMS:
        name = family + ("_WITH_CASH" if cash else "_NO_CASH")
        folder = root / name
        binding = json.loads((folder / "RUN.json").read_text())
        pointer = json.loads((folder / "latest.json").read_text())
        model = Selector(
            scaler,
            family=family,
            cash_enabled=cash,
            dropout=PROTOCOL["dropout"],
            seed=PROTOCOL["seed"],
            zero_readout=True,
        )
        saved = load_checkpoint(folder, model, make_optimizer(model), binding)
        model.eval()
        assert saved["model_identity"] == barrier["terminal"][name]["model_identity"]
        assert saved["trainer_state"]["status"] in (
            "TRAIN_CONVERGENCE_CRITERION_MET",
            "CAPPED_NOT_CONVERGED",
            "STOP_PROXY_EXPOSURE_BREACH",
        )
        before = model_identity(model)
        wallets = []
        for episode in (*train, *dev):
            with torch.no_grad():
                requests = predict_windows(
                    model, episode.windows, feature_batch_size=PROTOCOL["feature_batch_size"]
                ).numpy()
            targets, records = prototype.mapped_path(requests, episode.contexts)
            try:
                loss, gradient, report = request_loss_and_gradient(requests, episode, prototype)
            except prototype.ProxyExposureBreach as error:
                detail = dict(
                    wallet_id=episode.wallet_id,
                    role=episode.role,
                    decisions=len(episode.contexts),
                    loss=None,
                    net_PnL=None,
                    status="STOP_PROXY_EXPOSURE_BREACH",
                    day_index=error.day_index,
                    boundary_index=error.boundary_index,
                    equity=float(error.equity),
                    exposure=error.exposure.tolist(),
                    gross_fraction=float(error.exposure.sum() / error.equity),
                    paid_terminal_cash_realized=False,
                    full_path_result_unavailable=True,
                    initial_capital=10000.0,
                )
                wallets.append(detail)
                if episode.role == "SEEN_VALIDATION":
                    assert (
                        original["arms"][name]["development"][0]["status"]
                        == "STOP_PROXY_EXPOSURE_BREACH"
                    )
                key = name + "__" + episode.wallet_id
                for field, value in dict(
                    decision_us=episode.windows.decision_us,
                    requests_E5=requests,
                    mapped_budget_E5=np.array([r["budget"] for r in records]),
                    net_targets=targets,
                ).items():
                    arrays[key + "__" + field] = value
                continue
            nav = report["nav"]
            ret = report["net_return"]
            detail = dict(
                wallet_id=episode.wallet_id,
                role=episode.role,
                decisions=len(episode.contexts),
                loss=loss,
                net_PnL=report["net_PnL"],
                liquidated_return=float(nav[-1] / 10000.0 - 1),
                maximum_drawdown=float(np.max(1 - nav / np.maximum.accumulate(nav))),
                annualized_daily_proxy_vol=float(np.std(ret, ddof=1) * np.sqrt(365)),
                maximum_allocated_leg_gross=max(r["allocated_leg_gross"] for r in records),
                maximum_allocated_asset_gross=float(
                    max(np.max(r["allocated_underlier_gross"]) for r in records)
                ),
                request_mean=requests.mean(0).tolist(),
                request_first=requests[0].tolist(),
                request_last=requests[-1].tolist(),
                fees=report["fees"],
                spread=report["spread"],
                slippage=report["slippage"],
                funding=report["funding"],
                paid_terminal_cash_realized=report["terminal_cash_realized"],
                initial_capital=10000.0,
                status=report["status"],
            )
            wallets.append(detail)
            if episode.role == "SEEN_VALIDATION":
                old = original["arms"][name]["development"][0]
                for key in ("net_PnL", "loss", "fees", "funding"):
                    assert detail[key] == old[key], (name, key)
            key = name + "__" + episode.wallet_id
            for field, value in dict(
                decision_us=episode.windows.decision_us,
                requests_E5=requests,
                mapped_budget_E5=np.array([r["budget"] for r in records]),
                net_targets=targets,
                nav=nav,
                net_return=ret,
                quantity=report["quantity"],
            ).items():
                arrays[key + "__" + field] = value
        assert model_identity(model) == before
        reports[name] = dict(
            parameter_count=model.parameter_count,
            terminal=barrier["terminal"][name],
            initial_train_loss=saved["trainer_state"]["history"][0]["loss"],
            final_deterministic_train_loss=(
                None
                if any(w["loss"] is None for w in wallets if w["role"] == "TRAIN")
                else sum(w["loss"] * w["decisions"] for w in wallets if w["role"] == "TRAIN") / 778
            ),
            training_history=saved["trainer_state"]["history"],
            wallets=wallets,
        )
        dest = pack / name
        dest.mkdir()
        for file in ("RUN.json", "latest.json", "TERMINAL.json", pointer["file"]):
            shutil.copyfile(folder / file, dest / file)
        snapshots[name] = dict(
            pointer=pointer,
            checkpoint_source_path=str((dest / pointer["file"]).relative_to(pack)),
            Adam_RNG_train_state_saved=True,
            train_state_status=saved["trainer_state"]["status"],
        )
    for file in (
        "RUN.json",
        "SCALER.npz",
        "SCALER.json",
        "ALL_FOUR_TERMINAL.json",
        "DEVELOPMENT_RESULTS.json",
    ):
        shutil.copyfile(root / file, pack / file)
    np.savez_compressed(out / "SIMULATED_PATHS.npz", **arrays)
    archive = out / "TERMINAL_MODELS_ADAM_RNG.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(pack.rglob("*")):
            if file.is_file():
                z.write(file, file.relative_to(pack))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    resource = dict(
        original_phase=json.loads((s / "FOUR_FIT_RESOURCES.json").read_text()),
        continuation_phase=json.loads((s / "CONTINUATION_RESOURCES.json").read_text()),
        parallel_fourth_phase=json.loads((s / "PARALLEL_ARM_RESOURCES.json").read_text()),
    )
    resource["summed_bounded_phase_seconds_including_parallel_overlap"] = sum(
        r["elapsed_seconds"] for r in resource.values()
    )
    report = dict(
        schema="TEMPORAL_SINGLE_FOUR_FIT_RESULT_V1",
        status=original["status"],
        actual_fits=4,
        refits=0,
        hyperparameter_or_architecture_search=False,
        arms=reports,
        snapshots=snapshots,
        scaler_identity=scaler.identity,
        scaler_fit_count=1,
        unique_train_feature_rows=scaler.provenance["real_row_count"],
        protocol=PROTOCOL,
        packet_identity=identity,
        resources=resource,
        initial_allocation="NO_CASH_CASH0_VOL.5_CS.5;WITH_CASH_CASH.5_VOL.25_CS.25",
        terminal_snapshots_all_saved_before_seen_development=True,
        readback_seen_results_exact=True,
        economic_dependencies="new_train_minute_boundary_prices/event_funding_vs_original_seen_dev_daily_proxy;conditional_proxy",
        capital="five_independent_fresh10k_training_wallets_and_one_separate_seen_dev10k;do_not_sum_wallet_PnL_as_shared_portfolio",
        continuation_source_SHA256=sha(
            Path("research/temporal-four-fit-20261009/CONTINUE_AFTER_EXPOSURE_STOP.py")
        ),
        execution_schedule_amendment=json.loads(
            Path(
                "research/temporal-four-fit-20261009/EXECUTION_SCHEDULE_AMENDMENT.json"
            ).read_text()
        ),
        parallel_worker_SHA256=sha(
            Path("research/temporal-four-fit-20261009/LAST_ARM_PARALLEL.py")
        ),
        frozen_source_commit="4f854822c07ea56ce33168d7f5c99d3980779c5f",
        failure_controller_commit="8e4598dedc75736666baa1cc89066b6b69780dc9",
        qualification="NO_NATIVE_OR_UNSEEN_OOS_QUALIFICATION;convergence_and_training_improvement_do_not_imply_alpha;cap_not_selector_impossibility",
        native_wallets=0,
        provider_downloads=0,
        optimization_steps_during_export=0,
        artifacts=dict(
            terminal_archive=dict(bytes=archive.stat().st_size, SHA256=sha(archive)),
            simulated_paths=dict(
                bytes=(out / "SIMULATED_PATHS.npz").stat().st_size,
                SHA256=sha(out / "SIMULATED_PATHS.npz"),
            ),
        ),
    )
    (out / "RESULT.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    (out / "DEVELOPMENT_RESULTS.json").write_bytes((root / "DEVELOPMENT_RESULTS.json").read_bytes())
    (out / "EXPORT_SCRIPT.py").write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            dict(
                status=report["status"],
                arms={
                    k: dict(
                        updates=v["terminal"]["step"],
                        status=v["terminal"]["status"],
                        dev_PnL=v["wallets"][-1]["net_PnL"],
                    )
                    for k, v in reports.items()
                },
                artifact_bytes=archive.stat().st_size,
            )
        )
    )


if __name__ == "__main__":
    main()
