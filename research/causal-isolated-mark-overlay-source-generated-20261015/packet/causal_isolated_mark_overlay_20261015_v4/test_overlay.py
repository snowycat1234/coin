"""Generated-only regression tests. No historical observation or financial import."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
from decimal import Decimal
import unittest

from overlay import (
    FIXTURE_BASE_MS as B, FIXTURE_HOLES, FIXTURE_ALLOWLIST_SHA256, MINUTE as M,
    GenuineObservation, MissingCell, OverlayRejected, SavedGeneratedEvent,
    build_generated_overlay as build, build_generated_past_only_sensitivity as sensitivity,
    audit_saved_generated_events as audit, METHOD, QUALITY, EVENT_KINDS,
)


def observation(symbol="FIXTURE_ETH", offset=1, price="001.23000000000000000000000001", **changes):
    opened = B + offset * M
    o = GenuineObservation(f"generated-{symbol}-{offset}", symbol, opened, opened + M - 1,
        opened + M, opened + M, opened + M, price, "a" * 64,
        f"generated-source-row-{symbol}-{offset}")
    return replace(o, **changes)


def hole(symbol="FIXTURE_ETH", offset=2):
    return next(h for h in FIXTURE_HOLES if h.symbol == symbol and h.minute_open_ms == B + offset * M)


def all_anchors(two=True):
    missing = {(h.symbol, h.minute_open_ms) for h in FIXTURE_HOLES}
    anchors = {}
    for h in FIXTURE_HOLES:
        if (h.symbol, h.minute_open_ms - M) in missing:
            continue
        offset = (h.minute_open_ms - B) // M
        for before in ((2, 1) if two else (1,)):
            o = observation(h.symbol, offset - before, str(100 + offset - before) + ".00000000")
            anchors[(o.symbol, o.minute_open_ms)] = o
    return tuple(anchors.values())


class GeneratedCausalOverlayTests(unittest.TestCase):
    def one(self, obs=None, h=None, asof=None):
        h = hole() if h is None else h
        return build((observation(),) if obs is None else obs, (h,),
                     as_of_ms=h.minute_open_ms + M if asof is None else asof)

    def test_exact_27_shape_eight_runs_four_singles(self):
        self.assertEqual(len(FIXTURE_HOLES), 27)
        lengths=[]
        for symbol in sorted({h.symbol for h in FIXTURE_HOLES}):
            points=sorted(h.minute_open_ms for h in FIXTURE_HOLES if h.symbol==symbol)
            n=1
            for a,b in zip(points,points[1:]):
                if b==a+M:n+=1
                else:lengths.append(n);n=1
            lengths.append(n)
        self.assertEqual(sorted(lengths), [1,1,1,1,5,5,6,7])
        batch=build(all_anchors(),FIXTURE_HOLES,as_of_ms=B+1100*M)
        self.assertEqual(len(batch.records),27)
        self.assertEqual(batch.fixture_allowlist_sha256,FIXTURE_ALLOWLIST_SHA256)

    def test_prefix_invariance_every_completion(self):
        obs=all_anchors()
        final=build(obs,FIXTURE_HOLES,as_of_ms=B+1100*M)
        for clock in sorted({h.minute_open_ms+M for h in FIXTURE_HOLES}):
            hs=tuple(h for h in FIXTURE_HOLES if h.minute_open_ms+M<=clock)
            prefix=tuple(o for o in obs if o.installed_at_ms<=clock)
            at=build(prefix,hs,as_of_ms=clock)
            expected=tuple(r for r in final.records if r.completed_at_ms<=clock)
            self.assertEqual(at.records,expected)
            self.assertEqual(at.record_sha256,final.record_sha256[:len(expected)])

    def test_future_perturbation_invariance(self):
        future=observation(offset=3,price="99999999999999999999999999")
        self.assertEqual(self.one(),self.one((future,observation())))
        self.assertEqual(self.one((future,observation())),
                         self.one((replace(future,price_text="0.00000000000000001"),observation())))

    def test_causal_available_and_installed_clock(self):
        h=hole();clock=h.minute_open_ms+M
        self.assertEqual(self.one((replace(observation(),available_at_ms=clock,installed_at_ms=clock),)).records[0].price_text,
                         observation().price_text)
        for field in ("available_at_ms","installed_at_ms"):
            changes={"installed_at_ms":clock+1}
            if field=="available_at_ms":changes[field]=clock+1
            with self.assertRaises(OverlayRejected):self.one((replace(observation(),**changes),))

    def test_no_early_target_at_open_or_inclusive_close(self):
        h=hole()
        for clock in (h.minute_open_ms,h.minute_open_ms+M-1):
            with self.assertRaises(OverlayRejected):self.one(asof=clock)
        self.assertEqual(self.one().records[0].completed_at_ms,h.minute_open_ms+M)

    def test_multihole_original_anchor_never_derived(self):
        hs=tuple(h for h in FIXTURE_HOLES if h.symbol=="FIXTURE_ETH" and B+20*M<=h.minute_open_ms<=B+26*M)
        o=observation(offset=19)
        batch=build((o,),hs,as_of_ms=B+27*M)
        self.assertEqual(len(batch.records),7)
        self.assertEqual({r.anchor_observation_id for r in batch.records},{o.observation_id})
        self.assertEqual([r.anchor_age_ms for r in batch.records],[i*M for i in range(1,8)])
        self.assertEqual({r.source_freshness_clock_ms for r in batch.records},{o.available_at_ms})

    def test_genuine_recovery_remains_genuine_unchanged(self):
        anchors=list(all_anchors());recovery=observation(offset=27,price="98.7654321000")
        originals=deepcopy(anchors+[recovery])
        batch=build(anchors+[recovery],FIXTURE_HOLES,as_of_ms=B+1100*M)
        self.assertEqual(anchors+[recovery],originals)
        self.assertNotIn(recovery.minute_open_ms,[r.minute_open_ms for r in batch.records if r.symbol==recovery.symbol])
        self.assertEqual(recovery.source_quality,"GENUINE_MARK_SOURCE")
        self.assertEqual(recovery.available_at_ms,B+28*M)

    def test_exact_source_representation_no_financial_rounding(self):
        for text in ("0001.23000000000000000000000000000001","1E-100","100.00000000000000000"):
            result=self.one((observation(price=text),))
            self.assertEqual(result.records[0].price_text,text)

    def test_no_input_mutation_and_immutable_output(self):
        obs=[observation()];holes=[hole()];before=deepcopy((obs,holes))
        result=build(obs,holes,as_of_ms=B+3*M)
        self.assertEqual((obs,holes),before)
        with self.assertRaises(FrozenInstanceError):result.records[0].price_text="2"
        with self.assertRaises(FrozenInstanceError):result.quality_sidecar[0].quality="DIRECT"

    def test_present_genuine_overwrite_rejected_even_if_later(self):
        for lag in (0,100000):
            target=observation(offset=2,available_at_ms=B+3*M+lag,installed_at_ms=B+3*M+lag)
            with self.assertRaises(OverlayRejected):self.one((observation(),target))

    def test_unlisted_hole_and_unlisted_long_run_reject(self):
        for offset in (3,19,27,100000):
            with self.assertRaises(OverlayRejected):self.one(h=replace(hole(),minute_open_ms=B+offset*M))
        with self.assertRaises(OverlayRejected):self.one((observation(offset=0),))

    def test_wide_and_fullmonth_gap_rejected(self):
        for count in (28,40320,44640):
            hs=[replace(hole(),minute_open_ms=B+i*M) for i in range(count)]
            with self.assertRaises(OverlayRejected):build((observation(),),hs,as_of_ms=B+(count+1)*M)

    def test_trade_volume_and_fabricated_ohlcv_reject(self):
        for changes in ({"domain":"TRADE"},{"selected_field":"volume"},{"selected_field":"OHLCV"}):
            with self.assertRaises(OverlayRejected):self.one(h=replace(hole(),**changes))
            with self.assertRaises(OverlayRejected):self.one((replace(observation(),**changes),))

    def test_absence_proof_and_missingness_must_match(self):
        for changes in ({"proof_sha256":"b"*64},{"proof_id":"invented-proof"},{"original_cell_missing":False}):
            with self.assertRaises(OverlayRejected):self.one(h=replace(hole(),**changes))

    def test_missing_invalid_nonpositive_anchor_rejected(self):
        with self.assertRaises(OverlayRejected):self.one(())
        for text in ("", "0", "-1", "NaN", "Infinity", "not-a-number", None, 1.0):
            with self.assertRaises(OverlayRejected):self.one((observation(price=text),))

    def test_no_future_only_or_derived_anchor(self):
        with self.assertRaises(OverlayRejected):self.one((observation(offset=3),))
        for quality in (METHOD,QUALITY,"DIRECT","ESTIMATED"):
            with self.assertRaises(OverlayRejected):self.one((observation(source_quality=quality),))

    def test_duplicate_conflicting_observation_ids(self):
        o=observation()
        for other in (o,replace(o,price_text="2"),replace(o,minute_open_ms=B,source_close_inclusive_ms=B+M-1,completed_at_ms=B+M)):
            with self.assertRaises(OverlayRejected):self.one((o,other))

    def test_duplicate_cell_and_source_record_ids(self):
        o=observation()
        for other in (replace(o,observation_id="other"),
                      replace(observation(offset=0),source_record_id=o.source_record_id)):
            with self.assertRaises(OverlayRejected):self.one((o,other))

    def test_duplicate_requested_holes_reject(self):
        with self.assertRaises(OverlayRejected):build((observation(),),(hole(),hole()),as_of_ms=B+3*M)

    def test_explicit_open_close_mapping_and_clock_types(self):
        o=observation()
        for changes in ({"source_close_inclusive_ms":o.minute_open_ms},
                        {"completed_at_ms":o.source_close_inclusive_ms},
                        {"available_at_ms":o.completed_at_ms-1},
                        {"installed_at_ms":o.available_at_ms-1},
                        {"completed_at_ms":float(o.completed_at_ms)}):
            with self.assertRaises(OverlayRejected):self.one((replace(o,**changes),))
        for clock in (True,-1,1.0):
            with self.assertRaises(OverlayRejected):self.one(asof=clock)

    def test_quality_sidecar_blocks_new_increases_topups_no_liquidation_certificate(self):
        result=self.one()
        self.assertEqual(result.records[0].estimate_method,METHOD)
        self.assertEqual(result.records[0].quality,QUALITY)
        self.assertFalse(result.records[0].is_genuine)
        side=result.quality_sidecar[0]
        self.assertFalse(side.new_increase_source_eligible)
        self.assertFalse(side.topup_source_eligible)
        self.assertEqual(side.native_intent_lifecycle,"UNCHANGED_NOT_IMPLEMENTED_HERE")

    def test_deterministic_order_replay_and_commitments(self):
        obs=all_anchors();hs=FIXTURE_HOLES
        a=build(obs,hs,as_of_ms=B+1100*M)
        b=build(tuple(reversed(obs)),tuple(reversed(hs)),as_of_ms=B+1100*M)
        self.assertEqual(a,b)
        self.assertEqual(len(a.overlay_sha256),64)
        self.assertNotEqual(self.one().overlay_sha256,self.one((observation(price="2.00"),)).overlay_sha256)

    def test_actual_symbols_and_historical_flag_bypass_absent(self):
        for symbol in ("ETHUSDT","BTCUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"):
            with self.assertRaises(OverlayRejected):self.one((observation(symbol=symbol),))
            with self.assertRaises(OverlayRejected):self.one(h=replace(hole(),symbol=symbol))
        with self.assertRaises(TypeError):build((observation(),),(hole(),),as_of_ms=B+3*M,allow_actual=True)

    def test_fixed_past_only_envelope_preserves_endpoint_representation(self):
        obs=(observation(offset=0,price="0.99000000"),observation(price="1.23000000000000"))
        row=sensitivity(self.one(obs),obs)[0]
        self.assertEqual(row.lower_reference_price_text,"0.99000000")
        self.assertEqual(row.upper_reference_price_text,"1.23000000000000")
        self.assertFalse(row.guaranteed_bound_on_missing_price)
        self.assertFalse(row.certifies_liquidation)
        self.assertFalse(row.certifies_no_liquidation)
        self.assertEqual(row.quantity_sensitivity,"PENDING_ACTUAL_EVIDENCE")
        self.assertEqual(row.cashflow_sensitivity,"PENDING_ACTUAL_EVIDENCE")

    def test_envelope_future_perturbation_invariance(self):
        obs=(observation(offset=0,price="0.99"),observation())
        future=observation(offset=3,price="999999")
        self.assertEqual(sensitivity(self.one(obs),obs),sensitivity(self.one(obs+(future,)),obs+(future,)))

    def test_envelope_missing_second_anchor_pending(self):
        row=sensitivity(self.one(),(observation(),))[0]
        self.assertEqual(row.status,"PENDING_TWO_PAST_GENUINE_OBSERVATIONS")
        self.assertIsNone(row.lower_reference_price_text)
        self.assertTrue(row.actual_sensitivity_admission.startswith("BLOCKED"))

    def test_envelope_cannot_swap_primary_or_use_delayed_future_bound(self):
        obs=(observation(offset=0,price="0.99",available_at_ms=B+4*M,installed_at_ms=B+4*M),observation())
        row=sensitivity(self.one(obs),obs)[0]
        self.assertEqual(row.status,"PENDING_TWO_PAST_GENUINE_OBSERVATIONS")
        with self.assertRaises(OverlayRejected):sensitivity(self.one(),(observation(price="2"),))

    def test_event_impact_all_categories_pending_actual_quantity_cashflow(self):
        batch=self.one();h=hole();clock=h.minute_open_ms+M
        events=[]
        for kind in EVENT_KINDS:
            kw={"position_start_ms":clock-1,"position_end_exclusive_ms":clock+1} if kind=="POSITION" else {"mark_reference_open_ms":h.minute_open_ms}
            events.append(SavedGeneratedEvent("saved-fake-"+kind,h.symbol,clock,kind,**kw))
        result=audit(batch,events);row=result['rows'][0]
        self.assertEqual(sum(map(len,row['saved_generated_overlap_ids'].values())),7)
        self.assertEqual(row['quantity_sensitivity'],"PENDING_ACTUAL_EVIDENCE")
        self.assertEqual(row['cashflow_sensitivity'],"PENDING_ACTUAL_EVIDENCE")
        self.assertFalse(row['claim_of_negligible_impact'])
        self.assertEqual(events,list(events))

    def test_event_mapping_is_saved_explicit_never_guessed_on_boundary(self):
        h=hole();clock=h.minute_open_ms+M
        e=SavedGeneratedEvent("unmapped",h.symbol,clock,"FUNDING")
        row=audit(self.one(),(e,))['rows'][0]
        self.assertEqual(row['saved_generated_overlap_ids']['FUNDING'],[])
        self.assertEqual(row['saved_generated_events_without_mark_mapping'],['unmapped'])
        invalid=replace(e,mark_reference_open_ms=h.minute_open_ms,event_clock_ms=clock-1)
        with self.assertRaises(OverlayRejected):audit(self.one(),(invalid,))

    def test_event_duplicate_real_unknown_and_invalid_intervals_reject(self):
        e=SavedGeneratedEvent("saved",hole().symbol,B+3*M,"FUNDING",hole().minute_open_ms)
        for events in ((e,e),(replace(e,symbol="ETHUSDT"),),(replace(e,kind="FAKE"),),
                       (replace(e,kind="POSITION",position_start_ms=B+3*M,position_end_exclusive_ms=B+3*M),)):
            with self.assertRaises(OverlayRejected):audit(self.one(),events)

    def test_empty_generated_overlay_deterministic(self):
        a=build((),(),as_of_ms=0)
        self.assertEqual(a.records,())
        self.assertEqual(sensitivity(a,()),())
        self.assertEqual(audit(a,())['rows'],[])


class MetadataBoundaryTests(unittest.TestCase):
    def test_actual_metadata_points_are_disjoint_and_not_executable(self):
        from metadata_binding import ACTUAL27_ORIGINAL_OPEN_POINTS
        self.assertEqual(len(ACTUAL27_ORIGINAL_OPEN_POINTS),27)
        actual=tuple(MissingCell(s,t,"original-proof","b"*64) for s,t in ACTUAL27_ORIGINAL_OPEN_POINTS)
        with self.assertRaises(OverlayRejected):build((),actual,as_of_ms=2_000_000_000_000)

    def test_actual_metadata_identity_mismatch_reject(self):
        from metadata_binding import validate_actual27_metadata_bytes
        with self.assertRaises(OverlayRejected):validate_actual27_metadata_bytes(b'{}',b'{}',b'{}')

    def test_missing_cell_clock_and_identity_types_are_exact(self):
        for changes in ({"minute_open_ms":float(hole().minute_open_ms)},
                        {"original_cell_missing":1}, {"symbol":None},
                        {"proof_id":None}, {"proof_sha256":None},
                        {"domain":None}, {"selected_field":None}):
            with self.subTest(changes=changes):
                with self.assertRaises(OverlayRejected):
                    build((observation(),),(replace(hole(),**changes),),as_of_ms=B+3*M)

    def test_rehashed_batch_shared_genuine_anchor_cannot_conflict(self):
        from overlay import _digest
        hs=(hole(offset=20),hole(offset=21))
        batch=build((observation(offset=19),),hs,as_of_ms=B+22*M)
        for changes in ({"price_text":"2.000"}, {"anchor_observation_id":"different-id"},
                        {"anchor_source_record_id":"different-source-id"},
                        {"anchor_source_sha256":"b"*64},
                        {"anchor_available_at_ms":B+20*M+1,
                         "anchor_installed_at_ms":B+20*M+1,"source_freshness_clock_ms":B+20*M+1}):
            records=(batch.records[0],replace(batch.records[1],**changes))
            hashes=tuple(_digest(asdict(r)) for r in records)
            commitment=_digest({"policy_id":batch.policy_id,"policy_sha256":batch.policy_sha256,
                "fixture_allowlist_sha256":batch.fixture_allowlist_sha256,"record_sha256":hashes,
                "quality_sidecar":[asdict(x) for x in batch.quality_sidecar]})
            forged=replace(batch,records=records,record_sha256=hashes,overlay_sha256=commitment)
            with self.subTest(changes=changes):
                with self.assertRaises(OverlayRejected):audit(forged,())
                with self.assertRaises(OverlayRejected):sensitivity(forged,(observation(offset=19),))

    def test_subset_cluster_cannot_launder_original_missing_cell_as_genuine_anchor(self):
        hs=tuple(h for h in FIXTURE_HOLES if h.symbol=="FIXTURE_ETH"
                 and B+21*M<=h.minute_open_ms<=B+26*M)
        with self.assertRaises(OverlayRejected):
            build((observation(offset=20),),hs,as_of_ms=B+27*M)
        # Known absent cells are forbidden globally, including future/unrequested
        # cells. A true source recovery would require a separate reviewed API.
        for h in FIXTURE_HOLES:
            absent_as_genuine=observation(h.symbol,(h.minute_open_ms-B)//M)
            with self.assertRaises(OverlayRejected):
                build((observation(),absent_as_genuine),(hole(),),as_of_ms=B+3*M)

    def test_rehashed_batch_cannot_anchor_on_frozen_original_missing_cell(self):
        from overlay import _digest
        h=hole(offset=21)
        batch=build((observation(offset=19),),(h,),as_of_ms=B+22*M)
        r=batch.records[0]
        forged_record=replace(r,anchor_minute_open_ms=B+20*M,
            anchor_completed_at_ms=B+21*M,anchor_available_at_ms=B+21*M,
            anchor_installed_at_ms=B+21*M,anchor_age_ms=M,source_freshness_clock_ms=B+21*M)
        hashes=(_digest(asdict(forged_record)),)
        commitment=_digest({"policy_id":batch.policy_id,"policy_sha256":batch.policy_sha256,
            "fixture_allowlist_sha256":batch.fixture_allowlist_sha256,"record_sha256":hashes,
            "quality_sidecar":[asdict(x) for x in batch.quality_sidecar]})
        forged=replace(batch,records=(forged_record,),record_sha256=hashes,overlay_sha256=commitment)
        with self.assertRaises(OverlayRejected):audit(forged,())
        with self.assertRaises(OverlayRejected):sensitivity(forged,(observation(offset=20),))

    def test_event_audit_rejects_fully_rehashed_malformed_provenance(self):
        from overlay import _digest
        batch=build((observation(),),(hole(),),as_of_ms=B+3*M)
        original=batch.records[0]
        changes=(
            {"price_text":"NaN"}, {"price_text":"Infinity"}, {"price_text":"0"},
            {"price_text":1.25}, {"anchor_age_ms":-1}, {"anchor_age_ms":0},
            {"evaluation_clock_ms":0}, {"source_close_inclusive_ms":original.minute_open_ms},
            {"completed_at_ms":original.minute_open_ms},
            {"anchor_minute_open_ms":original.minute_open_ms},
            {"anchor_completed_at_ms":original.completed_at_ms+M},
            {"anchor_available_at_ms":original.evaluation_clock_ms+M},
            {"anchor_installed_at_ms":original.anchor_available_at_ms-1},
            {"source_freshness_clock_ms":original.evaluation_clock_ms},
            {"anchor_source_sha256":"invented"}, {"anchor_source_record_id":"/private/path"},
            {"anchor_observation_id":""},
            {"price_text":"NaN","anchor_age_ms":-1,"evaluation_clock_ms":0,
             "anchor_available_at_ms":original.evaluation_clock_ms+M},
        )
        for fields in changes:
            with self.subTest(fields=fields):
                records=(replace(original,**fields),)
                hashes=tuple(_digest(asdict(r)) for r in records)
                commitment=_digest({"policy_id":batch.policy_id,"policy_sha256":batch.policy_sha256,
                    "fixture_allowlist_sha256":batch.fixture_allowlist_sha256,"record_sha256":hashes,
                    "quality_sidecar":[asdict(x) for x in batch.quality_sidecar]})
                forged=replace(batch,records=records,record_sha256=hashes,overlay_sha256=commitment)
                with self.assertRaises(OverlayRejected):audit(forged,())
                with self.assertRaises(OverlayRejected):sensitivity(forged,(observation(),))

    def test_impact_audit_rejects_forged_scope_and_record_promotion(self):
        batch=build((observation(),),(hole(),),as_of_ms=B+3*M)
        for forged in (replace(batch,scope="ACTUAL"),replace(batch,policy_id="approved-by-me"),
                       replace(batch,records=(replace(batch.records[0],symbol="ETHUSDT"),)),
                       replace(batch,records=(replace(batch.records[0],is_genuine=True),))):
            with self.assertRaises(OverlayRejected):audit(forged,())
            with self.assertRaises(OverlayRejected):sensitivity(forged,(observation(),))


if __name__ == "__main__":
    unittest.main(verbosity=2)
