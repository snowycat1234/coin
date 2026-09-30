"""Verify the shared, kernel-enforced runtime and training memory budget."""
import json
from pathlib import Path

RAM_LIMIT = 5_000_000_000


def status() -> dict:
    membership = Path("/proc/self/cgroup").read_text().strip()
    relative = membership.split("::", 1)[1]
    current = Path("/sys/fs/cgroup" + relative)
    aggregate = next((path for path in (current, *current.parents)
                      if path.name == "coin-quant.slice"), None)
    if aggregate is None:
        raise RuntimeError("Run through scripts/bounded.sh: shared 5 GB RAM budget is required")
    fields = {name: (aggregate / name).read_text().strip() for name in
              ("memory.max", "memory.current", "memory.peak", "memory.swap.max",
               "memory.swap.current", "memory.events")}
    if fields["memory.max"] == "max" or int(fields["memory.max"]) > RAM_LIMIT:
        raise RuntimeError("Shared project memory budget exceeds 5 GB")
    if fields["memory.swap.max"] != "0" or fields["memory.swap.current"] != "0":
        raise RuntimeError("Project swap is forbidden")
    return {"aggregate_cgroup": str(aggregate), "ram_limit_bytes": int(fields["memory.max"]),
            "ram_current_bytes": int(fields["memory.current"]),
            "ram_peak_bytes": int(fields["memory.peak"]), "swap_bytes": 0,
            "memory_events": fields["memory.events"], "gpu_used": False}


if __name__ == "__main__":
    print(json.dumps(status(), indent=2))
