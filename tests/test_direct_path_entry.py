"""Synthetic pack/entry tests. NO optimizer calls or actual model fits."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from modules.direct_path.entry import THREAD_ENV, bounded_process, file_sha, frozen_model, verify_worker_limits
from modules.direct_path.pack import SCHEMA, load_pack
from modules.direct_path import pack
from modules.direct_path.prototype import CORE5, DAY_US, E5, SmallBudgetHead
from modules.direct_path.training import WINDOWS, common_standardizer, stamp


def make_pack(root):
    entries = []
    for tag, (start, end) in WINDOWS.items():
        d = np.arange(stamp(start), stamp(end), DAY_US, dtype=np.int64)
        t = len(d)
        events = d + 1
        marks = np.full(t, 100.)
        rates = np.full(t, -.0001)
        a = dict(decision_us=d, available_us=d.copy(),
                 target_available_us=np.repeat(d[:, None], 5, axis=1),
                 expert_targets=np.zeros((t, 5, 5)), eligible=np.ones((t, 5), bool),
                 past_returns30=np.zeros((t, 30, 5)),
                 market13=np.full((t, 13), 1000. if tag == "H1_VALIDATE" else 2.),
                 prices=np.full((t + 1, 5), 100.), funding_coeff=np.zeros((t, 5)),
                 greedy_request=np.tile(np.eye(5)[1], (t, 1)),
                 label_available_us=d + DAY_US, funding_event_us=events,
                 funding_symbol_index=np.zeros(t, np.int64), funding_mark_close_us=d,
                 funding_mark_price=marks, funding_rate_fraction=rates)
        a["funding_coeff"][:, 0] = marks * rates
        name = tag + ".npz"
        np.savez_compressed(root / name, **a)
        entries.append(dict(window_id=tag, file=name, bytes=(root / name).stat().st_size,
                            sha256=file_sha(root / name), funding_events_complete=True,
                            binding={key: "a" * 64 for key in ("teacher_jsonl_sha256",
                                     "expert_identity_sha256", "mapper_sha256",
                                     "market_binding_sha256")}))
    manifest = dict(schema=SCHEMA, source_commit="b" * 40,
                    symbol_order=list(CORE5), expert_order=list(E5), fragments=entries)
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path, file_sha(path)


def rewrite_npz(root, mutate):
    path = root / "manifest.json"
    m = json.loads(path.read_text())
    e = m["fragments"][0]
    file = root / e["file"]
    with np.load(file, allow_pickle=False) as z:
        a = {k: z[k].copy() for k in z.files}
    mutate(a)
    np.savez_compressed(file, **a)
    e.update(bytes=file.stat().st_size, sha256=file_sha(file))
    path.write_text(json.dumps(m))
    return file_sha(path)


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="direct-path-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path, self.sha = make_pack(self.root)

    def test_adapter_and_training_only_standardizer(self):
        _, fs = load_pack(self.path, self.sha)
        self.assertEqual([len(f["contexts"]) for f in fs], [30, 31, 121, 61])
        mean, scale = common_standardizer(fs[:3])
        np.testing.assert_array_equal(mean[:13], np.full(13, 2.))
        np.testing.assert_array_equal(scale[:13], np.ones(13))
        self.assertEqual(fs[0]["funding_coeff"][0, 0], -.01)

    def test_actual_bytes_not_just_hash_strings(self):
        with (self.root / "BEAR2022NOV.npz").open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(ValueError, "binding failed"):
            load_pack(self.path, self.sha)
        with self.assertRaisesRegex(ValueError, "approved manifest"):
            load_pack(self.path, "0" * 64)

    def test_verified_snapshot_cannot_be_reopened_as_different_arrays(self):
        original = pack.checked_npz_bytes
        changed = False

        def mutate_after_hash(raw):
            nonlocal changed
            if not changed:
                changed = True
                rewrite_npz(self.root, lambda a: a["market13"].__setitem__(slice(None), 9.))
            return original(raw)

        with patch.object(pack, "checked_npz_bytes", side_effect=mutate_after_hash):
            _, fs = load_pack(self.path, self.sha)
        self.assertEqual(fs[0]["contexts"][0].market13[0], 2.)
        self.assertNotEqual(fs[0]["binding"]["input_npz_sha256"],
                            file_sha(self.root / "BEAR2022NOV.npz"))

    def test_label_maturity_cannot_be_relaxed(self):
        sha = rewrite_npz(self.root, lambda a: a["label_available_us"].__setitem__(0, a["decision_us"][0] + 1))
        with self.assertRaisesRegex(ValueError, "mature"):
            load_pack(self.path, sha)

    def test_funding_sign_strict_past_and_coverage(self):
        sha = rewrite_npz(self.root, lambda a: a["funding_coeff"].__imul__(-1))
        with self.assertRaisesRegex(ValueError, "signed strict-past"):
            load_pack(self.path, sha)
        make_pack(self.root)
        sha = rewrite_npz(self.root, lambda a: a["funding_mark_close_us"].__setitem__(0, a["funding_event_us"][0]))
        with self.assertRaisesRegex(ValueError, "strictly past"):
            load_pack(self.path, sha)
        make_pack(self.root)
        m = json.loads(self.path.read_text())
        m["fragments"][0]["funding_events_complete"] = False
        self.path.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "complete funding"):
            load_pack(self.path, file_sha(self.path))

    def test_funding_tied_boundary_uses_prior_interval(self):
        def change(a):
            a["funding_event_us"][:] = a["decision_us"] + DAY_US
        sha = rewrite_npz(self.root, change)
        _, fs = load_pack(self.path, sha)
        np.testing.assert_array_equal(fs[0]["funding_coeff"][:, 0], np.full(30, -.01))

    def test_roles_order_and_explicit_field_map(self):
        m = json.loads(self.path.read_text())
        m["symbol_order"] = m["symbol_order"][::-1]
        self.path.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "order"):
            load_pack(self.path, file_sha(self.path))
        make_pack(self.root)
        sha = rewrite_npz(self.root, lambda a: a.__setitem__("native_close", a.pop("prices")))
        m = json.loads(self.path.read_text())
        m["fragments"][0]["field_map"] = {"prices": "native_close"}
        self.path.write_text(json.dumps(m))
        load_pack(self.path, file_sha(self.path))

    def test_default_cli_check_has_zero_fits(self):
        out = self.root / "checked"
        result = subprocess.run([sys.executable, "-m", "modules.direct_path.entry",
                                 "--manifest", str(self.path), "--approved-pack-sha256", self.sha,
                                 "--output", str(out)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        pair = json.loads((out / "pair.json").read_text())
        self.assertEqual(pair["status"], "INPUT_VALIDATED_NOT_TRAINED")
        self.assertEqual(pair["fits_started"], 0)
        self.assertFalse(any(out.glob("*REQUESTS*")))
        check = json.loads((out / "check.json").read_text())
        self.assertLessEqual(check["address_limit_bytes"], 900000000)
        self.assertLessEqual(len(check["cpu_affinity"]), 2)
        self.assertLessEqual(check["peak_rss_bytes"], 1000000000)
        again = subprocess.run(result.args, capture_output=True, timeout=10)
        self.assertNotEqual(again.returncode, 0)  # no overwrite/resume


class SupervisorTests(unittest.TestCase):
    def test_unlimited_worker_refused_before_numpy_or_fitting(self):
        env = dict.fromkeys(THREAD_ENV, "1")
        env["DIRECT_PATH_SUPERVISED"] = "1"
        with patch.dict(os.environ, env), patch("os.sched_getaffinity", return_value={0, 1}):
            with patch("resource.getrlimit", return_value=(-1, -1)):
                with self.assertRaisesRegex(ValueError, "hard-limited"):
                    verify_worker_limits()
            with patch("resource.getrlimit", return_value=(900000000, 900000000)):
                verify_worker_limits()

    def test_hard_wall_and_rss_guard_without_fits(self):
        with tempfile.TemporaryDirectory(prefix="direct-path-limit-test-") as tmp:
            r = bounded_process([sys.executable, "-c", "import time; time.sleep(5)"],
                                Path(tmp) / "wall.log", wall_seconds=.12)
            self.assertEqual(r["status"], "STOP_HARD_WALL_LIMIT")
            self.assertEqual(r["returncode"], -9)
            self.assertLess(r["wall_seconds"], 1.)
            r = bounded_process([sys.executable, "-c", "import time; time.sleep(5)"],
                                Path(tmp) / "rss.log", wall_seconds=2, rss_limit=1)
            self.assertEqual(r["status"], "STOP_RSS_LIMIT")
            self.assertEqual(r["returncode"], -9)
            r = bounded_process([sys.executable, "-c", "import threading,time; "
                                 "[threading.Thread(target=lambda: time.sleep(5)).start() for _ in range(3)]; time.sleep(5)"],
                                Path(tmp) / "thread.log", wall_seconds=2)
            self.assertEqual(r["status"], "STOP_THREAD_LIMIT")
            self.assertEqual(r["returncode"], -9)

    def test_frozen_inference_roundtrip_only(self):
        with tempfile.TemporaryDirectory(prefix="direct-path-model-test-") as tmp:
            head = SmallBudgetHead(np.zeros(43), np.ones(43))  # seeded, NEVER fitted
            path = Path(tmp) / "synthetic_untrained.npz"
            np.savez(path, mean=head.mean, scale=head.scale, **head.parameters)
            frozen = frozen_model(path, file_sha(path))
            np.testing.assert_array_equal(head.forward(np.ones((3, 43)))[0],
                                          frozen.forward(np.ones((3, 43)))[0])
            with self.assertRaises(ValueError):
                frozen.parameters["w1"][0, 0] = 0
            with self.assertRaisesRegex(ValueError, "byte binding"):
                frozen_model(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
