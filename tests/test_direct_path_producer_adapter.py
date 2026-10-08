"""Producer-schema receipt counterexamples. No fit or optimizer calls."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from modules.direct_path.data_adapter import FEATURE_NAMES, MARKET13, SCHEMA, load_training_and_validation
from modules.direct_path.entry import file_sha
from modules.direct_path.prototype import CORE5, DAY_US, E5
from tests.test_direct_path_entry import make_pack


def make_producer(root):
    path, _ = make_pack(root)
    m = json.loads(path.read_text())
    for entry in m["fragments"]:
        entry["binding"]["input_npz_sha256"] = "a" * 64
        p = root / entry["file"]
        with np.load(p, allow_pickle=False) as z:
            a = {k: z[k].copy() for k in z.files}
        d = a["decision_us"]
        t = len(d)
        events = [dict(symbol=CORE5[0], event_us=int(d[i] + 1), raw_rate=-.0001,
                       coefficient_included=True, mark_close_us=int(d[i]),
                       strictly_past_mark_price=100., coefficient_USDT_per_contract=-.01,
                       day_index=i) for i in range(t)]
        a["market_state13"] = a.pop("market13")
        a["market_state13_available_us"] = a.pop("available_us")
        a["expert_eligible"] = a.pop("eligible")
        for key in list(a):
            if key.startswith("funding_") and key != "funding_coeff":
                del a[key]
        a.update(symbol_order=np.array(CORE5), expert_order=np.array(E5),
                 price_close_us=np.r_[d, d[-1] + DAY_US], price_available_us=np.r_[d, d[-1] + DAY_US],
                 global_forced_terminal_day=np.arange(t) == t - 1)
        np.savez_compressed(p, **a)
        proof_name = entry["window_id"] + "_SOURCE_RECEIPT.json.gz"
        receipt = dict(window_id=entry["window_id"], binding=entry["binding"],
                       calendar=dict(start_us=int(d[0]), end_exclusive_us=int(d[-1] + DAY_US), days=t),
                       funding_events=events, teacher_row_receipts=[dict(decision_us=int(d[i]),
                       source_label_available_us=int(a["label_available_us"][i]),
                       candidate_request=a["greedy_request"][i].tolist(), source_row_SHA256="c" * 64,
                       source_optimization_allowed=i < t - 1) for i in range(t)])
        (root / proof_name).write_bytes(gzip.compress(json.dumps(receipt).encode(), mtime=0))
        entry.update(sha256=file_sha(p), bytes=p.stat().st_size, receipt_file=proof_name,
                     receipt_sha256=file_sha(root / proof_name), market13_order=list(MARKET13),
                     feature_names=FEATURE_NAMES)
    m.update(schema=SCHEMA, market13_order=list(MARKET13), feature_names=FEATURE_NAMES,
             feature_schema_SHA256=hashlib.sha256(json.dumps(FEATURE_NAMES, sort_keys=True).encode()).hexdigest(),
             separate_fresh_10k_wallets=True)
    index = root / "INDEX.json"
    index.write_text(json.dumps(m))
    return index, file_sha(index)


class ProducerAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="direct-path-producer-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index, self.sha = make_producer(self.root)

    def mutate_receipt(self, change):
        m = json.loads(self.index.read_text())
        e = m["fragments"][0]
        path = self.root / e["receipt_file"]
        receipt = json.loads(gzip.decompress(path.read_bytes()))
        change(receipt)
        path.write_bytes(gzip.compress(json.dumps(receipt).encode(), mtime=0))
        e["receipt_sha256"] = file_sha(path)
        self.index.write_text(json.dumps(m))
        return file_sha(self.index)

    def test_source_and_delivered_hashes_remain_distinct(self):
        train, validation, _ = load_training_and_validation(self.root, self.sha)
        self.assertEqual([len(f["contexts"]) for f in train] + [len(validation["contexts"])], [30, 31, 121, 61])
        self.assertEqual(train[0]["binding"]["input_npz_sha256"], "a" * 64)
        self.assertNotEqual(train[0]["delivered_input_npz_sha256"], "a" * 64)

    def test_sign_and_same_time_mark_cannot_be_changed(self):
        sha = self.mutate_receipt(lambda r: r["funding_events"][0].update(raw_rate=.0001))
        with self.assertRaisesRegex(ValueError, "signed funding"):
            load_training_and_validation(self.root, sha)
        make_producer(self.root)
        sha = self.mutate_receipt(lambda r: r["funding_events"][0].update(
            mark_close_us=r["funding_events"][0]["event_us"]))
        with self.assertRaisesRegex(ValueError, "strictly-past"):
            load_training_and_validation(self.root, sha)

    def test_named_feature_order_and_teacher_clock_receipt(self):
        m = json.loads(self.index.read_text())
        m["feature_names"] = m["feature_names"][::-1]
        self.index.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "feature schema"):
            load_training_and_validation(self.root, file_sha(self.index))
        make_producer(self.root)
        sha = self.mutate_receipt(lambda r: r["teacher_row_receipts"][0].update(
            source_label_available_us=r["teacher_row_receipts"][0]["decision_us"] + 1))
        with self.assertRaisesRegex(ValueError, "maturity receipt"):
            load_training_and_validation(self.root, sha)


if __name__ == "__main__":
    unittest.main()
