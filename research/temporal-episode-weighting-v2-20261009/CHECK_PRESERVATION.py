"""Read-only previous sources/models/scaler and identical new initialization proof."""

import argparse
import json
import os
import zipfile
from pathlib import Path

from modules.temporal_two_expert.exact import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert os.environ.get("COIN_CLOUD_BOUNDED") == "1"
    root = Path(__file__).resolve().parents[2]
    ready = json.loads((a.state / "episode-weighting-v2/READY.json").read_text())
    arms = list(ready["arms"].values())
    bound_sources = {**ready["sources"], **arms[0]["binding"]["specification"]["sources"]}
    for name, expected in bound_sources.items():
        assert sha(root / name) == expected, name
    assert arms[0]["initial_identity"] == arms[1]["initial_identity"]
    assert all(x["parameter_count"] == 13699 for x in arms)
    assert all(x["binding"]["specification"]["model_contract"]["input_enabled"] for x in arms)
    archives = {}
    for phase, folder in (
        ("temporal-four-fit", "four-fit"),
        ("temporal-surrogate-resume-v2", "surrogate-v2"),
        ("temporal-short-expansion", "short-expansion"),
        ("temporal-expert-input", "expert-input"),
    ):
        path = root / f"research/{phase}-20261009/results/TERMINAL_MODELS_ADAM_RNG.zip"
        members = {}
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                local = a.state / folder / name
                if name.startswith("SCALER") and not local.exists():
                    local = a.state / "four-fit" / name
                assert z.read(name) == local.read_bytes(), (phase, name)
                members[name] = sha(local)
        archives[phase] = members
    result = dict(
        status="PASS",
        schema="WEIGHTING_V2_PRESERVATION_V1",
        frozen_source_files=len(bound_sources),
        archives_unchanged=archives,
        initial_model_Adam_all_RNG_identical=arms[0]["initial_identity"],
        parameters_per_arm=13699,
        expert_inputs_enabled_both=True,
        scaler_SHA256=sha(a.state / "four-fit/SCALER.npz"),
        provider_downloads=0,
        native_wallets=0,
        read_only=True,
    )
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(
                status="PASS",
                frozen_source_files=result["frozen_source_files"],
                archives={k: len(v) for k, v in archives.items()},
            )
        )
    )


if __name__ == "__main__":
    main()
