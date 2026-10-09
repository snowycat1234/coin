"""Pure pinned transport/clock/mask check, without minute market access or wallet."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--pinned-parser", type=Path, required=True)
    a = p.parse_args()
    expected = "948f496f6307576832fa47afcfcd7161b0d855456b49ae511da5066d09f2efbd"
    assert hashlib.sha256(a.pinned_parser.read_bytes()).hexdigest() == expected
    spec = importlib.util.spec_from_file_location(
        "_exact_corrected_native_request_contract", a.pinned_parser
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = a.bundle / "MANIFEST.json"
    h = hashlib.sha256(manifest.read_bytes()).hexdigest()
    m, arrays = module.load_bundle(manifest, h)
    original = a.state / "recovery/direct_path_fragments/H1_VALIDATE.npz"
    short = a.state / "short-source/DEV61_MOMENTUM_SHORT_CONTEXTS.npz"
    assert (
        hashlib.sha256(original.read_bytes()).hexdigest()
        == "c13de3125698f1fc350d1435453cbb6e33b7d5873537d7f859c1570344f081bc"
    )
    assert (
        hashlib.sha256(short.read_bytes()).hexdigest()
        == "89183eb92bd45b65a1209aa139f80964cc013c62015a803336db7a7bbd90840d"
    )
    with np.load(original, allow_pickle=False) as z, np.load(short, allow_pickle=False) as s:
        context = dict(
            expert_order=tuple(module.E5) + (module.SHORT,),
            past_returns30=z["past_returns30"].copy(),
            expert_targets=np.concatenate((z["expert_targets"], s["expert_targets"]), axis=1),
            expert_eligible=np.concatenate((z["expert_eligible"], s["expert_eligible"]), axis=1),
            target_available_us=np.concatenate(
                (z["target_available_us"], s["target_available_us"]), axis=1
            ),
        )
    full, result = module.validate(m, arrays, context)
    with np.load(a.bundle / m["current_expert_input_file"], allow_pickle=False) as x:
        np.testing.assert_array_equal(x["decision_us"], arrays["decision_us"])
        np.testing.assert_array_equal(x["symbol_order"], arrays["symbol_order"])
        np.testing.assert_array_equal(x["signed_targets"], context["expert_targets"][:, (1, 4, 5)])
        masks = context["expert_eligible"][:, (1, 4, 5)]
        clocks = context["target_available_us"][:, (1, 4, 5)]
        np.testing.assert_array_equal(x["expert_eligible"], masks)
        np.testing.assert_array_equal(x["target_available_us"], clocks)
        expected_state = np.concatenate(
            (
                np.where(masks[:, :, None], x["signed_targets"], 0).reshape(61, 15) / 0.3,
                masks.astype(float),
            ),
            axis=1,
        )
        np.testing.assert_array_equal(x["expert_state"], expected_state)
        np.testing.assert_array_equal(
            x["input_available_us"], np.concatenate((np.repeat(clocks, 5, axis=1), clocks), axis=1)
        )
        assert float(x["target_unit"]) == 0.3
        assert np.all(x["input_available_us"] <= arrays["decision_us"][:, None])
        assert np.all(x["input_available_us"] < arrays["decision_us"][:, None] + 60000001)
        assert m["input_enabled"] is True
        assert m["arm_id"] in ("EXP_GRU64_WEIGHT_DATE", "EXP_GRU64_WEIGHT_MIXED")
        assert m["completed_weighting_updates"] == 512
    assert np.array_equal(full, arrays["desired_expert_budget"])
    receipt = dict(
        status="PASS_PINNED_NATIVE61_AND_EXACT_CURRENT_EXPERT_INPUT_TARGET_CLOCK_MASK_CONTRACT",
        arm_id=m["arm_id"],
        manifest_sha256=h,
        contract_commit="a596f9e5983692873b70f6737cac6ce853dee72f",
        contract_SHA256="9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2",
        pinned_parser_SHA256=expected,
        native_wallets=0,
        optimizer_updates=0,
        context_scope=(
            "Recovered61-dayE5 + exact appended momentum context; "
            "complete-minute grid/source validation belongs to existing native executor"
        ),
        report=result,
    )
    (a.bundle / "EXPORT_CONTRACT_CHECK.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
