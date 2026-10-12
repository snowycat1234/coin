"""Regression: acceptance and audit-failure receipts must survive NumPy CI gates."""
import json
import numpy as np
from experiment import finish,ARMS
def test_summary_serialization_and_audit_failure(tmp_path):
    reports={a:dict(full_calendar=True,paid_flat=True,liquidations=0,inventory_audit='PASS',summary=dict(net_PnL=100 if a=='DUAL' else 10,all_observation_max_drawdown=.01),metrics=dict(actual_daily_annual_vol=.1,worst30=-.01)) for a in ARMS}
    returns={a:np.full(456,.001 if a=='DUAL' else .0001) for a in ARMS}
    finish(tmp_path,'P1','synthetic',reports,returns,{},0.,'synthetic_no_wallet')
    good=json.loads((tmp_path/'RESULT.json').read_text());assert good['status']=='PASS_FIXED_DUAL_SPEED_WINDOW_GATES' and all(good['gates'].values())
    reports['SLOW']['inventory_audit']='FAIL';finish(tmp_path,'P1','synthetic',reports,returns,{},0.,'synthetic_no_wallet')
    bad=json.loads((tmp_path/'RESULT.json').read_text());assert bad['status']=='STOP_FIXED_DUAL_SPEED_WINDOW_GATES' and bad['gates']['full_paid_audited'] is False
