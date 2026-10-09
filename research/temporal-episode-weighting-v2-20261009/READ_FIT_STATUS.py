"""Read immutable completed-update checkpoints and prescribed training diagnostics."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import torch


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    starts = {}
    for line in (a.run / "CONTROLLER.log").read_text().splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("stage") == "weighting_worker_slice_started":
            starts[item["arm"]] = item
    workers = {}
    for arm, item in starts.items():
        folder = a.run / arm
        pointer = json.loads((folder / "latest.json").read_text())
        path = folder / pointer["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pointer["SHA256"]
        saved = torch.load(path, map_location="cpu", weights_only=True)
        binding = saved["binding"]
        assert binding["run_id"] == pointer["run_id"]
        parent = binding["specification"]["algorithm"]["parent"]["step"]
        alive = (Path("/proc") / str(item["PID"])).exists()
        terminal = folder / "TERMINAL.json"
        workers[arm] = dict(
            PID=item["PID"],
            cpu=item["cpu"],
            slice=item["slice"],
            process_alive=alive,
            CPU_affinity=sorted(os.sched_getaffinity(item["PID"])) if alive else [],
            completed_stage_updates=pointer["step"] - parent,
            cumulative_base_Adam_step=pointer["step"],
            new_parameters_Adam_step=pointer["step"] - parent,
            latest_atomic_checkpoint=pointer,
            diagnostics=saved["trainer_state"]["history"],
            terminal=json.loads(terminal.read_text()) if terminal.exists() else None,
            status="TERMINAL"
            if terminal.exists()
            else ("RUNNING" if alive else "SLICE_TRANSITION_OR_INSPECT_EXIT"),
        )
    assert len(workers) == 2
    result = dict(
        schema="MATCHED_FIXED512_WEIGHTING_ACTUAL_STATUS_V2",
        observed_UTC=datetime.now(timezone.utc).isoformat(),
        boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        workers=workers,
        parameter_count_per_arm=13699,
        fixed_update_target_each=512,
        initial_snapshot_SHA256="0f51bd3316f6e1100de518e8283ef3afb1c1148007bbb4d5fa7e3d1375acaddb",
        cgroup_memory_current_bytes=int(Path("/sys/fs/cgroup/memory.current").read_text()),
        cgroup_swap_current_bytes=int(Path("/sys/fs/cgroup/memory.swap.current").read_text()),
        limits="two1CPU2GBworkers;shared8GB;1200s_resumable_slices_until512_each;swap0GPU0",
        economic_scoring_before_both_fixed512_terminals=False,
    )
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({arm: w["completed_stage_updates"] for arm, w in workers.items()}))


if __name__ == "__main__":
    main()
