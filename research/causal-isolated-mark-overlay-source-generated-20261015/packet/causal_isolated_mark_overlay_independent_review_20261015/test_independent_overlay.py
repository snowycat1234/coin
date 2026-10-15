"""Independent fake-only contract/adversarial tests; no actual price rows."""
from dataclasses import asdict, FrozenInstanceError, replace
from decimal import Decimal
from hashlib import sha256
import json
import unittest

import overlay as m
from metadata_binding import (ACTUAL27_ORIGINAL_OPEN_POINTS,
                              validate_actual27_metadata_bytes)

B, M = m.FIXTURE_BASE_MS, m.MINUTE


def fake(symbol="FIXTURE_ETH", minute=1, price="00017.20000000000000000001", **kw):
    t = B + minute * M
    value = m.GenuineObservation("independent-" + symbol + "-" + str(minute), symbol,
        t, t + M - 1, t + M, t + M, t + M, price, "c" * 64,
        "independent-row-" + symbol + "-" + str(minute))
    return replace(value, **kw)


def missing(symbol="FIXTURE_ETH", minute=2):
    return next(h for h in m.FIXTURE_HOLES
                if h.symbol == symbol and h.minute_open_ms == B + minute * M)


def complete_fake(two=True):
    keys = {(h.symbol, h.minute_open_ms) for h in m.FIXTURE_HOLES}
    output = {}
    for h in m.FIXTURE_HOLES:
        if (h.symbol, h.minute_open_ms - M) not in keys:
            minute = (h.minute_open_ms - B) // M
            for shift in ((1, 2) if two else (1,)):
                o = fake(h.symbol, minute - shift, str(123 + minute - shift) + ".0000001")
                output[(o.symbol, o.minute_open_ms)] = o
    return tuple(output.values())


def single(obs=None):
    return m.build_generated_overlay((fake(),) if obs is None else obs,
                                      (missing(),), as_of_ms=B + 3 * M)


def digest(x):
    return sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def rehash_records(batch, records):
    hashes = tuple(digest(asdict(r)) for r in records)
    commitment = digest({"policy_id": m.POLICY_ID, "policy_sha256": m.POLICY_SHA256,
        "fixture_allowlist_sha256": m.FIXTURE_ALLOWLIST_SHA256,
        "record_sha256": hashes, "quality_sidecar": [asdict(x) for x in batch.quality_sidecar]})
    return replace(batch, records=records, record_sha256=hashes, overlay_sha256=commitment)


def rehash(batch, record):
    return rehash_records(batch, (record,))


class IndependentFakeOnlyTests(unittest.TestCase):
    def test_exact_shape_and_unshifted_open_identity(self):
        self.assertEqual(len(m.FIXTURE_HOLES), 27)
        runs = []
        for s in {h.symbol for h in m.FIXTURE_HOLES}:
            ts = sorted(h.minute_open_ms for h in m.FIXTURE_HOLES if h.symbol == s)
            n = 1
            for a, b in zip(ts, ts[1:]):
                if b - a == M:
                    n += 1
                else:
                    runs.append(n); n = 1
            runs.append(n)
        self.assertEqual(sorted(runs), [1, 1, 1, 1, 5, 5, 6, 7])
        batch = m.build_generated_overlay(complete_fake(), m.FIXTURE_HOLES, as_of_ms=B + 1100 * M)
        self.assertEqual({(r.symbol, r.minute_open_ms) for r in batch.records},
                         {(h.symbol, h.minute_open_ms) for h in m.FIXTURE_HOLES})
        self.assertEqual(len({r.minute_open_ms for r in batch.records}), 11)

    def test_every_prefix_record_and_receipt_is_invariant(self):
        obs = complete_fake()
        final = m.build_generated_overlay(obs, m.FIXTURE_HOLES, as_of_ms=B + 1100 * M)
        for clock in sorted({h.minute_open_ms + M for h in m.FIXTURE_HOLES}):
            prefix = m.build_generated_overlay(tuple(o for o in obs if o.installed_at_ms <= clock),
                tuple(h for h in m.FIXTURE_HOLES if h.minute_open_ms + M <= clock), as_of_ms=clock)
            expected = tuple(r for r in final.records if r.completed_at_ms <= clock)
            self.assertEqual(prefix.records, expected)
            self.assertEqual(prefix.record_sha256, final.record_sha256[:len(expected)])

    def test_future_valid_price_perturbations_and_snapshot_do_not_revise(self):
        baseline = single()
        for text in ("0.00000000000000000001", "99999999999999999999999999"):
            obs = (fake(), fake(minute=3, price=text))
            for asof in (B + 4 * M, B + 999999 * M):
                self.assertEqual(baseline, m.build_generated_overlay(obs, (missing(),), as_of_ms=asof))

    def test_available_and_installed_at_boundary_equal_pass_one_ms_later_fail(self):
        clock = B + 3 * M
        o = fake(available_at_ms=clock, installed_at_ms=clock)
        self.assertEqual(single((o,)).records[0].anchor_installed_at_ms, clock)
        for changes in ({"installed_at_ms": clock + 1},
                        {"available_at_ms": clock + 1, "installed_at_ms": clock + 1}):
            with self.assertRaises(m.OverlayRejected): single((replace(o, **changes),))

    def test_open_inclusive_close_and_nominal_completion_strictness(self):
        h = missing()
        for clock in (h.minute_open_ms, h.minute_open_ms + M - 1):
            with self.assertRaises(m.OverlayRejected):
                m.build_generated_overlay((fake(),), (h,), as_of_ms=clock)
        r = single().records[0]
        self.assertEqual((r.minute_open_ms, r.source_close_inclusive_ms, r.completed_at_ms),
                         (h.minute_open_ms, h.minute_open_ms + M - 1, h.minute_open_ms + M))
        self.assertEqual(r.evaluation_clock_ms, r.completed_at_ms)

    def test_seven_run_same_genuine_anchor_and_strictly_increasing_old_age(self):
        hs = tuple(h for h in m.FIXTURE_HOLES if h.symbol == "FIXTURE_ETH"
                   and B + 20 * M <= h.minute_open_ms <= B + 26 * M)
        o = fake(minute=19, available_at_ms=B + 20 * M + 1, installed_at_ms=B + 20 * M + 2)
        rs = m.build_generated_overlay((o,), hs, as_of_ms=B + 27 * M).records
        self.assertEqual([r.anchor_age_ms for r in rs], [M * i for i in range(1, 8)])
        for r in rs:
            self.assertEqual(r.price_text, o.price_text)
            self.assertEqual(r.anchor_observation_id, o.observation_id)
            self.assertEqual(r.anchor_source_sha256, o.source_sha256)
            self.assertEqual(r.anchor_source_record_id, o.source_record_id)
            self.assertEqual(r.source_freshness_clock_ms, o.available_at_ms)
            self.assertEqual(r.anchor_completed_at_ms, o.completed_at_ms)

    def test_true_recovery_is_untouched_and_later_hole_uses_new_genuine(self):
        obs = complete_fake()
        recovery = fake(minute=27, price="51.00000000001")
        newer = fake(minute=56, price="62.00000000002")
        inputs = obs + (recovery, newer)
        before = tuple(asdict(x) for x in inputs)
        # Replace the same synthetic genuine cell with a newer explicit record,
        # never a derived overlay record.
        inputs = tuple(x for x in inputs if not (x.minute_open_ms == newer.minute_open_ms
                       and x.symbol == newer.symbol and x is not newer))
        batch = m.build_generated_overlay(inputs, m.FIXTURE_HOLES, as_of_ms=B + 1100 * M)
        later = next(r for r in batch.records if r.symbol == newer.symbol and r.minute_open_ms == B + 57 * M)
        self.assertEqual(later.anchor_observation_id, newer.observation_id)
        self.assertEqual(later.price_text, newer.price_text)
        self.assertEqual(tuple(asdict(x) for x in obs + (recovery, newer)), before)
        self.assertNotIn(recovery.minute_open_ms, [r.minute_open_ms for r in batch.records if r.symbol == recovery.symbol])

    def test_derived_anchor_objects_and_quality_cannot_be_promoted(self):
        with self.assertRaises(m.OverlayRejected): single(single().records)
        for q in (m.METHOD, m.QUALITY, "DIRECT", "ESTIMATED"):
            with self.assertRaises(m.OverlayRejected): single((fake(source_quality=q),))

    def test_known_missing_cell_cannot_be_declared_genuine_for_a_subset(self):
        hs = tuple(h for h in m.FIXTURE_HOLES if h.symbol == "FIXTURE_ETH"
                   and B + 21 * M <= h.minute_open_ms <= B + 26 * M)
        with self.assertRaises(m.OverlayRejected):
            m.build_generated_overlay((fake(minute=20),), hs, as_of_ms=B + 27 * M)
        # The invariant must also hold at the exported fake audit boundary,
        # even when unkeyed integrity hashes are recomputed.
        hs = (missing(minute=21),)
        batch = m.build_generated_overlay((fake(minute=19),), hs, as_of_ms=B + 22 * M)
        r = replace(batch.records[0], anchor_minute_open_ms=B+20*M,
                    anchor_completed_at_ms=B+21*M, anchor_available_at_ms=B+21*M,
                    anchor_installed_at_ms=B+21*M, anchor_age_ms=M,
                    source_freshness_clock_ms=B+21*M)
        with self.assertRaises(m.OverlayRejected): m.audit_saved_generated_events(rehash(batch, r), ())

    def test_exact_positive_finite_representation_copy_and_invalid_rejection(self):
        for text in ("0001.23000000000000000000000001", "1E-100", "9.9000000000000"):
            self.assertEqual(single((fake(price=text),)).records[0].price_text, text)
        for text in (None, True, False, 1, 1.0, "", "0", "-0", "-1", "NaN", "sNaN", "Infinity", "-Infinity", "bad"):
            with self.assertRaises(m.OverlayRejected): single((fake(price=text),))

    def test_invalid_missing_or_bool_clocks_and_ids_reject(self):
        for field in ("minute_open_ms", "source_close_inclusive_ms", "completed_at_ms", "available_at_ms", "installed_at_ms"):
            for value in (None, True, -1, 1.0):
                with self.assertRaises(m.OverlayRejected): single((fake(**{field: value}),))
        for kw in ({"observation_id": "bad/id"}, {"source_sha256": "x" * 64}, {"source_record_id": ""}):
            with self.assertRaises(m.OverlayRejected): single((fake(**kw),))

    def test_duplicates_conflicts_and_present_target_reject(self):
        for obs in ((fake(), fake()), (fake(), replace(fake(), price_text="88")),
                    (fake(), fake(minute=0, source_record_id=fake().source_record_id)),
                    (fake(), fake(minute=2, available_at_ms=B + 100 * M, installed_at_ms=B + 100 * M))):
            with self.assertRaises(m.OverlayRejected): single(obs)
        with self.assertRaises(m.OverlayRejected):
            m.build_generated_overlay((fake(),), (missing(), missing()), as_of_ms=B + 3 * M)

    def test_unlisted_long_or_full_month_and_nonmissing_cells_never_filled(self):
        for count in (28, 40320):
            with self.assertRaises(m.OverlayRejected):
                m.build_generated_overlay((fake(),), (missing(),) * count, as_of_ms=B + 1100 * M)
        for kw in ({"original_cell_missing": False}, {"original_cell_missing": 1},
                   {"minute_open_ms": B + 3 * M}, {"proof_id": "other"},
                   {"domain": "TRADE"}, {"selected_field": "volume"}, {"selected_field": "OHLCV"}):
            with self.assertRaises(m.OverlayRejected):
                m.build_generated_overlay((fake(),), (replace(missing(), **kw),), as_of_ms=B + 1100 * M)
        with self.assertRaises(m.OverlayRejected): single((fake(minute=0),))

    def test_requested_open_identity_requires_strict_integer_even_if_float_equal(self):
        for value in (float(missing().minute_open_ms), str(missing().minute_open_ms), True):
            with self.assertRaises(m.OverlayRejected):
                m.build_generated_overlay((fake(),), (replace(missing(), minute_open_ms=value),), as_of_ms=B+3*M)

    def test_actual_allowlist_and_authority_flags_cannot_enter_generated_builder(self):
        for symbol, clock in ACTUAL27_ORIGINAL_OPEN_POINTS:
            with self.assertRaises(m.OverlayRejected):
                m.build_generated_overlay((), (m.MissingCell(symbol, clock, "fake", "d" * 64),), as_of_ms=2_000_000_000_000)
        for flag in ("allow_actual", "historical", "financial_GO", "source_admission"):
            with self.assertRaises(TypeError):
                m.build_generated_overlay((fake(),), (missing(),), as_of_ms=B + 3 * M, **{flag: True})

    def test_immutable_separate_unknown_sidecar_and_no_authority(self):
        batch = single()
        self.assertIs(type(batch.records), tuple)
        with self.assertRaises(FrozenInstanceError): batch.records[0].price_text = "10"
        for row in batch.quality_sidecar:
            self.assertEqual(row.quality, "UNKNOWN_OR_DERIVED")
            self.assertEqual(row.actual_historical_arrival_status, "UNKNOWN_NOT_CERTIFIED_BY_THIS_POLICY")
            self.assertFalse(row.new_increase_source_eligible)
            self.assertFalse(row.topup_source_eligible)
            self.assertFalse(row.certifies_liquidation)
            self.assertFalse(row.certifies_no_liquidation)

    def test_order_replay_and_per_record_hashes_are_exact(self):
        obs = complete_fake()
        a = m.build_generated_overlay(obs, m.FIXTURE_HOLES, as_of_ms=B + 1100 * M)
        b = m.build_generated_overlay(tuple(reversed(obs)), tuple(reversed(m.FIXTURE_HOLES)), as_of_ms=B + 1100 * M)
        self.assertEqual(a, b)
        self.assertEqual(a.record_sha256, tuple(digest(asdict(r)) for r in a.records))

    def test_fixed_last_two_past_installed_only_and_missing_anchor_pending(self):
        obs = (fake(minute=0, price="9.9000000000"), fake(price="10.000000001"), fake(minute=3, price="999999"))
        row = m.build_generated_past_only_sensitivity(single(obs), obs)[0]
        self.assertEqual((row.lower_reference_price_text, row.upper_reference_price_text), (obs[0].price_text, obs[1].price_text))
        self.assertEqual(row.genuine_observation_ids, (obs[0].observation_id, obs[1].observation_id))
        self.assertFalse(row.guaranteed_bound_on_missing_price)
        self.assertFalse(row.certifies_liquidation)
        self.assertFalse(row.certifies_no_liquidation)
        self.assertIn("BLOCKED", row.actual_sensitivity_admission)
        delayed = replace(obs[0], available_at_ms=B + 4 * M, installed_at_ms=B + 4 * M)
        pending = m.build_generated_past_only_sensitivity(single((delayed, obs[1])), (delayed, obs[1]))[0]
        self.assertIn("PENDING", pending.status)
        self.assertIsNone(pending.lower_reference_price_text)

    def test_saved_fake_events_classify_all_categories_without_claiming_actual_impact(self):
        h = missing(); clock = h.minute_open_ms + M
        events = tuple(m.SavedGeneratedEvent("ind-event-" + k, h.symbol, clock, k,
            **({"position_start_ms": clock - 1, "position_end_exclusive_ms": clock + 1}
               if k == "POSITION" else {"mark_reference_open_ms": h.minute_open_ms})) for k in m.EVENT_KINDS)
        report = m.audit_saved_generated_events(single(), events)
        row = report["rows"][0]
        self.assertEqual(sum(len(v) for v in row["saved_generated_overlap_ids"].values()), 7)
        self.assertEqual(report["actual_event_review"], "PENDING")
        self.assertEqual(row["actual_positions_fills_funding_risk_terminal_overlap"], "PENDING_ACTUAL_SAVED_EVIDENCE")
        self.assertEqual(row["quantity_sensitivity"], "PENDING_ACTUAL_EVIDENCE")
        self.assertEqual(row["cashflow_sensitivity"], "PENDING_ACTUAL_EVIDENCE")
        self.assertFalse(row["claim_of_negligible_impact"])

    def test_saved_event_position_end_exclusive_and_unknown_mapping_are_explicit(self):
        h = missing(); c = h.minute_open_ms + M
        events = (m.SavedGeneratedEvent("end", h.symbol, c, "POSITION", position_start_ms=c-M, position_end_exclusive_ms=c),
                  m.SavedGeneratedEvent("start", h.symbol, c, "POSITION", position_start_ms=c, position_end_exclusive_ms=c+M),
                  m.SavedGeneratedEvent("unknown", h.symbol, c, "FUNDING"))
        row = m.audit_saved_generated_events(single(), events)["rows"][0]
        self.assertEqual(row["saved_generated_overlap_ids"]["POSITION"], ["start"])
        self.assertEqual(row["saved_generated_events_without_mark_mapping"], ["unknown"])

    def test_saved_event_invalid_uncompleted_reference_and_duplicates_reject(self):
        e = m.SavedGeneratedEvent("saved", "FIXTURE_ETH", B + 3 * M, "FUNDING", B + 2 * M)
        for events in ((e, e), (replace(e, event_clock_ms=B+3*M-1),),
                       (replace(e, event_clock_ms=True),), (replace(e, symbol="ETHUSDT"),)):
            with self.assertRaises(m.OverlayRejected): m.audit_saved_generated_events(single(), events)

    def test_rehashed_structurally_malformed_fake_receipts_reject(self):
        batch = single(); r = batch.records[0]
        variants = ({"price_text": "NaN"}, {"price_text": "0"}, {"price_text": True},
            {"anchor_age_ms": -1}, {"evaluation_clock_ms": 0},
            {"anchor_available_at_ms": B + 100 * M}, {"anchor_installed_at_ms": B + 100 * M},
            {"source_freshness_clock_ms": r.completed_at_ms}, {"source_close_inclusive_ms": r.minute_open_ms},
            {"anchor_source_sha256": "bad"}, {"anchor_source_record_id": ""},
            {"anchor_completed_at_ms": r.completed_at_ms}, {"anchor_minute_open_ms": r.minute_open_ms})
        for changes in variants:
            with self.subTest(changes=changes):
                forged = rehash(batch, replace(r, **changes))
                with self.assertRaises(m.OverlayRejected): m.audit_saved_generated_events(forged, ())

    def test_shared_anchor_cross_record_identity_value_conflicts_reject(self):
        hs = (missing(minute=20), missing(minute=21))
        batch = m.build_generated_overlay((fake(minute=19),), hs, as_of_ms=B+22*M)
        variants = ({"price_text": "999"}, {"anchor_observation_id": "other-observation"},
                    {"anchor_source_record_id": "other-source-row"}, {"anchor_source_sha256": "d"*64},
                    {"anchor_available_at_ms": B+20*M+1, "anchor_installed_at_ms": B+20*M+1,
                     "source_freshness_clock_ms": B+20*M+1})
        for changes in variants:
            with self.subTest(changes=changes):
                records = (batch.records[0], replace(batch.records[1], **changes))
                with self.assertRaises(m.OverlayRejected):
                    m.audit_saved_generated_events(rehash_records(batch, records), ())

    def test_actual_metadata_is_pinned_only_and_not_historical_arrival_certification(self):
        # Supplied by the runner before its runtime I/O guard.
        report = validate_actual27_metadata_bytes(*METADATA_BLOBS)
        self.assertEqual((report.asset_minutes, report.unique_open_clocks), (27, 11))
        self.assertEqual((report.asset_specific_runs, report.isolated_single_minute_runs, report.longest_run_minutes), (8, 4, 7))
        self.assertEqual((report.prior_official_daily_attempts, report.prior_daily_added_rows), (5, 0))
        self.assertFalse(report.nominal_completion_certifies_historical_arrival)
        self.assertFalse(report.actual_application_enabled)
        self.assertTrue(report.raw_revalidation_pending)
        self.assertEqual(report.actual_price_values_loaded, 0)
        for i in range(3):
            modified = list(METADATA_BLOBS); modified[i] += b" "
            with self.assertRaises(m.OverlayRejected): validate_actual27_metadata_bytes(*modified)

