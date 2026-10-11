import importlib.util
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location('date_support',Path(__file__).with_name('audit.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_repeated_models_assets_and_zero_weight_loss_cannot_create_dates():
    rows=[dict(UTC_decision_date='2021-01-03',objective_weight=1,effective_data_loss=2.)]*15
    rows += [dict(UTC_decision_date='2021-01-04',objective_weight=0,effective_data_loss=2.),
             dict(UTC_decision_date='2021-01-05',objective_weight=1,effective_data_loss=0.)]
    assert m.unique_active_dates(rows)==['2021-01-03']


def test_prepared_calendar_retains_future_unknowns_and_is_never_called_actual_fit():
    d=np.arange(m.m.utc('2021-01-02'),m.m.utc('2022-12-01'),m.DAY_US,dtype=np.int64);n=len(d)
    v=dict(common_feature_known=np.ones(n,bool),label_complete=np.ones((n,3),bool),
        label_available_us=d+m.DAY_US+m.m.LATENCY_US,utility=np.zeros((n,3)))
    v['label_complete'][d==m.m.utc('2022-10-03'),1]=False
    source=dict(decision_us=d,baseline_ready=np.ones(n,bool),symbol_order=np.array(['BTCUSDT']))
    rows,arrays,result=m.prepare_support(source,v)
    assert result['prepared_complete_unique_train_dates']>=600 and result['actual_new_fit_dates']==0
    assert result['registered_old_UtilitySelector_fit_dates_if_reused']<600
    assert result['natural_full_development_calendar_dates']==61
    assert any(r['UTC_decision_date']=='2022-10-03' and not r['reward_complete'] for r in rows)
    assert all(not r['actual_model_fit'] and r['actual_loss_weight']==0 for r in rows)
    assert np.all(v['label_available_us'][arrays['prepared_train_indices']]<m.m.utc('2022-09-15'))
