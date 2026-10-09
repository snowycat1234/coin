"""Zero-fit recovery provenance checks; no objective or wallet runs."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np


HERE = Path(__file__).resolve()
SOURCE_ROOT = Path(os.environ.get("TWO_EXPERT_RUNTIME_TEST_SOURCE_ROOT", HERE.parent.parent)).resolve()
WRAPPER = HERE.parent / "two_expert_recovery_runtime.py"
if not WRAPPER.is_file():
    WRAPPER = SOURCE_ROOT / "modules/native_action/two_expert_recovery_runtime.py"
spec = importlib.util.spec_from_file_location("recovery_runtime_under_test", WRAPPER)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
sys.path.insert(0, str(SOURCE_ROOT))


class RecoveryRuntimeZeroFitTests(unittest.TestCase):
    def fixture(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name) / "source"
        for relative in runtime.IMPORTED_SHA256:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_ROOT / relative, target)
        return root

    def test_every_corrupt_imported_source_is_rejected(self):
        for relative in runtime.IMPORTED_SHA256:
            root = self.fixture()
            with (root / relative).open("ab") as stream:
                stream.write(b"\n# corrupt\n")
            with self.subTest(source=relative), self.assertRaises(ValueError):
                runtime.current_source_manifest(root)

    def test_missing_auxiliary_is_explicit_and_never_claimed_checked(self):
        manifest = runtime.current_source_manifest(self.fixture())
        for relative in runtime.AUXILIARY_SHA256:
            entry = manifest["sources"][relative]
            self.assertEqual(entry["status"], "UNAVAILABLE_HISTORICAL_PROVENANCE_ONLY")
            self.assertFalse(entry["bytes_verified"])
            self.assertFalse(entry["imported_for_runtime"])
            self.assertNotIn("verified_SHA256", entry)

    def test_present_wrong_auxiliary_rejects(self):
        for relative in runtime.AUXILIARY_SHA256:
            root = self.fixture()
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("incorrect source bytes\n")
            with self.subTest(source=relative), self.assertRaises(ValueError):
                runtime.current_source_manifest(root)

    def test_original_functions_and_metadata_are_preserved(self):
        direct = importlib.import_module("modules.native_action.two_expert_direct")
        adequacy = importlib.import_module("modules.native_action.two_expert_adequacy")
        before = {name: getattr(direct, name) for name in
            ("source_hashes", "path_loss_and_gradient", "loss_and_gradient", "TwoExpertHead",
             "load_frozen", "model_metadata", "load_training_and_validation", "validate_fragment")}
        original_continue = adequacy.continue_fixed_pair
        fit = SOURCE_ROOT.parent / "two_expert_direct_fit"
        original_metadata = {arm: (fit / (arm + "_MODEL.json")).read_bytes() for arm in direct.ARMS}
        with runtime.bound_runtime(SOURCE_ROOT) as binding:
            self.assertEqual(direct.source_hashes(), runtime.HISTORICAL_SHA256)
            for name, function in before.items():
                if name != "source_hashes":
                    self.assertIs(getattr(direct, name), function)
            self.assertIs(adequacy.continue_fixed_pair, original_continue)
            for arm in direct.ARMS:
                metadata = json.loads(original_metadata[arm])
                direct.load_frozen(fit / (arm + ".npz"), metadata,
                    expected_model_sha256=adequacy.ORIGINAL_MODEL_SHA256[arm], cash_enabled=arm == "WITH_CASH")
                self.assertEqual(metadata, json.loads(original_metadata[arm]))
                self.assertEqual((fit / (arm + "_MODEL.json")).read_bytes(), original_metadata[arm])
            self.assertEqual(binding["manifest"]["sources"]["scripts/investment/regime_ranking_screen.py"]
                             ["status"], "VERIFIED_PRESENT")
        self.assertIs(direct.source_hashes, before["source_hashes"])

    def test_first64_coefficient_mismatch_still_rejects(self):
        with runtime.bound_runtime(SOURCE_ROOT) as binding:
            direct, adequacy = binding["direct"], binding["adequacy"]
            recovered = direct.TwoExpertHead(np.zeros(2), np.ones(2))
            frozen = direct.TwoExpertHead(np.zeros(2), np.ones(2))
            frozen.parameters["w"][1] = np.nextafter(0., 1.)
            with self.assertRaises(ValueError):
                adequacy._verify_exact_recovery(recovered, frozen)

    def test_read_only_check_preserves_pack_and_original_models(self):
        folder = SOURCE_ROOT.parent
        watched = sorted((folder / "direct_path_fragments").iterdir()) + sorted(
            (folder / "two_expert_direct_fit").iterdir())
        before = {str(path): runtime.sha(path) for path in watched if path.is_file()}
        result = runtime.check(folder / "direct_path_fragments",
            "e4fecc49cd1bb05f72dc0f8d24e793a5d7e4d2436c89a18bd9d7c625a7849be8",
            folder / "two_expert_direct_fit", root=SOURCE_ROOT)
        self.assertEqual(result["status"], "READY_ZERO_FIT_CONTINUATION")
        self.assertEqual(result["fit_count"], 0)
        self.assertEqual(result["training_rows"], 182)
        self.assertEqual(before, {str(path): runtime.sha(path) for path in watched if path.is_file()})

    def test_module_import_context_can_run_read_only_readiness(self):
        root = self.fixture()
        shutil.copyfile(WRAPPER, root / "modules/native_action/two_expert_recovery_runtime.py")
        pack = SOURCE_ROOT.parent / "direct_path_fragments"
        fit = SOURCE_ROOT.parent / "two_expert_direct_fit"
        script = ("import sys; from modules.native_action import two_expert_recovery_runtime as r; "
                  "result=r.check(sys.argv[1], "
                  "'e4fecc49cd1bb05f72dc0f8d24e793a5d7e4d2436c89a18bd9d7c625a7849be8', sys.argv[2]); "
                  "assert result['status']=='READY_ZERO_FIT_CONTINUATION'; "
                  "assert result['fit_count']==0; assert result['training_rows']==182")
        result = subprocess.run([sys.executable, "-c", script, str(pack), str(fit)],
                                cwd=root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
