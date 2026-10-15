"""Fake recording dictionaries only, without any account or execution scope."""
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_common as c
import cs_config as config
import cs_native as native
import cs_saved as saved
from cs_source_guard import SourceOnlyGuard


def fake_recording_contract(tier):
    cfg=native.V2.ENGINE.PerpetualConfig(initial_cash='10000',max_gross_weight=str(config.TIER_GROSS_CAPS[tier]),
                                       max_asset_weight='.30',leverage='1',half_spread_bps='4',slippage_bps='4')
    profile=c.exact_object(c.exact(ROOT/'bounded_account_continuation_20261015/QUANTITY_PROFILE.json',
                                  '94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf'))
    profiles={s:native.V2.ENGINE.InstrumentProfile(quantity_step=profile['rows'][s]['quantity_step'],min_notional='10').metadata() for s in native.S}
    scope=dict(recording_only=True,real_scope=False,generated_only_fake_metadata=True)
    audit=dict(symbols=list(native.S),positions=dict.fromkeys(native.S,{}),marks=dict.fromkeys(native.S,[]),
        config={f.name:str(getattr(cfg,f.name)) for f in fields(cfg)},instrument_profiles=profiles,
        closing_min_notional_exempt=True,cost_context=None,bound_nominal_tier=tier,historical_execution_admitted=True,
        historical_execution_scope=scope,generated_only_fake_metadata=True,
        contract=dict(symbols=list(native.S),bound_nominal_tier=tier,free_cash_floor='1000',total_isolated_ceiling='8500',
            leverage=1,nominal_roundtrip_bps=27.,taker_fee_bps_per_side=5.5,topup_enabled=False,policy_variant='GUARD50_EXIT_ONLY',
            quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE',historical_execution_admitted=True,generated_only=False,
            closing_min_notional_exempt=True,instrument_profiles=deepcopy(profiles),scope_binding=scope))
    result=dict(common_execution_policy=dict(tier=tier,gross_ceiling=config.TIER_GROSS_CAPS[tier],asset_ceiling=.30,
        annual_covariance_volatility_ceiling=config.TIER_BUDGETS[tier],initial_cash='10000',free_cash_increase_floor='1000',
        actual_isolated_margin_ceiling='8500',automatic_topup=False,policy_variant='GUARD50_EXIT_ONLY',historical_execution_admitted=True))
    return audit,result


def fake_recording_guard():
    zeros=dict.fromkeys(SourceOnlyGuard.CATEGORIES,0)
    return dict(schema='OBSERVED_PORTABLE_CS_SOURCE_GUARD_V2',status='PASS_FINANCIAL_WORKER_SOURCE_ONLY_RECAPTURE',
        forbidden_attempts=zeros,error=None,attempted_targets=[],guard_active=False,historical_execution_authorized=False,
        financial_execution_authorized=False,source_scopes_revoked=True,saved_targets_and_covariance_rebuilt=False,
        checkpoints=[dict(label=label,attempts=deepcopy(zeros)) for label in [
            'FRESH_WORKER_CS_SOURCE_RECAPTURE_BEFORE_FINANCE_IMPORT','EXACT_SAVED_CS_TARGETS_LOADED_WITHOUT_REGENERATION']],
        observed_workspace_read_paths={'GENERATED_ONLY_FAKE_RECORDED_READ_NEVER_OPENED':1})


class ContractGuardReview(unittest.TestCase):
    def test_all_tier_fake_metadata_positive_mints_no_account_or_scope(self):
        for tier in config.TIERS:
            audit,result=fake_recording_contract(tier)
            self.assertIsNone(saved.saved_account_contract(audit,result,tier))
            self.assertTrue(audit['historical_execution_scope']['recording_only'])
    def test_exact_tier_caps_profile_and_symbols_reject_resealed_recording_changes(self):
        audit,result=fake_recording_contract('MID')
        for field,value in [('symbols',list(reversed(native.S))),('closing_min_notional_exempt',False),('cost_context',{}),
                            ('bound_nominal_tier','HIGH'),('historical_execution_admitted',False)]:
            bad=deepcopy(audit);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):saved.saved_account_contract(bad,result,'MID')
        for field,value in [('max_gross_weight','0.9'),('max_asset_weight','0.2'),('fee_rate','0.001')]:
            bad=deepcopy(audit);bad['config'][field]=value
            with self.subTest(config=field),self.assertRaises(ValueError):saved.saved_account_contract(bad,result,'MID')
        bad=deepcopy(audit);bad['instrument_profiles'][native.S[0]]['quantity_step']='0.00000001'
        with self.assertRaises(ValueError):saved.saved_account_contract(bad,result,'MID')
    def test_contract_and_common_policy_fields_cannot_be_borrowed_or_omitted(self):
        audit,result=fake_recording_contract('LOW')
        for key in audit['contract']:
            bad=deepcopy(audit);del bad['contract'][key]
            with self.subTest(contract=key),self.assertRaises((ValueError,KeyError)):saved.saved_account_contract(bad,result,'LOW')
        for key in result['common_execution_policy']:
            bad=deepcopy(result);del bad['common_execution_policy'][key]
            with self.subTest(common=key),self.assertRaises(ValueError):saved.saved_account_contract(audit,bad,'LOW')
    def test_exact_generated_guard_positive_is_recording_only(self):
        self.assertIsNone(saved.saved_source_guard(fake_recording_guard()))
    def test_empty_missing_boolean_or_nonzero_counters_fail_before_vacuous_pass(self):
        guard=fake_recording_guard()
        for counters in ({},{'financial_constructors':0},{k:False for k in SourceOnlyGuard.CATEGORIES},
                         {**guard['forbidden_attempts'],'financial_imports':1}):
            bad=deepcopy(guard);bad['forbidden_attempts']=counters
            with self.subTest(counters=counters),self.assertRaises(ValueError):saved.saved_source_guard(bad)
    def test_false_authority_error_active_scope_or_target_rebuild_flags_denied(self):
        guard=fake_recording_guard()
        for key,value in [('schema','OTHER'),('error','FAKE_ERROR'),('attempted_targets',[{}]),('guard_active',True),
            ('historical_execution_authorized',True),('financial_execution_authorized',True),('source_scopes_revoked',False),
            ('saved_targets_and_covariance_rebuilt',True),('observed_workspace_read_paths',{})]:
            bad=deepcopy(guard);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):saved.saved_source_guard(bad)
    def test_exact_two_ordered_observed_checkpoints_and_full_zero_counters_required(self):
        guard=fake_recording_guard()
        for points in ([],list(reversed(guard['checkpoints'])),guard['checkpoints'][:1],guard['checkpoints']*2):
            bad=deepcopy(guard);bad['checkpoints']=points
            with self.assertRaises(ValueError):saved.saved_source_guard(bad)
        bad=deepcopy(guard);bad['checkpoints'][0]['attempts']={}
        with self.assertRaises(ValueError):saved.saved_source_guard(bad)

if __name__=='__main__':unittest.main(verbosity=2)
