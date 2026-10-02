"""Immutable units addendum and zero-fit price-relevance decomposition."""
import json
import sys
from pathlib import Path
import numpy as np
import polars as pl

sys.path.insert(0, '/mnt/d/codex/coin/scripts/research_v7')
from oracle_flow_ceiling import correlations, exclusive_json
from quant.paths import ROOT
from quant.research_fast.dataset import STREAMS, file_sha
from quant import resources

resources.status()
report_path = ROOT / 'reports/fast_research/V7_OOF_FLOW_IMPACT_20261002_V2.json'
report = json.loads(report_path.read_text())
oracle = json.loads((ROOT/'reports/fast_research/V7_ORACLE_FLOW_HORIZON_20261002_V1.json').read_text())
frame = pl.read_parquet(Path(oracle['run_dir'])/'oracle_common_endpoints.parquet')
run = Path(report['run_dir'])
test = np.load(run/'test_indices.npy',allow_pickle=False)
oof = np.load(run/'OOF_indices.npy',allow_pickle=False)
corrected, mechanisms = [], []
for result in report['horizons']:
    h = result['horizon_minutes']
    pred_test = np.load(run/f'horizon-{h}m/M1-test-predicted-flow.npy',allow_pickle=False)
    pred_oof = np.load(run/f'horizon-{h}m/OOF-predicted-flow.npy',allow_pickle=False)[oof]
    fitting = json.loads((run/f'horizon-{h}m/M1-final/FIT_RECEIPT.json').read_text())
    for column, stream in enumerate(STREAMS):
        for split, rows, predictions, metrics_name in [('test',test,pred_test,'M1_test_flow'),('OOF',oof,pred_oof,'M1_OOF_flow')]:
            actual = frame[f'{stream}__flow_{h}m'].to_numpy()[rows]
            value = float(np.mean(np.sign(predictions[:,column])*actual))
            recorded = result[metrics_name][stream]['signed_return_mean_bps']
            assert abs(value*10000-recorded) <= 1e-10
            corrected.append({'horizon_minutes':h,'stream':stream,'split':split,
                'misnamed_original_field':'signed_return_mean_bps','original_value':recorded,
                'correct_field':'signed_flow_imbalance_mean','correct_value':value,
                'units':'dimensionless aggressive flow imbalance, NOT price-return bps or trade edge'})
        actual = frame[f'{stream}__flow_{h}m'].to_numpy()[test]
        predicted = pred_test[:,column]
        innovation = actual-predicted
        train_mean = fitting['target_scaler']['mean'][column]
        mse = float(np.mean((actual-predicted)**2))
        baseline = float(np.mean((actual-train_mean)**2))
        price_relevance=[]
        for symbol in ('BTCUSDT','ETHUSDT'):
            returns=frame[f'spot_{symbol}__return_{h}m_proxy'].to_numpy()[test]
            price_relevance.append({'spot_target':symbol,
                'predicted_flow_vs_future_return':correlations(predicted,returns),
                'true_future_flow_oracle_vs_future_return':correlations(actual,returns),
                'future_flow_prediction_residual_ORACLE_vs_future_return':correlations(innovation,returns)})
        mechanisms.append({'horizon_minutes':h,'stream':stream,
            'flow_prediction_std':float(predicted.std()),'actual_future_flow_std':float(actual.std()),
            'forecast_std_over_actual_std':float(predicted.std()/actual.std()),
            'MSE_skill_vs_train_mean':1-mse/baseline,
            'price_relevance':price_relevance})
output={'status':'IMMUTABLE_V7_OOF_FLOW_UNITS_AND_PRICE_RELEVANCE_ADDENDUM',
    'original_report_sha256':file_sha(report_path),'original_report_unchanged':True,
    'analysis_script_sha256':file_sha(Path(__file__)),
    'unit_corrections':corrected,'zero_fit_component_mechanism_diagnostic':mechanisms,
    'model_refits':0,'new_thresholds_or_horizons':0,
    'claim_limits':['Misnamed M1 signed_return_mean_bps is not an economic edge; all actual return and NAV accounting stays unchanged.',
        'Future-flow residual is an oracle diagnostic, never a model feature or implementable signal.',
        'Correlation/variance decomposition is descriptive on an already inspected future-valid July development subset.',
        'Per-minute sign-return means overlap and are not roundtrip edge, cost capacity or net APR.'],
    'gpu_hours':0,'shared_cgroup':resources.status()}
exclusive_json(ROOT/'reports/fast_research/V7_OOF_FLOW_UNITS_AND_COMPONENT_ADDENDUM_20261002_V1.json',output)
for item in mechanisms:
    same=next(x for x in item['price_relevance'] if item['stream'].endswith(x['spot_target']))
    print(json.dumps({'horizon':item['horizon_minutes'],'stream':item['stream'],
        'mse_skill':item['MSE_skill_vs_train_mean'],'std_ratio':item['forecast_std_over_actual_std'],
        'pred_price_IC':same['predicted_flow_vs_future_return']['pearson'],
        'oracle_price_IC':same['true_future_flow_oracle_vs_future_return']['pearson'],
        'innovation_price_IC':same['future_flow_prediction_residual_ORACLE_vs_future_return']['pearson']}))
