"""Export evidence from two ALREADY frozen heads. No optimizer calls or fits."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import numpy as np

from .data_adapter import load_training_and_validation
from .entry import ARMS, file_sha, frozen_model, write_json
from .prototype import SEED, SmallBudgetHead, daily_proxy, mapped_path

PARAMETER_ORDER = ("w1", "b1", "w2", "b2")


def export(run_root, manifest_path, approved_sha, output):
    run = Path(run_root)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    pair = json.loads((run / "pair.json").read_text())
    if (pair["status"] != "PAIRED_FROZEN_NATIVE_VALIDATION_PENDING"
            or pair["fits_started"] != 2 or pair["fits_completed"] != 2
            or pair["approved_pack_sha256"] != approved_sha):
        raise ValueError("Exactly the successful authorized pair required; never refit")
    train, validation, manifest = load_training_and_validation(Path(manifest_path).parent, approved_sha)
    for name, sha in pair["code_sha256"].items():
        if file_sha(Path(__file__).parent / name) != sha:
            raise ValueError("Training source changed since the fit: " + name)
    for name in ("pair.json", "check.json", "standardizer.npz"):
        shutil.copyfile(run / name, out / name)
    shutil.copyfile(Path(__file__).parent / "PROTOCOL.md", out / "PROTOCOL_AT_FREEZE.md")
    initial_hashes, summaries = [], {}
    for arm in ARMS:
        report = json.loads((run / (arm + ".json")).read_text())
        if report["completed_epochs"] != 64 or report["fits_completed"] != 1:
            raise ValueError("Only epoch64 allowed")
        records = [json.loads(line) for line in (run / (arm + "_EPOCHS.jsonl")).read_text().splitlines()]
        if [r["epoch"] for r in records] != list(range(1, 65)):
            raise ValueError("Complete 64-epoch actual log required")
        model_path = run / report["model_file"]
        head = frozen_model(model_path, report["model_sha256"])
        vector = np.concatenate([head.parameters[k].ravel(order="C") for k in PARAMETER_ORDER])
        initial = SmallBudgetHead(head.mean, head.scale)
        initial_vector = np.concatenate([initial.parameters[k].ravel(order="C") for k in PARAMETER_ORDER])
        initial_sha = hashlib.sha256(initial_vector.astype("<f8").tobytes()).hexdigest()
        initial_hashes.append(initial_sha)
        write_json(out / (arm + "_PARAMETERS.json"), dict(
            arm=arm, epoch=64, seed=SEED, parameter_count=int(vector.size),
            order=[dict(name=k, shape=list(head.parameters[k].shape), flatten="C") for k in PARAMETER_ORDER],
            vector=vector.tolist(), vector_float64_le_sha256=hashlib.sha256(vector.astype("<f8").tobytes()).hexdigest(),
            same_seed_initial_vector_sha256=initial_sha, model_sha256=report["model_sha256"],
            standardizer_sha256=report["standardizer_sha256"], approved_index_sha256=approved_sha))
        for name in (report["model_file"], arm + ".json", arm + "_EPOCHS.jsonl",
                     report["validation_request_file"]):
            shutil.copyfile(run / name, out / name)
        summaries[arm] = []
        for index, fragment in enumerate(train):
            cs = fragment["contexts"]
            request, _ = head.forward(np.array([c.features() for c in cs]))
            targets, maps = mapped_path(request, cs)
            path = daily_proxy(targets, fragment["prices"], fragment["funding_coeff"])
            expected = report["training_daily_proxy_only"][index]
            for key in expected:
                if path[key] != expected[key]:
                    raise ValueError("Frozen proxy report mismatch: " + key)
            name = arm + "_" + fragment["window_id"] + "_PROXY_PATH.npz"
            np.savez_compressed(out / name,
                decision_us=np.array([c.decision_us for c in cs]), request=request,
                mapped_budget=np.array([m["budget"] for m in maps]), mapped_targets=targets,
                quantity=path["quantity"], nav=path["nav"], net_return=path["net_return"],
                force_cash=np.arange(len(cs)) == len(cs) - 1)
            summaries[arm].append(dict(window_id=fragment["window_id"], **expected,
                                       path_file=name, path_sha256=file_sha(out / name)))
        request, _ = head.forward(np.array([c.features() for c in validation["contexts"]]))
        request_path = out / report["validation_request_file"]
        if file_sha(request_path) != report["validation_request_sha256"]:
            raise ValueError("Published validation request binding failed")
        with np.load(request_path, allow_pickle=False) as a:
            if not np.array_equal(a["request"], request):
                raise ValueError("Frozen validation inference differs; never refit")
    if len(set(initial_hashes)) != 1:
        raise ValueError("Paired initialization differs")
    write_json(out / "FROZEN_RESULTS.json", dict(
        status="PAIRED_FROZEN_NATIVE_VALIDATION_PENDING", actual_fits=2, epochs=64,
        approved_index_sha256=approved_sha, source_full_inputs_commit=manifest["source_full_inputs_commit"],
        producer_protocol_commit=manifest["protocol_source_commit"],
        feature_schema_sha256=manifest["feature_schema_SHA256"],
        same_seed_initial_vector_sha256=initial_hashes[0], training_daily_proxy_only=summaries,
        independent_wallets_not_summed=True, validation_daily_proxy_pnl_not_computed=True,
        native_wallet_validation="PARENT_EXECUTOR_PENDING", refits=0,
        resource_guards={a: pair["arms"][a]["guard"] for a in ARMS}))
    members = [dict(name=p.name, bytes=p.stat().st_size, sha256=file_sha(p))
               for p in sorted(out.iterdir()) if p.is_file()]
    write_json(out / "MANIFEST_SHA256.json", dict(schema="DIRECT_PATH_FROZEN_PAIR_V1",
               members=members, fits_started=2, fits_completed=2, native_validation="PENDING"))
    archive = out.with_suffix(".zip")
    if archive.exists():
        raise FileExistsError("Frozen evidence ZIP must not be overwritten")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(out.iterdir()):
            z.write(p, arcname=p.name)
    return dict(file=archive.name, bytes=archive.stat().st_size, sha256=file_sha(archive),
                members=len(list(out.iterdir())), actual_fits=2, refits=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--approved-index-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.run_root, args.manifest, args.approved_index_sha256, args.output)))


if __name__ == "__main__":
    main()
