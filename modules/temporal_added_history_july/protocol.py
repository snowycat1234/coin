import json
from pathlib import Path

from modules.temporal_expanded_refit.protocol import sources as fitting_sources
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "research/temporal-added-history-july-20261010"
OLD = ROOT / "research/temporal-july-frozen-transfer-20261010/results"
SCALER = "5c0085131d590e64316de3cc558e906f418bff50bc5d934339609da2c4b045ad"
CLASSIFICATION = "SECOND_SEEN_HISTORICAL_DEVELOPMENT_ADDED_HISTORY_COMPARISON"
MODELS = {
    "FULL773_256": dict(
        commit="657aeaff93889da600ad88b3603739508ba03216",
        folder="research/temporal-selected-refit-q4-20261010/frozen/FULL773_LOW_LR3E4_DATE_256",
        file="step-00000256-f212bfc864a64e02b5bfc0b9ff51867c.pt",
        checkpoint_SHA256="58db72621c9596a195267869a9cfa75f56c52162521f3ff77bf5d69c7d7bb88a",
        model_identity="38eb7275e4f69382083cbc3d81463d5fd2de955be2ad55919bed42c55c435e84",
        active_training_intervals=773,
    ),
    "EXPANDED1137_256": dict(
        commit="0e5f41c255f315dccdd922de9a4ce762a1f40771",
        folder="research/temporal-expanded-refit-q4-20261010/frozen",
        file="step-00000256-ddf13a2492fc4d3ebec3d4e16f77a232.pt",
        checkpoint_SHA256="d971fbc148ec79a49c760766a64088d31e62461484e6141a44e9e0d2e557f146",
        model_identity="7918706f2729f3a87ff47e67bceb7f34131783f4d606d59e99ce8db384ca7cec",
        active_training_intervals=1137,
    ),
}
ORDER = list(MODELS)
CONTROLS = ["PREFIX_STATIC_VOL", "Static50", "Cash50"]


def sources():
    paths = [
        p
        for folder in ("temporal_added_history_july", "temporal_july_transfer")
        for p in (ROOT / "modules" / folder).rglob("*.py")
    ]
    return {**fitting_sources(), **{str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}}


def protocol():
    p = dict(
        schema="TWO_FROZEN256_FIXED_JULY_ADDED_HISTORY_V1",
        classification=CLASSIFICATION,
        models=MODELS,
        policy_order=ORDER,
        decisions=63,
        active_intervals=62,
        start_UTC="2024-07-01T00:00:00Z",
        end_exclusive_UTC="2024-09-02T00:00:00Z",
        paid_close_UTC="2024-09-01T00:01:00.000001Z",
        calendar="existing63decision_ABI;62realintervals;forcedpaidflat;structuralcashsuffixonly",
        shared_scaler_identity=SCALER,
        scaler_rows=907,
        architecture_parameters=13699,
        seed=20261009,
        fitting_lr=0.0003,
        fitted_updates=256,
        shared_training_end_exclusive_UTC="2024-05-01T00:00:00Z",
        only_training_data_difference="earlier364actual2021intervals;originalfivewallets907scalerunchanged;dateweightsrecomputed",
        original_July_inputs_commit="90b8fd65d092b52091b3fee7717c0478b265bc6e",
        original_July_economics_commit="5109edcaa5a790a023a11828cfd1452b5705ba1a",
        new_daily_wallets=2,
        model_inferences=2,
        fits=0,
        optimizer_updates=0,
        normalization_updates=0,
        provider_downloads=0,
        native_wallets=0,
        controls_reused=CONTROLS,
        exact_prior_model_paths="reuse_only_identical_checkpoint/scaler/calendar/context/request_path",
        masks="same64completedsteps24causalfeatures24validitymasks18currentexpertinputs;originaldynamiceligibility",
        wallet="separatefresh10000CASH;gross.6/asset.3/annualcovrisk.1/dailybudgetL1.1;originalsignedfunding/cost/reductions",
        costs="fees.00055/spread.0004/slippage.0004;signedquantity;paidterminalflatten",
        native_mark_gap=["2024-08-12T10:02:00Z", "2024-08-12T10:03:00Z"],
        stop="aftertwofixedwalletsregardlessofoutcome;noadditionalperiod/fit/tuning/checkpointselection/promotion",
        execution_budget="singleCPU1thread;resident2GB/shared8GB;hard1200s;swap0/GPU0",
        no_new_OOS=True,
        no_full_native_validation=True,
    )
    return dict(p, identity=digest(p))


def public_gate(publication):
    public = json.loads(Path(publication).read_text())
    ready = DEST / "PRESCORE.json"
    path = str(ready.relative_to(ROOT))
    if public["status"] != "PASS_ALL_PUBLIC_BYTES" or not any(
        row["path"] == path and row["SHA256"] == sha(ready) for row in public["files"]
    ):
        raise ValueError("Public byte-verified paired pre-score protocol required")
    frozen = json.loads(ready.read_text())
    if frozen["protocol"] != protocol() or frozen["sources"] != sources():
        raise ValueError("Frozen paired source/recipe changed before evaluation")
    return frozen, public
