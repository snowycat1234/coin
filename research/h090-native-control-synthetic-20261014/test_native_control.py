"""Generated minute integration tests; no history or live account traffic."""
import ast,hashlib,json,unittest
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal as D
from pathlib import Path
import numpy as np
from generated_fixtures import *
from native_control import (H090NativeControl,NativeH090Descriptor,original_control,
    original_weight_guard,h090_weight_guard,SyntheticSourceRegistry,DESCRIPTOR,
    POLICY,NATIVE,ORIGINAL_ACCOUNT)
from cost_factory import h090_config_from_original,h090_account_for_cost,ORIGINAL_FINANCE,COSTS
from calendar_readiness_v2 import SourceReadinessError,SourcePacket
from bind_sources import verify
HERE=Path(__file__).resolve().parent


def quantities(sim):return {s:str(sim.account.positions[s].quantity) for s in S}


def prime(sim):
    sim.account.update_marks(START,{s:dict(price=D(str(sim.daily_prices[s][START])),
        close_us=START,available_us=START) for s in S})
    sim.previous_quote=dict.fromkeys(S,10000000.)


class NativeControlTests(unittest.TestCase):
    def test_full_cached_source_closure_and_original_bytes_unchanged(self):
        pins=verify()
        self.assertEqual(pins['account_freeze_SHA256'],'af840b51613335a83d5badd8454e0861863e6fb20dda136d2054457ffeb1cdf5')
        original=(HERE/'dependencies/repo/src/quant/perpetual_account.py').read_text()
        vendor=(HERE/'dependencies/account/vendor_quant/perpetual_account.py').read_text()
        self.assertEqual(original.replace('self.max_gross_weight <= D("0.6")','self.max_gross_weight <= D("0.9")'),vendor)
        # The whole native financial/scheduling iteration, after the separate
        # input-admission block, is exactly the original function AST.
        old=ast.parse((HERE/'dependencies/repo/scripts/investment/resumable_perpetual.py').read_text())
        new=ast.parse((HERE/'native_control.py').read_text())
        def method(tree,cls,name):
            klass=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name==cls)
            return next(x for x in klass.body if isinstance(x,ast.FunctionDef) and x.name==name)
        a=method(old,'NativeDailySimulator','advance_day')
        b=method(new,'H090NativeControl','advance_day')
        self.assertEqual([ast.dump(x) for x in a.body[3:]],[ast.dump(x) for x in b.body[2:]])

    def test_original60_control_full_decimal_and_minute_parity(self):
        for original_recipe in (False,True):
            bundle=make_generated(weights=[.25,-.15,.1,0,0],original_recipe=original_recipe)
            window,factory,_,_,_=bundle
            direct=NATIVE(window,'LONG_SHORT',BASE27,UNIT,target_factory=factory,account_factory=ORIGINAL_ACCOUNT)
            control=original_control(window,BASE27,UNIT,target_factory=factory)
            finish(direct);finish(control)
            self.assertEqual(direct.snapshot(),control.snapshot())
            np.testing.assert_array_equal(direct.result()['minute'].to_numpy(),control.result()['minute'].to_numpy())
            self.assertEqual(direct.account.trades,control.account.trades)
            self.assertEqual(direct.funding_journal,control.funding_journal)

    def test_original60_direct_and_preloaded_caps_never_extended(self):
        bad=make_generated(weights=[.3,.3,.3,0,0])
        with self.assertRaisesRegex(ValueError,'ORIGINAL_030_060'):
            original_control(bad[0],BASE27,UNIT,target_factory=bad[1])
        control=original_control(bad[0],BASE27,UNIT)
        with self.assertRaisesRegex(ValueError,'Existing .30 asset and .60'):
            control.advance_day(dict(zip(S,[.3,.3,.3,0,0])))
        self.assertEqual(len(control.account.trades),0)

    def test_h090_valid90_intent_and_atomic_actual_cap_are_distinct(self):
        sim=new_h090(make_generated())
        self.assertAlmostEqual(sum(abs(v) for v in sim.weights[START].values()),.9)
        self.assertEqual(sim.reservations.reservations,{'CSH_H090_CONTROL':D('9000')})
        finish(sim)
        self.assertTrue(any(r.get('reason')=='SHARED_CAPITAL_OR_RESERVE_CAP' for r in sim.rejections))
        self.assertEqual(sim.stop,None)
        self.assertTrue(sim.terminal)
        self.assertTrue(all(D(q)==0 for q in quantities(sim).values()))
        self.assertLess(sum(D(row['decimal_strings']['margin_allocated']) for row in sim.account.trades),D('8500'))
        self.assertGreater(sim.account.fees,D('0'))

    def test_direct_and_preloaded_finance_and_all_journal_parity(self):
        bundle=make_generated(weights=[.2,-.1,.15,0,0])
        a=new_h090(bundle);b=new_h090(bundle,preloaded=False)
        finish(a);finish(b,bundle)
        self.assertEqual(a.account.snapshot(),b.account.snapshot())
        self.assertEqual(a.funding_journal,b.funding_journal)
        self.assertEqual(a.rejections,b.rejections)
        self.assertEqual(a.breaches,b.breaches)
        self.assertEqual(a.target_rows,b.target_rows)
        np.testing.assert_array_equal(a.result()['minute'].to_numpy(),b.result()['minute'].to_numpy())

    def test_exact_unlagged_original_recipe_and_fixed_multiplier(self):
        bundle=make_generated(original_recipe=True)
        sim=new_h090(bundle)
        self.assertIn('UNLAGGED_ORIGINAL',sim.meta['source'])
        self.assertEqual(sim.original_weights[START],dict(zip(S,bundle[-1][0].tolist())))
        ctx=sim.risk_contexts[START]
        self.assertLessEqual(ctx['original_annual_vol'],.10+1e-12)
        self.assertLessEqual(ctx['risk_metadata']['annual_vol_after_scaling'],.15)
        for s,original in zip(S,bundle[-1][0]):
            self.assertGreaterEqual(sim.weights[START][s]*original,0)
            self.assertLessEqual(abs(sim.weights[START][s]),abs(original*1.5)+1e-14)
        finish(sim)
        self.assertGreater(len(sim.account.trades),0)
        self.assertEqual(sim.result()['summary']['historical_status'],'NO_GO')

    def test_direct_invalid_caps_wrong_proposal_and_missing_original_reject(self):
        bundle=make_generated(weights=[.2,-.1,.15,0,0])
        for values in ([.31,0,0,0,0],[.3,.3,.3,.01,0],[float('nan'),0,0,0,0]):
            sim=new_h090(bundle,preloaded=False)
            with self.assertRaises(ValueError):sim.advance_day(dict(zip(S,values)),original_csh_weights=dict(zip(S,bundle[-1][0])))
            self.assertEqual(len(sim.account.trades),0)
        sim=new_h090(bundle,preloaded=False)
        with self.assertRaisesRegex(ValueError,'FROZEN_ORIGINAL_CSH'):
            sim.advance_day(dict(zip(S,[.3,-.15,.225,0,0])))
        with self.assertRaisesRegex(ValueError,'MUST_EQUAL_CERTIFIED'):
            sim.advance_day(dict(zip(S,[.2,-.1,.15,0,0])),original_csh_weights=dict(zip(S,bundle[-1][0])))

    def test_direct_certified_target_and_preloaded_tamper_guard(self):
        bundle=make_generated(weights=[.2,-.1,.15,0,0])
        source=new_h090(bundle)
        direct=new_h090(bundle,preloaded=False)
        direct.advance_day(dict(source.weights[START]),original_csh_weights=dict(zip(S,bundle[-1][0])))
        self.assertGreater(len(direct.account.trades),0)
        altered=new_h090(bundle)
        altered.weights[START][S[0]]=.29
        with self.assertRaisesRegex(ValueError,'PRELOADED_H090_TARGET_CHANGED'):
            altered.advance_day()
        self.assertEqual(len(altered.account.trades),0)

    def test_descriptor_and_config_class_and_cost_identity_reject(self):
        with self.assertRaises(ValueError):NativeH090Descriptor(gross_cap=.6)
        bundle=make_generated()
        with self.assertRaises(ValueError):
            H090NativeControl(bundle[0],'LONG_SHORT',BASE27,UNIT,source_registry=bundle[3],descriptor=asdict(DESCRIPTOR))
        from vendor_quant.perpetual_account import PerpetualConfig
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_CONFIG_CLASS'):
            h090_config_from_original(PerpetualConfig(),BASE27)
        with self.assertRaises(ValueError):POLICY.HighRiskToyAccount(ORIGINAL_FINANCE.PerpetualConfig())
        with self.assertRaises(ValueError):h090_account_for_cost({**BASE27,'roundtrip_bps':26})
        account=h090_account_for_cost(BASE27)
        self.assertEqual(account.config.max_gross_weight,D('.90'))
        for f in ORIGINAL_FINANCE.PerpetualConfig.__dataclass_fields__:
            if f!='max_gross_weight':self.assertEqual(getattr(account.config,f),getattr(COSTS.scenario_config(BASE27),f))

    def test_preload_schema_order_and_overcap_guard_before_account(self):
        bundle=make_generated()
        def changed(kind):
            def factory(daily,clocks,mode):
                frame,meta=bundle[1](daily,clocks,mode)
                rows=frame.to_dicts()
                if kind=='order':rows[:5]=rows[:5][::-1]
                if kind=='cap':rows[0]['target_weight']=.31
                if kind=='gross':
                    for row in rows[:3]:row['target_weight']=.3
                return PORT.native.pl.DataFrame(rows),meta
            return factory
        for kind in ('order','cap','gross'):
            with self.assertRaises(ValueError):
                H090NativeControl(bundle[0],'LONG_SHORT',BASE27,UNIT,source_registry=bundle[3],
                    source_packets=bundle[2],target_factory=changed(kind))

    def test_bad_source_parser_errors_become_explicit_reduce_only(self):
        mutations=[lambda s:s.__setitem__('symbol_order',None),
                   lambda s:s['daily_bars'][-1].__setitem__('close',10**400),
                   lambda s:s['daily_bars'][-1].__setitem__('available_us',START+1),
                   lambda s:s['daily_bars'][-1].__setitem__('imputed',True)]
        for mutation in mutations:
            sim=new_h090(make_generated(source_mutations={START:mutation}))
            finish(sim)
            self.assertEqual(len(sim.account.trades),0)
            self.assertEqual(sim.account.free_cash,D('10000'))
            self.assertTrue(any(e['kind']=='SOURCE_INVALID_REDUCE_ONLY' for e in sim.policy_events))
            self.assertTrue(all(row['target_weight']==0 for row in sim.target_rows))

    def test_finite_source_covariance_overflow_is_reduce_only_and_financial_errors_are_not_gaps(self):
        def overflow(source):source['daily_bars'][-1]['close']=1e200
        sim=new_h090(make_generated(source_mutations={START:overflow}))
        finish(sim)
        self.assertEqual(len(sim.account.trades),0)
        self.assertIn('CERTIFIED_SOURCE_COVARIANCE_INVALID',sim.policy_events[0]['reason'])
        # An account runtime error is never caught by source readiness handling.
        good=new_h090(make_generated());prime(good)
        good.schedule(dict(zip(S,[D('1'),D(0),D(0),D(0),D(0)])),START,'DAILY_TARGET')
        before=good.account.snapshot()
        with self.assertRaisesRegex(ValueError,'fill precedes execution latency'):
            good.account.execute_fill(S[0],'BUY',D('1'),START+1,START,'FINANCIAL_CLOCK_ERROR',
                execution_mid_price=D('100'),quote_available_us=START,available_quantity=D('1'),reduce_only=False)
        self.assertEqual(good.account.snapshot(),before)

    def test_stale_delayed_source_after_hold_keeps_inventory_until_paid_exit(self):
        for kind in ('stale','delayed'):
            def mutation(source):
                if kind=='stale':
                    for row in source['daily_bars']:
                        for field in ('open_us','close_us','available_us'):row[field]-=DAY
                else:source['daily_bars'][-1]['available_us']=START+DAY+1
            bundle=make_generated(days=2,weights=[.2,-.1,0,0,0],source_mutations={START+DAY:mutation})
            sim=new_h090(bundle);sim.advance_day()
            held=quantities(sim);before=sim.account.snapshot();fees=sim.account.fees
            self.assertTrue(any(D(q)!=0 for q in held.values()))
            sim._admit_decision(sim.cursor,None,None,None,None)
            self.assertEqual(sim.account.snapshot(),before)
            self.assertEqual(quantities(sim),held)
            sim.advance_day()
            self.assertGreater(sim.account.fees,fees)
            self.assertTrue(all(p.quantity==0 for p in sim.account.positions.values()))
            close_rows=[r for r in sim.account.trades if r['leg']=='CLOSE']
            self.assertTrue(all(r['event_us']>=START+DAY+MINUTE+1 for r in close_rows))

    def test_gap_zero_capacity_retains_inventory_and_incomplete_status(self):
        quote=np.full(2880,10000000.);quote[1439:]=0
        def delayed(source):source['daily_bars'][-1]['available_us']=START+DAY+1
        sim=new_h090(make_generated(days=2,weights=[.2,0,0,0,0],quote=quote,
            source_mutations={START+DAY:delayed}))
        sim.advance_day();held=quantities(sim);sim.advance_day()
        self.assertEqual(quantities(sim),held)
        self.assertEqual(sim.completion,'NOT_EVALUABLE_UNEXECUTABLE_ASSET_EXIT')
        self.assertEqual(sim.stop,START+DAY+5*MINUTE+1)
        self.assertEqual(sum(r['leg']=='CLOSE' for r in sim.account.trades),0)

    def test_external_manifest_and_index_pins_not_taken_from_packet(self):
        bundle=make_generated();sim=new_h090(bundle,preloaded=False)
        packet=bundle[2][START]
        wrong=SourcePacket(packet.source_bytes,packet.manifest_bytes,'f'*64)
        sim.advance_day(original_csh_weights=dict(zip(S,bundle[-1][0])),source_packet=wrong)
        self.assertEqual(len(sim.account.trades),0)
        self.assertIn('EXTERNAL_APPROVED_MANIFEST_MISMATCH',sim.policy_events[0]['reason'])
        manifest=json.loads(packet.manifest_bytes);manifest['source_index_SHA256']='a'*64
        mb=json.dumps(manifest).encode();changed=SourcePacket(packet.source_bytes,mb,hashlib.sha256(mb).hexdigest())
        registry=SyntheticSourceRegistry({START:{'manifest_SHA256':changed.approved_manifest_sha256,
            'source_index_SHA256':json.loads(packet.manifest_bytes)['source_index_SHA256']}})
        with self.assertRaisesRegex(SourceReadinessError,'INDEX_MISMATCH'):registry.check(changed,START)

    def test_funding_before_same_time_fill_and_signed_exact_funding(self):
        events=[dict(event_us=START+n*MINUTE+1,symbol=s,raw_rate=.001)
                for n in (1,2,4) for s in (S[0],S[1])]
        events.sort(key=lambda r:(r['event_us'],S.index(r['symbol'])))
        quote=np.full(1440,500000.)
        sim=new_h090(make_generated(weights=[.2,-.1,0,0,0],quote=quote,events=events))
        finish(sim)
        first=[r for r in sim.account.funding if r['event_us']==START+MINUTE+1]
        self.assertTrue(first)
        self.assertTrue(all(D(r['decimal_strings']['quantity'])==0 for r in first))
        owned=[r for r in sim.account.funding if r['owned']]
        self.assertTrue(owned)
        for row in owned:
            exact=row['decimal_strings']
            expected=-D(exact['quantity'])*D(exact['mark_price'])*D(exact['rate_fraction'])
            self.assertEqual(D(exact['signed_funding_USDT']),expected)
            self.assertLess(row['mark_close_us'],row['event_us'])
        self.assertTrue(any(D(r['decimal_strings']['signed_funding_USDT'])<0 for r in owned))
        self.assertTrue(any(D(r['decimal_strings']['signed_funding_USDT'])>0 for r in owned))
        self.assertEqual(sim.event_cursor,len(events))

    def test_partial_reversal_shares_original_prior_capacity_and_ordering(self):
        bundle=make_generated(weights=[.2,0,0,0,0])
        sim=new_h090(bundle);prime(sim)
        # Account-generated initial inventory, with the production callback
        # active and a certified current source context.
        open_event=START+MINUTE+1
        sim.schedule(dict(zip(S,[D('10'),D(0),D(0),D(0),D(0)])),START,'DAILY_TARGET')
        sim.attempt(START+MINUTE,{s:dict(open=100.,quote_volume=10000000.) for s in S})
        self.assertEqual(sim.account.positions[S[0]].quantity,D('10'))
        sim.schedule(dict(zip(S,[D('-3'),D(0),D(0),D(0),D(0)])),START+2*MINUTE,'DAILY_TARGET')
        sim.previous_quote=dict.fromkeys(S,500000.) # 5 units shared at next open
        row={s:dict(open=100.,quote_volume=999999999.) for s in S}
        before=len(sim.account.trades);sim.attempt(START+3*MINUTE,row)
        recent=sim.account.trades[before:]
        self.assertEqual(len(recent),1);self.assertEqual(recent[0]['leg'],'CLOSE')
        self.assertEqual(D(recent[0]['decimal_strings']['quantity']),D('5'))
        self.assertEqual(sim.account.positions[S[0]].quantity,D('5'))
        # Closing 5 uses all capacity, so reversal cannot reopen this minute.
        before=len(sim.account.trades);sim.attempt(START+4*MINUTE,row)
        recent=sim.account.trades[before:]
        self.assertEqual(sum(D(r['decimal_strings']['quantity']) for r in recent),D('5'))
        self.assertEqual(sim.account.positions[S[0]].quantity,D('0'))
        self.assertTrue(all(r['leg']=='CLOSE' for r in recent))
        sim.attempt(START+5*MINUTE,row)
        self.assertEqual(sim.account.positions[S[0]].quantity,D('-3'))

    def test_freshness_gate_blocks_pending_increase_and_allows_reduction(self):
        sim=new_h090(make_generated(weights=[.2,0,0,0,0]));prime(sim)
        sim.risk_contexts[START]['ready']=False
        sim.schedule(dict(zip(S,[D('10'),D(0),D(0),D(0),D(0)])),START,'DAILY_TARGET')
        sim.attempt(START+MINUTE,{s:dict(open=100.,quote_volume=10000000.) for s in S})
        self.assertEqual(len(sim.account.trades),0)
        self.assertTrue(any(r.get('reason')=='SOURCE_FRESHNESS_REQUIRED_FOR_INCREASE' for r in sim.rejections))
        sim.risk_contexts[START]['ready']=True
        sim.attempt(START+2*MINUTE,{s:dict(open=100.,quote_volume=10000000.) for s in S})
        self.assertGreater(len(sim.account.trades),0)
        sim.risk_contexts[START]['ready']=False
        sim.schedule(dict.fromkeys(S,D('0')),START+3*MINUTE,'DATA_GAP_EXIT')
        sim.attempt(START+4*MINUTE,{s:dict(open=100.,quote_volume=10000000.) for s in S})
        self.assertEqual(sim.account.positions[S[0]].quantity,D('0'))

    def test_pending_covariance_corner_rejects_hidden_hedged_transition_risk(self):
        source=source_document(START)
        for i in range(200):
            for row in source['daily_bars'][i*5:(i+1)*5]:row['close']=100*(1.08 if i%2 else 1.)
        packet,manifest=encode_source(source)
        bundle=make_generated(weights=[.2,-.2,0,0,0])
        packets={START:packet}
        registry=SyntheticSourceRegistry({START:{'manifest_SHA256':packet.approved_manifest_sha256,
            'source_index_SHA256':manifest['source_index_SHA256']}})
        sim=H090NativeControl(bundle[0],'LONG_SHORT',BASE27,UNIT,source_registry=registry,
            source_packets=packets,target_factory=bundle[1])
        finish(sim)
        self.assertEqual(len(sim.account.trades),0)
        self.assertTrue(any(r.get('reason')=='SINGLE_OWNER_ACTUAL_PENDING_RISK_ENVELOPE' for r in sim.rejections))

    def test_paid_terminal60_late_partials_and_residual_are_truthful(self):
        for capacity,flat in ((50000.,True),(0.,False)):
            quote=np.full(1440,10000000.);quote[-61:]=capacity
            sim=new_h090(make_generated(weights=[.2,0,0,0,0],quote=quote));finish(sim)
            self.assertTrue(sim.terminal)
            terminal=[r for r in sim.account.trades if r['signal_us']==sim.terminal_signal_us]
            if flat:
                self.assertTrue(terminal)
                self.assertTrue(all(r['leg']=='CLOSE' and D(r['decimal_strings']['fee_amount'])>0 for r in terminal))
                self.assertTrue(all(p.quantity==0 for p in sim.account.positions.values()))
                self.assertGreater(len(terminal),5)
            else:
                self.assertEqual(terminal,[])
                self.assertNotEqual(sim.account.positions[S[0]].quantity,D('0'))
                expired=[r for r in sim.rejections if r.get('reason')=='SIXTY_TERMINAL_ATTEMPTS_EXPIRED']
                self.assertEqual(len(expired),1)
            terminal_ids=[r['order_id'] for r in sim.rejections if r.get('kind')=='TERMINAL']
            self.assertLessEqual(len(set(terminal_ids)),1)
            self.assertEqual(sim.terminal_signal_us,sim.end-61*MINUTE)

    def test_snapshot_version_binds_h090_and_explicitly_refuses_restore(self):
        sim=new_h090(make_generated());finish(sim)
        snapshot=sim.snapshot();json.dumps(snapshot,allow_nan=False)
        self.assertEqual(snapshot['version'],'h090_native_single_control_generated_v1')
        binding=snapshot['h090_binding']
        self.assertEqual(binding['descriptor'],asdict(DESCRIPTOR))
        self.assertEqual(binding['reservations'],{'CSH_H090_CONTROL':'9000'})
        self.assertTrue(binding['processed_native_receipts'])
        self.assertIn('source_readiness',binding)
        self.assertEqual(binding['full_restore_status'],'NOT_IMPLEMENTED_NOT_CERTIFIED_HISTORY_NO_GO')
        with self.assertRaisesRegex(ValueError,'NO_GO_EXACT_H090'):H090NativeControl.from_snapshot(snapshot,sim.window)
        with self.assertRaisesRegex(ValueError,'NO_GO_H090_FORK'):sim.fork()
        with self.assertRaisesRegex(ValueError,'Scheduler version'):NATIVE.from_snapshot(snapshot,sim.window)
        self.assertEqual(sim.result()['summary']['full_recovery'],'NOT_IMPLEMENTED_NOT_CERTIFIED')

    def test_history_and_real_source_registry_are_unconditionally_blocked(self):
        bundle=make_generated();window=dict(bundle[0]);window.pop('fixture_scope')
        with self.assertRaisesRegex(ValueError,'NO_HISTORICAL_ENTRY'):
            H090NativeControl(window,'LONG_SHORT',BASE27,UNIT,source_registry=bundle[3])
        with self.assertRaisesRegex(ValueError,'HISTORY_NO_GO'):
            SyntheticSourceRegistry(dict(bundle[3].identity()),scope='REAL_PROVIDER_CERTIFIED')

if __name__=='__main__':unittest.main(verbosity=2)
