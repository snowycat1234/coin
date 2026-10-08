"""Linux CPU-only supervisor. Default check mode NEVER fits a model.

Run-pair is a separate explicit action, to be used only after parent approval.
No network, model selection, resume, parameter overrides, or GPU dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

ARMS = ("IMITATE_REQUEST", "DIRECT_PATH_UTILITY")
WALL_SECONDS = 120
CHECK_SECONDS = 30
MAX_RSS_BYTES = 1000000000
MAX_ADDRESS_BYTES = 900000000  # kernel limit is stricter than the RSS budget
MAX_THREADS = 2
THREAD_ENV = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


def write_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def set_child_limits():
    for kind, limit in ((resource.RLIMIT_AS, MAX_ADDRESS_BYTES), (resource.RLIMIT_CPU, 240)):
        inherited = resource.getrlimit(kind)[1]
        limit = limit if inherited == resource.RLIM_INFINITY else min(limit, inherited)
        resource.setrlimit(kind, (limit, limit))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    allowed = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, allowed[:2])


def bounded_process(command, log_path, wall_seconds=WALL_SECONDS,
                    rss_limit=MAX_RSS_BYTES, thread_limit=MAX_THREADS):
    """Own process group, kernel AS cap, monotonic deadline and RSS/thread guard.

    Small limits may be supplied by engineering tests, never by the fit CLI.
    stdout/stderr go to a file, so a child cannot block on a full pipe.
    """
    env = os.environ.copy()
    env.update({key: "1" for key in THREAD_ENV})
    env.update(CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1",
               DIRECT_PATH_SUPERVISED="1")
    began = time.monotonic()
    peak_rss, peak_threads, reason = 0, 0, None
    with Path(log_path).open("w") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=log,
                                   start_new_session=True, preexec_fn=set_child_limits)
        try:
            while process.poll() is None:
                try:
                    status = Path(f"/proc/{process.pid}/status").read_text()
                    fields = {line.split(":", 1)[0]: line.split(":", 1)[1].strip()
                              for line in status.splitlines() if ":" in line}
                    rss = int(fields.get("VmRSS", "0 kB").split()[0]) * 1024
                    threads = int(fields.get("Threads", "0"))
                    peak_rss, peak_threads = max(peak_rss, rss), max(peak_threads, threads)
                    if rss > rss_limit:
                        reason = "STOP_RSS_LIMIT"
                    elif threads > thread_limit:
                        reason = "STOP_THREAD_LIMIT"
                except FileNotFoundError:
                    pass  # child exit raced the read
                remaining = wall_seconds - (time.monotonic() - began)
                if remaining <= 0:
                    reason = "STOP_HARD_WALL_LIMIT"
                if reason:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                try:
                    process.wait(timeout=min(.025, max(.001, remaining)))
                except subprocess.TimeoutExpired:
                    pass
        except BaseException:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        process.wait()
    return dict(status=reason or ("COMPLETED" if process.returncode == 0 else "STOP_CHILD_FAILURE"),
                returncode=process.returncode, wall_seconds=time.monotonic() - began,
                peak_observed_rss_bytes=peak_rss, peak_observed_threads=peak_threads,
                kernel_address_limit_bytes=MAX_ADDRESS_BYTES, cpu_affinity_limit=2,
                wall_limit_seconds=wall_seconds, rss_limit_bytes=rss_limit,
                thread_limit=thread_limit)


def frozen_model(path, approved_sha):
    """Byte-bound inference-only model. Does not train or select checkpoints."""
    from .pack import MAX_NPZ_BYTES, bounded_bytes, checked_npz_bytes
    from .prototype import SmallBudgetHead, finite
    raw = bounded_bytes(path, MAX_NPZ_BYTES)
    if hashlib.sha256(raw).hexdigest() != approved_sha:
        raise ValueError("Frozen model byte binding failed")
    a = checked_npz_bytes(raw)
    if set(a) != {"mean", "scale", "w1", "b1", "w2", "b2"}:
        raise ValueError("Exact frozen 397-parameter artifact required")
    head = SmallBudgetHead(a["mean"], a["scale"])
    for key, parameter in head.parameters.items():
        head.parameters[key] = finite(a[key], parameter.shape, key).copy()
        head.parameters[key].setflags(write=False)
    head.mean.setflags(write=False)
    head.scale.setflags(write=False)
    return head


def verify_worker_limits():
    """Check before NumPy import, including Linux RLIM_INFINITY == -1."""
    as_limit = resource.getrlimit(resource.RLIMIT_AS)[1]
    if (os.environ.get("DIRECT_PATH_SUPERVISED") != "1"
            or as_limit == resource.RLIM_INFINITY or not 0 < as_limit <= MAX_ADDRESS_BYTES
            or len(os.sched_getaffinity(0)) > 2
            or any(os.environ.get(k) != "1" for k in THREAD_ENV)):
        raise ValueError("Worker requires the hard-limited supervisor")


def worker(args):
    verify_worker_limits()
    import numpy as np
    from .pack import bounded_bytes, load_pack, MAX_MANIFEST_BYTES
    from .prototype import SEED, loss_and_gradient
    from .training import EPOCHS, LEARNING_RATE, common_standardizer, fit_arm
    out = Path(args.output)
    report_path = out / ("check.json" if args.arm is None else args.arm + ".json")
    report = dict(status="CHECKING", fits_started=0, fits_completed=0,
                  approved_pack_sha256=args.approved_pack_sha256)
    write_json(report_path, report)
    try:
        raw = bounded_bytes(args.manifest, MAX_MANIFEST_BYTES)
        if hashlib.sha256(raw).hexdigest() != args.approved_pack_sha256:
            raise ValueError("Exact parent-approved index bytes required")
        schema = json.loads(raw)["schema"]
        if schema == "BYTE_BOUND_DIRECT_PATH_FRAGMENTS_V1":
            from .data_adapter import load_training_and_validation
            train, validation, manifest = load_training_and_validation(
                Path(args.manifest).parent, args.approved_pack_sha256)
            fragments = train + [validation]
        else:
            manifest, fragments = load_pack(args.manifest, args.approved_pack_sha256)
        train = fragments[:3]
        mean, scale = common_standardizer(train)
        report.update(window_ids=[f["window_id"] for f in fragments],
                      observations=[len(f["contexts"]) for f in fragments],
                      source_commit=manifest.get("source_commit", manifest.get("source_full_inputs_commit")),
                      protocol_source_commit=manifest.get("protocol_source_commit"),
                      binding=[f["binding"] for f in fragments],
                      delivered_input_npz_sha256=[f.get("delivered_input_npz_sha256",
                          f["binding"]["input_npz_sha256"]) for f in fragments])
        if args.arm is None:
            np.savez(out / "standardizer.npz", mean=mean, scale=scale)
            report.update(status="INPUT_VALIDATED_NOT_TRAINED",
                          standardizer_sha256=file_sha(out / "standardizer.npz"))
            write_json(report_path, report)
            return
        check = json.loads((out / "check.json").read_text())
        standard = out / "standardizer.npz"
        if (check["approved_pack_sha256"] != args.approved_pack_sha256
                or check["status"] != "INPUT_VALIDATED_NOT_TRAINED"
                or file_sha(standard) != check["standardizer_sha256"]):
            raise ValueError("Shared input check/standardizer binding failed")
        with np.load(standard, allow_pickle=False) as scaler:
            if not np.array_equal(scaler["mean"], mean) or not np.array_equal(scaler["scale"], scale):
                raise ValueError("Shared training-only standardizer changed")
            mean, scale = scaler["mean"].copy(), scaler["scale"].copy()
        report.update(status="FITTING", arm=args.arm, fits_started=1, completed_epochs=0,
                      epochs=EPOCHS, learning_rate=LEARNING_RATE, seed=SEED,
                      parameters=397, fit_started_unix_ns=time.time_ns(),
                      standardizer_sha256=check["standardizer_sha256"])
        write_json(report_path, report)
        progress_path = out / (args.arm + "_EPOCHS.jsonl")

        def progress(epoch, loss, norm):
            with progress_path.open("a") as log:
                log.write(json.dumps(dict(epoch=epoch, preupdate_loss=loss,
                          gradient_norm=norm, unix_ns=time.time_ns()), allow_nan=False) + "\n")
            report.update(completed_epochs=epoch, last_preupdate_loss=loss,
                          last_gradient_norm=norm)
            write_json(report_path, report)

        head = fit_arm(train, args.arm, mean, scale, progress)
        # Validate the actual epoch64 parameters too, rather than reporting the
        # proxy evaluated before the final Adam update as the frozen model's PnL.
        loss, _, paths = loss_and_gradient(head, train, args.arm)
        model_path = out / (args.arm + ".npz")
        np.savez(model_path, mean=head.mean, scale=head.scale, **head.parameters)
        model_sha = file_sha(model_path)
        loaded = frozen_model(model_path, model_sha)
        validation = fragments[3]
        request, _ = loaded.forward(np.array([c.features() for c in validation["contexts"]]))
        # Persist genuine head requests. Terminal forced-flat is the existing
        # shared mapper/executor rule, never a fabricated one-hot head output.
        request_path = out / (args.arm + "_H1_VALIDATE_REQUESTS.npz")
        np.savez(request_path, decision_us=np.array([c.decision_us for c in validation["contexts"]]),
                 request=request, force_cash=np.arange(len(request)) == len(request) - 1)
        summaries = [{k: p[k] for k in ("status", "net_PnL", "utility_sum", "fees",
                     "spread", "slippage", "funding", "gross", "terminal_cash_realized")}
                     for p in paths]
        report.update(status="FROZEN_EPOCH64_NATIVE_VALIDATION_PENDING", fits_completed=1,
                      fit_finished_unix_ns=time.time_ns(),
                      frozen_loss=float(loss), model_file=model_path.name,
                      model_sha256=model_sha, training_daily_proxy_only=summaries,
                      validation_request_file=request_path.name,
                      validation_request_sha256=file_sha(request_path))
        write_json(report_path, report)
    except Exception as error:
        report.update(status="INCOMPLETE", error_type=type(error).__name__, error=str(error))
        write_json(report_path, report)
        raise
    finally:
        report.update(peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      address_limit_bytes=resource.getrlimit(resource.RLIMIT_AS)[1],
                      cpu_limit_seconds=resource.getrlimit(resource.RLIMIT_CPU)[1],
                      cpu_affinity=sorted(os.sched_getaffinity(0)))
        write_json(report_path, report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("check", "run-pair", "worker"), default="check")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--approved-pack-sha256", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--arm", choices=ARMS, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.mode == "worker":
        worker(args)
        return 0
    if args.arm is not None:
        parser.error("--arm is private to the supervised child")
    if len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise RuntimeError("STOP: active swap is incompatible with the frozen budget")
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)  # no reruns/resumes or overwritten evidence
    code = {p.name: file_sha(p) for p in Path(__file__).parent.glob("*.py")}
    pair = dict(status="CHECKING", fits_started=0, fits_completed=0, code_sha256=code,
                mode=args.mode, approved_pack_sha256=args.approved_pack_sha256,
                active_swap=False, gpu_used=False, arms={}, limits=dict(
                    arm_wall_seconds=WALL_SECONDS, rss_bytes=MAX_RSS_BYTES,
                    address_bytes=MAX_ADDRESS_BYTES, threads=MAX_THREADS, cpus=2))
    write_json(out / "pair.json", pair)
    base = [sys.executable, "-m", "modules.direct_path.entry", "--mode", "worker",
            "--manifest", str(Path(args.manifest).resolve()), "--approved-pack-sha256",
            args.approved_pack_sha256, "--output", str(out)]
    guard = bounded_process(base, out / "check.log", CHECK_SECONDS)
    pair["check_guard"] = guard
    if guard["status"] != "COMPLETED":
        pair["status"] = "INCOMPLETE"
    elif args.mode == "check":
        pair["status"] = "INPUT_VALIDATED_NOT_TRAINED"
    else:
        for arm in ARMS:  # serial, at most exactly two fits; STOP halts the pair
            pair.update(status="FITTING", active_arm=arm)
            write_json(out / "pair.json", pair)
            guard = bounded_process(base + ["--arm", arm], out / (arm + ".log"))
            report_path = out / (arm + ".json")
            report = json.loads(report_path.read_text()) if report_path.exists() else {}
            pair["arms"][arm] = dict(guard=guard, report=report)
            pair["fits_started"] += report.get("fits_started", 0)
            pair["fits_completed"] += report.get("fits_completed", 0)
            if (guard["status"] != "COMPLETED"
                    or report.get("status") != "FROZEN_EPOCH64_NATIVE_VALIDATION_PENDING"):
                pair["status"] = "INCOMPLETE"
                break
            write_json(out / "pair.json", pair)
        else:
            pair["status"] = "PAIRED_FROZEN_NATIVE_VALIDATION_PENDING"
        pair["active_arm"] = None
    write_json(out / "pair.json", pair)
    print(json.dumps({k: pair[k] for k in ("status", "fits_started", "fits_completed")}))
    return 1 if pair["status"] == "INCOMPLETE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
