"""Read atomic completed-step pointers and actual process state; never fit."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    starts = {}
    for line in (a.run / "CONTROLLER.log").read_text().splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("stage") == "expert_input_worker_started":
            starts[record["arm"]] = record
    workers = {}
    for arm, started in starts.items():
        folder = a.run / arm
        pointer = json.loads((folder / "latest.json").read_text())
        binding = json.loads((folder / "RUN.json").read_text())
        parent = binding["specification"]["algorithm"]["parent"]["step"]
        process = Path("/proc") / str(started["PID"])
        alive = process.exists()
        terminal = folder / "TERMINAL.json"
        workers[arm] = dict(
            PID=started["PID"],
            cpu=started["cpu"],
            process_alive=alive,
            CPU_affinity=sorted(os.sched_getaffinity(started["PID"])) if alive else [],
            completed_stage_updates=pointer["step"] - parent,
            cumulative_base_Adam_step=pointer["step"],
            new_parameters_Adam_step=pointer["step"] - parent,
            latest_atomic_checkpoint=pointer,
            terminal=json.loads(terminal.read_text()) if terminal.exists() else None,
            status="TERMINAL" if terminal.exists() else ("RUNNING" if alive else "INSPECT_EXIT"),
        )
    assert len(workers) == 2
    record = dict(
        schema="MATCHED_EXPERT_INPUT_ACTUAL_FIT_STATUS_V1",
        observed_UTC=datetime.now(timezone.utc).isoformat(),
        boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        frozen_producer_commit="c0c110468cd0deee312e18f159c44b98108d8691",
        workers=workers,
        parameter_count_per_arm=13699,
        cgroup_memory_current_bytes=int(Path("/sys/fs/cgroup/memory.current").read_text()),
        cgroup_swap_current_bytes=int(Path("/sys/fs/cgroup/memory.swap.current").read_text()),
        limits="two1CPU2GBworkers;shared8GB;1200s/1024updates_each;swap0GPU0",
        economic_scoring_before_both_terminal=False,
        weighting_updates=0,
    )
    a.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({arm: w["completed_stage_updates"] for arm, w in workers.items()}))


if __name__ == "__main__":
    main()
