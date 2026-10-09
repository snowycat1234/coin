"""Read exact final snapshots, Adam ages, common random state and scoring barrier."""

import argparse
import json
import os
from pathlib import Path

import torch

from modules.temporal_episode_weighting_v2.stage import ARMS, SUCCESS, tree_identity
from modules.temporal_two_expert.exact import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("COIN_CLOUD_BOUNDED") == "1"
    records, rngs = {}, []
    for arm in ARMS:
        folder = args.run / arm
        pointer = json.loads((folder / "latest.json").read_text())
        assert sha(folder / pointer["file"]) == pointer["SHA256"]
        saved = torch.load(folder / pointer["file"], weights_only=True, map_location="cpu")
        terminal = json.loads((folder / "TERMINAL.json").read_text())
        assert saved["step"] == pointer["step"] == 1292
        assert saved["model_identity"] == terminal["model_identity"] == pointer["model_identity"]
        assert saved["trainer_state"]["status"] == terminal["status"] == SUCCESS
        assert terminal["completed_stage_updates"] == terminal["new_head_Adam_step"] == 512
        assert [d["snapshot_step"] for d in saved["trainer_state"]["history"]] == [0, 128, 256, 512]
        ages = [float(s["step"]) for s in saved["optimizer"]["state"].values()]
        assert ages.count(1292.0) == 10 and ages.count(512.0) == 3 and len(ages) == 13
        assert (
            (folder / "TERMINAL.json").stat().st_mtime
            <= (args.run / "BOTH_TERMINAL.json").stat().st_mtime
            <= (args.run / "RESULT.json").stat().st_mtime
        )
        rngs.append(tree_identity(saved["rng"]))
        records[arm] = dict(
            checkpoint_SHA256=pointer["SHA256"],
            model_identity=pointer["model_identity"],
            old_parameter_Adam_age=1292,
            new_parameter_Adam_age=512,
            old_parameters=10,
            new_parameters=3,
            new_updates=512,
            diagnostics=[0, 128, 256, 512],
            terminal_before_seen_score=True,
        )
    assert rngs[0] == rngs[1]
    result = dict(
        status="PASS",
        arms=records,
        both_final_all_RNG_identities_equal=rngs[0],
        optimizer_updates=0,
        native_wallets=0,
        exact_terminal_checkpoint_read_only=True,
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(
                status="PASS",
                both512=True,
                base_Adam1292=True,
                new_Adam512=True,
                final_common_RNG=True,
            )
        )
    )


if __name__ == "__main__":
    main()
